"""Scenario: error-state — deliberate mid-session WARNING emission.

Unlocks the ``warnings_render_dim_not_red_banner`` hard predicate per
Codex Entry 1154 Phase 2 sequencing #3.

Flow:
  1. Boot drain (launcher's boot_budget_s); captures initial WARNING.
  2. Settle
  3. Send ``__WARNING__ trigger`` via chat. The mock backend detects
     the trigger and emits a fresh WARNING to stderr before tokens.
  4. Drain for token stream + on_done.

Predicate verifies the WARNING is rendered with a dim ``⚠`` marker and
NOT wrapped in a red ``Error:`` banner.
"""
from __future__ import annotations

from dataclasses import dataclass

NAME = "error-state"


@dataclass
class ScenarioSpec:
    name: str
    steps: list[float | str]
    drain_quiet_s: float
    drain_maxwait_s: float


def spec() -> ScenarioSpec:
    trigger = list("__WARNING__ deliberate test")
    typed: list[float | str] = []
    for ch in trigger:
        typed.append(ch)
        typed.append(0.04)

    return ScenarioSpec(
        name=NAME,
        steps=[
            2.5,        # settle after boot drain
            *typed,
            "\r",       # Enter — send chat with warning trigger
            3.0,        # wait for warning emission + on_done
        ],
        drain_quiet_s=1.2,
        drain_maxwait_s=6.0,
    )
