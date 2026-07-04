"""Tests for the teacher-student loop orchestration (hermetic, injected runners)."""

from __future__ import annotations

import json
from pathlib import Path

from autocode.anvil.teacher.loop import TeachTask, teach
from autocode.anvil.teacher.playbook import PlaybookStore
from autocode.anvil.teacher.runners import RunResult
from autocode.anvil.teacher.schemas import (
    Layer,
    Step,
    Task,
    TestResults,
    Trajectory,
    Verdict,
    VerdictLabel,
)
from autocode.anvil.teacher.taxonomy import RootCauseClass


def _student_run(prompt: str, sb: Path, cfg) -> RunResult:
    tj = Trajectory(
        trajectory_id="tj_student",
        task=Task(instruction=prompt),
        steps=[
            Step(i=0, layer=Layer.L4.value, action="plan", tool=""),
            Step(i=1, layer=Layer.L4.value, action="generate", tool="edit_file"),
        ],
        role="student",
    )
    tj.compute_layer_distribution()
    return RunResult(role="student", trajectory=tj, diff="--- a\n+++ b\n", exit_code=0)


def _teacher_run(prompt: str, sb: Path, cfg) -> RunResult:
    tj = Trajectory(
        trajectory_id="tj_teacher",
        task=Task(instruction=prompt),
        steps=[
            Step(i=0, layer=Layer.L1.value, action="tool_call", tool="callgraph"),
            Step(i=1, layer=Layer.L2.value, action="retrieve", tool="repomap"),
        ],
        role="teacher",
    )
    tj.compute_layer_distribution()
    return RunResult(role="teacher", trajectory=tj, diff="--- a\n+++ b\n", exit_code=0)


def _verify(sandbox: Path, profile) -> Verdict:
    if sandbox.name == "student":
        return Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=0, failed=1),
            label=VerdictLabel.FAIL.value,
        )
    return Verdict(
        diff_applies=True,
        build_passed=True,
        tests=TestResults(passed=3),
        lint_clean=True,
        types_clean=True,
        label=VerdictLabel.SUCCESS.value,
    )


def test_teacher_student_cycle_appends_playbook_delta(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path / "playbook")
    task = TeachTask(task_id="t1", instruction="add caller for refresh", language="python")
    result = teach(
        task,
        workdir=tmp_path / "work",
        playbook_store=store,
        student_runner=_student_run,
        teacher_runner=_teacher_run,
        verify_fn=_verify,
        created="2026-06-21",
    )
    assert result.student_verdict.label == VerdictLabel.FAIL.value
    assert result.teacher_verdict.label == VerdictLabel.SUCCESS.value
    # Contrast: student burned L4, teacher used L1/L2 => missing_capability.
    assert (
        result.packet.root_cause.to_dict()["class"] == RootCauseClass.TOOL_MISSING_CAPABILITY.value
    )
    assert result.delta_appended is True
    # The delta really landed in the durable-memory plane and the runtime can load it.
    assert store.load_rules("python")


def test_no_teacher_still_teaches_from_student_alone(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path / "playbook")
    task = TeachTask(task_id="t2", instruction="fix it", language="python")
    result = teach(
        task,
        workdir=tmp_path / "work",
        playbook_store=store,
        run_teacher=False,
        student_runner=_student_run,
        verify_fn=_verify,
    )
    assert result.teacher_trajectory is None
    # Without contrast, an all-L4 student with no retrieval => retrieval.miss.
    assert result.packet.root_cause.to_dict()["class"] in {
        RootCauseClass.RETRIEVAL_MISS.value,
        RootCauseClass.VERIFY_NO_SELF_CHECK.value,
    }
    assert result.delta_appended is True


def test_success_appends_no_delta(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path / "playbook")

    def all_success(sandbox: Path, profile) -> Verdict:
        return Verdict(
            diff_applies=True,
            build_passed=True,
            tests=TestResults(passed=3),
            lint_clean=True,
            types_clean=True,
            label=VerdictLabel.SUCCESS.value,
        )

    task = TeachTask(task_id="t3", instruction="trivial", language="python")
    result = teach(
        task,
        workdir=tmp_path / "work",
        playbook_store=store,
        student_runner=_student_run,
        teacher_runner=_teacher_run,
        verify_fn=all_success,
    )
    assert result.delta_appended is False
    assert store.load_rules("python") == []


def test_offline_harness_fix_bundle_composes_with_gate(tmp_path: Path) -> None:
    store = PlaybookStore(tmp_path / "playbook")
    task = TeachTask(task_id="t4", instruction="add caller", language="python")
    result = teach(
        task,
        workdir=tmp_path / "work",
        playbook_store=store,
        student_runner=_student_run,
        teacher_runner=_teacher_run,
        verify_fn=_verify,
        emit_harness_fix=True,
        anvil_root=tmp_path / "anvil",
    )
    assert result.bundle_path is not None
    bundle_dir = Path(result.bundle_path)
    meta = json.loads((bundle_dir / "bundle.json").read_text())
    assert meta["channel"] == "self_distill"
    assert meta["status"] == "proposed"
    assert (bundle_dir / "decision.md").is_file()
    assert (bundle_dir / "teaching_packet.json").is_file()

    # It composes with the copycat gate: a planned bundle (no check plan) cannot pass.
    from autocode.anvil.gate import gate

    gate_result = gate(bundle_dir, repo_root=tmp_path)
    assert gate_result.passed is False  # planned, not implemented => not promotable
