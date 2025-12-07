---

# EasyDiet — Conversational Gemini (Server + Console Client)

This project provides:

* a **FastAPI server** (`backend/server.py`) that talks to **Google Gemini** and **persists chat history** in SQLite, and
* a **console client** (`cli.py`) that chats with the server and remembers your conversation across runs.

> Works on Windows, macOS, and Linux. Python 3.9+ recommended.

---

## 0) Prerequisites

* **Python** 3.9 or newer (check with `python --version`)
* (Optional) **Node.js** if you also plan to hook up a React frontend later
* A **Gemini API Key** from Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

## 1) First-time Setup

Unzip the repo so you have a structure like:

```
/ (project root)
├─ backend/
│  ├─ server.py
│  ├─ requirements.txt
│  └─ .env            # you'll create this
└─ cli.py
```

Create `backend/.env` and add:

```
GEMINI_API_KEY=YOUR_KEY_HERE
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
MODEL_NAME=gemini-2.5-flash
```

> Keep this file private. Do **not** commit your key.

---

## 2) Create & Activate a Virtual Environment

### Windows (PowerShell)

```powershell
# From project root
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\.venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
# From project root
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3) Install Server Dependencies

```bash
# From project root, with venv active
pip install -r backend/requirements.txt
```

> What’s inside:
>
> * `fastapi` (web API), `uvicorn` (server),
> * `google-generativeai` (Gemini SDK),
> * `python-dotenv` (loads `.env`), `pydantic` (request/response models).

---

## 4) Run the Server

### From project root (module path)

```bash
# venv active
python -m uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
```

Health check:

* Open a browser to `http://localhost:8000/api/health`
  You should see JSON like: `{ "ok": true, "model": "gemini-2.5-flash" }`.

---

## 5) Quick Test (no client yet)

### Windows (PowerShell)

```powershell
$body = @{ message = "Say hi in five words." } | ConvertTo-Json
Invoke-WebRequest -Uri http://localhost:8000/api/chat -Method POST -Body $body -ContentType "application/json"
```

### macOS / Linux (curl)

```bash
curl -s http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Say hi in five words."}'
```

The response includes a `conversation_id`. Reuse that ID in the next call to keep context.

---

## 6) Run the Console Client

The console client talks to the server and **remembers the conversation across runs** using `.chat_state.json` in the project root.

```bash
# From project root (venv active)
pip install requests
python cli.py
```

You’ll see a prompt:

```
EasyDiet Console Chat (API=http://localhost:8000)
Commands: /new  /history  /exit
> 
```

* Type any message and press Enter.
* `/history` prints the stored turns for the current conversation.
* `/new` starts a fresh conversation (gets a new `conversation_id`).
* `/exit` quits.

> To point the client to a different server URL, set `EASYDIET_API_BASE`.
> Windows PowerShell:
> `$env:EASYDIET_API_BASE = "http://127.0.0.1:8000" ; python cli.py`
> macOS/Linux:
> `EASYDIET_API_BASE="http://127.0.0.1:8000" python cli.py`

---

## 7) Files You’ll See During Use

* **backend/chat.db** — SQLite database storing conversation turns:

  ```
  conv_id | role ('user'/'model') | text | ts(ms)
  ```
* **backend/chat.db-wal** and **backend/chat.db-shm** — SQLite **W**rite-**A**head **L**og and shared memory files (normal when WAL mode is enabled; improves reliability).
* **.chat_state.json** — tiny state file used by `cli.py` to remember your current `conversation_id`.

To **hard reset** everything:

1. Stop the server
2. Delete `backend/chat.db`, `backend/chat.db-wal`, `backend/chat.db-shm`, and `.chat_state.json`
3. Start the server again

---

## 8) Troubleshooting

* **“Can’t activate venv” on Windows:**
  Run PowerShell as your normal user and do:
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force`
  then `.\.venv\Scripts\Activate.ps1`

* **`uvicorn` not found:**
  Make sure the venv is active, or run via module:
  `python -m uvicorn backend.server:app --reload --port 8000`

* **Gemini error / model not found:**
  Update the SDK: `pip install --upgrade google-generativeai`
  Ensure `MODEL_NAME=gemini-2.5-flash` (or another supported model) in `backend/.env`.

* **CORS in a browser:**
  If you later add a web frontend, add its origin(s) to `ALLOWED_ORIGINS` in `server.py` (or env) and restart.

---

## 9) How It Works (short version you can say in a meeting)

* **Server** persists all chat turns in **SQLite** (`chat.db`).
* On each request, it **rebuilds the history** for that `conversation_id`, calls Gemini’s `generate_content`, stores the reply, and returns it.
* A global style is set via **`system_instruction`** on the model (no `system` role in messages).
* **Console client** saves `conversation_id` in `.chat_state.json` so chats continue across runs.

---

## 10) Optional: Handy Commands

**Windows (PowerShell) quick tests**

```powershell
# Start a convo
$resp1 = Invoke-WebRequest -Uri http://localhost:8000/api/chat -Method POST `
  -Body (@{message="My name is Alex."} | ConvertTo-Json) -ContentType "application/json"
$cid = ($resp1.Content | ConvertFrom-Json).conversation_id

# Follow-up with same id
Invoke-WebRequest -Uri http://localhost:8000/api/chat -Method POST `
  -Body (@{message="What is my name?"; conversation_id=$cid} | ConvertTo-Json) `
  -ContentType "application/json"

# See persisted history
Invoke-WebRequest http://localhost:8000/api/history/$cid
```

---

## License

For class/demo use.

---
