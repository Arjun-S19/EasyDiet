import pytest
from fastapi.testclient import TestClient

import backend.server as server


class DummyResponse:
    def __init__(self, text: str):
        self.text = text


@pytest.fixture
def client(monkeypatch):
    """
    Build a TestClient with:
    - fake auth (always 'test-user-id')
    - stubbed DB helpers (no Supabase calls)
    - stubbed Gemini helpers (no real API calls)
    """

    # ---- 1) Fake authentication ----
    # Override the dependency used by FastAPI, not the function itself.
    def fake_get_current_user():
        return "test-user-id"

    server.app.dependency_overrides[server.get_current_user] = fake_get_current_user

    # ---- 2) Stub DB helpers so Supabase is never touched ----
    # Very lightweight in-memory "DB"
    state = {
        "conversations": {},
        "messages": [],
        "profiles": {},
    }

    def fake_ensure_profile(user_id: str):
        profile = state["profiles"].get(user_id)
        if profile is None:
            profile = {"user_id": user_id, "fitness_goals": None, "dietary_restrictions": None}
            state["profiles"][user_id] = profile
        return profile

    def fake_update_profile(user_id: str, updates):
        profile = fake_ensure_profile(user_id)
        profile.update(updates)
        return profile

    def fake_create_conversation(user_id: str, title=None):
        conv_id = f"conv-{len(state['conversations']) + 1}"
        conversation = {
            "id": conv_id,
            "user_id": user_id,
            "title": title or "New conversation",
            "last_message_preview": None,
        }
        state["conversations"][conv_id] = conversation
        return conversation

    def fake_ensure_conversation_owner(user_id: str, conversation_id: str):
        conv = state["conversations"].get(conversation_id)
        if not conv or conv["user_id"] != user_id:
            # Mirror your real behavior: raise 404 via HTTPException
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv

    def fake_insert_message(conversation_id: str, role: str, content: str, user_id: str | None):
        state["messages"].append(
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "user_id": user_id,
            }
        )

    def fake_touch_conversation(conversation_id: str, preview: str):
        conv = state["conversations"].get(conversation_id)
        if conv:
            conv["last_message_preview"] = preview[:140]

    def fake_fetch_history(conversation_id: str):
        # Build minimal gemini-style history from stored messages
        history = []
        for msg in state["messages"]:
            if msg["conversation_id"] != conversation_id:
                continue
            if msg["role"] not in ("user", "model"):
                continue
            history.append({"role": msg["role"], "parts": [msg["content"]]})
        return history

    monkeypatch.setattr(server, "ensure_profile", fake_ensure_profile, raising=False)
    monkeypatch.setattr(server, "update_profile", fake_update_profile, raising=False)
    monkeypatch.setattr(server, "create_conversation", fake_create_conversation, raising=False)
    monkeypatch.setattr(server, "ensure_conversation_owner", fake_ensure_conversation_owner, raising=False)
    monkeypatch.setattr(server, "insert_message", fake_insert_message, raising=False)
    monkeypatch.setattr(server, "touch_conversation", fake_touch_conversation, raising=False)
    monkeypatch.setattr(server, "fetch_history", fake_fetch_history, raising=False)

    # ---- 3) Stub Gemini helpers (no actual network) ----
    def fake_generate_chat_with_rotation(profile, history):
        # You can assert on profile/history here if you want tighter checks
        return DummyResponse("stubbed model reply")

    def fake_detect_profile_updates_with_rotation(message, profile):
        # Return fake updates if you want to assert they’re written
        return {"fitness_goals": "gain muscle"} if "bulk" in message.lower() else {}

    monkeypatch.setattr(
        server,
        "generate_chat_with_rotation",
        fake_generate_chat_with_rotation,
        raising=False,
    )
    monkeypatch.setattr(
        server,
        "detect_profile_updates_with_rotation",
        fake_detect_profile_updates_with_rotation,
        raising=False,
    )

    return TestClient(server.app)


def test_chat_creates_conversation_and_returns_reply(client):
    """
    Basic integration test: POST /api/chat with no conversation_id
    should:
      - create a new conversation
      - call the stubbed Gemini helper
      - return the stubbed reply
    """
    headers = {"Authorization": "Bearer dummy-token"}
    payload = {"message": "Hello bot!"}

    res = client.post("/api/chat", json=payload, headers=headers)
    assert res.status_code == 200

    data = res.json()
    assert "conversation_id" in data
    assert data["reply"] == "stubbed model reply"
    assert data["model"] == server.MODEL

    conv_id = data["conversation_id"]

    # Verify that the conversation exists and has messages when we query messages endpoint
    res_msgs = client.get(f"/api/conversations/{conv_id}/messages", headers=headers)
    assert res_msgs.status_code == 200
    messages = res_msgs.json()
    # Messages history is coming from our fake_fetch_history
    # For this run, we expect at least one user message and one model message
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "model" in roles


def test_chat_uses_existing_conversation_and_updates_profile(client):
    """
    Second call using the same conversation_id should:
      - not create a new conversation
      - still return stubbed reply
      - apply profile updates from detect_profile_updates_with_rotation
    """
    headers = {"Authorization": "Bearer dummy-token"}

    # First call to create a conversation
    res1 = client.post("/api/chat", json={"message": "Hello first"}, headers=headers)
    assert res1.status_code == 200
    conv_id = res1.json()["conversation_id"]

    # Second call with a "bulk" message to trigger fake profile update
    res2 = client.post(
        "/api/chat",
        json={"message": "I want to bulk up", "conversation_id": conv_id},
        headers=headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conversation_id"] == conv_id
    assert data2["reply"] == "stubbed model reply"

    # Check that /api/profile reflects our fake profile update
    res_profile = client.get("/api/profile", headers=headers)
    assert res_profile.status_code == 200
    profile = res_profile.json()
    assert profile["fitness_goals"] == "gain muscle"
