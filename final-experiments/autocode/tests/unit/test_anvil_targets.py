"""Tests for concrete copycat census collectors (the ``puku-cli`` target).

The collector drives ``puku-cli --help`` (the public, observable surface) and
falls back to a bundled snapshot when the binary is absent, so a census is always
reproducible offline.
"""

from __future__ import annotations

from autocode.anvil.census import Census
from autocode.anvil.targets import (
    CODEX_TARGET_ID,
    PUKU_TARGET_ID,
    collect_census,
    collect_codex_census,
    collect_puku_census,
    has_collector,
)


def test_collects_from_injected_help() -> None:
    help_text = (
        "Options:\n"
        "  --max-budget-usd <amount>   Maximum dollar amount to spend\n"
        "Commands:\n"
        "  doctor                      Check health\n"
    )
    census = collect_puku_census(help_text=help_text, version="1.8.27")
    assert isinstance(census, Census)
    assert census.target == PUKU_TARGET_ID
    assert census.target_version == "1.8.27"
    ids = {c.id for c in census.capabilities}
    assert "flag:max-budget-usd" in ids
    assert "cmd:doctor" in ids


def test_uses_injected_runner_when_no_help_text() -> None:
    calls: list[list[str]] = []

    def fake_runner(args: list[str]) -> str | None:
        calls.append(args)
        if args[:1] == ["--help"]:
            return "Options:\n  --effort <level>   Effort level\n"
        if args[:1] == ["--version"]:
            return "9.9.9 (puku-cli)"
        return None

    census = collect_puku_census(runner=fake_runner)
    assert ["--help"] in calls
    assert census.target_version == "9.9.9"
    assert "flag:effort" in {c.id for c in census.capabilities}
    assert "--help" in census.source


def test_falls_back_to_bundled_snapshot_when_binary_absent() -> None:
    # Runner returns None for everything (binary missing) -> snapshot is used.
    census = collect_puku_census(runner=lambda args: None)
    assert "snapshot" in census.source.lower()
    ids = {c.id for c in census.capabilities}
    # The snapshot is the real surface; these are the high-value copycat gaps.
    assert "flag:max-budget-usd" in ids
    assert "flag:permission-mode" in ids
    assert "flag:output-format" in ids
    assert "cmd:doctor" in ids


# --- Second target: codex ---------------------------------------------------


def test_codex_collector_uses_snapshot_offline() -> None:
    census = collect_codex_census(runner=lambda args: None)
    assert census.target == CODEX_TARGET_ID
    assert "snapshot" in census.source.lower()
    ids = {c.id for c in census.capabilities}
    # Real codex surface from the bundled snapshot.
    assert "flag:model" in ids
    assert "flag:sandbox" in ids
    assert "cmd:exec" in ids
    assert "cmd:resume" in ids
    # The wrapped-description noise must NOT appear (parser hardening).
    assert "cmd:the" not in ids
    assert "cmd:working" not in ids


def test_codex_version_extracted_from_codex_cli_format() -> None:
    def fake_runner(args: list[str]) -> str | None:
        if args[:1] == ["--help"]:
            return "Options:\n  -m, --model <MODEL>   model\n"
        if args[:1] == ["--version"]:
            return "codex-cli 0.141.0"  # name precedes version
        return None

    census = collect_codex_census(runner=fake_runner)
    assert census.target_version == "0.141.0"


def test_collect_census_dispatches_both_targets() -> None:
    assert has_collector(PUKU_TARGET_ID)
    assert has_collector(CODEX_TARGET_ID)
    puku = collect_census(PUKU_TARGET_ID, runner=lambda args: None)
    codex = collect_census(CODEX_TARGET_ID, runner=lambda args: None)
    assert puku.target == PUKU_TARGET_ID
    assert codex.target == CODEX_TARGET_ID
