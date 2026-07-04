"""Ralph long-horizon recovery detection and message construction."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from autocode.agent.hooks import AgentHookBase
from autocode.session.intent_store import Intent

TelemetryEmit = Callable[[str, dict[str, object]], None]
IntentProvider = Callable[[], Intent | None]
RecoveryInjector = Callable[[str], None]
RecoveryCompactor = Callable[[], None]


@dataclass(slots=True)
class RalphAgentState:
    """Minimal turn state needed to decide whether Ralph should fire."""

    turn_index: int
    assistant_message: str = ""
    tool_calls_last_turn: int = 0
    zero_progress_turns: int = 0
    zero_tool_turns: int = 0
    context_fraction: float = 0.0
    recoveries_fired: int = 0


@dataclass(frozen=True, slots=True)
class RalphRecoveryDecision:
    """Decision returned by the recovery detector."""

    should_recover: bool
    trigger_kind: str
    reason: str
    context_fraction: float = 0.0


@dataclass(frozen=True, slots=True)
class RalphRecoveryResult:
    """Result returned after attempting recovery."""

    recovered: bool
    message: str
    trigger_kind: str
    recoveries_fired: int


class RalphRecoveryDetector:
    """Detect give-up/stagnation/context-saturation recovery triggers."""

    GIVE_UP_PHRASES = (
        "i'll stop here",
        "i will stop here",
        "this is too complex",
        "unable to continue",
        "i'm unable to continue",
        "i am unable to continue",
        "not sure how to proceed",
        "cannot proceed",
    )
    MAX_RECOVERIES_PER_SESSION = 3
    CONTEXT_SATURATION_FRACTION = 0.85

    def check(self, state: RalphAgentState) -> RalphRecoveryDecision:
        """Return whether recovery should fire for the current state."""

        if state.turn_index <= 1:
            return RalphRecoveryDecision(False, "first_turn", "Ralph never fires on turn 1")
        if state.recoveries_fired >= self.MAX_RECOVERIES_PER_SESSION:
            return RalphRecoveryDecision(
                False,
                "cap_exceeded",
                "Ralph recovery cap reached for this session",
                state.context_fraction,
            )

        message = state.assistant_message.lower()
        if state.tool_calls_last_turn == 0 and any(
            phrase in message for phrase in self.GIVE_UP_PHRASES
        ):
            return RalphRecoveryDecision(
                True,
                "give_up_phrase",
                "Assistant produced a give-up phrase without calling tools",
                state.context_fraction,
            )
        if state.zero_progress_turns >= 3:
            return RalphRecoveryDecision(
                True,
                "stagnation",
                "Three consecutive zero-progress turns detected",
                state.context_fraction,
            )
        if (
            state.context_fraction > self.CONTEXT_SATURATION_FRACTION
            and state.zero_tool_turns >= 3
        ):
            return RalphRecoveryDecision(
                True,
                "context_saturation",
                "Context is saturated and recent turns had no tool calls",
                state.context_fraction,
            )

        return RalphRecoveryDecision(
            False,
            "none",
            "No Ralph recovery trigger matched",
            state.context_fraction,
        )


class RalphLoop:
    """Construct recovery messages from persisted intent and detector state."""

    def __init__(
        self,
        detector: RalphRecoveryDetector | None = None,
        telemetry_emit: TelemetryEmit | None = None,
    ) -> None:
        self.detector = detector or RalphRecoveryDetector()
        self.telemetry_emit = telemetry_emit

    def maybe_recover(
        self,
        intent: Intent,
        state: RalphAgentState,
    ) -> RalphRecoveryResult:
        """Return a recovery message when the detector fires."""

        if _ralph_disabled():
            return RalphRecoveryResult(
                recovered=False,
                message="",
                trigger_kind="disabled",
                recoveries_fired=state.recoveries_fired,
            )

        decision = self.detector.check(state)
        if not decision.should_recover:
            return RalphRecoveryResult(
                recovered=False,
                message="",
                trigger_kind=decision.trigger_kind,
                recoveries_fired=state.recoveries_fired,
            )

        recoveries_fired = state.recoveries_fired + 1
        if self.telemetry_emit is not None:
            self.telemetry_emit(
                "ralph_recovery_fired",
                {
                    "trigger_kind": decision.trigger_kind,
                    "context_fraction": decision.context_fraction,
                    "recoveries_fired": recoveries_fired,
                },
            )
        return RalphRecoveryResult(
            recovered=True,
            message=self._recovery_message(intent, decision),
            trigger_kind=decision.trigger_kind,
            recoveries_fired=recoveries_fired,
        )

    def _recovery_message(
        self,
        intent: Intent,
        decision: RalphRecoveryDecision,
    ) -> str:
        sections = [
            "[Ralph recovery — session resumed after context exhaustion]",
            "",
            f"Original goal: {intent.original_goal}",
        ]
        if intent.success_criteria:
            sections.append("Success criteria:")
            sections.extend(f"- {criterion}" for criterion in intent.success_criteria)
        if intent.constraints:
            sections.append("Constraints:")
            sections.extend(f"- {constraint}" for constraint in intent.constraints)
        if intent.progress_so_far:
            sections.append("Progress so far:")
            sections.extend(f"- {progress}" for progress in intent.progress_so_far)
        sections.append(f"Recovery trigger: {decision.trigger_kind}")
        return "\n".join(sections)


def _ralph_disabled() -> bool:
    return os.environ.get("AUTOCODE_DISABLE_RALPH", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class RalphRecoveryHook(AgentHookBase):
    """Hook adapter that evaluates Ralph recovery after a completed turn."""

    def __init__(
        self,
        *,
        recovery_loop: RalphLoop,
        intent_provider: IntentProvider,
        inject_recovery: RecoveryInjector,
        compact_for_recovery: RecoveryCompactor | None = None,
    ) -> None:
        self._recovery_loop = recovery_loop
        self._intent_provider = intent_provider
        self._inject_recovery = inject_recovery
        self._compact_for_recovery = compact_for_recovery
        self._turn_index = 0
        self._assistant_chunks: list[str] = []
        self._tool_calls_last_turn = 0
        self._zero_tool_turns = 0
        self._recoveries_fired = 0
        self.last_result: RalphRecoveryResult | None = None

    @property
    def recoveries_fired(self) -> int:
        return self._recoveries_fired

    def pre_turn(self, turn_id: str) -> None:
        self._turn_index += 1
        self._assistant_chunks.clear()
        self._tool_calls_last_turn = 0

    def pre_tool_call(self, tc: object) -> None:
        self._tool_calls_last_turn += 1

    def on_token(self, text: str) -> None:
        self._assistant_chunks.append(text)

    def post_turn(self, turn_id: str, status: str) -> None:
        intent = self._intent_provider()
        if intent is None:
            return
        if self._tool_calls_last_turn == 0:
            self._zero_tool_turns += 1
        else:
            self._zero_tool_turns = 0
        result = self._recovery_loop.maybe_recover(
            intent,
            RalphAgentState(
                turn_index=self._turn_index,
                assistant_message="".join(self._assistant_chunks),
                tool_calls_last_turn=self._tool_calls_last_turn,
                zero_tool_turns=self._zero_tool_turns,
                recoveries_fired=self._recoveries_fired,
            ),
        )
        self.last_result = result
        self._recoveries_fired = result.recoveries_fired
        if result.recovered:
            if self._compact_for_recovery is not None:
                self._compact_for_recovery()
            self._inject_recovery(result.message)
