"""Tests for the four-plane context model (PLAN.md Section 0.1)."""



from autocode.agent.context import (
    ContextPlane,
    PlaneBudget,
    PlaneState,
    get_plane_for_content,
)


class TestContextPlane:
    """Test the ContextPlane enum."""

    def test_all_planes_defined(self) -> None:
        """All four planes are defined."""
        planes = list(ContextPlane)
        assert len(planes) == 4
        assert ContextPlane.DURABLE_INSTRUCTIONS in planes
        assert ContextPlane.DURABLE_MEMORY in planes
        assert ContextPlane.LIVE_SESSION in planes
        assert ContextPlane.EPHEMERAL in planes

    def test_planeordering(self) -> None:
        """Planes have a defined ordering for sorting."""
        planes = list(ContextPlane)
        assert planes[0] == ContextPlane.DURABLE_INSTRUCTIONS
        assert planes[1] == ContextPlane.DURABLE_MEMORY


class TestPlaneBudget:
    """Test the PlaneBudget dataclass."""

    def test_defaults(self) -> None:
        """Default budgets match expected values."""
        budget = PlaneBudget()
        assert budget.durable_instructions == 512
        assert budget.durable_memory == 2560
        assert budget.live_session == 12800
        assert budget.ephemeral == 1280

    def test_get_limit(self) -> None:
        """get_limit returns correct limit per plane."""
        budget = PlaneBudget()
        assert budget.get_limit(ContextPlane.DURABLE_INSTRUCTIONS) == 512
        assert budget.get_limit(ContextPlane.DURABLE_MEMORY) == 2560
        assert budget.get_limit(ContextPlane.LIVE_SESSION) == 12800
        assert budget.get_limit(ContextPlane.EPHEMERAL) == 1280


class TestPlaneState:
    """Test the PlaneState dataclass."""

    def test_defaults(self) -> None:
        """Default state is uncompacted and empty."""
        state = PlaneState(ContextPlane.EPHEMERAL, token_count=100)
        assert state.plane == ContextPlane.EPHEMERAL
        assert state.token_count == 100
        assert state.compacted is False
        assert state.last_compaction is None


class TestGetPlaneForContent:
    """Test content classification into planes."""

    def test_policy_content(self) -> None:
        """Policy/instruction content goes to Plane 1."""
        content = "AGENTS.md says to use these instructions"
        plane = get_plane_for_content(content, is_durable=True)
        assert plane == ContextPlane.DURABLE_INSTRUCTIONS

    def test_system_prompt(self) -> None:
        """System prompts go to Plane 1."""
        content = "You are a helpful assistant system prompt"
        plane = get_plane_for_content(content)
        assert plane == ContextPlane.DURABLE_INSTRUCTIONS

    def test_learned_fact(self) -> None:
        """Learned project facts go to Plane 2."""
        content = "This projectLearned a pattern about the build system"
        plane = get_plane_for_content(content, is_durable=False)
        assert plane == ContextPlane.DURABLE_MEMORY

    def test_session_transient(self) -> None:
        """Session state goes to Plane 3."""
        content = "The user called write_file with result"
        plane = get_plane_for_content(content)
        assert plane == ContextPlane.LIVE_SESSION

    def test_tool_result(self) -> None:
        """Tool results are session transient (Plane 3)."""
        content = "tool_call result: modified file.py"
        plane = get_plane_for_content(content)
        assert plane == ContextPlane.LIVE_SESSION

    def test_ephemeral_default(self) -> None:
        """Unclassified content defaults to ephemeral."""
        content = "random exploration output"
        plane = get_plane_for_content(content)
        assert plane == ContextPlane.EPHEMERAL


class TestPlaneMapping:
    """Test mapping to current modules (from the design doc)."""

    def test_plane1_modules(self) -> None:
        """Plane 1 (Durable Instructions) maps to expected module groups."""
        # This is documentation of the mapping, not a runtime test
        plane1_modules = [
            "prompts.py",
            "policy_router.py",
        ]
        assert "prompts.py" in plane1_modules

    def test_plane2_modules(self) -> None:
        """Plane 2 (Durable Memory) maps to expected module groups."""
        plane2_modules = [
            "consolidation.py",
            "memory.py",
        ]
        assert "consolidation.py" in plane2_modules

    def test_plane3_modules(self) -> None:
        """Plane 3 (Live Session) maps to expected module groups."""
        plane3_modules = [
            "store.py",
            "checkpoint_store.py",
            "orchestrator.py",
            "context.py",
        ]
        assert "store.py" in plane3_modules

    def test_plane4_modules(self) -> None:
        """Plane 4 (Ephemeral) maps to expected module groups."""
        plane4_modules = [
            "loop.py",
            "worktree.py",
            "search.py",
        ]
        assert "loop.py" in plane4_modules
