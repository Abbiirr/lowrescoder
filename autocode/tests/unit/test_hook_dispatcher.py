from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from autocode.layer4.llm import ToolCall


@dataclass
class RecordingHook:
    name: str
    calls: list[str]
    fail_on: str = ""
    result_suffix: str = ""
    enabled: bool = True
    tokens: list[str] = field(default_factory=list)

    def should_run(self) -> bool:
        return self.enabled

    def pre_tool_call(self, tc: ToolCall) -> None:
        self.calls.append(f"{self.name}:pre:{tc.name}")
        if self.fail_on == "pre":
            raise RuntimeError("pre failed")

    def post_tool_call_success(self, tc: ToolCall, result: str) -> str | None:
        self.calls.append(f"{self.name}:success:{result}")
        if self.fail_on == "success":
            raise RuntimeError("success failed")
        if self.result_suffix:
            return f"{result}{self.result_suffix}"
        return None

    def post_tool_call_error(self, tc: ToolCall, exc: BaseException) -> None:
        self.calls.append(f"{self.name}:error:{type(exc).__name__}")
        if self.fail_on == "error":
            raise RuntimeError("error failed")

    def pre_turn(self, turn_id: str) -> None:
        self.calls.append(f"{self.name}:pre_turn:{turn_id}")

    def post_turn(self, turn_id: str, status: str) -> None:
        self.calls.append(f"{self.name}:post_turn:{turn_id}:{status}")

    def on_token(self, text: str) -> None:
        self.tokens.append(text)
        self.calls.append(f"{self.name}:token:{text}")

    async def post_tool_call_success_async(self, tc: ToolCall, result: str) -> str | None:
        self.calls.append(f"{self.name}:async_success:{result}")
        if self.fail_on == "async_success":
            raise RuntimeError("async success failed")
        if self.result_suffix:
            return f"{result}{self.result_suffix}"
        return None


def _tool_call(name: str = "read_file", arguments: dict[str, Any] | None = None) -> ToolCall:
    return ToolCall(id="tc-1", name=name, arguments=arguments or {})


def test_dispatcher_runs_hooks_in_registration_order() -> None:
    from autocode.agent.hooks import HookDispatcher

    calls: list[str] = []
    dispatcher = HookDispatcher()
    dispatcher.register(RecordingHook("a", calls))
    dispatcher.register(RecordingHook("b", calls))

    dispatcher.pre_tool_call(_tool_call())

    assert calls == ["a:pre:read_file", "b:pre:read_file"]


def test_dispatcher_isolates_hook_exceptions() -> None:
    from autocode.agent.hooks import HookDispatcher

    calls: list[str] = []
    dispatcher = HookDispatcher()
    dispatcher.register(RecordingHook("bad", calls, fail_on="pre"))
    dispatcher.register(RecordingHook("good", calls))

    dispatcher.pre_tool_call(_tool_call())

    assert calls == ["bad:pre:read_file", "good:pre:read_file"]


def test_dispatcher_skips_disabled_hooks() -> None:
    from autocode.agent.hooks import HookDispatcher

    calls: list[str] = []
    dispatcher = HookDispatcher()
    dispatcher.register(RecordingHook("off", calls, enabled=False))
    dispatcher.register(RecordingHook("on", calls))

    dispatcher.pre_turn("turn-001")
    dispatcher.post_turn("turn-001", "completed")

    assert calls == ["on:pre_turn:turn-001", "on:post_turn:turn-001:completed"]


def test_dispatcher_chains_success_result_overrides() -> None:
    from autocode.agent.hooks import HookDispatcher

    calls: list[str] = []
    dispatcher = HookDispatcher()
    dispatcher.register(RecordingHook("a", calls, result_suffix="-a"))
    dispatcher.register(RecordingHook("b", calls, result_suffix="-b"))

    result = dispatcher.post_tool_call_success(_tool_call(), "base")

    assert result == "base-a-b"
    assert calls == ["a:success:base", "b:success:base-a"]


def test_dispatcher_dispatches_token_callbacks() -> None:
    from autocode.agent.hooks import HookDispatcher

    calls: list[str] = []
    hook = RecordingHook("h", calls)
    dispatcher = HookDispatcher([hook])

    dispatcher.on_token("hello")

    assert hook.tokens == ["hello"]
    assert calls == ["h:token:hello"]


@pytest.mark.asyncio()
async def test_dispatcher_chains_async_success_result_overrides() -> None:
    from autocode.agent.hooks import HookDispatcher

    calls: list[str] = []
    dispatcher = HookDispatcher()
    dispatcher.register(RecordingHook("bad", calls, fail_on="async_success"))
    dispatcher.register(RecordingHook("a", calls, result_suffix="-a"))
    dispatcher.register(RecordingHook("b", calls, result_suffix="-b"))

    result = await dispatcher.post_tool_call_success_async(_tool_call(), "base")

    assert result == "base-a-b"
    assert calls == [
        "bad:async_success:base",
        "a:async_success:base",
        "b:async_success:base-a",
    ]


def test_scratch_offload_hook_replaces_large_result_and_emits_telemetry(tmp_path) -> None:
    from autocode.agent.hooks import ScratchOffloadHook
    from autocode.agent.scratch import ScratchStore

    events: list[tuple[str, dict[str, Any]]] = []
    hook = ScratchOffloadHook(
        scratch_store=ScratchStore(tmp_path / "scratch", thread_id="s1"),
        telemetry_emit=lambda kind, data: events.append((kind, data)),
    )

    hook.pre_turn("turn-001")
    result = hook.post_tool_call_success(
        _tool_call("large_tool"),
        "\n".join(f"line {i}" for i in range(1000)),
    )

    assert result is not None
    assert "[Tool output offloaded" in result
    assert events[0][0] == "tool_output_offloaded"
    assert events[0][1]["tool_name"] == "large_tool"
    assert events[0][1]["result_bytes"] > 5_000


def test_git_aware_staging_hook_appends_commit_proposal(tmp_path, monkeypatch) -> None:
    from autocode.agent.git_aware_staging import StagingResult
    from autocode.agent.hooks import GitAwareStagingHook

    calls: list[tuple[list[str], Path]] = []

    def fake_stage(files: list[str], *, project_root: Path, **kwargs: Any) -> StagingResult:
        calls.append((files, project_root))
        return StagingResult(
            staged=True,
            files=files,
            proposed_commit_message="Update staged.txt",
        )

    monkeypatch.setattr("autocode.agent.hooks.stage_post_edit", fake_stage)
    hook = GitAwareStagingHook(
        project_root=tmp_path,
        extract_touched_files=lambda tc: ["staged.txt"],
    )

    result = hook.post_tool_call_success(_tool_call("write_file"), "ok")

    assert calls == [(["staged.txt"], tmp_path)]
    assert result is not None
    assert "Proposed commit message: Update staged.txt" in result


def test_per_tool_checkpoint_hook_snapshots_touched_files(tmp_path, monkeypatch) -> None:
    from autocode.agent.hooks import PerToolCheckpointHook

    snapshot_calls: list[tuple[Path, Path, list[str]]] = []

    def fake_snapshot_files(project_root: Path, snap_dir: Path, touched: list[str]) -> None:
        snapshot_calls.append((project_root, snap_dir, touched))

    monkeypatch.setattr("autocode.agent.hooks.snapshot_files", fake_snapshot_files)
    checkpoint_store = RecordingCheckpointStore()
    task_store = object()
    hook = PerToolCheckpointHook(
        checkpoint_store=checkpoint_store,
        task_store=task_store,
        project_root=tmp_path,
        session_id="s1",
        extract_touched_files=lambda tc: ["changed.py"],
    )

    hook.pre_tool_call(_tool_call("write_file", {"path": "changed.py"}))

    assert snapshot_calls
    assert snapshot_calls[0][0] == tmp_path
    assert snapshot_calls[0][2] == ["changed.py"]
    assert checkpoint_store.calls == [
        {
            "task_store": task_store,
            "tool_call_id": "tc-1",
            "tool_name": "write_file",
            "tool_call_idx": 0,
            "kind": "pre_tool",
            "files_touched": ["changed.py"],
            "label": "pre write_file",
        }
    ]


@pytest.mark.asyncio()
async def test_auto_verify_hook_appends_success_note(tmp_path) -> None:
    from autocode.agent.auto_verify import AutoVerifyConfig, VerificationResult
    from autocode.agent.hooks import AutoVerifyHook

    async def fake_verify(*args: Any, **kwargs: Any) -> VerificationResult:
        return VerificationResult(checked_files=[tmp_path / "changed.py"])

    hook = AutoVerifyHook(
        project_root=tmp_path,
        config=AutoVerifyConfig(),
        verify_after_edit=fake_verify,
        extract_touched_files=lambda tc: ["changed.py"],
    )

    result = await hook.post_tool_call_success_async(
        _tool_call("write_file", {"path": "changed.py"}),
        "write ok",
    )

    assert result == "write ok\n\nVerification passed: 1 file checked."


class RecordingCheckpointStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def save_per_tool_checkpoint(self, task_store: Any, **kwargs: Any) -> str:
        self.calls.append({"task_store": task_store, **kwargs})
        return "ckpt-1"
