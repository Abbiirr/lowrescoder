"""The copycat capability model + a ``--help`` surface parser (PLAN_05 §2.3).

A :class:`Capability` is one observable unit of a target's structure — a flag, a
subcommand, an output format. A :class:`Census` is the full set for one target,
serialized to ``anvil/copycat/census/<target>.yaml``.

The parser is deliberately *structural only*: it reads what ``--help`` makes
public. It never inspects a target's source, traces, or internals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Matches both clap/commander `(choices: ...)` and yargs `[choices: ...]`.
_CHOICES_RE = re.compile(r"choices:\s*([^)\]]*)[)\]]")
_QUOTED_RE = re.compile(r'"([^"]*)"')
# A help row splits flags/name from description on a run of >= 2 spaces.
_ROW_SPLIT_RE = re.compile(r"\s{2,}")


@dataclass(frozen=True)
class Capability:
    """One observable capability of a target (a flag, subcommand, etc.)."""

    id: str
    kind: str
    surface: tuple[str, ...] = ()
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "surface": list(self.surface),
            "description": self.description,
        }
        if self.metadata:
            d["metadata"] = dict(self.metadata)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Capability:
        return cls(
            id=str(d["id"]),
            kind=str(d.get("kind", "")),
            surface=tuple(d.get("surface", []) or []),
            description=str(d.get("description", "")),
            metadata=dict(d.get("metadata", {}) or {}),
        )


@dataclass(frozen=True)
class Census:
    """The full observable capability set for one target."""

    target: str
    source: str
    capabilities: tuple[Capability, ...] = ()
    target_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "target_version": self.target_version,
            "source": self.source,
            "capabilities": [c.to_dict() for c in self.capabilities],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Census:
        caps = tuple(Capability.from_dict(c) for c in d.get("capabilities", []) or [])
        return cls(
            target=str(d.get("target", "")),
            source=str(d.get("source", "")),
            capabilities=caps,
            target_version=str(d.get("target_version", "")),
        )

    def write_yaml(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return p

    @classmethod
    def read_yaml(cls, path: str | Path) -> Census:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)


def _normalize_flag_id(tokens: list[str]) -> str:
    """Canonical id from a flag's tokens: longest ``--long`` name wins."""
    longs = [t for t in tokens if t.startswith("--")]
    chosen = max(longs, key=len) if longs else tokens[0]
    return "flag:" + chosen.lstrip("-")


def _parse_choices(description: str) -> list[str]:
    m = _CHOICES_RE.search(description)
    if not m:
        return []
    return _QUOTED_RE.findall(m.group(1))


def _parse_option_row(flags_part: str, description: str) -> Capability | None:
    """Parse one ``Options:`` row, e.g. ``-c, --continue`` / ``--x <v>``."""
    tokens: list[str] = []
    takes_value = False
    for chunk in flags_part.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Strip a trailing value placeholder: ``--out <file>`` / ``--debug [filter]``.
        m = re.match(r"^(--?[A-Za-z0-9][A-Za-z0-9-]*)(?:[ =]+[<\[].*)?$", chunk)
        if not m:
            continue
        if "<" in chunk or "[" in chunk:
            takes_value = True
        tokens.append(m.group(1))
    if not tokens:
        return None
    metadata: dict[str, Any] = {"takes_value": takes_value}
    choices = _parse_choices(description)
    if choices:
        metadata["choices"] = choices
    return Capability(
        id=_normalize_flag_id(tokens),
        kind="flag",
        surface=tuple(tokens),
        description=description.strip(),
        metadata=metadata,
    )


def _parse_command_row(name_part: str, description: str) -> Capability | None:
    """Parse one ``Commands:`` row, e.g. ``plugin|plugins [options]``."""
    head = name_part.strip().split()[0] if name_part.strip() else ""
    if not head:
        return None
    names = head.split("|")
    primary = names[0]
    if not re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", primary):
        return None
    metadata: dict[str, Any] = {}
    if len(names) > 1:
        metadata["aliases"] = names[1:]
    return Capability(
        id="cmd:" + primary,
        kind="subcommand",
        surface=(primary,),
        description=description.strip(),
        metadata=metadata,
    )


def parse_help_text(text: str) -> list[Capability]:
    """Parse a ``--help`` blob into a normalized capability list.

    Recognizes the conventional ``Options:`` and ``Commands:`` sections used by
    commander/click/typer-style CLIs. ``Usage:``/``Arguments:`` noise is ignored.
    """
    caps: list[Capability] = []
    seen: set[str] = set()
    section: str | None = None
    # The column the first command in a section starts at — rows indented deeper
    # are wrapped-description continuation lines, not commands (clap/commander).
    command_indent: int | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        header = stripped.rstrip(":").lower()
        if not line[0].isspace() and header in {"options", "commands", "arguments", "usage"}:
            section = header
            command_indent = None
            continue
        # Section bodies are indented; a non-indented line ends the section.
        if not line[0].isspace():
            section = None
            continue
        if section not in {"options", "commands"}:
            continue

        indent = len(line) - len(line.lstrip())
        parts = _ROW_SPLIT_RE.split(stripped, maxsplit=1)
        left = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else ""

        cap: Capability | None
        if section == "options":
            if not left.startswith("-"):
                continue
            cap = _parse_option_row(left, desc)
        else:
            # First command establishes the command column; deeper rows are
            # wrapped descriptions and are skipped.
            if command_indent is None:
                command_indent = indent
            elif indent > command_indent:
                continue
            cap = _parse_command_row(left, desc)

        if cap is not None and cap.id not in seen:
            seen.add(cap.id)
            caps.append(cap)
    return caps
