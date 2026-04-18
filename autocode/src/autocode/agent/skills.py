"""SkillCatalog with progressive disclosure.

Discovers Claude-Code-style skills from project and user directories, exposes
a cheap catalog of frontmatter-only entries for the system prompt, and lazily
loads the full SKILL.md body on demand. Live reload via mtime check.

Supported frontmatter fields (YAML between ``---`` fences at top of file):

- ``name`` (required) — skill identifier
- ``description`` — one-line summary for the catalog
- ``allowed-tools`` — list, either YAML flow (`[Read, Grep]`) or inline
- ``disable-model-invocation`` — bool; if true, hide from the model-visible
  catalog (skill remains usable programmatically)

Discovery order on name conflict: project scope wins over user scope. Both
locations are walked once per ``scan()`` call; scans are cheap (frontmatter
only, no body reads).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SkillSource(StrEnum):
    """Which scope a skill was discovered in."""

    PROJECT = "project"
    USER = "user"


@dataclass(frozen=True)
class SkillCatalogEntry:
    """One catalog entry — frontmatter only, no body."""

    name: str
    description: str
    path: Path
    source: SkillSource
    mtime: float
    allowed_tools: list[str] | None = None
    disable_model_invocation: bool = False


@dataclass
class _BodyCacheEntry:
    body: str = ""
    mtime: float = 0.0


class SkillCatalog:
    """Scan + progressive-disclosure loader for Claude-Code-style skills."""

    _FRONTMATTER_FENCE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
    _LIST_INLINE = re.compile(r"\[(.*?)\]")

    def __init__(
        self,
        project_root: Path | str,
        user_skills_dir: Path | str | None,
    ) -> None:
        self._project_skills_dir = Path(project_root) / ".claude" / "skills"
        self._user_skills_dir = (
            Path(user_skills_dir) if user_skills_dir is not None else None
        )
        # Map name -> entry for body lookup
        self._entries: dict[str, SkillCatalogEntry] = {}
        self._body_cache: dict[str, _BodyCacheEntry] = {}

    # ----- public API -----

    def scan(self) -> list[SkillCatalogEntry]:
        """Discover skills and return the current catalog.

        Frontmatter-only — does not load any body bytes. Subsequent
        ``load_body(name)`` calls read lazily.
        """
        found: dict[str, SkillCatalogEntry] = {}

        # User scope first; project scope overrides on collision.
        if self._user_skills_dir is not None:
            for entry in self._scan_dir(self._user_skills_dir, SkillSource.USER):
                found[entry.name] = entry

        for entry in self._scan_dir(self._project_skills_dir, SkillSource.PROJECT):
            found[entry.name] = entry  # project wins

        self._entries = found
        return list(found.values())

    def load_body(self, name: str) -> str:
        """Return the SKILL.md body for ``name`` (cached).

        Missing skill names return an empty string so callers can treat
        catalog misses gracefully.
        """
        entry = self._entries.get(name)
        if entry is None:
            # Re-scan in case the entry was just added
            self.scan()
            entry = self._entries.get(name)
        if entry is None:
            return ""

        cache = self._body_cache.get(name)
        if cache is not None and cache.mtime == entry.mtime:
            return cache.body

        body = self._read_body(entry.path)
        self._body_cache[name] = _BodyCacheEntry(body=body, mtime=entry.mtime)
        return body

    def reload_if_changed(self, name: str) -> bool:
        """Return True if the skill file's mtime has advanced.

        Also invalidates the cached body so the next ``load_body`` reads fresh.
        Does NOT rescan the full directory.
        """
        entry = self._entries.get(name)
        if entry is None:
            return False
        try:
            current_mtime = entry.path.stat().st_mtime
        except OSError:
            return False
        if current_mtime == entry.mtime:
            return False
        updated = self._scan_single(entry.path, entry.source)
        if updated is None:
            return False
        self._entries[name] = updated
        self._body_cache.pop(name, None)
        return True

    # ----- private helpers -----

    def _scan_dir(self, directory: Path, source: SkillSource) -> list[SkillCatalogEntry]:
        if not directory.is_dir():
            return []
        out: list[SkillCatalogEntry] = []
        for skill_dir in sorted(directory.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            entry = self._scan_single(skill_file, source)
            if entry is not None:
                out.append(entry)
        return out

    def _scan_single(self, skill_file: Path, source: SkillSource) -> SkillCatalogEntry | None:
        try:
            raw = skill_file.read_text(encoding="utf-8")
            stat = skill_file.stat()
        except OSError:
            return None

        frontmatter = self._extract_frontmatter(raw)
        if frontmatter is None:
            return None
        name = frontmatter.get("name", "").strip()
        if not name:
            return None

        return SkillCatalogEntry(
            name=name,
            description=frontmatter.get("description", "").strip(),
            path=skill_file,
            source=source,
            mtime=stat.st_mtime,
            allowed_tools=self._parse_list(frontmatter.get("allowed-tools")),
            disable_model_invocation=self._parse_bool(
                frontmatter.get("disable-model-invocation")
            ),
        )

    def _extract_frontmatter(self, text: str) -> dict[str, str] | None:
        match = self._FRONTMATTER_FENCE.match(text)
        if match is None:
            return None
        block = match.group(1)
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        return fields

    def _read_body(self, path: Path) -> str:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        match = self._FRONTMATTER_FENCE.match(raw)
        if match is None:
            return raw
        return raw[match.end():]

    @staticmethod
    def _parse_list(raw: str | None) -> list[str] | None:
        if raw is None:
            return None
        raw = raw.strip()
        if not raw:
            return None
        # Flow-style YAML list: [Read, Grep]
        match = SkillCatalog._LIST_INLINE.search(raw)
        if match is None:
            return [raw]
        items = [item.strip() for item in match.group(1).split(",") if item.strip()]
        return items

    @staticmethod
    def _parse_bool(raw: str | None) -> bool:
        if raw is None:
            return False
        return raw.strip().lower() in {"true", "yes", "1", "on"}

    def _cached_body_count(self) -> int:
        """Internal test helper — count of bodies loaded into cache."""
        return len(self._body_cache)


def skill_catalog_section(entries: list[SkillCatalogEntry]) -> str:
    """Build a compact catalog section for the system prompt.

    Hidden-from-model skills (``disable-model-invocation: true``) are
    filtered out. Returns empty string when no visible entries remain.
    """
    visible = [e for e in entries if not e.disable_model_invocation]
    if not visible:
        return ""
    lines = ["Available skills:"]
    for entry in visible:
        desc = entry.description or "(no description)"
        lines.append(f"- {entry.name} — {desc}")
    return "\n".join(lines) + "\n"


# Module-level default for callers that just want "find the current project's skills".
DEFAULT_USER_SKILLS_DIR: Path = Path.home() / ".claude" / "skills"


def default_catalog(project_root: Path | str) -> SkillCatalog:
    """Convenience factory returning a SkillCatalog with standard user dir."""
    return SkillCatalog(
        project_root=project_root,
        user_skills_dir=DEFAULT_USER_SKILLS_DIR,
    )


__all__ = [
    "DEFAULT_USER_SKILLS_DIR",
    "SkillCatalog",
    "SkillCatalogEntry",
    "SkillSource",
    "default_catalog",
    "skill_catalog_section",
]
