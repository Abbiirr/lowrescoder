"""Broken service layer after a partial refactor."""

from __future__ import annotations

from models import UserProfile


def normalize_payload(payload: dict[str, object]) -> dict[str, object]:
    """Normalize a profile payload.

    Broken on purpose: only accepts the new key and drops backward compatibility.
    """
    return {
        "id": int(payload["id"]),
        "display_name": str(payload["display_name"]).strip(),
        "email": str(payload["email"]).lower(),
    }


def serialize_profile(profile: UserProfile) -> dict[str, object]:
    """Serialize a profile for API responses.

    Broken on purpose: still uses the old attribute name.
    """
    return {
        "id": profile.user_id,
        "display_name": profile.name,
        "email": profile.email.lower(),
    }
