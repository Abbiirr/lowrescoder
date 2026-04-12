"""Tests for session memory consolidation (autoDream-style)."""

from __future__ import annotations

import json

from autocode.session.consolidation import (
    ConsolidationResult,
    SessionConsolidator,
    SessionLearning,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user_msg(content: str) -> dict:
    return {"role": "user", "content": content}


def _make_assistant_msg(content: str, tool_calls: list | None = None) -> dict:
    msg: dict = {"role": "assistant", "content": content}
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return msg


def _make_tool_call(name: str, arguments: dict) -> dict:
    return {"function": {"name": name, "arguments": json.dumps(arguments)}}


# ---------------------------------------------------------------------------
# Orient phase
# ---------------------------------------------------------------------------

class TestOrient:
    """Tests for the orient (phase 1) method."""

    def test_orient_counts_messages(self) -> None:
        """orient() should count user and assistant messages."""
        messages = [
            _make_user_msg("Hello"),
            _make_assistant_msg("Hi there"),
            _make_user_msg("Do something"),
            _make_assistant_msg("Done"),
            _make_user_msg("Thanks"),
        ]
        consolidator = SessionConsolidator()
        stats = consolidator.orient(messages)

        assert stats["total_messages"] == 5
        assert stats["user_messages"] == 3
        assert stats["assistant_messages"] == 2

    def test_orient_detects_errors(self) -> None:
        """orient() should extract error strings from message content."""
        messages = [
            _make_user_msg("I got an Error: file not found"),
            _make_assistant_msg("Let me fix that error for you"),
        ]
        consolidator = SessionConsolidator()
        stats = consolidator.orient(messages)

        assert len(stats["errors_seen"]) == 2
        assert "Error" in stats["errors_seen"][0]


# ---------------------------------------------------------------------------
# Gather phase
# ---------------------------------------------------------------------------

class TestGather:
    """Tests for the gather (phase 2) method."""

    def test_gather_extracts_file_patterns(self) -> None:
        """gather() should detect files edited via tool calls."""
        messages = [
            _make_assistant_msg("Editing files", tool_calls=[
                _make_tool_call("write_file", {"path": "src/main.py"}),
                _make_tool_call("edit_file", {"path": "src/utils.py"}),
            ]),
        ]
        consolidator = SessionConsolidator()
        orientation = consolidator.orient(messages)
        learnings = consolidator.gather(messages, orientation)

        file_learnings = [
            learning for learning in learnings if learning.category == "file_pattern"
        ]
        assert len(file_learnings) == 1
        assert "src/main.py" in file_learnings[0].summary
        assert "src/utils.py" in file_learnings[0].summary

    def test_gather_extracts_tool_usage(self) -> None:
        """gather() should count tool usage and create a learning."""
        messages = [
            _make_assistant_msg("Working", tool_calls=[
                _make_tool_call("read_file", {"path": "a.py"}),
                _make_tool_call("read_file", {"path": "b.py"}),
                _make_tool_call("write_file", {"path": "a.py"}),
            ]),
        ]
        consolidator = SessionConsolidator()
        orientation = consolidator.orient(messages)
        learnings = consolidator.gather(messages, orientation)

        tool_learnings = [
            learning for learning in learnings if learning.category == "tool_usage"
        ]
        assert len(tool_learnings) == 1
        assert "read_file" in tool_learnings[0].summary

    def test_gather_empty_session(self) -> None:
        """gather() on an empty session returns no learnings."""
        consolidator = SessionConsolidator()
        orientation = consolidator.orient([])
        learnings = consolidator.gather([], orientation)

        assert learnings == []


# ---------------------------------------------------------------------------
# Consolidate phase
# ---------------------------------------------------------------------------

class TestConsolidate:
    """Tests for the consolidate (phase 3) method."""

    def test_consolidate_deduplicates(self) -> None:
        """consolidate() should not add a learning with a duplicate summary."""
        existing = SessionLearning(
            category="file_pattern",
            summary="Files modified in session: src/main.py",
            evidence="1 files edited",
        )
        new_learning = SessionLearning(
            category="file_pattern",
            summary="Files modified in session: src/main.py",
            evidence="1 files edited",
        )
        consolidator = SessionConsolidator()
        consolidator._existing_learnings = [existing]
        merged = consolidator.consolidate([new_learning])

        assert len(merged) == 1

    def test_consolidate_merges_new(self) -> None:
        """consolidate() should add genuinely new learnings."""
        existing = SessionLearning(
            category="file_pattern",
            summary="Files modified in session: src/main.py",
            evidence="1 files edited",
        )
        new_learning = SessionLearning(
            category="tool_usage",
            summary="Most used tools: read_file(5)",
            evidence='{"read_file": 5}',
        )
        consolidator = SessionConsolidator()
        consolidator._existing_learnings = [existing]
        merged = consolidator.consolidate([new_learning])

        assert len(merged) == 2
        summaries = {learning.summary for learning in merged}
        assert "Files modified in session: src/main.py" in summaries
        assert "Most used tools: read_file(5)" in summaries


# ---------------------------------------------------------------------------
# Prune phase
# ---------------------------------------------------------------------------

class TestPrune:
    """Tests for the prune (phase 4) method."""

    def test_prune_respects_max(self) -> None:
        """prune() should keep at most max_learnings entries."""
        consolidator = SessionConsolidator(max_learnings=3)
        learnings = [
            SessionLearning(category="a", summary=f"item {i}", evidence="x", confidence=0.5)
            for i in range(10)
        ]
        pruned = consolidator.prune(learnings)

        assert len(pruned) == 3

    def test_prune_keeps_high_confidence(self) -> None:
        """prune() should prefer high-confidence learnings over low."""
        consolidator = SessionConsolidator(max_learnings=2)
        learnings = [
            SessionLearning(category="a", summary="low", evidence="x", confidence=0.2),
            SessionLearning(category="a", summary="high", evidence="x", confidence=0.95),
            SessionLearning(category="a", summary="mid", evidence="x", confidence=0.6),
        ]
        pruned = consolidator.prune(learnings)

        assert len(pruned) == 2
        summaries = [learning.summary for learning in pruned]
        assert summaries[0] == "high"
        assert summaries[1] == "mid"


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestRunFullPipeline:
    """End-to-end test of the consolidation pipeline."""

    def test_run_full_pipeline(self) -> None:
        """run() executes all four phases and returns a ConsolidationResult."""
        messages = [
            _make_user_msg("Fix the bug"),
            _make_assistant_msg("Looking at the error now"),
            _make_assistant_msg("Found it", tool_calls=[
                _make_tool_call("read_file", {"path": "src/bug.py"}),
                _make_tool_call("write_file", {"path": "src/bug.py"}),
            ]),
            _make_user_msg("Great, thanks"),
        ]
        existing = [
            SessionLearning(
                category="project_structure",
                summary="Main entry point is src/main.py",
                evidence="observed",
                confidence=0.9,
            ),
        ]

        consolidator = SessionConsolidator(max_learnings=50)
        result = consolidator.run(messages, existing=existing)

        assert isinstance(result, ConsolidationResult)
        assert result.learnings_gathered > 0
        assert result.learnings_kept >= 1  # at least existing one kept
        assert result.learnings_pruned >= 0
        assert isinstance(result.categories, dict)


class TestCarryForwardSummary:
    """Structured carry-forward summary generation."""

    def test_build_carry_forward_summary_uses_structured_sections(self) -> None:
        messages = [
            _make_user_msg("Refactor the parser and update the tests."),
            _make_assistant_msg("Investigating", tool_calls=[
                _make_tool_call("read_file", {"path": "src/parser.py"}),
                _make_tool_call("create_task", {"title": "Update parser tests"}),
                _make_tool_call("edit_file", {"path": "tests/test_parser.py"}),
            ]),
            _make_assistant_msg("Decision: keep the parser API stable while fixing edge cases."),
            {"role": "tool", "content": "[run_command] Error: parser still fails on edge cases."},
        ]

        summary = SessionConsolidator().build_carry_forward_summary(messages)

        assert "Carry-forward summary:" in summary
        assert "## Objective" in summary
        assert "Refactor the parser" in summary
        assert "## Files Read" in summary
        assert "src/parser.py" in summary
        assert "## Files Modified" in summary
        assert "tests/test_parser.py" in summary
        assert "## Plan Progress" in summary
        assert "Update parser tests" in summary
        assert "## Tool Patterns" in summary
        assert "## Decisions" in summary
        assert "## Blockers" in summary
        assert "## Next Actions" in summary
