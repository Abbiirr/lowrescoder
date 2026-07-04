"""Scripted scenarios for the AutoCode TUI visual snapshot pipeline."""

from __future__ import annotations

try:
    from .capture import Scenario  # package-style import
except ImportError:  # direct-script import fallback
    from capture import Scenario  # type: ignore[no-redef]

__all__ = ["SCENARIOS"]


# graceful_exit=False everywhere so pyte sees the alt-screen buffer in its
# live state. With Ctrl+D, BubbleTea restores the saved primary buffer and
# the pyte Screen shows post-exit state instead of the running TUI.
SCENARIOS: list[Scenario] = [
    Scenario(
        name="startup",
        steps=[1.0],  # let header + status bar render
        drain_maxwait_s=4.0,
        graceful_exit=False,
    ),
    Scenario(
        name="model_picker_open",
        steps=[
            0.8,       # let header render
            "/model\n",
            2.0,       # let backend respond + picker render
        ],
        drain_maxwait_s=5.0,
        graceful_exit=False,
    ),
    Scenario(
        name="model_picker_filtered",
        steps=[
            0.8,
            "/model\n",
            2.0,
            "cod",
            0.6,
        ],
        drain_maxwait_s=5.0,
        graceful_exit=False,
    ),
    Scenario(
        name="palette_open",
        steps=[
            0.8,
            "\x0b",    # Ctrl+K
            0.6,
        ],
        drain_maxwait_s=3.0,
        graceful_exit=False,
    ),
]
