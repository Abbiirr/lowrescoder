"""Stable TUI v1 Slice 4 — tests for HookRegistry (Milestone B.3).

Covers settings.json loading, event matchers, PreToolUse blocking (exit-code
and JSON), timeout enforcement, payload I/O, working directory, environment
variable injection, and execution order.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from autocode.agent.hooks import (
    HookDefinition,
    HookEvent,
    HookRegistry,
    HookResult,
    HookSource,
)


def _write_settings(root: Path, settings: dict) -> Path:
    settings_path = root / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings), encoding="utf-8")
    return settings_path


def _write_hook(root: Path, name: str, body: str) -> Path:
    path = root / name
    path.write_text(body, encoding="utf-8")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


# ---------- settings loading ----------


def test_load_empty_project_returns_empty_registry(tmp_path: Path) -> None:
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    assert registry.hooks_for(HookEvent.SESSION_START) == []
    assert registry.hooks_for(HookEvent.PRE_TOOL_USE) == []


def test_load_project_settings(tmp_path: Path) -> None:
    _write_settings(
        tmp_path,
        {"hooks": {"SessionStart": [{"command": ["/bin/true"]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    hooks = registry.hooks_for(HookEvent.SESSION_START)
    assert len(hooks) == 1
    assert hooks[0].source == HookSource.PROJECT
    assert hooks[0].command == ["/bin/true"]


def test_load_user_settings(tmp_path: Path) -> None:
    user_root = tmp_path / "u"
    _write_settings(user_root, {"hooks": {"Stop": [{"command": ["/bin/true"]}]}})
    registry = HookRegistry.load(project_root=tmp_path, user_root=user_root)
    hooks = registry.hooks_for(HookEvent.STOP)
    assert len(hooks) == 1
    assert hooks[0].source == HookSource.USER


def test_load_project_and_user_merge(tmp_path: Path) -> None:
    _write_settings(tmp_path, {"hooks": {"SessionStart": [{"command": ["/p"]}]}})
    user_root = tmp_path / "u"
    _write_settings(user_root, {"hooks": {"SessionStart": [{"command": ["/u"]}]}})
    registry = HookRegistry.load(project_root=tmp_path, user_root=user_root)
    hooks = registry.hooks_for(HookEvent.SESSION_START)
    # Both present; project first
    assert len(hooks) == 2
    assert hooks[0].source == HookSource.PROJECT
    assert hooks[1].source == HookSource.USER


def test_load_malformed_json_returns_empty(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("{ not json", encoding="utf-8")
    # Should not raise; should return empty
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    assert registry.hooks_for(HookEvent.SESSION_START) == []


# ---------- firing ----------


def test_fire_no_hooks_returns_empty(tmp_path: Path) -> None:
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(HookEvent.SESSION_START, {"session_id": "abc"})
    assert results == []


def test_fire_session_start_runs_hook(tmp_path: Path) -> None:
    trace = tmp_path / "trace.txt"
    hook = _write_hook(
        tmp_path,
        "log.sh",
        f"#!/bin/bash\necho hi > {trace}\nexit 0\n",
    )
    _write_settings(tmp_path, {"hooks": {"SessionStart": [{"command": [str(hook)]}]}})
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(HookEvent.SESSION_START, {"session_id": "abc"})
    assert len(results) == 1
    assert results[0].exit_code == 0
    assert trace.exists()


def test_fire_pre_tool_use_exit_nonzero_blocks(tmp_path: Path) -> None:
    hook = _write_hook(tmp_path, "deny.sh", "#!/bin/bash\nexit 1\n")
    _write_settings(
        tmp_path,
        {"hooks": {"PreToolUse": [{"command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(
        HookEvent.PRE_TOOL_USE, {"tool": "Bash"}, tool_name="Bash"
    )
    assert len(results) == 1
    assert results[0].blocked is True
    assert results[0].exit_code == 1


def test_fire_pre_tool_use_json_block_true(tmp_path: Path) -> None:
    hook = _write_hook(
        tmp_path,
        "json_block.sh",
        '#!/bin/bash\necho \'{"block": true, "reason": "policy"}\'\nexit 0\n',
    )
    _write_settings(
        tmp_path,
        {"hooks": {"PreToolUse": [{"command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(
        HookEvent.PRE_TOOL_USE, {"tool": "Bash"}, tool_name="Bash"
    )
    assert results[0].blocked is True
    assert "policy" in results[0].block_reason


def test_fire_pre_tool_use_matcher_filters_by_tool(tmp_path: Path) -> None:
    # Matcher "Bash" should fire only for Bash, skip for Read
    hook = _write_hook(tmp_path, "always.sh", "#!/bin/bash\nexit 0\n")
    _write_settings(
        tmp_path,
        {"hooks": {"PreToolUse": [{"matcher": "Bash", "command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)

    results_read = registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Read")
    assert results_read == []

    results_bash = registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Bash")
    assert len(results_bash) == 1


def test_fire_pre_tool_use_wildcard_matcher(tmp_path: Path) -> None:
    hook = _write_hook(tmp_path, "all.sh", "#!/bin/bash\nexit 0\n")
    _write_settings(
        tmp_path,
        {"hooks": {"PreToolUse": [{"matcher": "*", "command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Read")
    assert len(results) == 1


def test_fire_pre_tool_use_regex_matcher(tmp_path: Path) -> None:
    hook = _write_hook(tmp_path, "either.sh", "#!/bin/bash\nexit 0\n")
    _write_settings(
        tmp_path,
        {"hooks": {"PreToolUse": [{"matcher": "Write|Edit", "command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    assert len(registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Write")) == 1
    assert len(registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Edit")) == 1
    assert registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Read") == []


def test_fire_post_tool_use_does_not_block(tmp_path: Path) -> None:
    hook = _write_hook(tmp_path, "fail.sh", "#!/bin/bash\nexit 1\n")
    _write_settings(
        tmp_path,
        {"hooks": {"PostToolUse": [{"command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(HookEvent.POST_TOOL_USE, {}, tool_name="Read")
    # Result is captured, but PostToolUse is never advisory-blocking
    assert len(results) == 1
    assert results[0].blocked is False


def test_fire_timeout_enforced(tmp_path: Path) -> None:
    hook = _write_hook(
        tmp_path, "slow.sh", "#!/bin/bash\nsleep 10\nexit 0\n"
    )
    _write_settings(
        tmp_path,
        {
            "hooks": {
                "PreToolUse": [
                    {"command": [str(hook)], "timeout_s": 0.3}
                ]
            }
        },
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Read")
    assert len(results) == 1
    assert results[0].blocked is True
    assert "timeout" in results[0].block_reason.lower()


def test_fire_payload_written_to_stdin(tmp_path: Path) -> None:
    trace = tmp_path / "stdin.log"
    hook = _write_hook(
        tmp_path,
        "cat.sh",
        f"#!/bin/bash\ncat > {trace}\nexit 0\n",
    )
    _write_settings(
        tmp_path,
        {"hooks": {"SessionStart": [{"command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    registry.fire(HookEvent.SESSION_START, {"session_id": "xyz", "custom": "key"})
    captured = json.loads(trace.read_text())
    assert captured["session_id"] == "xyz"
    assert captured["custom"] == "key"
    # Canonical keys automatically added
    assert captured["event"] == "SessionStart"


def test_fire_adds_environment_variables(tmp_path: Path) -> None:
    trace = tmp_path / "env.log"
    hook = _write_hook(
        tmp_path,
        "env.sh",
        f"#!/bin/bash\necho \"EVENT=$AUTOCODE_EVENT\" > {trace}\n"
        f"echo \"SID=$AUTOCODE_SESSION_ID\" >> {trace}\nexit 0\n",
    )
    _write_settings(
        tmp_path,
        {"hooks": {"SessionStart": [{"command": [str(hook)]}]}},
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    registry.fire(HookEvent.SESSION_START, {"session_id": "sid-42"})
    log = trace.read_text()
    assert "EVENT=SessionStart" in log
    assert "SID=sid-42" in log


def test_fire_multiple_hooks_serial(tmp_path: Path) -> None:
    trace = tmp_path / "order.log"
    h1 = _write_hook(tmp_path, "h1.sh", f"#!/bin/bash\necho 1 >> {trace}\nexit 0\n")
    h2 = _write_hook(tmp_path, "h2.sh", f"#!/bin/bash\necho 2 >> {trace}\nexit 0\n")
    _write_settings(
        tmp_path,
        {
            "hooks": {
                "SessionStart": [
                    {"command": [str(h1)]},
                    {"command": [str(h2)]},
                ]
            }
        },
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(HookEvent.SESSION_START, {"session_id": "x"})
    assert len(results) == 2
    # Ran in order
    assert trace.read_text() == "1\n2\n"


def test_fire_pre_tool_use_second_hook_blocks_stops_iteration(tmp_path: Path) -> None:
    trace = tmp_path / "ran.log"
    # First hook allows; second blocks; third should NOT run
    h1 = _write_hook(tmp_path, "ok1.sh", f"#!/bin/bash\necho 1 >> {trace}\nexit 0\n")
    h2 = _write_hook(tmp_path, "deny.sh", f"#!/bin/bash\necho 2 >> {trace}\nexit 1\n")
    h3 = _write_hook(tmp_path, "ok3.sh", f"#!/bin/bash\necho 3 >> {trace}\nexit 0\n")
    _write_settings(
        tmp_path,
        {
            "hooks": {
                "PreToolUse": [
                    {"command": [str(h1)]},
                    {"command": [str(h2)]},
                    {"command": [str(h3)]},
                ]
            }
        },
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    results = registry.fire(HookEvent.PRE_TOOL_USE, {}, tool_name="Bash")
    assert any(r.blocked for r in results)
    # Short-circuit: h3 did not run
    logged = trace.read_text()
    assert "1\n" in logged
    assert "2\n" in logged
    assert "3" not in logged


def test_hook_definition_defaults() -> None:
    hd = HookDefinition(event=HookEvent.STOP, command=["/bin/true"])
    assert hd.matcher == "*"
    assert hd.timeout_s == 5.0
    assert hd.source == HookSource.PROJECT


def test_hook_result_defaults() -> None:
    r = HookResult(
        hook=HookDefinition(event=HookEvent.STOP, command=["/bin/true"]),
        exit_code=0,
        stdout="",
        stderr="",
        duration_ms=0,
    )
    assert r.blocked is False
    assert r.block_reason == ""


def test_is_blocking_helper() -> None:
    registry = HookRegistry(hooks=[])
    passing = HookResult(
        hook=HookDefinition(event=HookEvent.PRE_TOOL_USE, command=["x"]),
        exit_code=0, stdout="", stderr="", duration_ms=0, blocked=False,
    )
    blocking = HookResult(
        hook=HookDefinition(event=HookEvent.PRE_TOOL_USE, command=["x"]),
        exit_code=1, stdout="", stderr="", duration_ms=0, blocked=True,
    )
    assert registry.is_blocking([passing, passing]) is False
    assert registry.is_blocking([passing, blocking]) is True


def test_hooks_for_stop_failure_separate_from_stop(tmp_path: Path) -> None:
    _write_settings(
        tmp_path,
        {
            "hooks": {
                "Stop": [{"command": ["/bin/true"]}],
                "StopFailure": [{"command": ["/bin/false"]}],
            }
        },
    )
    registry = HookRegistry.load(project_root=tmp_path, user_root=None)
    assert len(registry.hooks_for(HookEvent.STOP)) == 1
    assert len(registry.hooks_for(HookEvent.STOP_FAILURE)) == 1
