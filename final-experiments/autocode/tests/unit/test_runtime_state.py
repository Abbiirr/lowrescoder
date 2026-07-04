"""Tests for canonical runtime state (PLAN.md Section 0.3)."""

from autocode.agent.context import RuntimeState


class TestRuntimeState:
    """Test the RuntimeState dataclass."""

    def test_default_state(self) -> None:
        """Default state has sensible defaults."""
        state = RuntimeState()
        assert state.session_id == ""
        assert state.task_id == ""
        assert state.approval_mode == "suggest"
        assert state.agent_mode == "normal"
        assert state.checkpoint_stack == []
        assert state.pending_approvals == []
        assert state.working_set == []

    def test_full_state(self) -> None:
        """Can create with all fields."""
        state = RuntimeState(
            session_id="sess-123",
            task_id="task-456",
            approval_mode="auto",
            agent_mode="research",
            project_root="/test/project",
            working_set=["src/main.py", "src/util.py"],
            checkpoint_stack=["cp-1", "cp-2"],
            pending_approvals=["write_file:file.py"],
            subagent_registry=[" subtask-1"],
            current_plan_ref="plan-789",
            last_compact_summary="summarized...",
        )
        assert state.session_id == "sess-123"
        assert state.task_id == "task-456"
        assert state.approval_mode == "auto"
        assert state.agent_mode == "research"
        assert len(state.working_set) == 2
        assert len(state.checkpoint_stack) == 2


class TestRuntimeStateSerialization:
    """Test to_dict and from_dict."""

    def test_to_dict(self) -> None:
        """to_dict serializes all fields."""
        state = RuntimeState(
            session_id="sess-abc",
            approval_mode="auto",
        )
        d = state.to_dict()
        assert d["session_id"] == "sess-abc"
        assert d["approval_mode"] == "auto"

    def test_roundtrip(self) -> None:
        """from_dict → to_dict roundtrips correctly."""
        original = RuntimeState(
            session_id="roundtrip-test",
            task_id="task-999",
            agent_mode="build",
            checkpoint_stack=["checkpoint-a"],
        )
        serialized = original.to_dict()
        restored = RuntimeState.from_dict(serialized)
        assert restored.session_id == original.session_id
        assert restored.task_id == original.task_id
        assert restored.agent_mode == original.agent_mode
        assert restored.checkpoint_stack == original.checkpoint_stack

    def test_partial_dict(self) -> None:
        """from_dict handles missing keys gracefully."""
        partial = {"session_id": "minimal", "task_id": "t1"}
        state = RuntimeState.from_dict(partial)
        assert state.session_id == "minimal"
        assert state.task_id == "t1"
        assert state.approval_mode == "suggest"  # default
        assert state.last_compact_summary == ""  # default


class TestRuntimeStateFieldAccess:
    """Test field mutability."""

    def test_append_checkpoint(self) -> None:
        """Can append to checkpoint stack."""
        state = RuntimeState()
        state.checkpoint_stack.append("new-cp")
        assert "new-cp" in state.checkpoint_stack

    def test_append_approval(self) -> None:
        """Can append to pending approvals."""
        state = RuntimeState()
        state.pending_approvals.append("write_file:test.py")
        assert len(state.pending_approvals) == 1


class TestOrchestratorRuntimeState:
    """Test that Orchestrator owns and syncs RuntimeState."""

    def test_orchestrator_has_runtime_state(self) -> None:
        """Orchestrator exposes runtime_state property."""
        from autocode.agent.orchestrator import Orchestrator

        orch = Orchestrator(session_id="test-sess")
        assert orch.runtime_state is not None
        assert orch.runtime_state.session_id == "test-sess"

    def test_session_id_syncs_to_runtime_state(self) -> None:
        """Setting session_id on orchestrator syncs to runtime state."""
        from autocode.agent.orchestrator import Orchestrator

        orch = Orchestrator(session_id="initial")
        orch.session_id = "updated"
        assert orch.runtime_state.session_id == "updated"

    def test_custom_runtime_state(self) -> None:
        """Can pass custom RuntimeState to Orchestrator."""
        from autocode.agent.orchestrator import Orchestrator

        state = RuntimeState(
            session_id="custom",
            approval_mode="auto",
            working_set=["a.py"],
        )
        orch = Orchestrator(runtime_state=state)
        assert orch.runtime_state.approval_mode == "auto"
        assert orch.runtime_state.working_set == ["a.py"]
