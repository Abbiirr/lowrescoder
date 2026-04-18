"""Scenario: model-picker — open /model picker, type a filter, capture state.

Unlocks the `picker_filter_accepts_input` hard predicate per Codex
Entry 1154 Phase 2 sequencing #1.

Flow:
  1. Boot drain (launcher's boot_budget_s)
  2. Settle
  3. Send `/model` + CR to open the picker
  4. Settle (picker renders)
  5. Type `cod` one char at a time (filter text should appear in picker header)
  6. Final drain; capture includes the `[filter: cod]` header
"""
from __future__ import annotations

from dataclasses import dataclass

NAME = "model-picker"


@dataclass
class ScenarioSpec:
    name: str
    steps: list[float | str]
    drain_quiet_s: float
    drain_maxwait_s: float


def spec() -> ScenarioSpec:
    return ScenarioSpec(
        name=NAME,
        steps=[
            2.0,        # settle after boot drain
            "/", 0.05,
            "m", 0.05,
            "o", 0.05,
            "d", 0.05,
            "e", 0.05,
            "l", 0.05,
            "\r",       # Enter — opens picker
            2.0,        # wait for picker to render
            "c", 0.08,
            "o", 0.08,
            "d", 0.08,
            1.5,        # wait for filter to apply
        ],
        drain_quiet_s=1.2,
        drain_maxwait_s=6.0,
    )
