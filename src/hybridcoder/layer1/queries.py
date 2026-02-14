"""Deterministic query handlers for L1 queries (zero LLM tokens).

Handles "list functions", "find definition", "get imports", "show signature",
"find references" queries using tree-sitter parsing only.
"""

from __future__ import annotations

import re
from itertools import islice
from pathlib import Path

from hybridcoder.core.types import Response, Symbol
from hybridcoder.layer1.parser import TreeSitterParser
from hybridcoder.layer1.symbols import SymbolExtractor

# Patterns to extract target file and symbol from queries
_FILE_PATTERN = re.compile(r"(?:in|from|of)\s+([\w./\\-]+\.py)\b", re.IGNORECASE)
_SYMBOL_PATTERN = re.compile(r"(?:of|for|to)\s+[`'\"]?(\w+)[`'\"]?", re.IGNORECASE)
_BACKTICK_SYMBOL = re.compile(r"`(\w+)`")

# Query type patterns
_LIST_SYMBOLS = re.compile(
    r"\b(?:list|show|get|what are(?: the)?)\s+(?:all\s+)?"
    r"(functions?|classes?|methods?|symbols?|defs?|definitions?)\b",
    re.IGNORECASE,
)
_FIND_DEFINITION = re.compile(
    r"\b(?:find|go to|where is|locate|show)\s+(?:the\s+)?"
    r"(?:definition|declaration)\s+(?:of|for)\s+",
    re.IGNORECASE,
)
_FIND_REFERENCES = re.compile(
    r"\b(?:find|show|get|list)\s+(?:all\s+)?"
    r"(?:references?|usages?|callers?|call sites?)\s+(?:of|for|to)\s+",
    re.IGNORECASE,
)
_GET_IMPORTS = re.compile(
    r"\b(?:get|list|show|what are)\s+(?:the\s+)?imports?\b",
    re.IGNORECASE,
)
_SHOW_SIGNATURE = re.compile(
    r"\b(?:show|get|what is)\s+(?:the\s+)?(?:signature|prototype)\s+(?:of|for)\s+",
    re.IGNORECASE,
)


class DeterministicQueryHandler:
    """Handle L1 deterministic queries using tree-sitter.

    These queries return a Response directly with zero LLM tokens.
    """

    def __init__(
        self,
        parser: TreeSitterParser | None = None,
        project_root: str | Path | None = None,
    ) -> None:
        self._parser = parser or TreeSitterParser()
        self._extractor = SymbolExtractor()
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def handle(self, message: str) -> Response:
        """Handle a deterministic query.

        Args:
            message: The user's query string.

        Returns:
            Response with content (symbol listings, definitions, etc.)
            and layer_used=1, tokens_used=0.
        """
        message = message.strip()

        if _LIST_SYMBOLS.search(message):
            return self._handle_list_symbols(message)

        if _FIND_DEFINITION.search(message):
            return self._handle_find_definition(message)

        if _FIND_REFERENCES.search(message):
            return self._handle_find_references(message)

        if _GET_IMPORTS.search(message):
            return self._handle_get_imports(message)

        if _SHOW_SIGNATURE.search(message):
            return self._handle_show_signature(message)

        return Response(
            content="Could not understand the query. Try: list functions in <file>",
            layer_used=1,
            tokens_used=0,
            success=False,
        )

    def _resolve_file(self, message: str) -> Path | None:
        """Extract and resolve a file path from the message."""
        match = _FILE_PATTERN.search(message)
        if not match:
            return None

        file_ref = match.group(1)
        path = Path(file_ref)
        if path.is_absolute() and path.exists():
            return path

        resolved = self._project_root / file_ref
        if resolved.exists():
            return resolved

        return None

    def _extract_symbol_name(self, message: str) -> str | None:
        """Extract the target symbol name from the message."""
        bt = _BACKTICK_SYMBOL.search(message)
        if bt:
            return bt.group(1)

        match = _SYMBOL_PATTERN.search(message)
        if match:
            return match.group(1)
        return None

    def _get_symbols(self, file_path: Path) -> list[Symbol]:
        """Parse a file and extract symbols."""
        result = self._parser.parse(str(file_path))
        return self._extractor.extract(result)

    def _handle_list_symbols(self, message: str) -> Response:
        """Handle 'list functions/classes/methods/symbols in <file>'."""
        file_path = self._resolve_file(message)
        if not file_path:
            return Response(
                content="Please specify a file, e.g.: list functions in src/module.py",
                layer_used=1, tokens_used=0, success=False,
            )

        symbols = self._get_symbols(file_path)

        # Filter by requested kind
        match = _LIST_SYMBOLS.search(message)
        requested = match.group(1).lower().rstrip("s") if match else "symbol"

        kind_map = {
            "function": ("function", "method"),
            "class": ("class",),
            "method": ("method",),
            "symbol": ("function", "method", "class", "variable", "import"),
            "def": ("function", "method"),
            "definition": ("function", "method", "class"),
        }

        allowed_kinds = kind_map.get(requested, ("function", "method", "class"))
        filtered = [s for s in symbols if s.kind in allowed_kinds]

        if not filtered:
            return Response(
                content=f"No {requested}s found in {file_path.name}",
                layer_used=1, tokens_used=0,
            )

        lines = [f"**{requested.title()}s in `{file_path.name}`:**\n"]
        for s in filtered:
            scope_str = f" ({s.scope})" if s.scope else ""
            type_str = f" -> {s.type_annotation}" if s.type_annotation else ""
            lines.append(f"- `{s.name}`{scope_str}{type_str}  (line {s.line})")

        return Response(
            content="\n".join(lines),
            layer_used=1,
            tokens_used=0,
        )

    def _handle_find_definition(self, message: str) -> Response:
        """Handle 'find definition of <symbol>'."""
        symbol_name = self._extract_symbol_name(message)
        if not symbol_name:
            return Response(
                content="Please specify a symbol, e.g.: find definition of `my_function`",
                layer_used=1, tokens_used=0, success=False,
            )

        file_path = self._resolve_file(message)
        if file_path:
            search_files = [file_path]
        else:
            search_files = list(islice(self._project_root.rglob("*.py"), 100))

        for fpath in search_files:
            try:
                symbols = self._get_symbols(fpath)
                for s in symbols:
                    if s.name == symbol_name and s.kind in ("function", "method", "class"):
                        if self._project_root in fpath.parents:
                            rel = fpath.relative_to(self._project_root)
                        else:
                            rel = fpath
                        return Response(
                            content=(
                                f"**`{symbol_name}`** ({s.kind}) defined at "
                                f"`{rel}:{s.line}`"
                                f"{f' (scope: {s.scope})' if s.scope else ''}"
                            ),
                            layer_used=1, tokens_used=0,
                        )
            except Exception:
                continue

        return Response(
            content=f"Definition of `{symbol_name}` not found",
            layer_used=1, tokens_used=0, success=False,
        )

    def _handle_find_references(self, message: str) -> Response:
        """Handle 'find references of <symbol>'."""
        symbol_name = self._extract_symbol_name(message)
        if not symbol_name:
            return Response(
                content="Please specify a symbol, e.g.: find references of `my_function`",
                layer_used=1, tokens_used=0, success=False,
            )

        file_path = self._resolve_file(message)
        if file_path:
            search_files = [file_path]
        else:
            search_files = list(islice(self._project_root.rglob("*.py"), 100))

        refs: list[str] = []
        for fpath in search_files:
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if symbol_name in line:
                        if self._project_root in fpath.parents:
                            rel = fpath.relative_to(self._project_root)
                        else:
                            rel = fpath
                        refs.append(f"- `{rel}:{i}`: {line.strip()}")
            except Exception:
                continue

        if not refs:
            return Response(
                content=f"No references to `{symbol_name}` found",
                layer_used=1, tokens_used=0,
            )

        lines = [f"**References to `{symbol_name}`** ({len(refs)} found):\n"]
        lines.extend(refs[:30])
        if len(refs) > 30:
            lines.append(f"\n... and {len(refs) - 30} more")

        return Response(
            content="\n".join(lines),
            layer_used=1, tokens_used=0,
        )

    def _handle_get_imports(self, message: str) -> Response:
        """Handle 'get imports in <file>'."""
        file_path = self._resolve_file(message)
        if not file_path:
            return Response(
                content="Please specify a file, e.g.: get imports in src/module.py",
                layer_used=1, tokens_used=0, success=False,
            )

        symbols = self._get_symbols(file_path)
        imports = [s for s in symbols if s.kind == "import"]

        if not imports:
            return Response(
                content=f"No imports found in `{file_path.name}`",
                layer_used=1, tokens_used=0,
            )

        lines = [f"**Imports in `{file_path.name}`:**\n"]
        for s in imports:
            lines.append(f"- `{s.name}`  (line {s.line})")

        return Response(
            content="\n".join(lines),
            layer_used=1, tokens_used=0,
        )

    def _handle_show_signature(self, message: str) -> Response:
        """Handle 'show signature of <function>'."""
        symbol_name = self._extract_symbol_name(message)
        if not symbol_name:
            return Response(
                content="Please specify a function, e.g.: show signature of `my_function`",
                layer_used=1, tokens_used=0, success=False,
            )

        file_path = self._resolve_file(message)
        if file_path:
            search_files = [file_path]
        else:
            search_files = list(islice(self._project_root.rglob("*.py"), 100))

        for fpath in search_files:
            try:
                source = fpath.read_text(encoding="utf-8", errors="ignore")
                lines = source.splitlines()
                symbols = self._get_symbols(fpath)

                for s in symbols:
                    if s.name == symbol_name and s.kind in ("function", "method"):
                        # Extract the def line(s) as the signature
                        sig_lines = []
                        for ln in range(s.line - 1, min(s.line + 5, len(lines))):
                            sig_lines.append(lines[ln])
                            if "):" in lines[ln] or ") ->" in lines[ln]:
                                break

                        signature = "\n".join(sig_lines)
                        return Response(
                            content=f"```python\n{signature}\n```",
                            layer_used=1, tokens_used=0,
                        )
            except Exception:
                continue

        return Response(
            content=f"Signature for `{symbol_name}` not found",
            layer_used=1, tokens_used=0, success=False,
        )
