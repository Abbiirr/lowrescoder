from models import UserProfile
from service import normalize_payload, serialize_profile


def test_serialize_profile_uses_display_name():
    profile = UserProfile(user_id=7, display_name="Ada", email="ADA@example.com")
    assert serialize_profile(profile) == {
        "id": 7,
        "display_name": "Ada",
        "email": "ada@example.com",
    }


def test_normalize_payload_accepts_legacy_name_key():
    payload = {"id": 3, "name": "  Grace Hopper ", "email": "Grace@Example.com"}
    assert normalize_payload(payload) == {
        "id": 3,
        "display_name": "Grace Hopper",
        "email": "grace@example.com",
    }


def test_normalize_payload_accepts_new_display_name_key():
    payload = {"id": 4, "display_name": "Linus", "email": "Linus@Example.com"}
    assert normalize_payload(payload) == {
        "id": 4,
        "display_name": "Linus",
        "email": "linus@example.com",
    }
