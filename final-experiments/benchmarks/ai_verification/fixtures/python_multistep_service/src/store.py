from __future__ import annotations

_records: dict[str, list[str]] = {}


def save(key: str, values: list[str]) -> None:
    _records[key] = values


def load(key: str) -> list[str] | None:
    return _records.get(key)


def all_keys() -> list[str]:
    return list(_records.keys())


def clear() -> None:
    _records.clear()
