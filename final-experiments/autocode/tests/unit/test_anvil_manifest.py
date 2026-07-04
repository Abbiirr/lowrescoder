"""Tests for AutoCode's own capability manifest (the gap-diff baseline).

The manifest introspects AutoCode's Typer CLI into the same :class:`Capability`
model the census uses, so a target census can be diffed against it directly.
"""

from __future__ import annotations

import typer

from autocode.anvil.manifest import autocode_manifest, manifest_from_typer


def _build_demo_app() -> typer.Typer:
    demo = typer.Typer()

    @demo.command()
    def build(
        name: str = typer.Argument(..., help="positional, not a flag"),
        force: bool = typer.Option(False, "--force", "-f", help="Force"),
    ) -> None:
        ...

    @demo.command("run-it")
    def run_it(
        budget: float = typer.Option(0.0, "--max-budget-usd", help="cap spend"),
    ) -> None:
        ...

    return demo


def test_introspects_commands_and_flags() -> None:
    manifest = manifest_from_typer(_build_demo_app(), name="demo")
    ids = {c.id for c in manifest.capabilities}
    assert "cmd:build" in ids
    assert "cmd:run-it" in ids
    assert "flag:force" in ids
    assert "flag:max-budget-usd" in ids


def test_positional_arguments_are_not_flags() -> None:
    manifest = manifest_from_typer(_build_demo_app(), name="demo")
    ids = {c.id for c in manifest.capabilities}
    assert "flag:name" not in ids
    assert "cmd:name" not in ids


def test_flag_records_short_and_long_surface() -> None:
    manifest = manifest_from_typer(_build_demo_app(), name="demo")
    force = next(c for c in manifest.capabilities if c.id == "flag:force")
    assert "--force" in force.surface
    assert "-f" in force.surface


def test_autocode_manifest_has_real_surface() -> None:
    manifest = autocode_manifest()
    assert manifest.target == "autocode"
    ids = {c.id for c in manifest.capabilities}
    # Stable AutoCode commands/flags that exist today.
    assert "cmd:exec" in ids
    assert "cmd:config" in ids
    assert "flag:json" in ids          # `autocode exec --json`
    assert "flag:auto-approve" in ids  # `autocode exec --auto-approve`
