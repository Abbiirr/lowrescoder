"""Tree-sitter parser with mtime-based LRU caching."""

from __future__ import annotations

import os
import threading
from collections import OrderedDict
from pathlib import Path

from autocode.core.types import ParseResult


class TreeSitterParser:
    """Parse Python source files using tree-sitter with an LRU mtime cache.

    Cache entries are invalidated when a file's mtime changes.
    The cache is bounded by ``max_entries`` (default 500).
    """

    def __init__(self, max_entries: int = 500) -> None:
        self._max_entries = max_entries
        # OrderedDict used as LRU: (tree, mtime)
        self._cache: OrderedDict[str, tuple[object, float]] = OrderedDict()
        self._lock = threading.Lock()
        self._parser: object | None = None
        self._language: object | None = None

    def _ensure_parser(self) -> None:
        """Lazy-init the tree-sitter parser and Python language."""
        if self._parser is not None:
            return

        try:
            import tree_sitter_python as tspython
            from tree_sitter import Language, Parser

            self._language = Language(tspython.language())
            self._parser = Parser(self._language)
        except ImportError as e:
            raise ImportError(
                "tree-sitter and tree-sitter-python are required for Layer 1. "
                "Install with: uv pip install -e '.[layer1]'"
            ) from e

    def parse(self, file_path: str | Path) -> ParseResult:
        """Parse a Python file, returning a cached result if unchanged.

        Args:
            file_path: Path to a Python source file.

        Returns:
            ParseResult with the tree-sitter Tree, file path, mtime, and language.

        Raises:
            FileNotFoundError: If the file does not exist.
            ImportError: If tree-sitter is not installed.
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        key = str(path)
        mtime = os.path.getmtime(key)

        with self._lock:
            if key in self._cache:
                cached_tree, cached_mtime = self._cache[key]
                if cached_mtime == mtime:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    return ParseResult(
                        tree=cached_tree,
                        file_path=key,
                        mtime=cached_mtime,
                        language="python",
                    )

        # Parse outside the lock to avoid blocking other threads
        self._ensure_parser()
        source = path.read_bytes()
        tree = self._parser.parse(source)  # type: ignore[union-attr]

        with self._lock:
            self._cache[key] = (tree, mtime)
            self._cache.move_to_end(key)
            # Evict oldest if over capacity
            while len(self._cache) > self._max_entries:
                self._cache.popitem(last=False)

        return ParseResult(
            tree=tree,
            file_path=key,
            mtime=mtime,
            language="python",
        )

    def parse_string(self, source: str, file_path: str = "<string>") -> ParseResult:
        """Parse a Python source string (no caching).

        Args:
            source: Python source code as a string.
            file_path: Label for the result (default "<string>").

        Returns:
            ParseResult with the parsed tree.
        """
        self._ensure_parser()
        tree = self._parser.parse(source.encode("utf-8"))  # type: ignore[union-attr]
        return ParseResult(
            tree=tree,
            file_path=file_path,
            mtime=0.0,
            language="python",
        )

    @property
    def cache_size(self) -> int:
        """Return the current number of cached entries."""
        with self._lock:
            return len(self._cache)

    def clear_cache(self) -> None:
        """Clear the entire parse cache."""
        with self._lock:
            self._cache.clear()
