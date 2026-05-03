from __future__ import annotations

from pathlib import Path

import pytest

from autocode.agent.context import ContextEngine
from autocode.session.session_notes import (
    ACTIVATION_TOKENS,
    MIN_TOOL_CALLS,
    SESSION_NOTES_TOOL_ALLOWLIST,
    UPDATE_INTERVAL_TOKENS,
    SessionNotes,
)
from autocode.session.store import SessionStore


def test_should_update_waits_for_activation_threshold(tmp_path: Path) -> None:
    notes = SessionNotes(session_id="s1", base_dir=tmp_path)
    for _ in range(MIN_TOOL_CALLS):
        notes.record_tool_call()

    assert notes.should_update(ACTIVATION_TOKENS - 1) is False
    assert notes.should_update(ACTIVATION_TOKENS) is True


def test_should_update_respects_interval_after_first_update(tmp_path: Path) -> None:
    notes = SessionNotes(session_id="s1", base_dir=tmp_path)
    for _ in range(MIN_TOOL_CALLS):
        notes.record_tool_call()

    notes.update_from_text("initial notes", total_tokens=ACTIVATION_TOKENS)
    for _ in range(MIN_TOOL_CALLS):
        notes.record_tool_call()

    assert notes.should_update(ACTIVATION_TOKENS + UPDATE_INTERVAL_TOKENS - 1) is False
    assert notes.should_update(ACTIVATION_TOKENS + UPDATE_INTERVAL_TOKENS) is True


def test_should_update_requires_three_tool_calls_between_updates(tmp_path: Path) -> None:
    notes = SessionNotes(session_id="s1", base_dir=tmp_path)

    assert notes.should_update(ACTIVATION_TOKENS) is False
    for _ in range(MIN_TOOL_CALLS - 1):
        notes.record_tool_call()
    assert notes.should_update(ACTIVATION_TOKENS) is False
    notes.record_tool_call()
    assert notes.should_update(ACTIVATION_TOKENS) is True


def test_read_for_compaction_returns_session_notes_file(tmp_path: Path) -> None:
    notes = SessionNotes(session_id="s1", base_dir=tmp_path)
    notes.update_from_text("Decision: keep Path A deterministic", total_tokens=ACTIVATION_TOKENS)

    assert "Path A deterministic" in notes.read_for_compaction()


@pytest.mark.asyncio
async def test_context_auto_compact_uses_path_a_when_session_notes_exist(
    tmp_path: Path,
) -> None:
    store = SessionStore(tmp_path / "sessions.db")
    session_id = store.create_session("test", "m", "p", str(tmp_path))
    for idx in range(8):
        store.add_message(session_id, "user", f"message {idx} " + ("x" * 500), 200)
    notes = SessionNotes(session_id=session_id, base_dir=tmp_path)
    notes.update_from_text("Session Notes: retain the important state", total_tokens=12_000)
    events: list[dict[str, object]] = []
    engine = ContextEngine(
        provider=None,
        session_store=store,
        context_length=2000,
        compaction_threshold=0.1,
        session_notes=notes,
        telemetry_emit=lambda kind, payload: events.append({"kind": kind, **payload}),
    )

    summary = await engine.auto_compact(session_id)

    assert "important state" in summary
    assert store.get_messages(session_id)[0].content == summary
    assert any(event["kind"] == "compaction_event" and event["path"] == "A" for event in events)


def test_session_notes_subagent_budget_is_bounded(tmp_path: Path) -> None:
    notes = SessionNotes(session_id="s1", base_dir=tmp_path, max_update_chars=40)

    notes.update_from_text("x" * 100, total_tokens=ACTIVATION_TOKENS)

    assert len(notes.read_for_compaction()) <= 40


def test_update_uses_write_only_bounded_updater_contract(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    class Loop:
        current_objective = "ship memory"
        session_summary = "decision: use files"

        def run_session_notes_update(
            self,
            prompt: str,
            *,
            allowed_tools: tuple[str, ...],
            max_output_chars: int,
        ) -> str:
            calls.append(
                {
                    "prompt": prompt,
                    "allowed_tools": allowed_tools,
                    "max_output_chars": max_output_chars,
                }
            )
            return "bounded updater result " + ("x" * 100)

    notes = SessionNotes(session_id="s1", base_dir=tmp_path, max_update_chars=200)

    notes.update(agent_loop=Loop(), total_tokens=ACTIVATION_TOKENS)

    assert calls[0]["allowed_tools"] == SESSION_NOTES_TOOL_ALLOWLIST
    assert calls[0]["max_output_chars"] == 200
    assert "Use only the write_file tool" in str(calls[0]["prompt"])
    assert len(notes.read_for_compaction()) == 123
