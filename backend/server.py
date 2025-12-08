import importlib
import os
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.generativeai import types as genai_types
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
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.getenv("MODEL_NAME", "gemini-2.5-flash")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

with open("backend/system_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

PROFILE_EXTRACTION_PROMPT = """You receive the current nutrition profile and the user's latest message. If the message updates their fitness goals or dietary restrictions, return JSON with keys `fitness_goals` and `dietary_restrictions`. Use null when no change is present. Respond with JSON only."""
PROFILE_MODEL = genai.GenerativeModel(
    MODEL,
    system_instruction=PROFILE_EXTRACTION_PROMPT,
)

HTML_GENERATION_CONFIG = genai_types.GenerationConfig(response_mime_type="text/plain")

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


def detect_profile_updates(message: str, profile: Dict[str, Any]) -> Dict[str, str]:
    prompt = f"Current profile: {profile}\nUser message: {message}"
    with suppress(Exception):
        response = PROFILE_MODEL.generate_content(
            [{"role": "user", "parts": [prompt]}],
            generation_config=genai_types.GenerationConfig(response_mime_type="application/json"),
        )
        raw_text = response.text or ""
        parsed = parse_profile_update(raw_text)
        return diff_profile(profile, parsed)
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
    chat_model = conversation_model(profile)

    try:
        response = chat_model.generate_content(history, generation_config=HTML_GENERATION_CONFIG)
        reply = response.text or "(no response)"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gemini error: {exc}") from exc

    insert_message(conversation_id, "model", reply, user_id=None)
    touch_conversation(conversation_id, reply)

    updates = detect_profile_updates(body.message, profile)
    if updates:
        update_profile(user_id, updates)

    return ChatOut(reply=reply, conversation_id=conversation_id)
