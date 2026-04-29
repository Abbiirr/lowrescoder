"""Repo map generator: ranked symbol summary within a token budget.

The generator combines deterministic symbol extraction with a small persistent
metadata cache. Python uses the existing tree-sitter Layer 1 parser; other
languages use conservative regex extractors until dedicated tree-sitter
grammars are added.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autocode.core.types import Symbol
from autocode.layer1.parser import TreeSitterParser
from autocode.layer1.symbols import SymbolExtractor

_CHARS_PER_TOKEN = 4
_DEFAULT_BUDGET_TOKENS = 1000
_SUPPORTED_EXTENSIONS = {".py", ".go"}
_SKIP_DIRS = {
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "build",
    "dist",
    "target",
}
_RANK_ORDER = {"class": 0, "function": 1, "method": 2, "type": 2, "variable": 3, "import": 4}


@dataclass(frozen=True)
class _FileSummary:
    rel_path: str
    language: str
    symbols: list[Symbol]
    imports: list[str]
    mtime_ns: int
    sha256: str


class RepoMapGenerator:
    """Generate a ranked markdown repo map within a token budget."""

    def __init__(
        self,
        parser: TreeSitterParser | None = None,
        budget_tokens: int = _DEFAULT_BUDGET_TOKENS,
        cache_dir: str | Path | None = None,
    ) -> None:
        self._parser = parser
        self._extractor: SymbolExtractor | None = None
        self._budget_tokens = budget_tokens
        self._cache_dir = Path(cache_dir).expanduser() if cache_dir else None

    @property
    def budget_tokens(self) -> int:
        """Configured approximate token budget."""
        return self._budget_tokens

    def generate(self, project_root: str | Path) -> str:
        """Generate a ranked markdown repo map for ``project_root``."""
        root = Path(project_root).resolve()
        cache_dir = self._resolve_cache_dir(root)
        summaries = self._collect_file_summaries(root, cache_dir)

        if not summaries:
            return "# Repo Map\n(no Python files found)"

        fan_in = self._dependency_fan_in(summaries)
        ranked = sorted(
            summaries,
            key=lambda summary: (
                -fan_in.get(summary.rel_path, 0),
                self._best_symbol_rank(summary.symbols),
                summary.rel_path,
            ),
        )
        return self._render_markdown(ranked, fan_in)

    def _resolve_cache_dir(self, root: Path) -> Path:
        if self._cache_dir is not None:
            cache_dir = self._cache_dir
        else:
            repo_hash = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
            cache_dir = Path.home() / ".autocode" / "cache" / "repomap" / repo_hash
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _collect_file_summaries(self, root: Path, cache_dir: Path) -> list[_FileSummary]:
        summaries: list[_FileSummary] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in _SUPPORTED_EXTENSIONS:
                continue
            rel_parts = path.relative_to(root).parts
            if self._should_skip(rel_parts):
                continue
            try:
                summaries.append(self._summary_for_file(root, path, cache_dir))
            except Exception:
                continue
        return summaries

    def _should_skip(self, rel_parts: tuple[str, ...]) -> bool:
        for part in rel_parts:
            if part.startswith(".") or part in _SKIP_DIRS:
                return True
        return False

    def _summary_for_file(self, root: Path, path: Path, cache_dir: Path) -> _FileSummary:
        rel_path = path.relative_to(root).as_posix()
        stat = path.stat()
        content = path.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        cached = self._read_cache(cache_dir, rel_path)
        if (
            cached
            and cached.get("mtime_ns") == stat.st_mtime_ns
            and cached.get("sha256") == digest
        ):
            return self._summary_from_cache(cached)

        language = self._language_for_path(path)
        symbols, imports = self._extract_file(path, rel_path, language, content)
        summary = _FileSummary(
            rel_path=rel_path,
            language=language,
            symbols=symbols,
            imports=imports,
            mtime_ns=stat.st_mtime_ns,
            sha256=digest,
        )
        self._write_cache(cache_dir, summary)
        return summary

    def _read_cache(self, cache_dir: Path, rel_path: str) -> dict[str, Any] | None:
        path = self._cache_path(cache_dir, rel_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _write_cache(self, cache_dir: Path, summary: _FileSummary) -> None:
        path = self._cache_path(cache_dir, summary.rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "rel_path": summary.rel_path,
            "language": summary.language,
            "imports": summary.imports,
            "mtime_ns": summary.mtime_ns,
            "sha256": summary.sha256,
            "symbols": [
                {
                    "name": symbol.name,
                    "kind": symbol.kind,
                    "file": symbol.file,
                    "line": symbol.line,
                    "end_line": symbol.end_line,
                    "scope": symbol.scope,
                    "type_annotation": symbol.type_annotation,
                }
                for symbol in summary.symbols
            ],
        }
        path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _cache_path(self, cache_dir: Path, rel_path: str) -> Path:
        digest = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()
        return cache_dir / f"{digest}.json"

    def _summary_from_cache(self, cached: dict[str, Any]) -> _FileSummary:
        symbols = [
            Symbol(
                name=str(raw["name"]),
                kind=str(raw["kind"]),
                file=str(raw["file"]),
                line=int(raw["line"]),
                end_line=int(raw["end_line"]),
                scope=raw.get("scope"),
                type_annotation=raw.get("type_annotation"),
            )
            for raw in cached.get("symbols", [])
            if isinstance(raw, dict)
        ]
        return _FileSummary(
            rel_path=str(cached["rel_path"]),
            language=str(cached["language"]),
            symbols=symbols,
            imports=[str(item) for item in cached.get("imports", [])],
            mtime_ns=int(cached["mtime_ns"]),
            sha256=str(cached["sha256"]),
        )

    def _language_for_path(self, path: Path) -> str:
        return "python" if path.suffix == ".py" else "go"

    def _extract_file(
        self,
        path: Path,
        rel_path: str,
        language: str,
        content: str,
    ) -> tuple[list[Symbol], list[str]]:
        if language == "python":
            return self._extract_python(path, rel_path, content)
        if language == "go":
            return self._extract_go(rel_path, content)
        return [], []

    def _extract_python(
        self,
        path: Path,
        rel_path: str,
        content: str,
    ) -> tuple[list[Symbol], list[str]]:
        parser = self._parser or TreeSitterParser()
        self._parser = parser
        self._extractor = self._extractor or SymbolExtractor()
        result = parser.parse(path)
        symbols = self._extractor.extract(result)
        for symbol in symbols:
            symbol.file = rel_path
        return symbols, self._python_import_targets(content)

    def _extract_go(self, rel_path: str, content: str) -> tuple[list[Symbol], list[str]]:
        symbols: list[Symbol] = []
        for line_no, line in enumerate(content.splitlines(), start=1):
            type_match = re.match(r"\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+", line)
            if type_match:
                symbols.append(Symbol(type_match.group(1), "type", rel_path, line_no, line_no))
                continue
            func_match = re.match(
                r"\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                line,
            )
            if func_match:
                symbols.append(Symbol(func_match.group(1), "function", rel_path, line_no, line_no))
        return symbols, self._go_import_targets(content)

    def _python_import_targets(self, content: str) -> list[str]:
        targets: list[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            match = re.match(r"from\s+([A-Za-z_][A-Za-z0-9_\.]*)\s+import\s+", stripped)
            if match:
                targets.append(match.group(1).replace(".", "/") + ".py")
                continue
            match = re.match(r"import\s+(.+)", stripped)
            if match:
                for raw_name in match.group(1).split(","):
                    name = raw_name.strip().split(" as ")[0].split(".")[0]
                    if name:
                        targets.append(name + ".py")
        return targets

    def _go_import_targets(self, content: str) -> list[str]:
        targets: list[str] = []
        for match in re.finditer(r'"([^"]+)"', content):
            value = match.group(1)
            if "." not in value:
                targets.append(value.rstrip("/") + ".go")
        return targets

    def _dependency_fan_in(self, summaries: list[_FileSummary]) -> dict[str, int]:
        known = {summary.rel_path for summary in summaries}
        by_basename = {Path(summary.rel_path).name: summary.rel_path for summary in summaries}
        fan_in = {summary.rel_path: 0 for summary in summaries}
        for summary in summaries:
            for target in summary.imports:
                rel_target = target if target in known else by_basename.get(Path(target).name)
                if rel_target and rel_target != summary.rel_path:
                    fan_in[rel_target] = fan_in.get(rel_target, 0) + 1
        return fan_in

    def _best_symbol_rank(self, symbols: list[Symbol]) -> int:
        if not symbols:
            return 99
        return min(_RANK_ORDER.get(symbol.kind, 50) for symbol in symbols)

    def _render_markdown(self, summaries: list[_FileSummary], fan_in: dict[str, int]) -> str:
        budget_chars = max(1, self._budget_tokens * _CHARS_PER_TOKEN)
        lines = ["# Repo Map\n"]
        used = len(lines[0])
        truncated = False

        for summary in summaries:
            symbols = sorted(
                summary.symbols,
                key=lambda symbol: (_RANK_ORDER.get(symbol.kind, 50), symbol.line, symbol.name),
            )
            if not symbols:
                continue
            fan = fan_in.get(summary.rel_path, 0)
            header = f"\n## {summary.rel_path} ({summary.language}, fan-in={fan})\n"
            body = "".join(self._format_symbol(symbol) for symbol in symbols)
            block = header + body
            if used + len(block) <= budget_chars:
                lines.append(block)
                used += len(block)
                continue

            if used + len(header) >= budget_chars:
                truncated = True
                break

            lines.append(header)
            used += len(header)
            for symbol in symbols:
                entry = self._format_symbol(symbol)
                if used + len(entry) > budget_chars:
                    truncated = True
                    break
                lines.append(entry)
                used += len(entry)
            if truncated:
                break

        if truncated:
            marker = "...(truncated)\n"
            if len(marker) <= budget_chars:
                while lines and used + len(marker) > budget_chars:
                    removed = lines.pop()
                    used -= len(removed)
                lines.append(marker)
        return "".join(lines)[:budget_chars]

    def _format_symbol(self, symbol: Symbol) -> str:
        scope_str = f" ({symbol.scope})" if symbol.scope else ""
        type_str = f" -> {symbol.type_annotation}" if symbol.type_annotation else ""
        return f"- {symbol.kind}: `{symbol.name}`{scope_str}{type_str} L{symbol.line}\n"
