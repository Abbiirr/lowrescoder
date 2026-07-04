"""Tests for auto-verify-after-edit runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from autocode.agent.approval import ApprovalManager, ApprovalMode
from autocode.agent.auto_verify import (
    AutoVerifyConfig,
    VerificationDiagnostic,
    verify_after_edit,
)
from autocode.agent.loop import AgentLoop
from autocode.agent.tools import ToolDefinition, ToolRegistry
from autocode.app.commands import create_default_router
from autocode.config import AutoCodeConfig
from autocode.layer4.llm import ToolCall
from autocode.session.store import SessionStore


@pytest.fixture()
def store(tmp_path: Path) -> SessionStore:
    session_store = SessionStore(tmp_path / "test.db")
    yield session_store
    session_store.close()


@pytest.fixture()
def session_id(store: SessionStore, tmp_path: Path) -> str:
    return store.create_session(
        title="Test",
        model="m",
        provider="mock",
        project_dir=str(tmp_path),
    )


@pytest.mark.asyncio()
async def test_verify_after_edit_returns_noop_for_file_without_adapter(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("plain text\n", encoding="utf-8")

    result = await verify_after_edit([target], project_root=tmp_path)

    assert result.ok
    assert result.checked_files == []
    assert result.skipped_files == [target]
    assert result.diagnostics == []


@pytest.mark.asyncio()
async def test_verify_after_edit_normalizes_lsp_diagnostics(tmp_path: Path) -> None:
    target = tmp_path / "hello.py"
    target.write_text("print('broken'\n", encoding="utf-8")

    async def fake_diagnostics(path: Path, root: Path) -> list[dict[str, Any]]:
        assert path == target
        assert root == tmp_path
        return [
            {
                "message": "unclosed parenthesis",
                "severity": 1,
                "range": {"start": {"line": 0, "character": 5}},
            }
        ]

    result = await verify_after_edit(
        [target],
        project_root=tmp_path,
        diagnostic_provider=fake_diagnostics,
    )

    assert not result.ok
    assert result.checked_files == [target]
    assert result.diagnostics == [
        VerificationDiagnostic(
            path=target,
            line=1,
            column=6,
            severity="error",
            message="unclosed parenthesis",
        )
    ]
    assert "hello.py:1:6 [error] unclosed parenthesis" in result.to_system_message()


@pytest.mark.asyncio()
async def test_verify_after_edit_respects_disabled_languages(tmp_path: Path) -> None:
    target = tmp_path / "hello.py"
    target.write_text("print('ok')\n", encoding="utf-8")

    result = await verify_after_edit(
        [target],
        project_root=tmp_path,
        config=AutoVerifyConfig(languages=["go"]),
        diagnostic_provider=lambda path, root: [],
    )

    assert result.ok
    assert result.checked_files == []
    assert result.skipped_files == [target]


@pytest.mark.asyncio()
async def test_agent_loop_appends_verification_failure_to_mutating_tool_result(
    store: SessionStore,
    session_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hello.py"

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="write_file",
        description="write",
        parameters={"type": "object", "properties": {}},
        handler=lambda path, content: "Wrote file",
        mutates_fs=True,
    ))
    failure = VerificationDiagnostic(
        path=target,
        line=1,
        column=1,
        severity="error",
        message="syntax error",
    )

    async def fake_verify_after_edit(*args: Any, **kwargs: Any) -> Any:
        from autocode.agent.auto_verify import VerificationResult

        return VerificationResult(checked_files=[target], diagnostics=[failure])

    monkeypatch.setattr(
        "autocode.agent.loop.verify_after_edit",
        fake_verify_after_edit,
        raising=False,
    )
    loop = AgentLoop(
        provider=None,
        tool_registry=registry,
        approval_manager=ApprovalManager(ApprovalMode.AUTO),
        session_store=store,
        session_id=session_id,
        project_root=tmp_path,
        verify_config=AutoVerifyConfig(enabled=True, max_iterations=3),
    )
    msg_id = store.add_message(session_id, "assistant", "")

    result = await loop._execute_tool_call(
        ToolCall(
            id="tc1",
            name="write_file",
            arguments={"path": str(target), "content": "bad"},
        ),
        msg_id=msg_id,
    )

    assert "Wrote file" in result.result
    assert "Verification failed" in result.result
    assert "hello.py:1:1 [error] syntax error" in result.result


@pytest.mark.asyncio()
async def test_agent_loop_verify_off_bypasses_post_edit_verification(
    store: SessionStore,
    session_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="write_file",
        description="write",
        parameters={"type": "object", "properties": {}},
        handler=lambda path, content: "Wrote file",
        mutates_fs=True,
    ))
    verify_calls = 0

    async def fake_verify_after_edit(*args: Any, **kwargs: Any) -> Any:
        nonlocal verify_calls
        verify_calls += 1
        raise AssertionError("verification should be bypassed")

    monkeypatch.setattr(
        "autocode.agent.loop.verify_after_edit",
        fake_verify_after_edit,
        raising=False,
    )
    loop = AgentLoop(
        provider=None,
        tool_registry=registry,
        approval_manager=ApprovalManager(ApprovalMode.AUTO),
        session_store=store,
        session_id=session_id,
        project_root=tmp_path,
        verify_config=AutoVerifyConfig(enabled=False),
    )
    msg_id = store.add_message(session_id, "assistant", "")

    result = await loop._execute_tool_call(
        ToolCall(
            id="tc1",
            name="write_file",
            arguments={"path": str(tmp_path / "hello.py"), "content": "bad"},
        ),
        msg_id=msg_id,
    )

    assert result.result == "Wrote file"
    assert verify_calls == 0


@pytest.mark.asyncio()
async def test_agent_loop_persistent_verification_error_surfaces_warning_without_rollback(
    store: SessionStore,
    session_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hello.py"
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="write_file",
        description="write",
        parameters={"type": "object", "properties": {}},
        handler=lambda path, content: "Wrote file",
        mutates_fs=True,
    ))
    failure = VerificationDiagnostic(
        path=target,
        line=1,
        column=1,
        severity="error",
        message="still broken",
    )

    async def fake_verify_after_edit(*args: Any, **kwargs: Any) -> Any:
        from autocode.agent.auto_verify import VerificationResult

        return VerificationResult(checked_files=[target], diagnostics=[failure])

    monkeypatch.setattr("autocode.agent.loop.verify_after_edit", fake_verify_after_edit)
    loop = AgentLoop(
        provider=None,
        tool_registry=registry,
        approval_manager=ApprovalManager(ApprovalMode.AUTO),
        session_store=store,
        session_id=session_id,
        project_root=tmp_path,
        verify_config=AutoVerifyConfig(enabled=True, max_iterations=1),
    )
    msg_id = store.add_message(session_id, "assistant", "")

    result = await loop._execute_tool_call(
        ToolCall(
            id="tc1",
            name="write_file",
            arguments={"path": str(target), "content": "bad"},
        ),
        msg_id=msg_id,
    )

    assert "Verification failed after 1 iteration" in result.result
    assert "No automatic rollback was performed" in result.result
    assert "/rollback" in result.result


@pytest.mark.asyncio()
async def test_agent_loop_cost_cap_halts_verification_retry_instruction(
    store: SessionStore,
    session_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "hello.py"
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="write_file",
        description="write",
        parameters={"type": "object", "properties": {}},
        handler=lambda path, content: "Wrote file",
        mutates_fs=True,
    ))
    failure = VerificationDiagnostic(
        path=target,
        line=1,
        column=1,
        severity="error",
        message="syntax error",
    )

    class FakeTokenTracker:
        def pop_cost_limit_warning(self) -> tuple[float, float]:
            return (0.07, 0.05)

    async def fake_verify_after_edit(*args: Any, **kwargs: Any) -> Any:
        from autocode.agent.auto_verify import VerificationResult

        return VerificationResult(checked_files=[target], diagnostics=[failure])

    monkeypatch.setattr("autocode.agent.loop.verify_after_edit", fake_verify_after_edit)
    loop = AgentLoop(
        provider=None,
        tool_registry=registry,
        approval_manager=ApprovalManager(ApprovalMode.AUTO),
        session_store=store,
        session_id=session_id,
        project_root=tmp_path,
        token_tracker=FakeTokenTracker(),
        verify_config=AutoVerifyConfig(enabled=True, max_iterations=3),
    )
    msg_id = store.add_message(session_id, "assistant", "")

    result = await loop._execute_tool_call(
        ToolCall(
            id="tc1",
            name="write_file",
            arguments={"path": str(target), "content": "bad"},
        ),
        msg_id=msg_id,
    )

    assert "Verification retry halted: cost limit reached" in result.result
    assert "$0.07" in result.result
    assert "$0.05" in result.result


@pytest.mark.asyncio()
async def test_verify_command_toggles_config(tmp_path: Path) -> None:
    class FakeApp:
        def __init__(self) -> None:
            self.config = AutoCodeConfig()
            self.messages: list[str] = []
            self.session_store = None
            self.session_id = "s"
            self.project_root = tmp_path
            self.command_router = create_default_router()

        def add_system_message(self, content: str) -> None:
            self.messages.append(content)

    app = FakeApp()
    router = create_default_router()
    dispatch = router.dispatch("/verify off")
    assert dispatch is not None
    command, args = dispatch

    await command.handler(app, args)

    assert app.config.agent.verify.enabled is False
    assert app.messages[-1] == "Verify: **off**"

    dispatch = router.dispatch("/verify status")
    assert dispatch is not None
    command, args = dispatch
    await command.handler(app, args)

    assert "Verify: **off**" in app.messages[-1]
