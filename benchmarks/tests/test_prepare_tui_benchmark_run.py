from __future__ import annotations

from pathlib import Path

from benchmarks.adapters.base import BenchmarkTask
from benchmarks.prepare_tui_benchmark_run import (
    CORE_SCOPE,
    FULL_SCOPE,
    CheckResult,
    build_operator_commands,
    emit_operator_pack,
    select_auth_source,
)


def test_select_auth_source_prefers_litellm_api_key() -> None:
    env = {
        "OPENROUTER_API_KEY": "or-key",
        "LITELLM_MASTER_KEY": "master-key",
        "LITELLM_API_KEY": "litellm-key",
    }
    assert select_auth_source(env) == "LITELLM_API_KEY"


def test_build_operator_commands_uses_full_sweep_and_altscreen() -> None:
    commands = build_operator_commands(
        scope=FULL_SCOPE,
        mode="altscreen",
        run_id="run-123",
        canary_tasks=2,
    )

    assert commands["tui_warmup"] == "uv run autocode chat --rust-altscreen"
    assert "--autocode-runner tui" in commands["tui_canary_lane"]
    assert "--autocode-runner tui" in commands["tui_sweep"]
    assert "run_b7_b30_sweep.sh" in commands["sweep"]
    assert "--lane B7" in commands["canary_lane"]
    assert "--max-tasks 2" in commands["canary_lane"]


def test_emit_operator_pack_writes_index_and_task_docs(tmp_path: Path) -> None:
    task = BenchmarkTask(
        task_id="sample-task",
        description="Fix the failing sample task",
        repo="example/repo",
        difficulty="medium",
        language="python",
        category="bugfix",
        setup_commands=["pip install -e ."],
        grading_command="pytest -q",
        extra={"python_version": "3.11"},
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")

    pack_dir = tmp_path / "pack"
    commands = build_operator_commands(
        scope=CORE_SCOPE,
        mode="inline",
        run_id="run-456",
        canary_tasks=1,
    )
    checks = [CheckResult(name="gateway_health", ok=True, detail="healthy")]

    emit_operator_pack(
        pack_dir=pack_dir,
        scope=CORE_SCOPE,
        mode="inline",
        run_id="run-456",
        commands=commands,
        manifests={
            "B7": (manifest_path, {}, [task]),
            "B8": (manifest_path, {}, []),
            "B9-PROXY": (manifest_path, {}, []),
            "B10-PROXY": (manifest_path, {}, []),
            "B11": (manifest_path, {}, []),
            "B12-PROXY": (manifest_path, {}, []),
            "B13-PROXY": (manifest_path, {}, []),
            "B14-PROXY": (manifest_path, {}, []),
        },
        checks=checks,
    )

    index_text = (pack_dir / "index.md").read_text(encoding="utf-8")
    task_text = (pack_dir / "tasks" / "B7--sample-task.md").read_text(
        encoding="utf-8"
    )

    assert "TUI Benchmark Operator Pack" in index_text
    assert "run-456" in index_text
    assert "tasks/B7--sample-task.md" in index_text
    assert "Fix the failing sample task" in task_text
    assert "uv run autocode chat" in task_text
    assert "pytest -q" in task_text
