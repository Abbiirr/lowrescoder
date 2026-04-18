"""Scenario: spinner-cadence — verify the spinner actually rotates.

Unlocks the ``spinner_frame_updates_over_time`` hard predicate per
Codex Entry 1154 Phase 2 sequencing #5.

Flow:
  1. Boot drain
  2. Settle
  3. Send ``__SLOW__ hold the spinner`` via chat. The mock backend
     detects the trigger and holds tokens for ~2 seconds before
     responding, which gives the braille spinner time to rotate across
     multiple frames.
  4. Drain until on_done flushes.

Predicate scans the **raw ANSI byte stream** (not just the final pyte
frame) for at least two distinct braille spinner glyphs appearing over
time.
"""
from __future__ import annotations

from dataclasses import dataclass

NAME = "spinner-cadence"


@dataclass
class ScenarioSpec:
    name: str
    steps: list[float | str]
    drain_quiet_s: float
    drain_maxwait_s: float


def spec() -> ScenarioSpec:
    trigger = list("__SLOW__ hold the spinner")
    typed: list[float | str] = []
    for ch in trigger:
        typed.append(ch)
        typed.append(0.04)

    return ScenarioSpec(
        name=NAME,
        steps=[
            2.5,        # settle after boot drain
            *typed,
            "\r",       # Enter — triggers the slow chat response
            4.5,        # 2s mock pause + 1s tokens + 1.5s margin
        ],
        drain_quiet_s=1.5,
        drain_maxwait_s=8.0,
    )
