"""File-system backed durable project memory."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

MAX_INDEX_LINES = 200
MAX_POINTER_CHARS = 150
TOPIC_SOFT_LINE_CAP = 1000


@dataclass(frozen=True)
class TopicWriteResult:
    slug: str
    path: Path
    warning: str | None = None


@dataclass(frozen=True)
class LogMatch:
    path: Path
    line_number: int
    line: str
    session_id: str


def _now() -> datetime:
    return datetime.now(UTC)


def _iso_now() -> str:
    return _now().isoformat()


class MemoryFS:
    """Three-layer durable memory stored under ``~/.autocode/projects``."""

    def __init__(self, project_root: str | Path, base_dir: str | Path | None = None) -> None:
        self.project_root = Path(project_root).expanduser().resolve()
        self._project_hash = self._compute_project_hash(self.project_root)
        self.base_dir = Path(base_dir).expanduser() if base_dir else self._compute_base_dir()
        self.memory_dir = self.base_dir / "memory"
        self.logs_dir = self.base_dir / "logs"
        self.index_path = self.base_dir / "MEMORY.md"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.index_path.write_text(self._initial_index(), encoding="utf-8")

    def _compute_base_dir(self) -> Path:
        return Path.home() / ".autocode" / "projects" / self._project_hash

    @classmethod
    def _compute_project_hash(cls, project_root: Path) -> str:
        canonical = cls._canonical_project_root(project_root)
        return hashlib.sha256(str(canonical).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _canonical_project_root(project_root: Path) -> Path:
        try:
            top = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            common = subprocess.run(
                ["git", "rev-parse", "--git-common-dir"],
                cwd=project_root,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            common_path = Path(common)
            if not common_path.is_absolute():
                common_path = Path(top) / common_path
            # Linked worktrees report the main repo's .git as common dir. Hash
            # its parent so all worktrees for the same repository share memory.
            if common_path.name == ".git":
                return common_path.parent.resolve()
            return Path(top).resolve()
        except Exception:
            return project_root.resolve()

    def _initial_index(self) -> str:
        return "# Project Memory\n\n## Topics\n\n## Recent\n"

    def read_index(self) -> str:
        return self.index_path.read_text(encoding="utf-8")

    def update_index_pointer(self, slug: str, summary: str) -> None:
        slug = self._sanitize_slug(slug)
        summary = " ".join(summary.split()) or slug
        pointer = f"- memory/{slug}.md — {summary}"
        if len(pointer) > MAX_POINTER_CHARS:
            pointer = pointer[: MAX_POINTER_CHARS - 1].rstrip() + "…"

        existing = self.read_index().splitlines()
        filtered = [
            line
            for line in existing
            if f"memory/{slug}.md" not in line and line.strip()
        ]
        if "## Recent" not in filtered:
            filtered.append("## Recent")
        recent_idx = filtered.index("## Recent")
        filtered.insert(recent_idx + 1, pointer)
        self.index_path.write_text(
            self._truncate_index("\n".join(filtered) + "\n"),
            encoding="utf-8",
        )

    def _truncate_index(self, content: str) -> str:
        lines = [line[:MAX_POINTER_CHARS] for line in content.splitlines()]
        while len(lines) > MAX_INDEX_LINES:
            recent_indices = [
                idx
                for idx, line in enumerate(lines)
                if line.startswith("- Recent") or line.startswith("- memory/")
            ]
            if recent_indices:
                lines.pop(recent_indices[-1])
            else:
                lines = lines[:MAX_INDEX_LINES]
                break
        return "\n".join(lines).rstrip() + "\n"

    def read_topic(self, slug: str) -> str:
        return self._topic_path(slug).read_text(encoding="utf-8")

    def write_topic(
        self,
        slug: str,
        content: str,
        summary: str | None = None,
        topic_type: str = "topic",
    ) -> TopicWriteResult:
        slug = self._sanitize_slug(slug)
        path = self._topic_path(slug)
        created = _iso_now()
        if path.exists():
            frontmatter, _body = self._extract_frontmatter(path.read_text(encoding="utf-8"))
            created = str(frontmatter.get("created") or created)
        body = content.rstrip() + "\n"
        size_lines = len(body.splitlines())
        warning = None
        if size_lines > TOPIC_SOFT_LINE_CAP:
            warning = (
                f"Topic exceeds {TOPIC_SOFT_LINE_CAP}-line soft cap; "
                f"recommend split into {slug}-<sub>.md"
            )
        text = (
            "---\n"
            f"topic: {slug}\n"
            f"type: {topic_type}\n"
            f"created: {created}\n"
            f"updated: {_iso_now()}\n"
            f"size_lines: {size_lines}\n"
            f"summary: {summary or self._derive_summary(body)}\n"
            "---\n\n"
            f"{body}"
        )
        path.write_text(text, encoding="utf-8")
        self.update_index_pointer(slug, summary or self._derive_summary(body))
        return TopicWriteResult(slug=slug, path=path, warning=warning)

    def list_topics(self) -> list[dict[str, Any]]:
        topics: list[dict[str, Any]] = []
        for path in sorted(self.memory_dir.glob("*.md")):
            frontmatter, body = self._extract_frontmatter(path.read_text(encoding="utf-8"))
            slug = path.stem
            topics.append(
                {
                    "slug": slug,
                    "path": str(path),
                    "topic": frontmatter.get("topic", slug),
                    "type": frontmatter.get("type", "topic"),
                    "summary": frontmatter.get("summary") or self._derive_summary(body),
                    "size_lines": int(frontmatter.get("size_lines") or 0),
                    "updated": frontmatter.get("updated", ""),
                }
            )
        return topics

    def get_memories(self, limit: int = 50) -> list[dict[str, Any]]:
        memories = []
        for topic in self.list_topics()[:limit]:
            memories.append(
                {
                    "id": topic["slug"],
                    "category": topic["type"],
                    "content": topic["summary"],
                    "relevance": 1.0,
                }
            )
        return memories

    def get_context(self) -> str:
        return self.read_index()

    def save(self, category: str, content: str, session_id: str) -> str:
        category_to_slug = {
            "tool_pattern": "patterns",
            "user_preference": "preferences",
            "project_fact": "facts",
            "error_resolution": "debugging",
        }
        slug = category_to_slug.get(category, "miscellany")
        existing = ""
        path = self._topic_path(slug)
        if path.exists():
            _frontmatter, existing = self._extract_frontmatter(path.read_text(encoding="utf-8"))
        appended = existing.rstrip()
        if appended:
            appended += "\n\n"
        appended += f"- [{category}] {content} (session: {session_id})\n"
        self.write_topic(slug, appended, summary=f"Latest {category} memory")
        return slug

    def apply_decay(self) -> int:
        return 0

    async def learn_from_session(self, *_args: Any, **_kwargs: Any) -> list[str]:
        return []

    def append_log(self, session_id: str, entry: dict[str, Any]) -> Path:
        now = _now()
        path = self.logs_dir / f"{now:%Y}" / f"{now:%m}" / f"{now:%Y-%m-%d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                self._format_log_block(
                    now.strftime("%H:%M:%S"),
                    {"session_id": session_id, **entry},
                )
            )
        return path

    def _format_log_block(self, time_str: str, entry: dict[str, Any]) -> str:
        lines = [f"\n## {time_str}", f"session_id: {entry.get('session_id', '')}"]
        for key in ("model", "provider", "goal"):
            if entry.get(key):
                lines.append(f"{key}: {entry[key]}")
        for key in ("done", "decisions", "open_threads"):
            value = entry.get(key, [])
            if value:
                lines.append(f"{key}:")
                if isinstance(value, list):
                    lines.extend(f"- {item}" for item in value)
                else:
                    lines.append(f"- {value}")
        if entry.get("stats"):
            lines.append(f"stats: {entry['stats']}")
        return "\n".join(lines) + "\n"

    def grep_logs(
        self,
        pattern: str,
        *,
        days: int = 30,
        max_matches: int = 50,
    ) -> list[LogMatch]:
        regex = re.compile(pattern, re.IGNORECASE)
        cutoff = (_now() - timedelta(days=days)).date()
        matches: list[LogMatch] = []
        for path in sorted(self.logs_dir.glob("*/*/*.md"), reverse=True):
            try:
                if datetime.strptime(path.stem, "%Y-%m-%d").date() < cutoff:
                    continue
            except ValueError:
                continue
            session_id = ""
            lines = path.read_text(encoding="utf-8").splitlines()
            for line_number, line in enumerate(lines, start=1):
                if line.startswith("session_id:"):
                    session_id = line.split(":", 1)[1].strip()
                if regex.search(line):
                    matches.append(
                        LogMatch(
                            path=path,
                            line_number=line_number,
                            line=line,
                            session_id=session_id,
                        )
                    )
                    if len(matches) >= max_matches:
                        return matches
        return matches

    def _topic_path(self, slug: str) -> Path:
        return self.memory_dir / f"{self._sanitize_slug(slug)}.md"

    def _sanitize_slug(self, slug: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
        return cleaned or "miscellany"

    def _extract_frontmatter(self, content: str) -> tuple[dict[str, str], str]:
        if not content.startswith("---\n"):
            return {}, content
        try:
            _start, rest = content.split("---\n", 1)
            raw_frontmatter, body = rest.split("---\n", 1)
        except ValueError:
            return {}, content
        data: dict[str, str] = {}
        for line in raw_frontmatter.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                data[key.strip()] = value.strip()
        return data, body.lstrip("\n")

    def _derive_summary(self, body: str) -> str:
        for line in body.splitlines():
            stripped = line.strip().lstrip("- ").strip()
            if stripped:
                return stripped[:MAX_POINTER_CHARS]
        return "Empty topic"
