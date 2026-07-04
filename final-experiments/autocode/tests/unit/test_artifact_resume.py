"""Tests for artifact-first resumability (PLAN.md Section 0.5)."""

from pathlib import Path

from autocode.agent.artifact_collector import (
    ArtifactCollector,
    CheckpointManifest,
    CompactSummary,
    HandoffPacket,
    ResumePacket,
)


class TestHandoffPacket:
    """Test HandoffPacket structure."""

    def test_create(self) -> None:
        """Can create a handoff packet."""
        packet = HandoffPacket(
            session_id="sess-1",
            created_at=1234567890.0,
            summary="Fixed bug in module X",
            checkpoint_id="cp-1",
            last_tool="Write_file",
            files_in_scope=["src/x.py"],
        )
        assert packet.session_id == "sess-1"
        assert packet.last_tool == "Write_file"


class TestCompactSummary:
    """Test CompactSummary structure."""

    def test_create(self) -> None:
        """Can create a compact summary."""
        summary = CompactSummary(
            session_id="sess-2",
            summary="Task in progress",
            checkpoint_ids=["cp-1", "cp-2"],
            last_turn_tool="Read_file",
        )
        assert len(summary.checkpoint_ids) == 2


class TestCheckpointManifest:
    """Test CheckpointManifest structure."""

    def test_create(self) -> None:
        """Can create a checkpoint manifest."""
        manifest = CheckpointManifest(
            session_id="sess-3",
            checkpoints=["cp-a", "cp-b", "cp-c"],
            created_at=1234567890.0,
        )
        assert len(manifest.checkpoints) == 3


class TestResumePacket:
    """Test ResumePacket combining all artifacts."""

    def test_create(self) -> None:
        """Can create a full resume packet."""
        handoff = HandoffPacket(
            session_id="sess-4",
            created_at=1234567890.0,
            summary="Resolved issue",
            checkpoint_id="cp-final",
            last_tool="Write_file",
            files_in_scope=["main.py"],
        )
        compact = CompactSummary(
            session_id="sess-4",
            summary="Resolved issue",
            checkpoint_ids=["cp-1", "cp-final"],
            last_turn_tool="Write_file",
        )
        manifest = CheckpointManifest(
            session_id="sess-4",
            checkpoints=["cp-1", "cp-final"],
            created_at=1234567890.0,
        )
        packet = ResumePacket(
            handoff=handoff,
            compact_summary=compact,
            manifest=manifest,
            files_in_scope=["main.py"],
        )
        assert packet.handoff.last_tool == "Write_file"
        assert len(packet.compact_summary.checkpoint_ids) == 2
        assert len(packet.files_in_scope) == 1

    def test_serialization(self) -> None:
        """ResumePacket serializes to dict."""
        handoff = HandoffPacket(
            session_id="sess-5",
            created_at=1000.0,
            summary="test",
            checkpoint_id="cp-1",
            last_tool="Read_file",
            files_in_scope=["a.py"],
        )
        compact = CompactSummary(
            session_id="sess-5",
            summary="test",
            checkpoint_ids=["cp-1"],
            last_turn_tool="Read_file",
        )
        manifest = CheckpointManifest(
            session_id="sess-5",
            checkpoints=["cp-1"],
            created_at=1000.0,
        )
        packet = ResumePacket(
            handoff=handoff,
            compact_summary=compact,
            manifest=manifest,
            files_in_scope=["a.py"],
        )
        d = packet.to_dict()
        assert d["handoff"]["session_id"] == "sess-5"
        assert d["compact_summary"]["last_turn_tool"] == "Read_file"
        assert d["manifest"]["checkpoints"] == ["cp-1"]


class TestArtifactCollectorCommandLog:
    """Test that ArtifactCollector captures command logs."""

    def test_log_command(self) -> None:
        """Can log command to ArtifactCollector."""
        collector = ArtifactCollector("test-session", Path("/tmp"))
        collector.ensure_dir()
        collector.log_command("echo hello", exit_code=0, duration_ms=10, tool_name="bash")
        assert len(collector._commands) == 1
        assert collector._commands[0].command == "echo hello"

    def test_command_captures_metadata(self) -> None:
        """Logged commands capture all metadata."""
        collector = ArtifactCollector("test-session", Path("/tmp"))
        collector.ensure_dir()
        collector.log_command("pytest", exit_code=1, duration_ms=5000, tool_name="pytest")
        entry = collector._commands[0]
        assert entry.exit_code == 1
        assert entry.duration_ms == 5000
        assert entry.tool_name == "pytest"
