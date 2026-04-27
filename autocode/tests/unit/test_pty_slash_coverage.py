"""Tests for the Rust TUI slash PTY coverage manifest."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_slash_smoke_module() -> ModuleType:
    path = (
        Path(__file__).resolve().parents[1]
        / "pty"
        / "pty_smoke_rust_slash_surfaces.py"
    )
    spec = importlib.util.spec_from_file_location("pty_smoke_rust_slash_surfaces", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_slash_surface_manifest_covers_high_risk_commands() -> None:
    """The PTY slash smoke should explicitly name the high-risk slash surfaces."""
    module = _load_slash_smoke_module()

    covered = {case.command for case in module.SLASH_SURFACE_CASES}

    assert {
        "/help",
        "/plan",
        "/tasks",
        "/grep",
        "/review",
        "/diff",
        "/restore",
        "/cc",
        "/escalation",
        "/multi",
    }.issubset(covered)


def test_slash_surface_manifest_has_unique_commands() -> None:
    """Duplicate commands make coverage accounting ambiguous."""
    module = _load_slash_smoke_module()

    commands = [case.command for case in module.SLASH_SURFACE_CASES]

    assert len(commands) == len(set(commands))
