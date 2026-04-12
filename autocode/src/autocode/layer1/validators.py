"""Syntax and import validation via tree-sitter.

Validates code edits before applying them to ensure they don't
introduce syntax errors.
"""

from __future__ import annotations

from autocode.layer1.parser import TreeSitterParser


class SyntaxValidator:
    """Validate Python source code syntax using tree-sitter."""

    def __init__(self, parser: TreeSitterParser | None = None) -> None:
        self._parser = parser or TreeSitterParser()

    def validate(self, source: str) -> tuple[bool, list[str]]:
        """Validate Python source code.

        Args:
            source: Python source code to validate.

        Returns:
            Tuple of (is_valid, list of error descriptions).
        """
        if not source.strip():
            return True, []

        try:
            result = self._parser.parse_string(source)
        except Exception as e:
            return False, [f"Parse error: {e}"]

        root = result.tree.root_node
        if not root.has_error:
            return True, []

        errors = self._collect_errors(root)
        return False, errors

    def validate_edit(self, original: str, modified: str) -> tuple[bool, list[str]]:
        """Validate that a code edit doesn't introduce syntax errors.

        Args:
            original: Original source code.
            modified: Modified source code.

        Returns:
            Tuple of (is_valid, list of new errors introduced by the edit).
        """
        orig_valid, orig_errors = self.validate(original)
        mod_valid, mod_errors = self.validate(modified)

        if mod_valid:
            return True, []

        # Only report errors that are NEW (not in original)
        new_errors = [e for e in mod_errors if e not in orig_errors]
        if not new_errors and not orig_valid:
            # Original had errors too, and no new ones introduced
            return True, []

        return False, new_errors if new_errors else mod_errors

    def _collect_errors(self, node: object, max_errors: int = 10) -> list[str]:
        """Collect error descriptions from the AST."""
        errors: list[str] = []
        self._walk_errors(node, errors, max_errors)
        return errors

    def _walk_errors(
        self, node: object, errors: list[str], max_errors: int,
    ) -> None:
        """Recursively walk the tree to find ERROR nodes."""
        if len(errors) >= max_errors:
            return

        if node.type == "ERROR":  # type: ignore[attr-defined]
            line = node.start_point[0] + 1  # type: ignore[attr-defined]
            col = node.start_point[1]  # type: ignore[attr-defined]
            text = node.text.decode("utf-8", errors="replace")[:50]  # type: ignore[attr-defined]
            errors.append(f"Syntax error at line {line}, col {col}: {text}")
            return

        for child in node.children:  # type: ignore[attr-defined]
            self._walk_errors(child, errors, max_errors)
