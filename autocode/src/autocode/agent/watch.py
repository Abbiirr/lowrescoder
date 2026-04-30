"""Watch-mode marker parsing and lightweight state."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_AUTOCODE_MARKER = re.compile(r"^\s*#\s*AUTOCODE:\s*(?P<instruction>.+?)\s*$")


def parse_watch_markers(path: Path) -> list[str]:
    """Extract `# AUTOCODE: <instruction>` markers from a saved file."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    markers: list[str] = []
    for line in lines:
        match = _AUTOCODE_MARKER.match(line)
        if match:
            markers.append(match.group("instruction").strip())
    return markers


@dataclass
class WatchMode:
    """Minimal watch-mode state holder used by command/frontends."""

    enabled: bool = False

    def status(self) -> str:
        return "enabled" if self.enabled else "disabled"
