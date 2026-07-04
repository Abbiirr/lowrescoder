"""Live-binary guard tests for copycat Channel A against the real ``puku-cli``.

These run only when the ``puku-cli`` binary is installed (skipped otherwise, e.g.
in CI without it). They guard two things the unit/snapshot tests cannot:

  1. the real ``--help`` parser keeps working across puku-cli version drift, and
  2. the five features AutoCode copied from puku-cli stay wired into its manifest
     (a regression here means a copied capability was removed/renamed).
"""

from __future__ import annotations

import re
import shutil

import pytest

from autocode.anvil.gapdiff import gap_diff
from autocode.anvil.manifest import autocode_manifest
from autocode.anvil.targets import PUKU_TARGET_ID, collect_census

pytestmark = pytest.mark.skipif(
    shutil.which("puku-cli") is None,
    reason="puku-cli binary not installed",
)

# The capabilities the copycat census must always recover from the live surface.
_HEADLINE_FLAGS = {
    "flag:max-budget-usd",
    "flag:permission-mode",
    "flag:output-format",
    "flag:add-dir",
    "flag:system-prompt",
    "flag:append-system-prompt",
}

# The puku-cli features AutoCode has copied clean-room — must stay present.
_COPIED_FLAGS = {
    "flag:permission-mode",
    "flag:max-budget-usd",
    "flag:system-prompt",
    "flag:append-system-prompt",
    "flag:add-dir",
    "flag:output-format",
}


def test_live_census_parses_real_surface() -> None:
    census = collect_census(PUKU_TARGET_ID)
    assert census.target == PUKU_TARGET_ID
    # Version looks like a real semver from `puku-cli --version`.
    assert re.match(r"^\d+\.\d+", census.target_version or ""), census.target_version
    # A real CLI has a substantial surface — guards a parser that silently empties.
    assert len(census.capabilities) >= 40
    ids = {c.id for c in census.capabilities}
    missing = _HEADLINE_FLAGS - ids
    assert not missing, f"live census lost headline flags: {missing}"


def test_copied_features_stay_present_in_manifest() -> None:
    census = collect_census(PUKU_TARGET_ID)
    report = gap_diff(census, autocode_manifest())
    present_ids = {p.capability.id for p in report.present}
    regressed = _COPIED_FLAGS - present_ids
    assert not regressed, f"copied puku-cli features no longer in AutoCode manifest: {regressed}"


def test_no_unimplemented_suitable_gaps_remain() -> None:
    # Invariant: every capability the gap-diff classifies clean-room-suitable has
    # been implemented (is present), so there are no suitable gaps left dangling.
    census = collect_census(PUKU_TARGET_ID)
    report = gap_diff(census, autocode_manifest())
    suitable = [g.capability.id for g in report.suitable_gaps()]
    assert suitable == [], f"unimplemented clean-room-suitable gaps: {suitable}"
