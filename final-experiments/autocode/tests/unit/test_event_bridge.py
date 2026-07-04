"""Tests for HarnessEvent → OrchestratorEvent bridge (PLAN.md Section 2.1)."""

from autocode.external.event_normalizer import (
    harness_event_to_orchestrator_dict,
    make_event,
)
from autocode.external.harness_adapter import HarnessEventType


class TestHarnessToOrchestratorMapping:
    """Test that each HarnessEventType maps to an OrchestratorEventType."""

    def test_session_started(self) -> None:
        """SESSION_STARTED maps to session_started."""
        event = make_event(HarnessEventType.SESSION_STARTED, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "session_started"

    def test_run_started(self) -> None:
        """RUN_STARTED maps to task_created."""
        event = make_event(HarnessEventType.RUN_STARTED, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "task_created"

    def test_tool_call(self) -> None:
        """TOOL_CALL maps to tool_called."""
        event = make_event(HarnessEventType.TOOL_CALL, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "tool_called"

    def test_approval(self) -> None:
        """APPROVAL maps to approval_requested."""
        event = make_event(HarnessEventType.APPROVAL, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "approval_requested"

    def test_result(self) -> None:
        """RESULT maps to task_completed."""
        event = make_event(HarnessEventType.RESULT, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "task_completed"

    def test_error(self) -> None:
        """ERROR maps to task_failed."""
        event = make_event(HarnessEventType.ERROR, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "task_failed"

    def test_message(self) -> None:
        """MESSAGE maps to message_sent."""
        event = make_event(HarnessEventType.MESSAGE, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "message_sent"

    def test_session_closed(self) -> None:
        """SESSION_CLOSED maps to session_ended."""
        event = make_event(HarnessEventType.SESSION_CLOSED, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["event_type"].value == "session_ended"


class TestBridgePreservesContext:
    """Test that the bridge preserves session/run context."""

    def test_session_id_preserved(self) -> None:
        """Session ID is preserved in the bridge."""
        event = make_event(HarnessEventType.MESSAGE, "my-session", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["session_id"] == "my-session"

    def test_run_id_as_task_id(self) -> None:
        """Run ID becomes task_id in orchestrator event."""
        event = make_event(HarnessEventType.MESSAGE, "s1", "my-run")
        result = harness_event_to_orchestrator_dict(event)
        assert result["task_id"] == "my-run"

    def test_payload_preserved(self) -> None:
        """Original payload is preserved inside the new payload."""
        event = make_event(
            HarnessEventType.TOOL_CALL,
            "s1",
            "r1",
            payload={"tool": "write_file"},
        )
        result = harness_event_to_orchestrator_dict(event)
        assert result["payload"]["tool"] == "write_file"

    def test_raw_text_preserved(self) -> None:
        """Raw text is preserved in the bridge payload."""
        event = make_event(
            HarnessEventType.STDOUT,
            "s1",
            "r1",
            raw_text="hello world",
        )
        result = harness_event_to_orchestrator_dict(event)
        assert result["payload"]["raw_text"] == "hello world"

    def test_source_metadata(self) -> None:
        """Metadata marks the event as from external harness."""
        event = make_event(HarnessEventType.MESSAGE, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["metadata"]["source"] == "external_harness"

    def test_harness_event_type_in_payload(self) -> None:
        """Original harness event type is preserved in payload."""
        event = make_event(HarnessEventType.TOOL_CALL, "s1", "r1")
        result = harness_event_to_orchestrator_dict(event)
        assert result["payload"]["harness_event_type"] == "tool_call"
