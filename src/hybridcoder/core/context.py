"""Context assembler: priority-based assembly within token budget.

Allocates a fixed token budget (default 5000) across:
- Rules (~300 tokens)
- Repo map (~600 tokens)
- Search results (~2200 tokens)
- Current file (~800 tokens)
- Conversation history (~800 tokens)
- Buffer (~300 tokens)
"""

from __future__ import annotations

from hybridcoder.core.types import SearchResult

# Approximate chars per token
_CHARS_PER_TOKEN = 4

# Default budget allocation (tokens)
_BUDGET = {
    "rules": 300,
    "repomap": 600,
    "search": 2200,
    "file": 800,
    "history": 800,
    "buffer": 300,
}


class ContextAssembler:
    """Assemble curated context within a token budget.

    Priority order: rules > repo map > search results > file > history.
    Each section is truncated to its budget. The total never exceeds
    the configured context_budget.
    """

    def __init__(self, context_budget: int = 5000) -> None:
        self._budget = context_budget
        # Scale allocations proportionally if budget differs from default
        scale = context_budget / sum(_BUDGET.values())
        self._allocations = {k: int(v * scale) for k, v in _BUDGET.items()}

    def assemble(
        self,
        query: str,
        *,
        rules: str = "",
        repomap: str = "",
        search_results: list[SearchResult] | None = None,
        current_file: str = "",
        history: str = "",
    ) -> str:
        """Assemble context from all sources within budget.

        Args:
            query: The user's query (for reference, not counted in budget).
            rules: Project rules text.
            repomap: Repo map text.
            search_results: Search results from hybrid search.
            current_file: Current file contents.
            history: Conversation history summary.

        Returns:
            Assembled context string, guaranteed to be within budget.
        """
        sections: list[str] = []
        total_chars = 0
        max_chars = self._budget * _CHARS_PER_TOKEN

        # 1. Rules (highest priority)
        if rules:
            truncated = self._truncate(rules, self._allocations["rules"])
            sections.append(f"## Project Rules\n{truncated}\n")
            total_chars += len(sections[-1])

        # 2. Repo map
        if repomap:
            truncated = self._truncate(repomap, self._allocations["repomap"])
            sections.append(f"## Repo Map\n{truncated}\n")
            total_chars += len(sections[-1])

        # 3. Search results
        if search_results:
            search_text = self._format_search_results(
                search_results, self._allocations["search"],
            )
            if search_text:
                sections.append(f"## Relevant Code\n{search_text}\n")
                total_chars += len(sections[-1])

        # 4. Current file
        if current_file:
            truncated = self._truncate(current_file, self._allocations["file"])
            sections.append(f"## Current File\n{truncated}\n")
            total_chars += len(sections[-1])

        # 5. History
        if history:
            truncated = self._truncate(history, self._allocations["history"])
            sections.append(f"## Recent Context\n{truncated}\n")
            total_chars += len(sections[-1])

        result = "\n".join(sections)

        # Final safety truncation
        if len(result) > max_chars:
            result = result[:max_chars] + "\n...(context truncated)"

        return result

    def token_count(self, text: str) -> int:
        """Estimate token count for a text string."""
        return len(text) // _CHARS_PER_TOKEN

    def _truncate(self, text: str, budget_tokens: int) -> str:
        """Truncate text to fit within a token budget."""
        max_chars = budget_tokens * _CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "...(truncated)"

    def _format_search_results(
        self, results: list[SearchResult], budget_tokens: int,
    ) -> str:
        """Format search results within budget."""
        max_chars = budget_tokens * _CHARS_PER_TOKEN
        lines: list[str] = []
        used = 0

        for r in results:
            loc = f"{r.chunk.file_path}:{r.chunk.start_line}-{r.chunk.end_line}"
            header = f"### {loc} ({r.match_type}, score: {r.score:.3f})\n"
            content = f"```{r.chunk.language}\n{r.chunk.content}\n```\n"
            entry = header + content

            if used + len(entry) > max_chars:
                # Try to fit just the header + truncated content
                remaining = max_chars - used
                if remaining > len(header) + 50:
                    truncated_content = r.chunk.content[:remaining - len(header) - 20]
                    entry = header + f"```{r.chunk.language}\n{truncated_content}\n...\n```\n"
                    lines.append(entry)
                break

            lines.append(entry)
            used += len(entry)

        return "".join(lines)
