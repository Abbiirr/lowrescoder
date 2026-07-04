"""Architecture guardrails for backend/frontend separation."""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "src" / "autocode" / "backend"


def _import_targets(tree: ast.AST) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return targets


def test_backend_package_has_no_ui_module_imports() -> None:
    """Backend modules must not depend on UI packages."""
    violations: list[str] = []

    for path in sorted(BACKEND_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for target in _import_targets(tree):
            if target.startswith("autocode.tui"):
                violations.append(f"{path.relative_to(BACKEND_ROOT.parent.parent)} -> {target}")

    assert violations == [], (
        "backend package must not import UI modules:\n" + "\n".join(violations)
    )
