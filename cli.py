import os, json
from pathlib import Path
import requests

API_BASE = os.environ.get("EASYDIET_API_BASE", "http://localhost:8000")
STATE_FILE = Path(".chat_state.json")

def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except: pass
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")

def send_chat(message, cid=None):
    body = {"message": message}
    if cid: body["conversation_id"] = cid
    r = requests.post(f"{API_BASE}/api/chat", json=body, timeout=120)
    r.raise_for_status()
    return r.json()

def show_history(cid):
    r = requests.get(f"{API_BASE}/api/history/{cid}", timeout=30)
    r.raise_for_status()
    for turn in r.json():
        print(f"[{turn['role']}] {turn['parts'][0]}")
        print()

def main():
    print(f"EasyDiet Console Chat  (API={API_BASE})")
    print("Commands: /new  /history  /exit")
    state = load_state()
    cid = state.get("conversation_id")

    while True:
        try:
            msg = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        
        if not msg: continue
        if msg == "/exit": break
        if msg == "/new":
            cid = None; state["conversation_id"] = None; save_state(state)
            print("(new conversation)\n"); continue
        if msg == "/history":
            if cid: show_history(cid)
            else: print("(no conversation yet)\n")
            continue

        try:
            data = send_chat(msg, cid)
            cid = data["conversation_id"]
            state["conversation_id"] = cid; save_state(state)
            print("AI:", data["reply"])
            print()
        except requests.HTTPError as e:
            print("HTTP error:", e.response.text)
        except Exception as e:
            print("Error:", str(e))

if __name__ == "__main__":
    main()
