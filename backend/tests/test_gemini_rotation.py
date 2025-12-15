import pytest

import backend.server as server
from google.api_core import exceptions as gapi_exceptions


class DummyResponse:
    def __init__(self, text: str):
        self.text = text


@pytest.fixture(autouse=True)
def reset_keys(monkeypatch):
    """
    Ensure each test starts with a clean, predictable rotation state.
    """
    # Use two fake keys so we can test rotation.
    monkeypatch.setattr(server, "GEMINI_API_KEYS", ["KEY_1", "KEY_2"], raising=False)
    monkeypatch.setattr(server, "_current_key_index", 0, raising=False)
    monkeypatch.setattr(server, "MAX_GEMINI_ATTEMPTS", len(server.GEMINI_API_KEYS), raising=False)

    # Don't actually configure the real client during tests.
    monkeypatch.setattr(server, "_configure_genai", lambda: None, raising=False)

    yield

    # (No teardown needed; pytest will reload fixtures per test)


def _setup_fake_conversation_model(monkeypatch, behaviors):
    """
    Patch server.conversation_model so each call returns a FakeModel whose
    generate_content method follows the sequence of 'behaviors'.

    behaviors: list of callables taking (call_index: int) and either:
      - return DummyResponse(text)
      - or raise an exception (e.g., gapi_exceptions.ResourceExhausted)
    """
    call_counter = {"n": 0}
    rotate_calls = []

    def fake_rotate():
        rotate_calls.append("rotated")

    def fake_conversation_model(profile):
        class FakeModel:
            def generate_content(self, history, generation_config=None):
                call_counter["n"] += 1
                idx = call_counter["n"]
                # If we run out of behaviors, just use the last one.
                behavior = behaviors[min(idx, len(behaviors)) - 1]
                return behavior(idx)

        return FakeModel()

    monkeypatch.setattr(server, "_rotate_key", fake_rotate, raising=False)
    monkeypatch.setattr(server, "conversation_model", fake_conversation_model, raising=False)

    return call_counter, rotate_calls


def _setup_fake_profile_model(monkeypatch, behaviors):
    """
    Similar helper for detect_profile_updates_with_rotation.
    Patches server.profile_model to use the given behavior sequence.
    """
    call_counter = {"n": 0}
    rotate_calls = []

    def fake_rotate():
        rotate_calls.append("rotated")

    def fake_profile_model():
        class FakeModel:
            def generate_content(self, history, generation_config=None):
                call_counter["n"] += 1
                idx = call_counter["n"]
                behavior = behaviors[min(idx, len(behaviors)) - 1]
                return behavior(idx)

        return FakeModel()

    monkeypatch.setattr(server, "_rotate_key", fake_rotate, raising=False)
    monkeypatch.setattr(server, "profile_model", fake_profile_model, raising=False)

    return call_counter, rotate_calls


def test_chat_success_no_rotation(monkeypatch):
    """
    If the first key works, we should not rotate and we should get the reply.
    """
    def behavior_success(_i):
        return DummyResponse("ok")

    call_counter, rotate_calls = _setup_fake_conversation_model(monkeypatch, [behavior_success])

    profile = {}
    history = []

    response = server.generate_chat_with_rotation(profile, history)

    assert isinstance(response, DummyResponse)
    assert response.text == "ok"
    assert call_counter["n"] == 1
    assert len(rotate_calls) == 0  # no rotation


def test_chat_rotate_then_succeed(monkeypatch):
    """
    If the first key hits quota/permission error, we rotate to the next key and succeed.
    """
    def behavior_fail_first(call_index):
        # first call: quota exceeded
        if call_index == 1:
            raise gapi_exceptions.ResourceExhausted("quota exceeded")
        return DummyResponse("ok after rotate")

    call_counter, rotate_calls = _setup_fake_conversation_model(monkeypatch, [behavior_fail_first])

    profile = {}
    history = []

    response = server.generate_chat_with_rotation(profile, history)

    assert isinstance(response, DummyResponse)
    assert response.text == "ok after rotate"
    # We should have tried twice: fail (key1) then success (key2)
    assert call_counter["n"] == 2
    # Rotation should have been called exactly once (after first failure)
    assert len(rotate_calls) == 1


def test_chat_all_keys_fail(monkeypatch):
    """
    If all keys hit quota/permission errors, the helper should raise.
    """
    def behavior_always_fail(_i):
        raise gapi_exceptions.ResourceExhausted("quota exceeded")

    call_counter, rotate_calls = _setup_fake_conversation_model(
        monkeypatch,
        [behavior_always_fail],
    )

    profile = {}
    history = []

    with pytest.raises(gapi_exceptions.ResourceExhausted):
        server.generate_chat_with_rotation(profile, history)

    # Should attempt once per key
    assert call_counter["n"] == len(server.GEMINI_API_KEYS)
    # And rotate after each failed attempt
    assert len(rotate_calls) == len(server.GEMINI_API_KEYS)


def test_profile_updates_rotate_then_succeed(monkeypatch):
    """
    detect_profile_updates_with_rotation should rotate on error and then return diffs.
    """
    # Fake parsed profile update returned from parse_profile_update
    parsed_profile = {"fitness_goals": "new goal"}

    # Patch parse_profile_update & diff_profile to be deterministic
    monkeypatch.setattr(server, "parse_profile_update", lambda raw: parsed_profile, raising=False)
    monkeypatch.setattr(
        server,
        "diff_profile",
        lambda current, parsed: {k: v for k, v in parsed.items() if current.get(k) != v},
        raising=False,
    )

    def behavior_fail_then_json(call_index):
        if call_index == 1:
            raise gapi_exceptions.PermissionDenied("bad key")
        # On success, return some JSON-ish text; our patched parse_profile_update ignores it anyway.
        return DummyResponse('{"fitness_goals": "new goal"}')

    call_counter, rotate_calls = _setup_fake_profile_model(monkeypatch, [behavior_fail_then_json])

    current_profile = {"fitness_goals": "old goal"}

    updates = server.detect_profile_updates_with_rotation("I want to bulk", current_profile)

    assert updates == {"fitness_goals": "new goal"}
    assert call_counter["n"] == 2
    assert len(rotate_calls) == 1


def test_profile_updates_all_fail_returns_empty(monkeypatch):
    """
    If profile extraction fails for all keys, it should NOT raise; it should return {}.
    """
    monkeypatch.setattr(server, "parse_profile_update", lambda raw: {}, raising=False)
    monkeypatch.setattr(
        server,
        "diff_profile",
        lambda current, parsed: {},
        raising=False,
    )

    def behavior_always_fail(_i):
        raise gapi_exceptions.ResourceExhausted("quota exceeded")

    call_counter, rotate_calls = _setup_fake_profile_model(monkeypatch, [behavior_always_fail])

    current_profile = {"fitness_goals": "old goal"}

    updates = server.detect_profile_updates_with_rotation("anything", current_profile)

    # No updates if everything fails
    assert updates == {}
    assert call_counter["n"] == len(server.GEMINI_API_KEYS)
    assert len(rotate_calls) == len(server.GEMINI_API_KEYS)
