"""Scenario: first-prompt-text — send "hello" and capture the response path.

Tests the basic-turn invariant: user sends a message, spinner shows
up, a response streams back, and the composer becomes usable again.
"""
from __future__ import annotations

from dataclasses import dataclass

NAME = "first-prompt-text"


@dataclass
class ScenarioSpec:
    name: str
    steps: list[float | str]
    drain_quiet_s: float
    drain_maxwait_s: float


def spec() -> ScenarioSpec:
    # Send keys individually with short delays — BubbleTea v2 handles one
    # key per select cycle better than a batched "hello\n" write, and
    # \r (CR) is the conventional Enter encoding for xterm-type terminals
    # rather than \n (LF).
    return ScenarioSpec(
        name=NAME,
        steps=[
            3.0,     # additional settle after the boot budget
            "h", 0.05,
            "e", 0.05,
            "l", 0.05,
            "l", 0.05,
            "o", 0.05,
            "\r",    # Enter — CR, not LF
            8.0,     # wait for mock-backend response cycle
        ],
        drain_quiet_s=1.5,
        drain_maxwait_s=10.0,
    )
