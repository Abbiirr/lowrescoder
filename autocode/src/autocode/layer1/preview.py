"""Cheap Layer 1 symbol previews for already-hot files."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

from autocode.core.types import Symbol
from autocode.layer1.parser import TreeSitterParser, get_shared_parser
from autocode.layer1.symbols import SymbolExtractor

_INTERESTING_KINDS = {"class", "function", "method"}


def _resolve_working_set_path(project_root: Path, file_ref: str) -> Path:
    path = Path(file_ref)
    return path if path.is_absolute() else project_root / path


def _format_symbol(symbol: Symbol) -> str:
    name = f"{symbol.scope}.{symbol.name}" if symbol.scope else symbol.name
    return f"{symbol.kind} {name}:L{symbol.line}"


def build_active_symbol_preview(
    *,
    project_root: str | Path,
    working_set: Sequence[str],
    parser: TreeSitterParser | None = None,
    extractor: SymbolExtractor | None = None,
    max_files: int = 5,
    max_symbols_per_file: int = 10,
    max_tokens: int = 200,
    deadline_ms: int = 100,
) -> str:
    """Build a bounded symbol preview from cached parses only.

    This intentionally never calls ``parse()``. A missing cached parse simply
    means the file is skipped, preserving first-turn latency.
    """
    if deadline_ms <= 0 or not working_set:
        return ""

    deadline = time.monotonic() + (deadline_ms / 1000)
    root = Path(project_root).expanduser().resolve()
    parser = parser or get_shared_parser()
    extractor = extractor or SymbolExtractor()
    max_chars = max_tokens * 4
    lines = ["- Active symbol preview:"]

    def expired() -> bool:
        return time.monotonic() >= deadline

    for file_ref in list(working_set)[:max_files]:
        if expired():
            return ""
        parse_result = parser.get_cached(_resolve_working_set_path(root, file_ref))
        if parse_result is None:
            continue
        if expired():
            return ""
        symbols = [
            symbol for symbol in extractor.extract(parse_result)
            if symbol.kind in _INTERESTING_KINDS
        ][:max_symbols_per_file]
        if not symbols:
            continue
        line = f"  - {file_ref}: " + ", ".join(_format_symbol(symbol) for symbol in symbols)
        if len("\n".join([*lines, line])) > max_chars:
            break
        lines.append(line)

    return "\n".join(lines) if len(lines) > 1 else ""
