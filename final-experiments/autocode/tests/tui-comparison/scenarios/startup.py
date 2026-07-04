"""Scenario: startup — capture the TUI's empty-state boot frame.

Feeds no scripted input; relies entirely on the boot-budget drain to
collect the initial render. This is the cheapest, fastest scenario
and is the minimum smoke signal for the substrate.
"""
from __future__ import annotations

from dataclasses import dataclass

NAME = "startup"


@dataclass
class ScenarioSpec:
    name: str
    steps: list[float | str]
    drain_quiet_s: float
    drain_maxwait_s: float


def spec() -> ScenarioSpec:
    return ScenarioSpec(
        name=NAME,
        steps=[],  # no scripted input — just drain boot output
        drain_quiet_s=1.0,
        drain_maxwait_s=3.0,
    )
