"""Data models after a half-applied rename from name to display_name."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UserProfile:
    user_id: int
    display_name: str
    email: str
