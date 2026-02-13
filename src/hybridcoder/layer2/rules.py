"""Rules loader: loads project context from CLAUDE.md, AGENTS.md, .rules/, etc."""

from __future__ import annotations

from pathlib import Path


class RulesLoader:
    """Load project rules and context files.

    Searches for CLAUDE.md, AGENTS.md, .rules/*.md, .cursorrules
    and concatenates them into a project context string.
    """

    # Files to look for, in priority order
    _RULE_FILES = [
        "CLAUDE.md",
        "AGENTS.md",
        ".cursorrules",
    ]

    def load(self, project_root: str | Path) -> str:
        """Load project rules from known files.

        Args:
            project_root: Path to the project root.

        Returns:
            Concatenated rules text, or empty string if none found.
        """
        root = Path(project_root).resolve()
        sections: list[str] = []

        # Check known rule files
        for name in self._RULE_FILES:
            path = root / name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    # Truncate very long files
                    if len(content) > 2000:
                        content = content[:2000] + "\n...(truncated)"
                    sections.append(f"## {name}\n{content}\n")
                except OSError:
                    continue

        # Check .rules/ directory
        rules_dir = root / ".rules"
        if rules_dir.is_dir():
            for rule_file in sorted(rules_dir.glob("*.md")):
                try:
                    content = rule_file.read_text(encoding="utf-8")
                    if len(content) > 1000:
                        content = content[:1000] + "\n...(truncated)"
                    sections.append(f"## {rule_file.name}\n{content}\n")
                except OSError:
                    continue

        return "\n".join(sections) if sections else ""
