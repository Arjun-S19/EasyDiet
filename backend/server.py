import importlib
import os
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.generativeai import types as genai_types
from google.api_core import exceptions as gapi_exceptions
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.profile_utils import diff_profile, format_profile_context, parse_profile_update

jwt = importlib.import_module("jwt")
supabase_module = importlib.import_module("supabase")
create_client = getattr(supabase_module, "create_client")

BASE_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv()

# Support rotation: comma-separated list of keys
GEMINI_API_KEYS = [
    k.strip()
    for k in os.getenv("GEMINI_API_KEYS", "").split(",")
    if k.strip()
]

if not GEMINI_API_KEYS:
    raise RuntimeError("GEMINI_API_KEYS env var is required (comma-separated list)")

MODEL = os.getenv("MODEL_NAME", "gemini-2.5-flash")

_current_key_index = 0


def _configure_genai():
    """Configure google.generativeai with the current key."""
    genai.configure(api_key=GEMINI_API_KEYS[_current_key_index])


def _rotate_key():
    """Advance to the next key in GEMINI_API_KEYS (round-robin)."""
    global _current_key_index
    _current_key_index = (_current_key_index + 1) % len(GEMINI_API_KEYS)


# Configure once at startup
_configure_genai()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

with open("backend/system_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

PROFILE_EXTRACTION_PROMPT = """You receive the current nutrition profile and the user's latest message. If the message updates their fitness goals or dietary restrictions, return JSON with keys `fitness_goals` and `dietary_restrictions`. Use null when no change is present. Respond with JSON only."""

def profile_model() -> genai.GenerativeModel:
    return genai.GenerativeModel(
        MODEL,
        system_instruction=PROFILE_EXTRACTION_PROMPT,
    )

HTML_GENERATION_CONFIG = genai_types.GenerationConfig(response_mime_type="text/plain")

MAX_GEMINI_ATTEMPTS = len(GEMINI_API_KEYS) or 2
MAX_TURNS = 30  # keep newest 30 user+model pairs
ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")]


class ChatIn(BaseModel):
    message: str
    conversation_id: Optional[str] = None

      
class ChatOut(BaseModel):
    reply: str
    conversation_id: str
    model: str = MODEL

      
class ProfilePayload(BaseModel):
    fitness_goals: Optional[str] = None
    dietary_restrictions: Optional[str] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_current_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return payload["sub"]


def supabase_single(response) -> Optional[Dict[str, Any]]:
    error = getattr(response, "error", None)
    if error:
        raise HTTPException(status_code=500, detail=str(error))
    data = getattr(response, "data", None) or []
    if not data:
        return None
    return data[0]


def ensure_profile(user_id: str) -> Dict[str, Any]:
    response = supabase.table("user_profiles").select("*").eq("user_id", user_id).limit(1).execute()
    profile = supabase_single(response)
    if profile:
        return profile
    insert = supabase.table("user_profiles").insert({"user_id": user_id}).execute()
    created = supabase_single(insert)
    if not created:
        raise HTTPException(status_code=500, detail="Unable to create profile")
    return created


def update_profile(user_id: str, updates: Dict[str, str]) -> Dict[str, Any]:
    payload = {**updates, "updated_at": now_iso()}
    response = supabase.table("user_profiles").update(payload).eq("user_id", user_id).execute()
    updated = supabase_single(response)
    return updated or ensure_profile(user_id)


def list_conversations(user_id: str) -> List[Dict[str, Any]]:
    response = (
        supabase.table("conversations")
        .select("id,title,created_at,updated_at,last_message_preview")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    if getattr(response, "error", None):
        raise HTTPException(status_code=500, detail=str(response.error))
    return response.data or []


def create_conversation(user_id: str, title: Optional[str] = None) -> Dict[str, Any]:
    conversation_id = str(uuid.uuid4())
    payload = {
        "id": conversation_id,
        "user_id": user_id,
        "title": title or "New conversation",
        "last_message_preview": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    response = supabase.table("conversations").insert(payload).execute()
    created = supabase_single(response)
    if not created:
        raise HTTPException(status_code=500, detail="Unable to create conversation")
    return created


def ensure_conversation_owner(user_id: str, conversation_id: str) -> Dict[str, Any]:
    response = supabase.table("conversations").select("*").eq("id", conversation_id).limit(1).execute()
    conversation = supabase_single(response)
    if not conversation or conversation.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def delete_conversation(user_id: str, conversation_id: str) -> None:
    ensure_conversation_owner(user_id, conversation_id)
    response = supabase.table("messages").delete().eq("conversation_id", conversation_id).execute()
    if getattr(response, "error", None):
        raise HTTPException(status_code=500, detail=str(response.error))
    supabase.table("conversations").delete().eq("id", conversation_id).execute()


def fetch_history(conversation_id: str) -> List[Dict[str, Any]]:
    response = (
        supabase.table("messages")
        .select("role,content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(MAX_TURNS * 2)
        .execute()
    )
    if getattr(response, "error", None):
        raise HTTPException(status_code=500, detail=str(response.error))
    history = []
    rows = list((response.data or []))[::-1]
    for row in rows:
        role = row.get("role")
        if role not in ("user", "model"):
            continue
        history.append({"role": role, "parts": [row.get("content", "")]})
    return history


def insert_message(conversation_id: str, role: str, content: str, user_id: Optional[str]) -> None:
    payload = {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "created_at": now_iso(),
    }
    if user_id:
        payload["user_id"] = user_id
    response = supabase.table("messages").insert(payload).execute()
    if getattr(response, "error", None):
        raise HTTPException(status_code=500, detail=str(response.error))


def touch_conversation(conversation_id: str, preview: str) -> None:
    snippet = preview[:140]
    response = (
        supabase.table("conversations")
        .update({"last_message_preview": snippet, "updated_at": now_iso()})
        .eq("id", conversation_id)
        .execute()
    )
    if getattr(response, "error", None):
        raise HTTPException(status_code=500, detail=str(response.error))

def generate_chat_with_rotation(
    profile: Dict[str, Any],
    history,
):
    """
    Generate a chat response, load-balancing across keys and failing
    over to other keys on quota/auth errors.
    """
    last_exc = None
    n_keys = len(GEMINI_API_KEYS)
    attempts = 0

    while attempts < n_keys:
        attempts += 1

        # Configure client with the *current* key
        _configure_genai()

        try:
            chat_model = conversation_model(profile)
            response = chat_model.generate_content(
                history,
                generation_config=HTML_GENERATION_CONFIG,
            )
            # On success, advance so the NEXT request uses the next key
            _rotate_key()
            return response

        except (gapi_exceptions.ResourceExhausted, gapi_exceptions.PermissionDenied) as exc:
            # quota/auth error → move to the next key and retry
            last_exc = exc
            _rotate_key()
            continue

        except Exception as exc:
            # Non-retryable error: bail out
            last_exc = exc
            break

    # All keys failed
    raise last_exc or RuntimeError("Gemini generation failed with unknown error")


def detect_profile_updates_with_rotation(message: str, profile: Dict[str, Any]) -> Dict[str, str]:
    """
    Detect profile updates using Gemini, load-balancing across keys and
    failing over on quota/auth errors. On total failure, returns {}.
    """
    prompt = f"Current profile: {profile}\nUser message: {message}"
    last_exc = None
    n_keys = len(GEMINI_API_KEYS)
    attempts = 0

    while attempts < n_keys:
        attempts += 1

        _configure_genai()

        try:
            model = profile_model()
            response = model.generate_content(
                [{"role": "user", "parts": [prompt]}],
                generation_config=genai_types.GenerationConfig(
                    response_mime_type="application/json"
                ),
            )
            raw_text = response.text or ""
            parsed = parse_profile_update(raw_text)
            updates = diff_profile(profile, parsed)

            # success → advance pointer for next request
            _rotate_key()
            return updates

        except (gapi_exceptions.ResourceExhausted, gapi_exceptions.PermissionDenied) as exc:
            last_exc = exc
            _rotate_key()
            continue

        except Exception as exc:
            last_exc = exc
            break

    with suppress(Exception):
        print("Profile update detection failed for all keys:", last_exc)
    return {}


def conversation_model(profile: Dict[str, Any]) -> genai.GenerativeModel:
    system_instruction = f"{SYSTEM_PROMPT}\n\n{format_profile_context(profile)}"
    return genai.GenerativeModel(MODEL, system_instruction=system_instruction)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ALLOWED_ORIGINS == ["*"] else ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL}


@app.get("/api/profile", response_model=ProfilePayload)
def get_profile(user_id: str = Depends(get_current_user)):
    return ensure_profile(user_id)


@app.put("/api/profile", response_model=ProfilePayload)
def put_profile(payload: ProfilePayload, user_id: str = Depends(get_current_user)):
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if not updates:
        return ensure_profile(user_id)
    return update_profile(user_id, updates)


@app.get("/api/conversations")
def get_conversations(user_id: str = Depends(get_current_user)):
    return list_conversations(user_id)


@app.post("/api/conversations")
def post_conversation(body: ConversationCreate, user_id: str = Depends(get_current_user)):
    conversation = create_conversation(user_id, body.title)
    return conversation


@app.delete("/api/conversations/{conversation_id}")
def remove_conversation(conversation_id: str, user_id: str = Depends(get_current_user)):
    delete_conversation(user_id, conversation_id)
    return {"ok": True}


@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str, user_id: str = Depends(get_current_user)):
    ensure_conversation_owner(user_id, conversation_id)
    return fetch_history(conversation_id)


@app.post("/api/chat", response_model=ChatOut)
def chat(body: ChatIn, user_id: str = Depends(get_current_user)):
    if body.conversation_id:
        ensure_conversation_owner(user_id, body.conversation_id)
        conversation_id = body.conversation_id
    else:
        conversation = create_conversation(user_id)
        conversation_id = conversation["id"]

    insert_message(conversation_id, "user", body.message, user_id)
    touch_conversation(conversation_id, body.message)

    history = fetch_history(conversation_id)
    profile = ensure_profile(user_id)

    try:
        response = generate_chat_with_rotation(profile, history)
        reply = response.text or "(no response)"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gemini error: {exc}") from exc

    insert_message(conversation_id, "model", reply, user_id=None)
    touch_conversation(conversation_id, reply)

    updates = detect_profile_updates_with_rotation(body.message, profile)
    if updates:
        update_profile(user_id, updates)

    return ChatOut(reply=reply, conversation_id=conversation_id)
