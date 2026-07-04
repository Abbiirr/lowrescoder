"""The teacher-student loop — teacher mode, end to end (§5 / PLAN_05 Channel C).

One cycle:

1. Seed two sandboxes from the task's starting files (one for each agent).
2. Run **autocode (student)** and **puku-cli (teacher)** headlessly through the
   local gateway (:mod:`autocode.anvil.teacher.runners`).
3. **Verify both** with the same deterministic oracle (:mod:`verifier`).
4. **Reflect** on the student run, contrasted against the (stronger) teacher run
   when the teacher succeeded with cheaper layers (:mod:`reflector`).
5. **Curate** the playbook: append the reversible delta (the *online* path).
6. *Optionally* emit a prediction-contracted **harness fix** as a patch bundle
   that composes with the copycat gate/promote machinery (the *offline* path).

The orchestration accepts injected runners/verifier so it is unit-testable
without spawning subprocesses; the defaults run the real agents.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autocode.anvil import ANVIL_VERSION
from autocode.anvil.teacher import runners as _runners
from autocode.anvil.teacher import verifier as _verifier
from autocode.anvil.teacher.playbook import PlaybookStore
from autocode.anvil.teacher.reflector import LLM, Reflection, reflect
from autocode.anvil.teacher.runners import GatewayConfig, RunResult
from autocode.anvil.teacher.schemas import (
    PlaybookDelta,
    Task,
    TeachingPacket,
    Trajectory,
    Verdict,
)
from autocode.anvil.teacher.signal import is_failure
from autocode.anvil.teacher.verifier import VerifierProfile

# (prompt, sandbox, cfg) -> RunResult
Runner = Callable[[str, Path, GatewayConfig], RunResult]
# (sandbox, profile) -> Verdict
VerifyFn = Callable[[Path, VerifierProfile], Verdict]


@dataclass
class TeachTask:
    """A self-contained teachable task (greenfield or bugfix)."""

    task_id: str
    instruction: str
    files: dict[str, str] = field(default_factory=dict)  # relative path -> content
    profile: VerifierProfile = field(default_factory=lambda: _verifier.DEFAULT_PROFILES["generic"])
    language: str = "python"


@dataclass
class TeacherStudentResult:
    task_id: str
    student_trajectory: Trajectory
    student_verdict: Verdict
    teacher_trajectory: Trajectory | None
    teacher_verdict: Verdict | None
    packet: TeachingPacket
    delta: PlaybookDelta | None
    delta_appended: bool
    bundle_path: str | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "student_label": self.student_verdict.label,
            "teacher_label": self.teacher_verdict.label if self.teacher_verdict else None,
            "root_cause": self.packet.root_cause.to_dict()["class"],
            "playbook_delta_appended": self.delta_appended,
            "harness_fix": (self.packet.harness_fix.to_dict() if self.packet.harness_fix else None),
            "bundle_path": self.bundle_path,
        }


def _seed(sandbox: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = sandbox / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _default_verify(sandbox: Path, profile: VerifierProfile) -> Verdict:
    # The agent edited the sandbox in place; verify the working tree directly.
    return _verifier.verify(sandbox, profile=profile)


def teach(
    task: TeachTask,
    *,
    workdir: str | Path,
    cfg: GatewayConfig | None = None,
    playbook_store: PlaybookStore | None = None,
    llm: LLM | None = None,
    run_teacher: bool = True,
    student_runner: Runner | None = None,
    teacher_runner: Runner | None = None,
    verify_fn: VerifyFn | None = None,
    created: str = "",
    emit_harness_fix: bool = False,
    anvil_root: str | Path | None = None,
) -> TeacherStudentResult:
    """Run one teacher-student cycle and curate the playbook."""
    cfg = cfg or GatewayConfig.from_env()
    workdir = Path(workdir)
    verify = verify_fn or _default_verify
    srun = student_runner or (
        lambda p, sb, c: _runners.run_student(
            p, sb, c, task=Task(instruction=task.instruction, repo=str(sb), source="synthetic")
        )
    )
    trun = teacher_runner or (
        lambda p, sb, c: _runners.run_teacher(
            p, sb, c, task=Task(instruction=task.instruction, repo=str(sb), source="synthetic")
        )
    )

    # --- student -----------------------------------------------------------
    student_sb = _runners.prepare_sandbox(workdir / "student")
    _seed(student_sb, task.files)
    _runners.prepare_sandbox(student_sb)  # baseline-commit the seed files
    student_run = srun(task.instruction, student_sb, cfg)
    student_verdict = verify(student_sb, task.profile)
    student_tj = student_run.trajectory
    student_tj.outcome = student_verdict
    student_tj.role = "student"

    # --- teacher -----------------------------------------------------------
    teacher_tj: Trajectory | None = None
    teacher_verdict: Verdict | None = None
    if run_teacher:
        teacher_sb = _runners.prepare_sandbox(workdir / "teacher")
        _seed(teacher_sb, task.files)
        _runners.prepare_sandbox(teacher_sb)
        teacher_run = trun(task.instruction, teacher_sb, cfg)
        teacher_verdict = verify(teacher_sb, task.profile)
        teacher_tj = teacher_run.trajectory
        teacher_tj.outcome = teacher_verdict
        teacher_tj.role = "teacher"

    # --- reflect (contrast only when the teacher actually solved it) --------
    contrast = teacher_tj if (teacher_tj is not None and teacher_tj.outcome.is_success) else None
    reflection: Reflection = reflect(
        student_tj,
        student_verdict,
        teacher=contrast,
        llm=llm,
        teacher_model=cfg.teacher_model,
        language=task.language,
        created=created,
    )

    # --- curate (online path): append the reversible playbook delta ---------
    store = playbook_store or PlaybookStore()
    delta_appended = False
    if reflection.delta is not None and is_failure(student_verdict):
        store.append_delta(reflection.delta)
        delta_appended = True

    # --- offline path (optional): emit a prediction-contracted bundle -------
    bundle_path: str | None = None
    if emit_harness_fix and reflection.packet.harness_fix is not None:
        bundle_path = _emit_harness_fix_bundle(
            reflection.packet, task, cfg, anvil_root=anvil_root, created=created
        )

    return TeacherStudentResult(
        task_id=task.task_id,
        student_trajectory=student_tj,
        student_verdict=student_verdict,
        teacher_trajectory=teacher_tj,
        teacher_verdict=teacher_verdict,
        packet=reflection.packet,
        delta=reflection.delta,
        delta_appended=delta_appended,
        bundle_path=bundle_path,
    )


def _emit_harness_fix_bundle(
    packet: TeachingPacket,
    task: TeachTask,
    cfg: GatewayConfig,
    *,
    anvil_root: str | Path | None,
    created: str,
) -> str:
    """Write the teacher's harness_fix as a patch bundle (offline path).

    Reuses the copycat ``patch_bundles/pb_NNN/`` layout + ``bundle.json`` shape so
    it composes with :mod:`autocode.anvil.gate` / :mod:`autocode.anvil.promote`.
    The teacher proposes (status ``planned``, empty ``check_plan``); a human
    implements and the gate verifies — the loop never self-promotes.
    """
    from autocode.anvil import paths

    fix = packet.harness_fix
    assert fix is not None
    root = paths.anvil_root(anvil_root)
    bundle_id = paths.next_bundle_id(root)
    bundle_dir = paths.patch_bundles_dir(root) / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    contract = {
        "capability": fix.target,
        "kind": fix.kind,
        "inspired_by": {
            "target": "puku-cli",
            "channel": "self_distill",
            "trajectory": packet.trajectory_id,
            "root_cause": packet.root_cause.to_dict()["class"],
        },
        "claim": (
            f"Adding '{fix.target}' resolves the '{packet.root_cause.to_dict()['class']}' "
            f"failure class without regressing the edge-cost guards."
        ),
        # Edge-cost guards are mandatory (§0.3.5).
        "no_regression_on": ["layer_distribution.L4", "latency_p50", "tokens_per_task"],
        "check_plan": [],
        "sketch": fix.sketch,
    }
    (bundle_dir / "prediction_contract.json").write_text(
        json.dumps(contract, indent=2) + "\n", encoding="utf-8"
    )
    (bundle_dir / "decision.md").write_text(_decision_md(packet, task, bundle_id), encoding="utf-8")
    (bundle_dir / "teaching_packet.json").write_text(packet.to_json(), encoding="utf-8")

    metadata = {
        "bundle_id": bundle_id,
        "capability_id": fix.target,
        "manifest_entry": fix.target,
        "target": "puku-cli",
        "channel": "self_distill",
        "reuse_scope": "outcomes",
        "status": "proposed",
        "implementation_status": "planned",
        "check_plan": [],
        "created_by": f"anvil-teacher@{ANVIL_VERSION}",
        "trajectory_id": packet.trajectory_id,
        "root_cause": packet.root_cause.to_dict()["class"],
    }
    (bundle_dir / "bundle.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return str(bundle_dir)


def _decision_md(packet: TeachingPacket, task: TeachTask, bundle_id: str) -> str:
    rc = packet.root_cause
    fix = packet.harness_fix
    return (
        f"# decision: teacher harness-fix ({bundle_id})\n\n"
        f"- **Task:** {task.instruction}\n"
        f"- **Trajectory:** `{packet.trajectory_id}`\n"
        f"- **Verdict (oracle):** `{packet.verdict.label}`\n"
        f"- **Root cause:** `{rc.to_dict()['class']}` (evidence step {rc.evidence_step})\n"
        f"- **Channel:** self_distill (PLAN_05 Channel C)\n\n"
        f"## Why\n\n{rc.explanation}\n\n"
        f"## Proposed harness fix\n\n"
        f"- **target:** `{fix.target if fix else ''}`\n"
        f"- **kind:** `{fix.kind if fix else ''}`\n"
        f"- **sketch:** {fix.sketch if fix else ''}\n\n"
        f"## Gate / promote\n\n"
        f"This is a *proposal* (status: planned, no check plan). A human implements the "
        f"capability and adds the executable check plan; `autocode anvil gate {bundle_id}` "
        f"then verifies it and `autocode anvil promote {bundle_id}` records it in the audit "
        f"log only if the prediction is met with no edge-cost regression.\n"
    )


__all__ = ["TeachTask", "TeacherStudentResult", "teach"]
