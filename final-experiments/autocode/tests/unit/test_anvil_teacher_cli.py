"""Smoke tests for the `autocode anvil teacher` CLI surface (no network)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from autocode.anvil.teacher.cli import teacher_app
from autocode.anvil.teacher.playbook import PlaybookStore
from autocode.anvil.teacher.schemas import PlaybookDelta

runner = CliRunner()


def test_verify_command_on_clean_repo(tmp_path: Path) -> None:
    result = runner.invoke(
        teacher_app, ["verify", str(tmp_path), "--language", "generic", "--json"]
    )
    assert result.exit_code == 0
    assert '"label"' in result.stdout


def test_playbook_show_and_rules(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    store.append_delta(
        PlaybookDelta(
            delta_id="pd_1",
            trajectory_id="tj_1",
            verdict="fail",
            root_cause_class="tool.missing_capability",
            trigger="callers-of X",
            observation="escalated",
            rule="prefer L2 retrieval",
            evidence_trajectory="tj_1",
            language="python",
        )
    )
    show = runner.invoke(
        teacher_app, ["playbook", "show", "python", "--playbook-dir", str(tmp_path)]
    )
    assert show.exit_code == 0
    assert "Playbook: python" in show.stdout

    rules = runner.invoke(
        teacher_app, ["playbook", "rules", "python", "--playbook-dir", str(tmp_path)]
    )
    assert rules.exit_code == 0
    assert "prefer L2 retrieval" in rules.stdout


def test_playbook_prune_command(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path)
    for n in range(2):
        store.append_delta(
            PlaybookDelta(
                delta_id=f"pd_{n}",
                trajectory_id=f"tj_{n}",
                verdict="fail",
                root_cause_class="tool.missing_capability",
                trigger="callers-of X",
                observation="escalated",
                rule="prefer L2 retrieval",
                evidence_trajectory=f"tj_{n}",
                language="python",
            )
        )
    result = runner.invoke(
        teacher_app, ["playbook", "prune", "python", "--playbook-dir", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "Master Rules" in result.stdout


def test_run_requires_instruction_or_task_file() -> None:
    result = runner.invoke(teacher_app, ["run"])
    assert result.exit_code == 2
