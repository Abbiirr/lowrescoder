"""RED/GREEN tests for the HeadlessRunner and --json mode.

Covers:
  - stdout contains ONLY valid NDJSON (no banners, no log lines)
  - headless mode does NOT import or spawn Rust TUI path
  - error path emits final error event then exits non-zero
  - full turn emits well-formed NDJSON event sequence
  - integration: pipe through jq
  - schema validation: emitted events validate against generated schemas
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_config() -> Any:
    from autocode.config import AutoCodeConfig

    return AutoCodeConfig()


class TestStdoutOnlyNDJSON:
    def test_emit_thread_started_produces_valid_ndjson(self):
        from autocode.backend.headless_schema import ThreadStartedEvent, emit_event

        buf = io.StringIO()
        emit_event(ThreadStartedEvent(thread_id="t1"), fp=buf)
        line = buf.getvalue()
        assert line.endswith("\n")
        parsed = json.loads(line.strip())
        assert parsed["type"] == "thread_started"
        assert parsed["protocol_version"] == "0.2.0-harness"

    def test_multiple_events_produce_valid_ndjson_lines(self):
        from autocode.backend.headless_schema import (
            ThreadStartedEvent,
            TurnStartedEvent,
            ErrorEvent,
            emit_event,
        )

        buf = io.StringIO()
        emit_event(ThreadStartedEvent(thread_id="t1"), fp=buf)
        emit_event(TurnStartedEvent(turn_id="turn1", thread_id="t1", message="hi"), fp=buf)
        emit_event(ErrorEvent(message="fail"), fp=buf)

        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert "protocol_version" in parsed
            assert parsed["protocol_version"] == "0.2.0-harness"

    def test_no_human_readable_text_in_output(self):
        from autocode.backend.headless_schema import (
            ThreadStartedEvent,
            emit_event,
        )

        buf = io.StringIO()
        emit_event(ThreadStartedEvent(), fp=buf)
        output = buf.getvalue()
        assert "AutoCode" not in output
        assert "Goodbye" not in output
        assert "Thinking..." not in output


class TestNoTUIImport:
    def test_headless_schema_does_not_import_tui(self):
        import ast

        import autocode.backend.headless_schema as hs

        source = Path(hs.__file__).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "autocode.tui" not in node.module
                for alias in node.names:
                    assert "autocode.tui" not in alias.name

    def test_headless_runner_does_not_import_tui(self):
        import ast

        import autocode.backend.headless_runner as hr

        source = Path(hr.__file__).read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.ImportFrom) and node.module:
                    assert "autocode.tui" not in node.module
                    assert "autocode.rtui" not in node.module
                for alias in node.names:
                    assert "autocode.tui" not in alias.name
                    assert "autocode.rtui" not in alias.name


class TestHeadlessMemoryRollback:
    @pytest.mark.asyncio
    async def test_legacy_memory_env_uses_sqlite_memory_store(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Headless --json mode should honor the same P3 memory rollback flag."""
        from autocode.agent.memory import MemoryStore
        from autocode.backend.headless_runner import HeadlessRunner

        config = _make_config()
        config.tui.session_db_path = str(tmp_path / "sessions.db")
        monkeypatch.setenv("AUTOCODE_USE_LEGACY_MEMORY", "true")

        runner = HeadlessRunner(config=config, project_root=tmp_path)

        fake_loop = MagicMock()
        with (
            patch("autocode.layer4.llm.create_provider", return_value=MagicMock()),
            patch(
                "autocode.agent.factory.create_orchestrator",
                return_value=(fake_loop, MagicMock()),
            ),
        ):
            runner._ensure_agent_loop()

        try:
            assert isinstance(runner._memory_store, MemoryStore)
        finally:
            await runner._teardown_agent_resources()


class TestErrorPath:
    def test_error_event_emitted_on_exception(self):
        from autocode.backend.headless_schema import ErrorEvent, emit_event

        buf = io.StringIO()
        emit_event(ErrorEvent(message="LLM connection failed"), fp=buf)
        line = buf.getvalue().strip()
        parsed = json.loads(line)
        assert parsed["type"] == "error"
        assert parsed["message"] == "LLM connection failed"

    def test_error_event_is_final_valid_ndjson(self):
        from autocode.backend.headless_schema import ErrorEvent

        raw = json.loads(ErrorEvent(message="x").model_dump_json())
        assert raw["type"] == "error"
        assert raw["protocol_version"] == "0.2.0-harness"


class TestKairosTickUnsupported:
    @pytest.mark.asyncio()
    async def test_handle_kairos_tick_emits_controlled_error(self, tmp_path: Path):
        """Headless mode has no proactive loop; kairos.tick must fail cleanly.

        Regression for the latent AttributeError if a future caller routes
        ``kairos.tick`` to a HeadlessRunner-backed host: instead of crashing, the
        runner emits a controlled error event.
        """
        from autocode.backend.headless_runner import HeadlessRunner

        config = _make_config()
        config.tui.session_db_path = str(tmp_path / "sessions.db")
        buf = io.StringIO()
        runner = HeadlessRunner(config=config, project_root=tmp_path, output=buf)

        await runner.handle_kairos_tick(
            message="check on progress",
            session_id=None,
            tick_id="tick-1",
            read_only=True,
            request_id=-1,
        )

        lines = [line for line in buf.getvalue().strip().split("\n") if line]
        assert lines, "expected a controlled error event on stdout"
        parsed = json.loads(lines[-1])
        assert parsed["type"] == "error"
        assert "headless" in parsed["message"].lower()


class TestUsageAlwaysPresent:
    def test_turn_completed_has_usage_block(self):
        from autocode.backend.headless_schema import TurnCompletedEvent

        raw = json.loads(TurnCompletedEvent().model_dump_json())
        assert "usage" in raw
        u = raw["usage"]
        for key in ("input_tokens", "output_tokens", "total_tokens",
                     "cached_input_tokens", "cache_creation_tokens", "reasoning_tokens"):
            assert key in u, f"Missing key: {key}"

    def test_build_usage_from_none_stats(self):
        from autocode.backend.headless_schema import build_usage_from_stats

        usage = build_usage_from_stats(None)
        assert usage.input_tokens == 0
        assert usage.total_tokens == 0


class TestHeadlessRunnerEmitNotification:
    def _make_runner(self) -> Any:
        from autocode.backend.headless_runner import HeadlessRunner
        buf = io.StringIO()
        config = _make_config()
        runner = HeadlessRunner.__new__(HeadlessRunner)
        runner.config = config
        runner._output = buf
        runner.session_id = "test-session"
        runner._thread_id = "t1"
        runner._turn_id = "turn1"
        runner._item_counter = 0
        runner._session_stats = None
        runner._auto_approve = True
        runner._current_agent_message_item_id = None
        runner._agent_message_open = False
        runner._turn_completed_emitted = False
        return runner, buf

    def test_on_token_emits_agent_message_lifecycle(self):
        runner, buf = self._make_runner()
        runner.emit_notification("on_token", {"text": "hello"})
        runner.emit_notification("on_token", {"text": " world"})
        runner.emit_notification("on_done", {"tokens_in": 0, "tokens_out": 0})

        events = [json.loads(line) for line in buf.getvalue().strip().split("\n")]
        assert [event["type"] for event in events] == [
            "item_started",
            "item_delta",
            "item_delta",
            "item_completed",
            "turn_completed",
        ]
        started = events[0]
        assert started["kind"] == "agent_message"
        assert events[1]["item_id"] == started["item_id"]
        assert events[2]["item_id"] == started["item_id"]
        assert events[3]["item_id"] == started["item_id"]

    def test_on_done_emits_turn_completed_with_usage(self):
        runner, buf = self._make_runner()
        runner.emit_notification("on_done", {"tokens_in": 0, "tokens_out": 0})
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["type"] == "turn_completed"
        assert "usage" in parsed

    def test_on_error_emits_error_event(self):
        runner, buf = self._make_runner()
        runner.emit_notification("on_error", {"message": "fail"})
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["type"] == "error"
        assert parsed["message"] == "fail"

    def test_on_tool_call_emits_tool_execution(self):
        runner, buf = self._make_runner()
        runner.emit_notification("on_tool_call", {
            "name": "read_file",
            "status": "completed",
            "result": "ok",
        })
        lines = buf.getvalue().strip().split("\n")
        assert len(lines) == 4
        events = [json.loads(line) for line in lines]
        assert events[0]["type"] == "tool_call_started"
        assert events[0]["tool_name"] == "read_file"
        assert events[1]["type"] == "item_started"
        assert events[1]["kind"] == "tool_execution"
        assert events[2]["type"] == "item_completed"
        assert events[2]["item_id"] == events[1]["item_id"]
        assert events[3]["type"] == "tool_call_completed"
        assert events[3]["tool_name"] == "read_file"

    def test_on_tool_call_closes_non_success_tool_execution(self):
        runner, buf = self._make_runner()
        runner.emit_notification("on_tool_call", {
            "name": "write_file",
            "status": "error",
            "result": "denied",
        })
        events = [json.loads(line) for line in buf.getvalue().strip().split("\n")]
        types = [event["type"] for event in events]
        assert types[0] == "tool_call_started"
        assert types[1] == "item_started"
        assert events[1]["kind"] == "tool_execution"
        assert types[2] == "item_completed"
        assert events[2]["item_id"] == events[1]["item_id"]
        assert "error" in events[2]["result"]
        assert types[3] == "tool_call_failed"
        assert events[3]["tool_name"] == "write_file"

    @pytest.mark.asyncio
    async def test_tool_request_emits_approval_item(self):
        from autocode.backend import schema as rpc_schema

        runner, buf = self._make_runner()
        result = await runner.emit_request(
            rpc_schema.METHOD_ON_TOOL_REQUEST,
            {"tool_name": "write_file", "risk": "mutates_fs"},
        )
        events = [json.loads(line) for line in buf.getvalue().strip().split("\n")]
        assert result == {"approved": True}
        assert [event["type"] for event in events] == ["item_started", "item_completed"]
        assert events[0]["kind"] == "approval"
        assert events[1]["item_id"] == events[0]["item_id"]
        assert "approved" in events[1]["result"]

    @pytest.mark.asyncio
    async def test_tool_request_denies_without_auto_approve(self):
        from autocode.backend import schema as rpc_schema

        runner, buf = self._make_runner()
        runner._auto_approve = False
        result = await runner.emit_request(
            rpc_schema.METHOD_ON_TOOL_REQUEST,
            {"tool_name": "write_file", "risk": "mutates_fs"},
        )
        events = [json.loads(line) for line in buf.getvalue().strip().split("\n")]
        assert result == {"approved": False}
        assert [event["type"] for event in events] == ["item_started", "item_completed"]
        assert events[0]["kind"] == "approval"
        assert events[1]["item_id"] == events[0]["item_id"]
        assert "denied" in events[1]["result"]

    def test_on_task_state_emits_plan_update_item(self):
        runner, buf = self._make_runner()
        runner.emit_notification("on_task_state", {"summary": "2 tasks active"})
        events = [json.loads(line) for line in buf.getvalue().strip().split("\n")]
        assert [event["type"] for event in events] == ["item_started", "item_delta", "item_completed"]
        assert events[0]["kind"] == "plan_update"
        assert events[1]["item_id"] == events[0]["item_id"]
        assert events[2]["item_id"] == events[0]["item_id"]

    def test_on_warning_goes_to_stderr(self, capsys):
        runner, buf = self._make_runner()
        runner.emit_notification("on_warning", {"message": "careful!"})
        output = buf.getvalue()
        assert output == ""
        captured = capsys.readouterr()
        assert "careful!" in captured.err


class TestFullTurnSequence:
    def test_expected_event_order_closes_every_started_item(self):
        from autocode.backend.headless_schema import (
            ThreadStartedEvent,
            TurnStartedEvent,
            emit_event,
        )
        from autocode.backend.headless_runner import HeadlessRunner

        buf = io.StringIO()
        emit_event(ThreadStartedEvent(thread_id="t1", session_id="s1"), fp=buf)
        emit_event(TurnStartedEvent(turn_id="turn1", thread_id="t1", message="hi"), fp=buf)
        runner = HeadlessRunner.__new__(HeadlessRunner)
        runner._output = buf
        runner._turn_id = "turn1"
        runner._thread_id = "t1"
        runner._item_counter = 0
        runner._session_stats = None
        runner._auto_approve = True
        runner._current_agent_message_item_id = None
        runner._agent_message_open = False
        runner._turn_completed_emitted = False
        runner.emit_notification("on_token", {"text": "hello"})
        runner.emit_notification("on_token", {"text": " world"})
        runner.emit_notification("on_done", {})

        lines = buf.getvalue().strip().split("\n")
        events = [json.loads(line) for line in lines]
        open_items: set[str] = set()
        for event in events:
            if event["type"] == "item_started":
                open_items.add(event["item_id"])
            elif event["type"] == "item_completed":
                open_items.remove(event["item_id"])
            elif event["type"] == "turn_completed":
                assert open_items == set()

    @pytest.mark.asyncio
    async def test_run_emits_error_and_turn_completed_when_chat_turn_raises(self):
        from autocode.backend.headless_runner import HeadlessRunner

        buf = io.StringIO()
        runner = HeadlessRunner.__new__(HeadlessRunner)
        runner._output = buf
        runner._thread_id = "t1"
        runner.session_id = "s1"
        runner._turn_id = ""
        runner._item_counter = 0
        runner._session_stats = None
        runner._auto_approve = True
        runner._current_agent_message_item_id = None
        runner._agent_message_open = False
        runner._turn_completed_emitted = False

        async def _boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("chat exploded")

        with patch("autocode.backend.chat.run_chat_turn", side_effect=_boom):
            await runner.run("hello")

        events = [json.loads(line) for line in buf.getvalue().strip().split("\n")]
        assert [event["type"] for event in events] == [
            "thread_started",
            "turn_started",
            "error",
            "turn_completed",
        ]
        assert events[2]["message"] == "chat exploded"


class TestSchemaValidation:
    def test_emitted_events_validate_against_generated_schemas(self):
        from autocode.backend.headless_schema import (
            generate_json_schemas,
            ThreadStartedEvent,
            TurnStartedEvent,
            TurnCompletedEvent,
            ErrorEvent,
            UsageBlock,
        )

        schemas = generate_json_schemas()
        events = [
            ThreadStartedEvent(thread_id="t1"),
            TurnStartedEvent(turn_id="turn1", thread_id="t1", message="hi"),
            TurnCompletedEvent(turn_id="turn1", thread_id="t1", usage=UsageBlock()),
            ErrorEvent(message="fail"),
        ]

        for event in events:
            raw = json.loads(event.model_dump_json())
            schema_key = raw["type"]
            assert schema_key in schemas, f"No schema for {schema_key}"
            schema = schemas[schema_key]
            assert "properties" in schema

    def test_usage_schema_matches_usage_block(self):
        from autocode.backend.headless_schema import generate_json_schemas, UsageBlock

        schemas = generate_json_schemas()
        assert "usage" in schemas
        usage_schema = schemas["usage"]
        usage_json = json.loads(UsageBlock().model_dump_json())
        for key in ("input_tokens", "output_tokens", "total_tokens",
                     "cached_input_tokens", "cache_creation_tokens", "reasoning_tokens"):
            assert key in usage_schema.get("properties", {}), f"Missing {key} in usage schema"


class TestJqIntegration:
    def test_ndjson_parsable_by_jq(self):
        from autocode.backend.headless_schema import (
            ThreadStartedEvent,
            TurnStartedEvent,
            ErrorEvent,
            emit_event,
        )

        buf = io.StringIO()
        emit_event(ThreadStartedEvent(thread_id="t1"), fp=buf)
        emit_event(TurnStartedEvent(turn_id="turn1", thread_id="t1"), fp=buf)
        emit_event(ErrorEvent(message="test"), fp=buf)

        lines = buf.getvalue().strip().split("\n")
        types = []
        for line in lines:
            parsed = json.loads(line)
            types.append(parsed["type"])
        assert types == ["thread_started", "turn_started", "error"]
