from __future__ import annotations

from autocode.agent.ralph_loop import (
    RalphAgentState,
    RalphLoop,
    RalphRecoveryDetector,
    RalphRecoveryHook,
)
from autocode.session.intent_store import Intent


def test_detector_fires_on_give_up_phrase_with_zero_tool_calls() -> None:
    detector = RalphRecoveryDetector()
    state = RalphAgentState(
        turn_index=2,
        assistant_message="I'm not sure how to proceed, so I'll stop here.",
        tool_calls_last_turn=0,
    )

    decision = detector.check(state)

    assert decision.should_recover is True
    assert decision.trigger_kind == "give_up_phrase"


def test_detector_does_not_fire_on_first_turn() -> None:
    detector = RalphRecoveryDetector()
    state = RalphAgentState(
        turn_index=1,
        assistant_message="I'm unable to continue.",
        tool_calls_last_turn=0,
    )

    decision = detector.check(state)

    assert decision.should_recover is False
    assert decision.trigger_kind == "first_turn"


def test_detector_honors_cap_three_recoveries_per_session() -> None:
    detector = RalphRecoveryDetector()
    state = RalphAgentState(
        turn_index=5,
        assistant_message="This is too complex.",
        tool_calls_last_turn=0,
        recoveries_fired=3,
    )

    decision = detector.check(state)

    assert decision.should_recover is False
    assert decision.trigger_kind == "cap_exceeded"


def test_detector_fires_on_three_zero_progress_turns() -> None:
    detector = RalphRecoveryDetector()
    state = RalphAgentState(
        turn_index=4,
        assistant_message="No progress yet.",
        tool_calls_last_turn=1,
        zero_progress_turns=3,
    )

    decision = detector.check(state)

    assert decision.should_recover is True
    assert decision.trigger_kind == "stagnation"


def test_detector_fires_on_context_saturation_with_no_recent_tools() -> None:
    detector = RalphRecoveryDetector()
    state = RalphAgentState(
        turn_index=8,
        assistant_message="Continuing.",
        tool_calls_last_turn=0,
        zero_tool_turns=3,
        context_fraction=0.86,
    )

    decision = detector.check(state)

    assert decision.should_recover is True
    assert decision.trigger_kind == "context_saturation"


def test_loop_recovery_message_starts_with_ralph_recovery_and_increments_cap() -> None:
    events: list[tuple[str, dict[str, object]]] = []
    intent = Intent(
        session_id="session-1",
        original_goal="Finish the backend recovery loop.",
        captured_at="2026-05-04T00:00:00+00:00",
        success_criteria=["recovery message injected"],
        constraints=["do not auto-rollback"],
        progress_so_far=["Intent captured"],
    )
    loop = RalphLoop(telemetry_emit=lambda kind, data: events.append((kind, data)))
    state = RalphAgentState(
        turn_index=3,
        assistant_message="I'll stop here.",
        tool_calls_last_turn=0,
    )

    result = loop.maybe_recover(intent, state)

    assert result.recovered is True
    assert result.message.startswith("[Ralph recovery")
    assert "Finish the backend recovery loop." in result.message
    assert result.recoveries_fired == 1
    assert events == [
        (
            "ralph_recovery_fired",
            {
                "trigger_kind": "give_up_phrase",
                "context_fraction": 0.0,
                "recoveries_fired": 1,
            },
        )
    ]


def test_loop_honors_disable_env_var(monkeypatch) -> None:
    events: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setenv("AUTOCODE_DISABLE_RALPH", "true")
    intent = Intent(
        session_id="session-1",
        original_goal="Finish the backend recovery loop.",
        captured_at="2026-05-04T00:00:00+00:00",
    )
    loop = RalphLoop(telemetry_emit=lambda kind, data: events.append((kind, data)))
    state = RalphAgentState(
        turn_index=3,
        assistant_message="I'll stop here.",
        tool_calls_last_turn=0,
    )

    result = loop.maybe_recover(intent, state)

    assert result.recovered is False
    assert result.trigger_kind == "disabled"
    assert result.recoveries_fired == 0
    assert events == []


def test_recovery_hook_injects_message_after_give_up_turn() -> None:
    injected: list[str] = []
    intent = Intent(
        session_id="session-1",
        original_goal="Finish the backend recovery loop.",
        captured_at="2026-05-04T00:00:00+00:00",
    )
    hook = RalphRecoveryHook(
        recovery_loop=RalphLoop(),
        intent_provider=lambda: intent,
        inject_recovery=injected.append,
    )

    hook.pre_turn("turn-1")
    hook.on_token("Working on it.")
    hook.post_turn("turn-1", "completed")
    hook.pre_turn("turn-2")
    hook.on_token("I'm not sure how to proceed, so I'll stop here.")
    hook.post_turn("turn-2", "completed")

    assert len(injected) == 1
    assert injected[0].startswith("[Ralph recovery")
    assert hook.recoveries_fired == 1
    assert hook.last_result is not None
    assert hook.last_result.trigger_kind == "give_up_phrase"


def test_recovery_hook_compacts_before_injecting_message() -> None:
    events: list[str] = []
    intent = Intent(
        session_id="session-1",
        original_goal="Finish the backend recovery loop.",
        captured_at="2026-05-04T00:00:00+00:00",
    )
    hook = RalphRecoveryHook(
        recovery_loop=RalphLoop(),
        intent_provider=lambda: intent,
        inject_recovery=lambda message: events.append(f"inject:{message}"),
        compact_for_recovery=lambda: events.append("compact"),
    )

    hook.pre_turn("turn-1")
    hook.on_token("Working on it.")
    hook.post_turn("turn-1", "completed")
    hook.pre_turn("turn-2")
    hook.on_token("I'm not sure how to proceed, so I'll stop here.")
    hook.post_turn("turn-2", "completed")

    assert events[0] == "compact"
    assert events[1].startswith("inject:[Ralph recovery")
