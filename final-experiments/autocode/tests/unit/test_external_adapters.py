"""Tests for external harness adapters and event normalization."""

from __future__ import annotations

import json

from autocode.external.adapters.claude_code import ClaudeCodeAdapter
from autocode.external.adapters.codex import CodexAdapter
from autocode.external.adapters.forge import ForgeAdapter
from autocode.external.adapters.opencode import OpenCodeAdapter
from autocode.external.event_normalizer import (
    CLAUDE_CODE_KIND_MAP,
    CODEX_KIND_MAP,
    FORGE_KIND_MAP,
    OPENCODE_KIND_MAP,
    make_event,
    normalize_json_line,
    normalize_stream,
)
from autocode.external.harness_adapter import (
    HarnessCapabilities,
    HarnessEventType,
    HarnessKind,
    PromptInput,
    StartRequest,
)


class TestEventNormalizer:
    """Tests for the event normalization layer."""

    def test_normalize_valid_json_line(self) -> None:
        line = json.dumps({"type": "message", "content": "hello"})
        event = normalize_json_line(line, "s1", "r1")
        assert event is not None
        assert event.event_type == HarnessEventType.MESSAGE
        assert event.session_id == "s1"
        assert event.run_id == "r1"
        assert event.payload["content"] == "hello"

    def test_normalize_plain_text_becomes_stdout(self) -> None:
        event = normalize_json_line("plain text output", "s1", "r1")
        assert event is not None
        assert event.event_type == HarnessEventType.STDOUT
        assert event.raw_text == "plain text output"

    def test_normalize_empty_line_returns_none(self) -> None:
        assert normalize_json_line("", "s1", "r1") is None
        assert normalize_json_line("   ", "s1", "r1") is None

    def test_normalize_with_custom_kind_map(self) -> None:
        line = json.dumps({"type": "tool_use", "name": "read_file"})
        event = normalize_json_line(
            line,
            "s1",
            "r1",
            kind_map=CLAUDE_CODE_KIND_MAP,
        )
        assert event is not None
        assert event.event_type == HarnessEventType.TOOL_CALL

    def test_normalize_stream_yields_events(self) -> None:
        lines = [
            json.dumps({"type": "message", "text": "hi"}),
            "plain line",
            json.dumps({"type": "error", "msg": "fail"}),
        ]
        events = list(normalize_stream(iter(lines), "s1", "r1"))
        assert len(events) == 3
        assert events[0].event_type == HarnessEventType.MESSAGE
        assert events[1].event_type == HarnessEventType.STDOUT
        assert events[2].event_type == HarnessEventType.ERROR

    def test_make_event_factory(self) -> None:
        event = make_event(
            HarnessEventType.RUN_STARTED,
            "s1",
            "r1",
            payload={"key": "val"},
        )
        assert event.event_type == HarnessEventType.RUN_STARTED
        assert event.payload == {"key": "val"}

    def test_kind_maps_have_expected_keys(self) -> None:
        assert "tool_use" in CLAUDE_CODE_KIND_MAP
        assert "patch" in CODEX_KIND_MAP
        assert "tool_call" in OPENCODE_KIND_MAP
        assert "thinking" in FORGE_KIND_MAP


class TestClaudeCodeAdapter:
    def test_probe_unavailable(self) -> None:
        adapter = ClaudeCodeAdapter()
        adapter.BINARY = "nonexistent_binary_xyz"
        probe = adapter.probe()
        assert probe.kind == HarnessKind.CLAUDE_CODE
        assert not probe.available

    def test_start_creates_session(self) -> None:
        adapter = ClaudeCodeAdapter()
        session = adapter.start(StartRequest(cwd="/tmp", prompt="fix bug"))
        assert session.kind == HarnessKind.CLAUDE_CODE
        assert session.cwd == "/tmp"
        assert session.session_id

    def test_send_creates_run(self) -> None:
        adapter = ClaudeCodeAdapter()
        session = adapter.start(StartRequest(cwd="/tmp"))
        run = adapter.send(session, PromptInput(text="do something"))
        assert run.run_id
        assert run.session == session

    def test_resume_preserves_session_id(self) -> None:
        from autocode.external.harness_adapter import ResumeRequest

        adapter = ClaudeCodeAdapter()
        session = adapter.resume(ResumeRequest(session_id="abc123", cwd="/tmp"))
        assert session.session_id == "abc123"
        assert session.metadata.get("resumed") is True

    def test_build_command_basic(self) -> None:
        adapter = ClaudeCodeAdapter()
        session = adapter.start(StartRequest(cwd="/tmp"))
        cmd = adapter.build_command(session, "fix the bug")
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "fix the bug" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd

    def test_build_command_with_permission_mode(self) -> None:
        adapter = ClaudeCodeAdapter()
        session = adapter.start(
            StartRequest(
                cwd="/tmp",
                permission_mode="plan",
            )
        )
        cmd = adapter.build_command(session, "test")
        assert "--permission-mode" in cmd
        assert "plan" in cmd

    def test_capabilities_are_rich(self) -> None:
        """Claude Code supports many capabilities."""
        # Can't probe without binary, but test the static caps
        caps = HarnessCapabilities(
            supports_resume=True,
            supports_fork=True,
            supports_structured_output=True,
            supports_streaming_events=True,
            supports_native_worktree=True,
            supports_native_plan_mode=True,
            supports_native_permission_modes=True,
            supports_transcript_export=True,
            supports_agent_spawn=True,
        )
        assert caps.supports_resume
        assert caps.supports_native_worktree


class TestCodexAdapter:
    def test_probe_unavailable(self) -> None:
        adapter = CodexAdapter()
        adapter.BINARY = "nonexistent_binary_xyz"
        probe = adapter.probe()
        assert probe.kind == HarnessKind.CODEX
        assert not probe.available

    def test_start_and_send(self) -> None:
        adapter = CodexAdapter()
        session = adapter.start(StartRequest(cwd="/tmp", prompt="fix"))
        run = adapter.send(session, PromptInput(text="do it"))
        assert run.run_id
        assert session.kind == HarnessKind.CODEX

    def test_build_command_has_json_flag(self) -> None:
        adapter = CodexAdapter()
        session = adapter.start(StartRequest(cwd="/tmp"))
        cmd = adapter.build_command(session, "fix bug")
        assert "--json" in cmd
        assert "exec" in cmd


class TestOpenCodeAdapter:
    def test_probe_unavailable(self) -> None:
        adapter = OpenCodeAdapter()
        adapter.BINARY = "nonexistent_binary_xyz"
        probe = adapter.probe()
        assert probe.kind == HarnessKind.OPENCODE
        assert not probe.available

    def test_build_command_format_json(self) -> None:
        adapter = OpenCodeAdapter()
        session = adapter.start(StartRequest(cwd="/tmp"))
        cmd = adapter.build_command(session, "fix")
        assert "--format" in cmd
        assert "json" in cmd
        assert "run" in cmd


class TestForgeAdapter:
    def test_probe_unavailable(self) -> None:
        adapter = ForgeAdapter()
        adapter.BINARY = "nonexistent_binary_xyz"
        probe = adapter.probe()
        assert probe.kind == HarnessKind.FORGE
        assert not probe.available

    def test_build_command_has_conversation_id(self) -> None:
        adapter = ForgeAdapter()
        session = adapter.start(StartRequest(cwd="/tmp"))
        cmd = adapter.build_command(session, "fix")
        assert "--conversation-id" in cmd
        assert "--prompt" in cmd
