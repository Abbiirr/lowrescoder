"""Repo map generator: ranked symbol summary within token budget.

Uses tree-sitter symbols to generate a compact overview of the codebase,
ranked by importance (public functions/classes first), within a configurable
token budget (default 600 tokens).
"""

from __future__ import annotations

from pathlib import Path

from autocode.core.types import Symbol
from autocode.layer1.parser import TreeSitterParser
from autocode.layer1.symbols import SymbolExtractor

# Approximate chars per token
_CHARS_PER_TOKEN = 4


class RepoMapGenerator:
    """Generate a ranked symbol map of the project within a token budget."""

    def __init__(
        self,
        parser: TreeSitterParser | None = None,
        budget_tokens: int = 600,
    ) -> None:
        self._parser = parser or TreeSitterParser()
        self._extractor = SymbolExtractor()
        self._budget_tokens = budget_tokens

    def generate(self, project_root: str | Path) -> str:
        """Generate a repo map for the project.

        Args:
            project_root: Path to the project root.

        Returns:
            A string containing the ranked symbol summary.
        """
        root = Path(project_root).resolve()
        budget_chars = self._budget_tokens * _CHARS_PER_TOKEN

        # Collect symbols from all Python files
        all_symbols: list[tuple[str, Symbol]] = []  # (relative_path, symbol)

        for fpath in sorted(root.rglob("*.py")):
            # Skip common non-source directories
            rel = str(fpath.relative_to(root)).replace("\\", "/")
            if any(part.startswith(".") or part in (
                "__pycache__", "node_modules", ".venv", "venv",
                "build", "dist",
            ) for part in fpath.relative_to(root).parts):
                continue

            try:
                result = self._parser.parse(str(fpath))
                symbols = self._extractor.extract(result)
                for sym in symbols:
                    all_symbols.append((rel, sym))
            except Exception:
                continue

        if not all_symbols:
            return "# Repo Map\n(no Python files found)"

        # Rank symbols: classes > functions > methods > imports > variables
        rank_order = {"class": 0, "function": 1, "method": 2, "variable": 3, "import": 4}
        all_symbols.sort(key=lambda x: (rank_order.get(x[1].kind, 5), x[0], x[1].line))

        # Build map within budget
        lines = ["# Repo Map\n"]
        current_file = ""
        used_chars = len(lines[0])

        for rel_path, sym in all_symbols:
            if rel_path != current_file:
                file_header = f"\n## {rel_path}\n"
                if used_chars + len(file_header) > budget_chars:
                    break
                lines.append(file_header)
                used_chars += len(file_header)
                current_file = rel_path

            # Format symbol entry
            scope_str = f" ({sym.scope})" if sym.scope else ""
            type_str = f" -> {sym.type_annotation}" if sym.type_annotation else ""
            entry = f"- {sym.kind}: `{sym.name}`{scope_str}{type_str} L{sym.line}\n"

            if used_chars + len(entry) > budget_chars:
                lines.append("...(truncated)\n")
                break

            lines.append(entry)
            used_chars += len(entry)

        return "".join(lines)
