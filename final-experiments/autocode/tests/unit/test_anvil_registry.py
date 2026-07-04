"""Tests for the Anvil copycat authorization registry (the hard gate).

Per PLAN_05 §1: no channel may run against a target not listed in the registry,
nor a channel not enabled for that target. `weights` scope additionally requires a
recorded per-provider ToS check. Enforcement is an assertion that fails the run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.anvil.registry import (
    RegistryError,
    Target,
    load_registry,
)

SAMPLE = """
targets:
  - id: puku-cli
    channel: [structural]
    source: "puku-cli --help (local binary)"
    license: "review-before-use"
    reuse_scope: structure_only
    notes: "Observable CLI surface only. Do NOT vendor verbatim code."

  - id: gateway-thinking-alias
    channel: [outcome, self_distill]
    source: "http://localhost:4000/v1"
    license: "per-provider-ToS"
    reuse_scope: outcomes
    rate_limit: { runs_per_day: 50 }

  - id: frontier-distill
    channel: [outcome]
    source: "http://localhost:4000/v1"
    license: "per-provider-ToS"
    reuse_scope: weights
    tos_check:
      provider: example
      reviewed_on: "2026-06-21"
      clause_summary: "outputs may be used for training"
"""


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    p = tmp_path / "registry.yaml"
    p.write_text(SAMPLE)
    return p


def test_load_registry_parses_targets(registry_path: Path) -> None:
    reg = load_registry(registry_path)
    assert set(reg.targets) == {"puku-cli", "gateway-thinking-alias", "frontier-distill"}
    puku = reg.get("puku-cli")
    assert isinstance(puku, Target)
    assert puku.channel == ("structural",)
    assert puku.reuse_scope == "structure_only"


def test_unknown_target_is_refused(registry_path: Path) -> None:
    reg = load_registry(registry_path)
    with pytest.raises(RegistryError, match="not in the registry"):
        reg.get("claude-code")


def test_channel_not_enabled_is_refused(registry_path: Path) -> None:
    reg = load_registry(registry_path)
    # puku-cli only permits the structural channel.
    reg.assert_channel_allowed("puku-cli", "structural")  # no raise
    with pytest.raises(RegistryError, match="channel 'outcome' is not enabled"):
        reg.assert_channel_allowed("puku-cli", "outcome")


def test_structure_only_permits_structural_scope(registry_path: Path) -> None:
    reg = load_registry(registry_path)
    reg.assert_reuse_scope("puku-cli", "structure_only")  # no raise


def test_weights_without_scope_is_refused(registry_path: Path) -> None:
    reg = load_registry(registry_path)
    # gateway-thinking-alias is reuse_scope: outcomes — weights must be refused.
    with pytest.raises(RegistryError, match="reuse_scope"):
        reg.assert_reuse_scope("gateway-thinking-alias", "weights")


def test_weights_requires_recorded_tos_check(registry_path: Path, tmp_path: Path) -> None:
    reg = load_registry(registry_path)
    # frontier-distill HAS a tos_check recorded — weights allowed.
    reg.assert_reuse_scope("frontier-distill", "weights")  # no raise

    # Remove the ToS check -> weights must be refused even with the right scope.
    bad = tmp_path / "bad.yaml"
    bad.write_text(SAMPLE.split("    tos_check:")[0])  # drop the tos_check block
    reg2 = load_registry(bad)
    with pytest.raises(RegistryError, match="ToS"):
        reg2.assert_reuse_scope("frontier-distill", "weights")


def test_invalid_channel_value_rejected(tmp_path: Path) -> None:
    p = tmp_path / "r.yaml"
    p.write_text(
        "targets:\n"
        "  - id: x\n"
        "    channel: [bogus]\n"
        "    source: y\n"
        "    license: z\n"
        "    reuse_scope: structure_only\n"
    )
    with pytest.raises(RegistryError, match="invalid channel"):
        load_registry(p)


def test_invalid_reuse_scope_rejected(tmp_path: Path) -> None:
    p = tmp_path / "r.yaml"
    p.write_text(
        "targets:\n"
        "  - id: x\n"
        "    channel: [structural]\n"
        "    source: y\n"
        "    license: z\n"
        "    reuse_scope: bogus\n"
    )
    with pytest.raises(RegistryError, match="invalid reuse_scope"):
        load_registry(p)


# --- The on-disk registry and the §5.2 reference targets -------------------- #

_SHIPPED_REGISTRY = (
    Path(__file__).resolve().parents[2] / "anvil" / "copycat" / "registry.yaml"
)

# The seven reference source-map targets PLAN_05 §5.2 requires.
_REFERENCE_TARGETS = (
    "claude-code",
    "openai-codex",
    "opencode",
    "aider",
    "pi-mono",
    "open-swe",
    "goose",
)


def test_shipped_registry_validates_and_lists_reference_targets() -> None:
    reg = load_registry(_SHIPPED_REGISTRY)
    for tid in _REFERENCE_TARGETS:
        target = reg.get(tid)  # raises RegistryError if missing/invalid
        assert "structural" in target.channel
        # §5.2 registers these at the most ToS-sensitive scope.
        assert target.reuse_scope == "weights"


def test_reference_targets_block_weights_without_recorded_tos() -> None:
    # No `tos-check` command exists yet to record the ToS read, so a `weights`
    # run against a reference target is correctly refused (the safe default).
    reg = load_registry(_SHIPPED_REGISTRY)
    for tid in _REFERENCE_TARGETS:
        with pytest.raises(RegistryError, match="ToS"):
            reg.assert_reuse_scope(tid, "weights")
        # Structural study (Channel A) is still permitted.
        reg.assert_channel_allowed(tid, "structural")
