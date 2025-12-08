import json
from typing import Dict, Optional

PROFILE_FIELDS = ("fitness_goals", "dietary_restrictions")


def _normalize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def format_profile_context(profile: Optional[Dict[str, Optional[str]]]) -> str:
    """Return a readable summary of the user's profile."""
    profile = profile or {}
    lines = ["User Profile Context"]
    for field in PROFILE_FIELDS:
        label = field.replace("_", " ").title()
        value = _normalize(profile.get(field)) or "Not provided"
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def parse_profile_update(raw_text: str) -> Dict[str, str]:
    """Parse JSON returned by the language model into cleaned profile fields."""
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {}

    updates: Dict[str, str] = {}
    for field in PROFILE_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str):
            continue
        cleaned = _normalize(value)
        if cleaned:
            updates[field] = cleaned
    return updates


def diff_profile(current: Optional[Dict[str, Optional[str]]], updates: Dict[str, str]) -> Dict[str, str]:
    """Return only the updates that differ from what is already stored."""
    current = current or {}
    diff: Dict[str, str] = {}
    for field, new_value in updates.items():
        existing = _normalize(current.get(field))
        if new_value != (existing or None):
            diff[field] = new_value
    return diff
