from backend.profile_utils import format_profile_context, parse_profile_update, diff_profile


def test_format_profile_context_defaults():
    result = format_profile_context(None)
    assert "User Profile Context" in result
    assert "Not provided" in result


def test_parse_profile_update_valid_json():
    updates = parse_profile_update('{"fitness_goals": "Lose fat ", "dietary_restrictions": "vegan"}')
    assert updates == {"fitness_goals": "Lose fat", "dietary_restrictions": "vegan"}


def test_parse_profile_update_invalid_json():
    assert parse_profile_update("not json") == {}


def test_diff_profile_only_changes():
    current = {"fitness_goals": "Maintain weight", "dietary_restrictions": None}
    updates = {"fitness_goals": "Gain muscle", "dietary_restrictions": "dairy-free"}
    diff = diff_profile(current, updates)
    assert diff == updates


def test_diff_profile_ignores_same_values():
    current = {"fitness_goals": "Maintain", "dietary_restrictions": "vegan"}
    updates = {"fitness_goals": "Maintain", "dietary_restrictions": "vegan"}
    assert diff_profile(current, updates) == {}
