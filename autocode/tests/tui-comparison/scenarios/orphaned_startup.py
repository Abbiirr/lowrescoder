"""Scenario: orphaned-startup — backend never sends on_status.

Unlocks the ``startup_timeout_fires_when_backend_absent`` hard
predicate per Codex Entry 1154 Phase 2 sequencing #4.

Flow:
  1. Launch autocode-tui with ``silent_backend.py`` as
     ``AUTOCODE_PYTHON_CMD``. The silent backend reads stdin but never
     emits ``on_status`` or any JSON-RPC response.
  2. Boot-budget window is 18s so the TUI's 15s
     ``startupTimeoutDuration`` fires inside the capture.
  3. No scripted keystrokes — the captured frame should already show
     the startup-timeout error.

Predicate verifies the captured frame contains the canonical
``Backend not connected`` / ``startup timeout`` error text.
"""
from __future__ import annotations

from dataclasses import dataclass

NAME = "orphaned-startup"

# Override the launcher to plug in the silent backend + give the TUI
# enough time for the 15s startup timeout to fire.
LAUNCHER_KWARGS = {
    "backend_script": "silent_backend.py",
    "boot_budget_s": 18.0,
}


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
            # Add 2 extra seconds of settle after the 18s boot budget so
            # the startup-timeout banner has time to render. No keys are
            # sent — the error frame is the entire evidence we assert on.
            2.0,
        ],
        drain_quiet_s=1.5,
        drain_maxwait_s=4.0,
    )
