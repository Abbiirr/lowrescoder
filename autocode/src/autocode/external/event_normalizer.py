"""Event normalization layer for external harness adapters.

Converts raw native CLI output (JSON lines, structured streams, plain text)
into the canonical HarnessEvent sequence defined in harness_adapter.py.

Also provides bridging from HarnessEvent into AutoCode's internal
OrchestratorEvent model (PLAN.md Section 2.1).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from autocode.external.harness_adapter import (
    HarnessEvent,
    HarnessEventType,
)


def normalize_json_line(
    line: str,
    session_id: str,
    run_id: str,
    kind_map: dict[str, HarnessEventType] | None = None,
) -> HarnessEvent | None:
    """Parse one JSON line and return a normalized HarnessEvent.

    Args:
        line: Raw JSON string from native CLI output
        session_id: Current session identifier
        run_id: Current run identifier
        kind_map: Optional mapping from native event type strings to
            HarnessEventType values (adapter-specific)

    Returns:
        HarnessEvent or None if the line is not parseable
    """
    line = line.strip()
    if not line:
        return None

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        # Plain text line — emit as stdout
        return HarnessEvent(
            event_type=HarnessEventType.STDOUT,
            session_id=session_id,
            run_id=run_id,
            raw_text=line,
        )

    if not isinstance(data, dict):
        return None

    # Determine event type from native payload
    native_type = (data.get("type") or data.get("event") or data.get("kind") or "").lower()

    event_type = HarnessEventType.MESSAGE  # default
    if kind_map and native_type in kind_map:
        event_type = kind_map[native_type]
    elif native_type in _DEFAULT_KIND_MAP:
        event_type = _DEFAULT_KIND_MAP[native_type]

    return HarnessEvent(
        event_type=event_type,
        session_id=session_id,
        run_id=run_id,
        payload=data,
        raw_text=line,
    )


def normalize_stream(
    lines: Iterator[str],
    session_id: str,
    run_id: str,
    kind_map: dict[str, HarnessEventType] | None = None,
) -> Iterator[HarnessEvent]:
    """Normalize a stream of raw output lines into HarnessEvents.

    Yields HarnessEvent objects for each parseable line.
    """
    for line in lines:
        event = normalize_json_line(line, session_id, run_id, kind_map)
        if event is not None:
            yield event


def make_event(
    event_type: HarnessEventType,
    session_id: str,
    run_id: str,
    payload: dict[str, Any] | None = None,
    raw_text: str = "",
) -> HarnessEvent:
    """Convenience factory for creating HarnessEvents."""
    return HarnessEvent(
        event_type=event_type,
        session_id=session_id,
        run_id=run_id,
        payload=payload or {},
        raw_text=raw_text,
    )


# Default mapping from common native event type strings to HarnessEventType
_DEFAULT_KIND_MAP: dict[str, HarnessEventType] = {
    # Common across harnesses
    "message": HarnessEventType.MESSAGE,
    "text": HarnessEventType.MESSAGE,
    "assistant": HarnessEventType.MESSAGE,
    "tool_use": HarnessEventType.TOOL_CALL,
    "tool_call": HarnessEventType.TOOL_CALL,
    "tool_result": HarnessEventType.TOOL_CALL,
    "result": HarnessEventType.RESULT,
    "error": HarnessEventType.ERROR,
    "stdout": HarnessEventType.STDOUT,
    "stderr": HarnessEventType.STDERR,
    # Claude Code specific
    "system": HarnessEventType.MESSAGE,
    "user": HarnessEventType.MESSAGE,
    # Codex specific
    "patch": HarnessEventType.ARTIFACT,
    "completion": HarnessEventType.RESULT,
    # Forge specific
    "thinking": HarnessEventType.MESSAGE,
    "approval_request": HarnessEventType.APPROVAL,
}


# Per-harness kind maps for use by concrete adapters
CLAUDE_CODE_KIND_MAP: dict[str, HarnessEventType] = {
    "system": HarnessEventType.MESSAGE,
    "assistant": HarnessEventType.MESSAGE,
    "user": HarnessEventType.MESSAGE,
    "tool_use": HarnessEventType.TOOL_CALL,
    "tool_result": HarnessEventType.TOOL_CALL,
    "result": HarnessEventType.RESULT,
    "error": HarnessEventType.ERROR,
}

CODEX_KIND_MAP: dict[str, HarnessEventType] = {
    "message": HarnessEventType.MESSAGE,
    "patch": HarnessEventType.ARTIFACT,
    "completion": HarnessEventType.RESULT,
    "error": HarnessEventType.ERROR,
}

OPENCODE_KIND_MAP: dict[str, HarnessEventType] = {
    "message": HarnessEventType.MESSAGE,
    "tool_call": HarnessEventType.TOOL_CALL,
    "result": HarnessEventType.RESULT,
    "error": HarnessEventType.ERROR,
}

FORGE_KIND_MAP: dict[str, HarnessEventType] = {
    "thinking": HarnessEventType.MESSAGE,
    "message": HarnessEventType.MESSAGE,
    "tool_call": HarnessEventType.TOOL_CALL,
    "approval_request": HarnessEventType.APPROVAL,
    "result": HarnessEventType.RESULT,
    "error": HarnessEventType.ERROR,
}


# --- Section 2.1: Bridge from HarnessEvent → OrchestratorEvent ---

_HARNESS_TO_ORCHESTRATOR_MAP: dict[str, str] = {
    HarnessEventType.SESSION_STARTED: "session_started",
    HarnessEventType.RUN_STARTED: "task_created",
    HarnessEventType.STDOUT: "tool_completed",
    HarnessEventType.STDERR: "tool_completed",
    HarnessEventType.MESSAGE: "message_sent",
    HarnessEventType.TOOL_CALL: "tool_called",
    HarnessEventType.APPROVAL: "approval_requested",
    HarnessEventType.ARTIFACT: "tool_completed",
    HarnessEventType.RESULT: "task_completed",
    HarnessEventType.ERROR: "task_failed",
    HarnessEventType.RUN_FINISHED: "task_completed",
    HarnessEventType.SESSION_CLOSED: "session_ended",
}


def harness_event_to_orchestrator_dict(event: HarnessEvent) -> dict[str, Any]:
    """Convert a HarnessEvent into an OrchestratorEvent-compatible dict.

    This bridges the external harness event model into AutoCode's internal
    orchestration event model, so external harness runs feed into the same
    audit trail and metrics pipeline.

    Args:
        event: A normalized HarnessEvent from any adapter.

    Returns:
        A dict that can be used to construct an OrchestratorEvent.
    """
    from autocode.agent.events import EventType

    orch_type_str = _HARNESS_TO_ORCHESTRATOR_MAP.get(event.event_type, "message_sent")

    orch_type = _resolve_event_type(orch_type_str, EventType)

    return {
        "event_type": orch_type,
        "session_id": event.session_id,
        "task_id": event.run_id,
        "payload": {
            "harness_event_type": event.event_type.value
            if isinstance(event.event_type, HarnessEventType)
            else str(event.event_type),
            "raw_text": event.raw_text,
            **event.payload,
        },
        "metadata": {
            "source": "external_harness",
        },
    }


def stream_as_orchestrator_events(
    harness_events: Iterator[HarnessEvent],
) -> Iterator[dict[str, Any]]:
    """Convert a stream of HarnessEvents into OrchestratorEvent-compatible dicts.

    This is the main integration point: concrete adapters yield HarnessEvents
    from stream_events(), and this function bridges them into the internal
    orchestration pipeline.
    """
    for event in harness_events:
        yield harness_event_to_orchestrator_dict(event)


def _resolve_event_type(type_str: str, event_type_cls: type) -> Any:
    """Resolve a string to an EventType enum value."""
    try:
        return event_type_cls(type_str)
    except (ValueError, AttributeError):
        try:
            members = list(getattr(event_type_cls, "__members__", {}).values())
            return members[0] if members else type_str
        except (AttributeError, IndexError):
            return type_str
