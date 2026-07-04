"""Scenario: ask-user-prompt — exercise the modal on_ask_user flow.

Unlocks the ``approval_prompt_keyboard_interactive`` hard predicate per
Codex Entry 1154 Phase 2 sequencing #2.

Flow:
  1. Boot drain (launcher's boot_budget_s)
  2. Settle
  3. Type the magic ``__ASK_USER__`` trigger in the composer. The mock
     backend detects the substring and emits an ``on_ask_user`` request
     instead of a plain chat response.
  4. Press Enter to send the chat message.
  5. Wait long enough for the modal to render (question + options +
     keyboard hint) and leave capture there — we deliberately do NOT
     answer the modal, so the final captured frame still shows it.

The pending ``on_ask_user`` request is discarded when the TUI process is
torn down at end-of-capture — the mock's wait loop times out cleanly.
"""
from __future__ import annotations

from dataclasses import dataclass

NAME = "ask-user-prompt"


@dataclass
class ScenarioSpec:
    name: str
    steps: list[float | str]
    drain_quiet_s: float
    drain_maxwait_s: float


def spec() -> ScenarioSpec:
    trigger = list("__ASK_USER__ please continue")
    typed: list[float | str] = []
    for ch in trigger:
        typed.append(ch)
        typed.append(0.04)

    return ScenarioSpec(
        name=NAME,
        steps=[
            2.5,        # settle after boot drain
            *typed,
            "\r",       # Enter — sends the chat message with the trigger
            4.0,        # wait for mock to emit on_ask_user and modal to render
        ],
        drain_quiet_s=1.5,
        drain_maxwait_s=8.0,
    )
