"""Static marketplace registry loader."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PluginRegistryItem:
    """One marketplace registry item."""

    name: str
    kind: str
    description: str
    source: str


class PluginRegistry:
    """Read-only static registry; remote fetch is intentionally unsupported."""

    remote_fetch_enabled = False

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_registry_path()

    def list(self) -> list[PluginRegistryItem]:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        if not isinstance(items, list):
            raise ValueError("registry items must be a list")
        return [self._load_item(raw) for raw in items]

    def get(self, name: str) -> PluginRegistryItem:
        for item in self.list():
            if item.name == name:
                return item
        raise KeyError(name)

    def _load_item(self, raw: object) -> PluginRegistryItem:
        if not isinstance(raw, dict):
            raise ValueError("registry item must be an object")
        return PluginRegistryItem(
            name=str(raw["name"]),
            kind=str(raw["kind"]),
            description=str(raw.get("description", "")),
            source=str(raw.get("source", "")),
        )


def default_registry_path() -> Path:
    """Return repo-local marketplace registry path."""
    return Path(__file__).resolve().parents[4] / "docs" / "marketplace" / "registry.json"
