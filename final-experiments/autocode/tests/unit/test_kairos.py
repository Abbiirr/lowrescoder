"""Tests for P5 KAIROS proactive-mode substrate."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.loop import AgentLoop
from autocode.agent.proactive import (
    KairosAuditLog,
    ProactiveLoop,
    TickConfig,
    build_tick_message,
    build_tick_rpc_request,
    detect_anti_narration,
    format_kairos_pulse,
    kairos_allows_tool,
    kairos_enabled_from_env,
    send_tick_rpc,
    should_skip_for_cost_cap,
)
from autocode.agent.prompts import PROACTIVE_MODE_PROMPT, build_dynamic_suffix
from autocode.agent.tools import ToolDefinition, ToolRegistry, create_default_registry
from autocode.layer4.llm import ToolCall
from autocode.session.store import SessionStore
from autocode.telemetry.events import TELEMETRY_EVENT_KINDS


def test_kairos_feature_flag_defaults_off() -> None:
    assert kairos_enabled_from_env({}) is False
    assert kairos_enabled_from_env({"AUTOCODE_FEATURE_KAIROS": "false"}) is False
    assert kairos_enabled_from_env({"AUTOCODE_FEATURE_KAIROS": "true"}) is True


def test_tick_config_uses_default_off_safe_budget() -> None:
    config = TickConfig()

    assert config.enabled is False
    assert config.base_interval_sec == 30.0
    assert config.blocking_budget_sec == 15.0
    assert config.cache_ttl_sec == 300.0
    assert config.terminal_focus_aware is True


def test_tick_message_includes_local_time_and_awake_instruction() -> None:
    now = datetime(2026, 5, 5, 9, 30, tzinfo=ZoneInfo("Asia/Dhaka"))

    message = build_tick_message(now=now)

    assert message.startswith("<tick ")
    assert "2026-05-05T09:30:00+06:00" in message
    assert "you're awake" in message.lower()
    assert "Sleep" in message
    assert message.endswith("</tick>")


def test_sleep_request_is_capped_at_ten_times_cache_ttl() -> None:
    loop = ProactiveLoop(config=TickConfig(cache_ttl_sec=5))

    granted = loop.request_sleep(999, reason="provider backoff")

    assert granted == 50
    assert loop.consume_requested_sleep() == 50
    assert loop.last_sleep_reason == "provider backoff"


def test_kairos_telemetry_event_kinds_are_registered() -> None:
    assert "kairos_tick" in TELEMETRY_EVENT_KINDS
    assert "kairos_sleep" in TELEMETRY_EVENT_KINDS
    assert "kairos_anti_narration" in TELEMETRY_EVENT_KINDS
    assert "kairos_action_blast_radius" in TELEMETRY_EVENT_KINDS


def test_sleep_request_emits_telemetry() -> None:
    events: list[tuple[str, dict]] = []
    loop = ProactiveLoop(
        config=TickConfig(cache_ttl_sec=5),
        telemetry_emit=lambda kind, data: events.append((kind, data)),
    )

    loop.request_sleep(999, reason="provider backoff")

    assert events == [
        (
            "kairos_sleep",
            {
                "requested_seconds": 999.0,
                "granted_seconds": 50.0,
                "reason": "provider backoff",
            },
        )
    ]


def test_terminal_focus_pauses_when_user_has_pending_input() -> None:
    loop = ProactiveLoop(
        config=TickConfig(terminal_focus_aware=True),
        has_pending_user_input=lambda: True,
    )
    loop.set_terminal_focused(True)

    assert loop.should_pause_for_user_input() is True

    loop.set_terminal_focused(False)
    assert loop.should_pause_for_user_input() is False


@pytest.mark.asyncio()
async def test_manual_tick_coalesces_when_tick_is_in_flight() -> None:
    injected: list[str] = []
    events: list[tuple[str, dict]] = []

    async def inject_tick(message: str) -> None:
        injected.append(message)
        await loop.inject_once()

    loop = ProactiveLoop(
        config=TickConfig(enabled=True),
        inject_tick=inject_tick,
        telemetry_emit=lambda kind, data: events.append((kind, data)),
    )

    await loop.inject_once()

    assert len(injected) == 1
    assert events[0][0] == "kairos_tick"


def test_sleep_tool_is_only_registered_when_proactive_loop_is_provided() -> None:
    assert create_default_registry().get("sleep") is None

    loop = ProactiveLoop(config=TickConfig(cache_ttl_sec=3))
    registry = create_default_registry(proactive_loop=loop)
    tool = registry.get("sleep")

    assert tool is not None
    assert tool.requires_approval is False
    assert tool.mutates_fs is False
    assert tool.executes_shell is False
    assert "Prefer this over" in tool.description

    result = tool.handler(seconds=999, reason="wait for CI")
    assert "Sleeping for 30.0s" in result
    assert "wait for CI" in result
    assert loop.consume_requested_sleep() == 30


def test_proactive_prompt_enforces_sleep_instead_of_narration() -> None:
    assert "If you have nothing useful to do on a tick" in PROACTIVE_MODE_PROMPT
    assert "MUST call Sleep" in PROACTIVE_MODE_PROMPT
    assert "Never respond with only a status message" in PROACTIVE_MODE_PROMPT


def test_dynamic_suffix_only_includes_proactive_prompt_when_enabled() -> None:
    assert "Autonomous work" not in build_dynamic_suffix()
    assert "Autonomous work" in build_dynamic_suffix(proactive_mode=True)


def test_anti_narration_detects_text_only_tick_response() -> None:
    assert detect_anti_narration("still waiting", tool_calls=[]) is True
    assert detect_anti_narration("", tool_calls=[]) is False
    assert detect_anti_narration(
        "sleeping",
        tool_calls=[ToolCall(id="tc1", name="sleep", arguments={"seconds": 30})],
    ) is False


def test_kairos_blocks_approval_required_tools_without_user_present() -> None:
    write_tool = ToolDefinition(
        name="write_file",
        description="write",
        parameters={"type": "object", "properties": {}},
        handler=lambda: "ok",
        requires_approval=True,
        mutates_fs=True,
    )
    sleep_tool = ToolDefinition(
        name="sleep",
        description="sleep",
        parameters={"type": "object", "properties": {}},
        handler=lambda: "ok",
        requires_approval=False,
    )

    assert kairos_allows_tool(write_tool, user_present=False) is False
    assert kairos_allows_tool(write_tool, user_present=True) is True
    assert kairos_allows_tool(sleep_tool, user_present=False) is True


def test_kairos_audit_log_records_blast_radius(tmp_path) -> None:
    audit = KairosAuditLog(tmp_path / "kairos.jsonl")

    audit.record_action(
        session_id="s1",
        action="tool_call_completed",
        files_changed=["src/app.py"],
        metadata={"tool_name": "edit_file"},
    )

    records = audit.read_records()
    assert records == [
        {
            "session_id": "s1",
            "action": "tool_call_completed",
            "files_changed": ["src/app.py"],
            "metadata": {"tool_name": "edit_file"},
        }
    ]


def test_kairos_pulse_formats_recent_audit_summary() -> None:
    records = [
        {
            "session_id": "s1",
            "action": "kairos_tick_dry_run",
            "files_changed": [],
            "metadata": {"tick_id": "t1", "read_only": True},
        },
        {
            "session_id": "s1",
            "action": "tool_call_completed",
            "files_changed": ["src/app.py", "README.md"],
            "metadata": {"tool_name": "edit_file"},
        },
        {
            "session_id": "s2",
            "action": "kairos_cost_cap_skip",
            "files_changed": [],
            "metadata": {"tick_id": "t2"},
        },
    ]

    pulse = format_kairos_pulse(records, limit=2)

    assert "KAIROS pulse" in pulse
    assert "3 audit records" in pulse
    assert "2 sessions" in pulse
    assert "2 unique files changed" in pulse
    assert "kairos_tick_dry_run: 1" in pulse
    assert "tool_call_completed: 1" in pulse
    assert "kairos_cost_cap_skip: 1" in pulse
    assert "Recent activity:" in pulse
    assert "tool=edit_file" in pulse
    assert "tick=t2" in pulse
    assert "tick=t1" not in pulse


def test_kairos_pulse_handles_empty_audit_log() -> None:
    assert format_kairos_pulse([]) == "KAIROS pulse: no audit records yet."


def test_build_tick_rpc_request_includes_trace_metadata() -> None:
    request = build_tick_rpc_request(
        request_id=7,
        session_id="s1",
        tick_id="tick-123",
        message="<tick>You're awake.</tick>",
        read_only=True,
    )

    assert request == {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "kairos.tick",
        "params": {
            "message": "<tick>You're awake.</tick>",
            "session_id": "s1",
            "tick_id": "tick-123",
            "read_only": True,
        },
    }


def test_cost_cap_skip_when_limit_is_zero() -> None:
    assert should_skip_for_cost_cap(cost_limit_usd=0.0, current_cost_usd=0.0) is True
    assert should_skip_for_cost_cap(cost_limit_usd=1.0, current_cost_usd=0.99) is False
    assert should_skip_for_cost_cap(cost_limit_usd=1.0, current_cost_usd=1.0) is True
    assert should_skip_for_cost_cap(cost_limit_usd=None, current_cost_usd=999.0) is False


@pytest.mark.asyncio()
async def test_send_tick_rpc_frames_jsonrpc_over_tcp() -> None:
    received: list[dict] = []

    async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        line = await reader.readline()
        request = json.loads(line.decode("utf-8"))
        received.append(request)
        writer.write(b'{"jsonrpc":"2.0","id":9,"result":{"ok":true}}\n')
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        result = await send_tick_rpc(
            host="127.0.0.1",
            port=port,
            session_id="s1",
            tick_id="tick-abc",
            message="<tick>You're awake.</tick>",
            read_only=True,
            request_id=9,
        )

    assert result == {"ok": True}
    assert received == [
        build_tick_rpc_request(
            request_id=9,
            session_id="s1",
            tick_id="tick-abc",
            message="<tick>You're awake.</tick>",
            read_only=True,
        )
    ]


@pytest.mark.asyncio()
async def test_tick_triggered_tool_budget_returns_deferred_on_timeout(
    tmp_path,
) -> None:
    store = SessionStore(tmp_path / "session.db")
    try:
        session_id = store.create_session(
            title="Test",
            model="m",
            provider="mock",
            project_dir=str(tmp_path),
        )
        loop = AgentLoop(
            provider=object(),
            tool_registry=ToolRegistry(),
            approval_manager=ApprovalManager(ApprovalMode.AUTONOMOUS),
            session_store=store,
            session_id=session_id,
        )

        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(1)
            return ("late", None)

        loop._execute_tool_call = slow_execute  # type: ignore[method-assign]

        outcome = await loop._execute_tool_call_with_budget(
            ToolCall(id="tc-slow", name="sleep", arguments={}),
            1,
            blocking_budget_sec=0.01,
        )
    finally:
        store.close()

    assert outcome.result == "Deferred: action exceeded 0.01s KAIROS blocking budget."
    assert outcome.terminate_final is None
