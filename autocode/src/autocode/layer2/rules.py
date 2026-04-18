"""Rules loader: loads project context from CLAUDE.md, AGENTS.md, .rules/, etc.

Contract:

- directory walk (specified project_root up to walk_up_to)
- CLAUDE.local.md precedence (loaded AFTER CLAUDE.md so it overrides)
- bounded @import syntax with circular-import guard and configurable
  max_import_depth
- external-path imports require explicit approval (default denies)
- HTML block-comment stripping (``<!-- ... -->``)
- provenance tracking via ``RulesResult.sources``
- legacy ``load()`` kept for backward compatibility with existing callers
  that just want concatenated text

The module is intentionally dependency-free — it is in the fast critical path
for every session startup.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

_HTML_BLOCK_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_AT_IMPORT_LINE = re.compile(r"^\s*@(\S+)\s*$")
# Default file-byte cap for any single loaded source — a loose guard so a
# 10 MB file does not overwhelm the prompt by accident. Callers can relax.
_DEFAULT_MAX_FILE_BYTES = 50_000
_DEFAULT_MAX_IMPORT_DEPTH = 5


class Provenance(StrEnum):
    """Origin label attached to each ``LoadedSource`` entry."""

    CLAUDE_MD = "claude.md"
    CLAUDE_LOCAL_MD = "claude.local.md"
    AGENTS_MD = "agents.md"
    CURSOR_RULES = "cursorrules"
    RULES_DIR = "rules_dir"
    IMPORT = "import"
    EXTERNAL_IMPORT = "external_import"


@dataclass(frozen=True)
class LoadedSource:
    """Provenance for a single included source.

    Attributes:
        path: Absolute path of the loaded file.
        kind: Which loader slot claimed it.
        length: Number of characters the source contributed AFTER any
            truncation or comment stripping.
    """

    path: Path
    kind: Provenance
    length: int = 0


@dataclass
class RulesResult:
    """Rich result of a loader run.

    Attributes:
        text: Concatenated rules text suitable for prompt injection.
        sources: Ordered provenance list of every included source.
        skipped_imports: Human-readable descriptions of @imports that were
            NOT expanded (external without approval, depth exceeded, etc.).
        circular_detected: Short-chain descriptions for circular imports.
    """

    text: str = ""
    sources: list[LoadedSource] = field(default_factory=list)
    skipped_imports: list[str] = field(default_factory=list)
    circular_detected: list[str] = field(default_factory=list)


class RulesLoader:
    """Load project rules from known files with migration-friendly contract.

    The default ``load(project_root)`` API preserves the pre-Slice-2 signature
    by returning concatenated text. Use ``load_detailed(...)`` to get a full
    ``RulesResult`` including provenance, import skips, and circular chains.
    """

    # Ordered slots: (filename, provenance kind). CLAUDE.local.md is loaded
    # AFTER CLAUDE.md so its entries override. Order is stable across runs.
    _DIRECTORY_SLOTS: tuple[tuple[str, Provenance], ...] = (
        ("CLAUDE.md", Provenance.CLAUDE_MD),
        ("CLAUDE.local.md", Provenance.CLAUDE_LOCAL_MD),
        ("AGENTS.md", Provenance.AGENTS_MD),
        (".cursorrules", Provenance.CURSOR_RULES),
    )

    def load(self, project_root: str | Path, **kwargs: Any) -> str:
        """Return concatenated rules text (legacy API).

        Forwards every keyword arg to :meth:`load_detailed`; callers that
        need provenance, skipped-import tracking, or the full source list
        should use ``load_detailed`` directly.
        """
        return self.load_detailed(project_root, **kwargs).text

    def load_detailed(
        self,
        project_root: str | Path,
        *,
        include_local: bool = True,
        include_imports: bool = True,
        max_import_depth: int = _DEFAULT_MAX_IMPORT_DEPTH,
        external_import_approver: Callable[[Path], bool] | None = None,
        strip_html_comments: bool = True,
        max_file_bytes: int = _DEFAULT_MAX_FILE_BYTES,
        walk_up_to: str | Path | None = None,
    ) -> RulesResult:
        """Walk project_root (optionally up to walk_up_to) and produce a full result."""
        root = Path(project_root).resolve()
        ceiling: Path | None = Path(walk_up_to).resolve() if walk_up_to else None
        result = RulesResult()

        # Collect the directory chain from most-shallow (ceiling) to root.
        chain = self._directory_chain(root, ceiling)

        visited: set[Path] = set()
        for directory in chain:
            for name, kind in self._DIRECTORY_SLOTS:
                if kind is Provenance.CLAUDE_LOCAL_MD and not include_local:
                    continue
                self._load_file_into(
                    directory / name,
                    kind=kind,
                    project_root=root,
                    result=result,
                    visited=visited,
                    include_imports=include_imports,
                    max_import_depth=max_import_depth,
                    external_import_approver=external_import_approver,
                    strip_html_comments=strip_html_comments,
                    max_file_bytes=max_file_bytes,
                    current_depth=0,
                )

            # .rules/*.md in the project root only (matches prior behavior)
            rules_dir = directory / ".rules"
            if rules_dir.is_dir():
                for rule_file in sorted(rules_dir.glob("*.md")):
                    self._load_file_into(
                        rule_file,
                        kind=Provenance.RULES_DIR,
                        project_root=root,
                        result=result,
                        visited=visited,
                        include_imports=include_imports,
                        max_import_depth=max_import_depth,
                        external_import_approver=external_import_approver,
                        strip_html_comments=strip_html_comments,
                        max_file_bytes=max_file_bytes,
                        current_depth=0,
                    )

        return result

    # ----- internal helpers -----

    def _directory_chain(self, root: Path, ceiling: Path | None) -> list[Path]:
        """Return directories from ceiling (or root) down to root.

        Walks up from ``root`` until ``ceiling`` (inclusive) or the filesystem
        root. Returns the list in broad → specific order so parent rules
        appear before child rules in the concatenated text.
        """
        chain: list[Path] = [root]
        if ceiling is None:
            return chain
        try:
            ceiling = ceiling.resolve()
        except OSError:
            return chain
        cur = root.parent
        # Walk up inclusive: if ceiling == root, chain stays [root].
        # If ceiling is a parent, include every intermediate dir.
        # Guard against infinite loops on non-ancestor ceilings.
        guard = 0
        while cur != ceiling and cur.parent != cur:
            chain.append(cur)
            cur = cur.parent
            guard += 1
            if guard > 50:
                break
        if cur == ceiling and ceiling not in chain:
            chain.append(ceiling)
        chain.reverse()  # broad → specific
        return chain

    def _load_file_into(
        self,
        path: Path,
        *,
        kind: Provenance,
        project_root: Path,
        result: RulesResult,
        visited: set[Path],
        include_imports: bool,
        max_import_depth: int,
        external_import_approver: Callable[[Path], bool] | None,
        strip_html_comments: bool,
        max_file_bytes: int,
        current_depth: int,
    ) -> None:
        resolved: Path
        try:
            resolved = path.resolve()
        except OSError:
            return
        if not resolved.is_file():
            return
        if resolved in visited:
            return
        visited.add(resolved)

        try:
            raw = resolved.read_text(encoding="utf-8")
        except OSError:
            return

        text, truncated = self._truncate_if_large(raw, max_file_bytes)
        if strip_html_comments:
            text = _HTML_BLOCK_COMMENT.sub("", text)

        # Expand @imports if requested
        if include_imports:
            text = self._expand_imports(
                text,
                source_file=resolved,
                project_root=project_root,
                result=result,
                visited=visited,
                include_imports=include_imports,
                max_import_depth=max_import_depth,
                external_import_approver=external_import_approver,
                strip_html_comments=strip_html_comments,
                max_file_bytes=max_file_bytes,
                current_depth=current_depth,
            )

        if truncated:
            text = text + "\n...(truncated)\n"

        display_header = f"## {resolved.name}\n"
        if result.text:
            result.text += "\n"
        result.text += display_header + text + ("\n" if not text.endswith("\n") else "")
        result.sources.append(LoadedSource(path=resolved, kind=kind, length=len(text)))

    def _expand_imports(
        self,
        text: str,
        *,
        source_file: Path,
        project_root: Path,
        result: RulesResult,
        visited: set[Path],
        include_imports: bool,
        max_import_depth: int,
        external_import_approver: Callable[[Path], bool] | None,
        strip_html_comments: bool,
        max_file_bytes: int,
        current_depth: int,
    ) -> str:
        lines = text.splitlines()
        out: list[str] = []
        for line in lines:
            match = _AT_IMPORT_LINE.match(line)
            if not match:
                out.append(line)
                continue

            import_target = match.group(1)
            resolved = self._resolve_import_path(
                import_target, source_file=source_file, project_root=project_root
            )
            if resolved is None:
                out.append(line)  # keep literal; nothing to import
                continue

            # Bounded depth
            if current_depth + 1 > max_import_depth:
                result.skipped_imports.append(
                    f"{resolved}: max import depth {max_import_depth} exceeded"
                )
                out.append(f"[@{import_target} — depth limit reached]")
                continue

            # External-path gate
            if not self._is_within(resolved, project_root):
                approved = (
                    external_import_approver is not None
                    and external_import_approver(resolved)
                )
                if not approved:
                    result.skipped_imports.append(
                        f"{resolved}: external import requires approval (declined)"
                    )
                    out.append(f"[@{import_target} — external import declined]")
                    continue

            # Circular-import guard
            if resolved in visited:
                result.circular_detected.append(
                    f"{source_file.name} -> {resolved.name}"
                )
                out.append(f"[@{import_target} — circular, already loaded]")
                continue

            expanded = self._load_and_expand(
                resolved,
                project_root=project_root,
                result=result,
                visited=visited,
                include_imports=include_imports,
                max_import_depth=max_import_depth,
                external_import_approver=external_import_approver,
                strip_html_comments=strip_html_comments,
                max_file_bytes=max_file_bytes,
                current_depth=current_depth + 1,
            )
            out.append(expanded)
        return "\n".join(out)

    def _load_and_expand(
        self,
        path: Path,
        *,
        project_root: Path,
        result: RulesResult,
        visited: set[Path],
        include_imports: bool,
        max_import_depth: int,
        external_import_approver: Callable[[Path], bool] | None,
        strip_html_comments: bool,
        max_file_bytes: int,
        current_depth: int,
    ) -> str:
        visited.add(path)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        text, truncated = self._truncate_if_large(raw, max_file_bytes)
        if strip_html_comments:
            text = _HTML_BLOCK_COMMENT.sub("", text)

        expanded = self._expand_imports(
            text,
            source_file=path,
            project_root=project_root,
            result=result,
            visited=visited,
            include_imports=include_imports,
            max_import_depth=max_import_depth,
            external_import_approver=external_import_approver,
            strip_html_comments=strip_html_comments,
            max_file_bytes=max_file_bytes,
            current_depth=current_depth,
        )
        if truncated:
            expanded += "\n...(truncated)\n"

        kind = (
            Provenance.EXTERNAL_IMPORT
            if not self._is_within(path, project_root)
            else Provenance.IMPORT
        )
        result.sources.append(LoadedSource(path=path, kind=kind, length=len(expanded)))
        return expanded

    @staticmethod
    def _resolve_import_path(
        import_target: str, *, source_file: Path, project_root: Path
    ) -> Path | None:
        candidate = Path(import_target)
        if candidate.is_absolute():
            resolved = candidate
        else:
            resolved = (source_file.parent / candidate).resolve()
        try:
            resolved = resolved.resolve()
        except OSError:
            return None
        if not resolved.is_file():
            return None
        return resolved

    @staticmethod
    def _is_within(candidate: Path, root: Path) -> bool:
        try:
            candidate.resolve().relative_to(root.resolve())
            return True
        except ValueError:
            return False

    @staticmethod
    def _truncate_if_large(text: str, max_bytes: int) -> tuple[str, bool]:
        if max_bytes <= 0 or len(text) <= max_bytes:
            return text, False
        return text[:max_bytes], True
