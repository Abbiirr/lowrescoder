"""Tests for the headless runner builders + sandbox/diff helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from autocode.anvil.teacher.runners import (
    GatewayConfig,
    build_student_cmd,
    build_student_env,
    build_teacher_cmd,
    build_teacher_env,
    prepare_sandbox,
    working_diff,
)


def _cfg() -> GatewayConfig:
    return GatewayConfig(
        api_base="http://localhost:4000/v1",
        api_key="sk-test",
        student_model="coding",
        teacher_model="fast",
        student_bin="autocode",
        puku_bin="puku-cli",
        max_budget_usd=0.25,
    )


def test_student_cmd_is_headless_json_with_bypass() -> None:
    cmd = build_student_cmd("fix the bug", _cfg())
    assert cmd[:3] == ["autocode", "exec", "fix the bug"]
    assert "--json" in cmd
    assert "--permission-mode" in cmd and "bypassPermissions" in cmd
    assert "--max-budget-usd" in cmd and "0.25" in cmd
    assert "--append-system-prompt" not in cmd  # omitted when empty


def test_student_cmd_loads_playbook_via_append_system_prompt() -> None:
    cmd = build_student_cmd("fix it", _cfg(), append_system_prompt="## Playbook\n- prefer L2")
    assert "--append-system-prompt" in cmd
    idx = cmd.index("--append-system-prompt")
    assert "prefer L2" in cmd[idx + 1]


def test_student_env_points_at_gateway() -> None:
    env = build_student_env(_cfg(), Path("/tmp/sb"))
    assert env["AUTOCODE_LLM_API_BASE"] == "http://localhost:4000/v1"
    assert env["AUTOCODE_LLM_MODEL"] == "coding"
    assert env["OPENROUTER_API_KEY"] == "sk-test"
    assert env["AUTOCODE_SANDBOX"] == "/tmp/sb"


def test_teacher_cmd_stream_json_via_openai_provider() -> None:
    cmd = build_teacher_cmd(_cfg(), Path("/tmp/sb"))
    assert cmd[0] == "puku-cli"
    assert "--print" in cmd
    assert "--output-format" in cmd and "stream-json" in cmd
    assert "--provider" in cmd and "openai" in cmd
    assert "--model" in cmd and "fast" in cmd
    assert "--add-dir" in cmd and "/tmp/sb" in cmd


def test_teacher_env_routes_gateway_and_clears_cloud_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-real-cloud")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    env = build_teacher_env(_cfg())
    assert env["OPENAI_BASE_URL"] == "http://localhost:4000/v1"
    assert env["OPENAI_API_KEY"] == "sk-test"
    # Critical safety: cloud keys are stripped so puku cannot bill a real provider.
    assert "ANTHROPIC_API_KEY" not in env
    assert "ANTHROPIC_BASE_URL" not in env


def test_gateway_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOCODE_LLM_API_BASE", "http://localhost:4000/v1")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("AUTOCODE_BENCH_MODEL", "swebench")
    cfg = GatewayConfig.from_env()
    assert cfg.api_base == "http://localhost:4000/v1"
    assert cfg.api_key == "sk-master"
    assert cfg.student_model == "swebench"
    assert cfg.is_local() is True


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_prepare_sandbox_and_working_diff(tmp_path: Path) -> None:
    sb = tmp_path / "sb"
    prepare_sandbox(sb)
    assert (sb / ".git").is_dir()
    # No change yet => empty diff.
    assert working_diff(sb).strip() == ""
    # Create a file => diff is non-empty and mentions the file.
    (sb / "mathutil.py").write_text("def add(a, b):\n    return a + b\n")
    diff = working_diff(sb)
    assert "mathutil.py" in diff
    assert "def add" in diff
