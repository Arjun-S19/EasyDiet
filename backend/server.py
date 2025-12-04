import os, uuid, sqlite3, time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.getenv("MODEL_NAME", "gemini-2.5-flash")

SYSTEM_PROMPT = (
    "You are EasyDiet's nutrition assistant. Be practical, concise, and friendly. "
    "Avoid medical claims; suggest general, safe guidance."
    "If the user asks something off topic, respond by saying 'I'm here to help with nutrition-related questions.'"
)

# Create model with system instruction
model = genai.GenerativeModel(
    MODEL,
    system_instruction=SYSTEM_PROMPT,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "chat.db")
MAX_TURNS = 30  # keep newest 30 user+model pairs

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
              conv_id TEXT NOT NULL,
              role    TEXT NOT NULL,   -- 'user' | 'model'
              text    TEXT NOT NULL,
              ts      INTEGER NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_conv_ts ON messages(conv_id, ts);")
        # Clean up any older 'system' rows from previous runs
        conn.execute("DELETE FROM messages WHERE role NOT IN ('user','model');")

def get_history(conv_id: str) -> List[Dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT role, text FROM messages WHERE conv_id=? ORDER BY ts ASC", (conv_id,)
        ).fetchall()
    # Only keep valid roles (belt & suspenders)
    history = [{"role": r, "parts": [t]} for (r, t) in rows if r in ("user","model")]
    return history

def append_message(conv_id: str, role: str, text: str):
    if role not in ("user","model"):
        return
    with db() as conn:
        conn.execute(
            "INSERT INTO messages (conv_id, role, text, ts) VALUES (?,?,?,?)",
            (conv_id, role, text, int(time.time()*1000)),
        )

def trim_turns(conv_id: str):
    # Keep newest MAX_TURNS pairs (2 rows per turn)
    with db() as conn:
        rows = conn.execute(
            "SELECT rowid, role FROM messages WHERE conv_id=? ORDER BY ts ASC", (conv_id,)
        ).fetchall()
        others = [(rowid, role) for (rowid, role) in rows if role in ("user","model")]
        overflow = max(0, len(others) - MAX_TURNS * 2)
        to_delete = [rowid for (rowid, _) in others[:overflow]]
        if to_delete:
            qmarks = ",".join("?"*len(to_delete))
            conn.execute(f"DELETE FROM messages WHERE rowid IN ({qmarks})", to_delete)

class ChatIn(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatOut(BaseModel):
    reply: str
    conversation_id: str
    model: str = MODEL

app = FastAPI()
init_db()

@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL}

@app.get("/api/history/{conv_id}")
def history(conv_id: str):
    return get_history(conv_id)

@app.post("/api/chat", response_model=ChatOut)
def chat(body: ChatIn):
    conv_id = body.conversation_id or str(uuid.uuid4())
    # Save user turn
    append_message(conv_id, "user", body.message)
    trim_turns(conv_id)

    # Get full history
    messages = get_history(conv_id)

    try:
        resp = model.generate_content(messages)
        text = resp.text or "(no response)"
    except Exception as e:
        raise HTTPException(500, f"Gemini error: {e}")

    append_message(conv_id, "model", text)
    return ChatOut(reply=text, conversation_id=conv_id)
