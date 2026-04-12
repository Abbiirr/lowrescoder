"""Tests for durable-memory rules (PLAN.md Section 0.2)."""


from autocode.session.consolidation import (
    DURABLE_WRITE_TRIGGERS,
    TRANSIENT_EXCLUSIONS,
    SessionLearning,
    get_plane_for_learning,
    should_promote_to_durable,
)


class TestDurableWriteTriggers:
    """Test that only allowed triggers can become durable memory."""

    def test_file_pattern_allowed(self) -> None:
        """file_pattern category is allowed."""
        learning = SessionLearning(
            category="file_pattern",
            summary="Tests go in tests/ directory",
            evidence="test directory structure",
            confidence=0.8,
        )
        assert should_promote_to_durable(learning) is True

    def test_error_fix_allowed(self) -> None:
        """error_fix category is allowed."""
        learning = SessionLearning(
            category="error_fix",
            summary="Fix: add import",
            evidence="error was missing import",
            confidence=0.7,
        )
        assert should_promote_to_durable(learning) is True

    def test_tool_usage_allowed(self) -> None:
        """tool_usage category is allowed."""
        learning = SessionLearning(
            category="tool_usage",
            summary="write_file used most",
            evidence="10 writes, 5 edits",
            confidence=0.9,
        )
        assert should_promote_to_durable(learning) is True

    def test_project_structure_allowed(self) -> None:
        """project_structure category is allowed."""
        learning = SessionLearning(
            category="project_structure",
            summary="src/ contains main code",
            evidence="directory structure",
            confidence=0.8,
        )
        assert should_promote_to_durable(learning) is True


class TestTransientExclusions:
    """Test that excluded categories are never promoted."""

    def test_result_excluded(self) -> None:
        """result category is excluded (Plane 4)."""
        learning = SessionLearning(
            category="result",
            summary="tool returned this",
            evidence="raw tool output",
            confidence=0.9,
        )
        assert should_promote_to_durable(learning) is False

    def test_search_hit_excluded(self) -> None:
        """search_hit category is excluded (Plane 4)."""
        learning = SessionLearning(
            category="search_hit",
            summary="found match",
            evidence="search result",
            confidence=0.8,
        )
        assert should_promote_to_durable(learning) is False

    def test_exploration_excluded(self) -> None:
        """exploration category is excluded (Plane 4)."""
        learning = SessionLearning(
            category="exploration",
            summary="tried this approach",
            evidence="failed attempt",
            confidence=0.5,
        )
        assert should_promote_to_durable(learning) is False


class TestConfidenceThreshold:
    """Test confidence-based filtering."""

    def test_low_confidence_rejected(self) -> None:
        """Low confidence (<0.5) is rejected."""
        learning = SessionLearning(
            category="file_pattern",
            summary="pattern",
            evidence="uncertain evidence",
            confidence=0.3,  # below threshold
        )
        assert should_promote_to_durable(learning) is False

    def test_high_confidence_accepted(self) -> None:
        """High confidence (>=0.5) can be accepted."""
        learning = SessionLearning(
            category="file_pattern",
            summary="pattern",
            evidence="strong evidence",
            confidence=0.8,
        )
        assert should_promote_to_durable(learning) is True

    def test_boundary_confidence(self) -> None:
        """Exactly 0.5 confidence meets threshold."""
        learning = SessionLearning(
            category="file_pattern",
            summary="pattern",
            evidence="evidence",
            confidence=0.5,
        )
        assert should_promote_to_durable(learning) is True


class TestGetPlaneForLearning:
    """Test plane mapping for learnings."""

    def test_durable_memory_plane(self) -> None:
        """Allowed triggers go to durable_memory plane."""
        learning = SessionLearning(
            category="file_pattern",
            summary="test pattern",
            evidence="evidence",
            confidence=0.8,
        )
        plane = get_plane_for_learning(learning)
        assert plane == "durable_memory"

    def test_live_session_plane(self) -> None:
        """Uncertain learning goes to live_session."""
        learning = SessionLearning(
            category="file_pattern",
            summary="uncertain",
            evidence="weak",
            confidence=0.4,  # above 0.3 threshold
        )
        plane = get_plane_for_learning(learning)
        assert plane == "live_session"

    def test_ephemeral_plane(self) -> None:
        """Very low confidence goes to ephemeral."""
        learning = SessionLearning(
            category="result",
            summary="result",
            evidence="raw",
            confidence=0.2,  # below 0.3
        )
        plane = get_plane_for_learning(learning)
        assert plane == "ephemeral"


class TestConstants:
    """Test that the constants are defined as expected."""

    def test_durable_triggers_has_content(self) -> None:
        """DURABLE_WRITE_TRIGGERS is non-empty."""
        assert len(DURABLE_WRITE_TRIGGERS) > 0
        assert "file_pattern" in DURABLE_WRITE_TRIGGERS

    def test_transient_exclusions_has_content(self) -> None:
        """TRANSIENT_EXCLUSIONS is non-empty."""
        assert len(TRANSIENT_EXCLUSIONS) > 0
        assert "result" in TRANSIENT_EXCLUSIONS
