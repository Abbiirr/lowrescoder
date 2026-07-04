"""``autocode anvil teacher`` — the teacher-mode command surface (PLAN_04 §6).

    autocode anvil teacher run "<instruction>" [--task-file t.json]  # one cycle
    autocode anvil teacher sense [--top N]                           # G5 distiller
    autocode anvil teacher playbook show <lang>                      # ACE playbook
    autocode anvil teacher playbook prune <lang>                     # -> Master Rules
    autocode anvil teacher playbook rules <lang>                     # runtime rules
    autocode anvil teacher verify <repo> --language python           # executable oracle

Manual-first by design (§6.1): the operator reads each teaching packet and the
appended playbook delta; nothing self-promotes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

if TYPE_CHECKING:
    from autocode.anvil.teacher.loop import TeachTask
    from autocode.anvil.teacher.playbook import MasterRule

console = Console()

teacher_app = typer.Typer(
    help="Teacher mode (PLAN_04): root-cause analysis + ACE playbook from puku-cli vs autocode.",
    no_args_is_help=True,
)
playbook_app = typer.Typer(help="Inspect / maintain the ACE playbook.", no_args_is_help=True)
teacher_app.add_typer(playbook_app, name="playbook")


def _load_task(instruction: str, task_file: str | None, language: str) -> TeachTask:
    from autocode.anvil.teacher import verifier
    from autocode.anvil.teacher.loop import TeachTask

    if task_file:
        data = json.loads(Path(task_file).read_text(encoding="utf-8"))
        prof = data.get("profile", {}) or {}
        profile = verifier.VerifierProfile(
            language=data.get("language", language),
            build_cmd=tuple(prof.get("build_cmd", ()) or ()),
            test_cmd=tuple(prof.get("test_cmd", ()) or ()),
            lint_cmd=tuple(prof.get("lint_cmd", ()) or ()),
            types_cmd=tuple(prof.get("types_cmd", ()) or ()),
            timeout_s=int(prof.get("timeout_s", 600)),
        )
        return TeachTask(
            task_id=data.get("task_id", "task"),
            instruction=data.get("instruction", instruction),
            files=dict(data.get("files", {}) or {}),
            profile=profile,
            language=data.get("language", language),
        )
    return TeachTask(
        task_id="adhoc",
        instruction=instruction,
        profile=verifier.DEFAULT_PROFILES.get(language, verifier.DEFAULT_PROFILES["generic"]),
        language=language,
    )


@teacher_app.command("run")
def run_cmd(
    instruction: str = typer.Argument("", help="The task instruction (or use --task-file)."),
    task_file: str | None = typer.Option(None, "--task-file", help="JSON TeachTask spec."),
    workdir: str | None = typer.Option(
        None, "--workdir", help="Sandbox dir (default under anvil/)."
    ),
    student_model: str | None = typer.Option(
        None, "--student-model", help="Gateway alias for autocode."
    ),
    teacher_model: str | None = typer.Option(
        None, "--teacher-model", help="Gateway alias for puku-cli."
    ),
    no_teacher: bool = typer.Option(False, "--no-teacher", help="Skip the puku-cli teacher run."),
    reflect: bool = typer.Option(
        True, "--reflect/--no-reflect", help="LLM-enrich via the gateway."
    ),
    emit_harness_fix: bool = typer.Option(
        False, "--emit-harness-fix", help="Also draft a patch bundle."
    ),
    playbook_dir: str | None = typer.Option(
        None, "--playbook-dir", help="Playbook root (default .autocode/playbook)."
    ),
    language: str = typer.Option("python", "--language", help="Language for playbook scoping."),
    json_output: bool = typer.Option(False, "--json", help="Print the result summary as JSON."),
) -> None:
    """Run one teacher-student cycle: student + teacher + verify + reflect + curate."""
    from autocode.anvil import paths
    from autocode.anvil.teacher.gateway import make_gateway_llm
    from autocode.anvil.teacher.loop import teach
    from autocode.anvil.teacher.playbook import PlaybookStore, default_playbook_dir
    from autocode.anvil.teacher.runners import GatewayConfig

    if not instruction and not task_file:
        console.print("[red]Provide an instruction argument or --task-file.[/]")
        raise typer.Exit(2)

    task = _load_task(instruction, task_file, language)
    cfg = GatewayConfig.from_env()
    if student_model:
        cfg.student_model = student_model
    if teacher_model:
        cfg.teacher_model = teacher_model

    wd = Path(workdir) if workdir else (paths.anvil_root() / "teacher_runs" / task.task_id)
    store = PlaybookStore(Path(playbook_dir) if playbook_dir else default_playbook_dir())
    llm = make_gateway_llm(cfg) if reflect else None

    console.print(
        f"[bold]anvil teacher[/] task={task.task_id} student={cfg.student_model} "
        f"teacher={'(skip)' if no_teacher else cfg.teacher_model} gateway={cfg.api_base}"
    )
    try:
        result = teach(
            task,
            workdir=wd,
            cfg=cfg,
            playbook_store=store,
            llm=llm,
            run_teacher=not no_teacher,
            emit_harness_fix=emit_harness_fix,
            created=datetime.now(UTC).isoformat(),
        )
    except Exception as exc:  # noqa: BLE001 - surface a clean operator error
        console.print(f"[red]teacher run failed:[/] {exc}")
        raise typer.Exit(1) from exc

    packet_path = wd / "teaching_packet.json"
    wd.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(result.packet.to_json(), encoding="utf-8")

    if json_output:
        console.print_json(json.dumps(result.summary()))
    else:
        s = result.summary()
        console.print(f"  student verdict : [bold]{s['student_label']}[/]")
        console.print(f"  teacher verdict : {s['teacher_label']}")
        console.print(f"  root cause      : [yellow]{s['root_cause']}[/]")
        console.print(
            f"  playbook delta  : {'appended' if s['playbook_delta_appended'] else 'none'}"
        )
        if s["harness_fix"]:
            console.print(
                f"  harness fix     : {s['harness_fix']['target']} ({s['harness_fix']['kind']})"
            )
        if s["bundle_path"]:
            console.print(f"  patch bundle    : {s['bundle_path']}")
        console.print(f"  teaching packet : {packet_path}")
    if result.delta_appended:
        console.print(f"[dim]Review: autocode anvil teacher playbook show {task.language}[/]")


@teacher_app.command("sense")
def sense_cmd(
    packet_dir: str = typer.Option(
        "",
        "--packet-dir",
        help="Directory of teaching_packet.json files (default: anvil/teacher_runs/<task>/**).",
    ),
    language: str = typer.Option(
        "python", "--language", help="Filter to one language (default: all)."
    ),
    top: int = typer.Option(5, "--top", help="Show only the top-N clusters."),
    json_output: bool = typer.Option(False, "--json", help="Emit the distilled corpus as JSON."),
    write_corpus: bool = typer.Option(
        False,
        "--write",
        help="Persist the corpus under <anvil>/teacher/distilled/ as a side effect.",
    ),
    anvil_root: str | None = typer.Option(
        None, "--anvil-root", help="Anvil data root (default <repo>/anvil)."
    ),
) -> None:
    """G5 distiller: cluster recorded teaching packets into a ranked evidence corpus.

    Reads every ``teaching_packet.json`` under ``--packet-dir`` (or, by default,
    under ``<anvil>/teacher_runs/**``), clusters failed trajectories by
    ``(language, root_cause_class)``, ranks them by the taxonomy's
    ``frequency × severity × (1 + is_tool_missing_capability × 2)`` rule, and
    prints the top-N. With ``--write`` the per-language per-cluster JSON files
    are persisted under ``<anvil>/teacher/distilled/``.
    """
    from autocode.anvil import paths as anvil_paths
    from autocode.anvil.teacher import distill as g5_distill
    from autocode.anvil.teacher.schemas import (
        RootCause,
        Task,
        TeachingPacket,
        Trajectory,
    )

    root = anvil_paths.anvil_root(anvil_root)
    search_root = Path(packet_dir) if packet_dir else (root / "teacher_runs")
    packets: list[tuple[Trajectory, RootCause, str]] = []
    if search_root.is_dir():
        for path in sorted(search_root.rglob("teaching_packet.json")):
            try:
                pkt = TeachingPacket.from_json(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            # Re-read the matching trajectory if it sits next to the packet.
            tj_path = path.parent / "trajectory.json"
            if tj_path.is_file():
                try:
                    tj = Trajectory.from_dict(json.loads(tj_path.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    tj = Trajectory(
                        trajectory_id=pkt.trajectory_id,
                        task=Task(instruction=""),
                        outcome=pkt.verdict,
                    )
            else:
                tj = Trajectory(
                    trajectory_id=pkt.trajectory_id,
                    task=Task(instruction=""),
                    outcome=pkt.verdict,
                )
            # The packet itself does not carry a language; the surrounding run
            # directory usually does (a sibling <lang>.md delta). Default to the
            # CLI flag so the operator can scope the cluster view.
            packets.append((tj, pkt.root_cause, language))

    if not packets:
        console.print(
            f"[yellow]No teaching packets found under {search_root}.[/]\n"
            f"Run [bold]autocode anvil teacher run[/] first."
        )
        raise typer.Exit(0)

    try:
        corpus = g5_distill.distill(
            g5_distill.attributed_from_packets(packets),
            generated_at=datetime.now(UTC).isoformat(),
            source=str(search_root),
        )
    except g5_distill.DistillError as exc:
        console.print(f"[red]distill refused:[/] {exc}")
        raise typer.Exit(1) from exc

    if write_corpus:
        index = g5_distill.write_corpus(corpus, root=root)
        console.print(f"[dim]wrote {index}[/]")

    if language:
        clusters = corpus.by_language(language) or corpus.clusters
    else:
        clusters = corpus.clusters
    top_clusters = tuple(sorted(clusters, key=lambda c: c.layer2.rank, reverse=True))[:top]

    if json_output:
        console.print_json(
            json.dumps({"clusters": [c.to_dict() for c in top_clusters]})
        )
        return

    table_header = (
        f"[bold]Distilled[/] {corpus.trajectory_count} trajectories "
        f"into {len(corpus.clusters)} cluster(s); top {len(top_clusters)}:"
    )
    console.print(table_header)
    for c in top_clusters:
        console.print(
            f"  [{c.layer2.rank:>7.2f}] {c.language}/{c.root_cause_class} "
            f"(freq={c.layer2.frequency}, sev={c.layer2.severity:.2f}, "
            f"L4={c.layer2.layer_distribution_L4:.2f}, "
            f"tier={c.layer3.fix_tier}, kind={c.layer3.component_kind})"
        )
    if top_clusters:
        console.print(
            "[dim]Propose a fix with: autocode anvil teacher run --emit-harness-fix ...[/]"
        )


@playbook_app.command("show")
def playbook_show(
    language: str = typer.Argument("python"),
    playbook_dir: str | None = typer.Option(None, "--playbook-dir"),
) -> None:
    """Print the rendered per-language playbook (Master Rules + deltas)."""
    from autocode.anvil.teacher.playbook import PlaybookStore, default_playbook_dir

    store = PlaybookStore(Path(playbook_dir) if playbook_dir else default_playbook_dir())
    md = store.md_path(language)
    if not md.is_file():
        console.print(f"[yellow]No playbook for '{language}' yet at {md.parent}[/]")
        raise typer.Exit(0)
    console.print(md.read_text(encoding="utf-8"))


@playbook_app.command("rules")
def playbook_rules(
    language: str = typer.Argument("python"),
    playbook_dir: str | None = typer.Option(None, "--playbook-dir"),
) -> None:
    """Print just the rules the runtime would load for ``language``."""
    from autocode.anvil.teacher.playbook import PlaybookStore, default_playbook_dir

    store = PlaybookStore(Path(playbook_dir) if playbook_dir else default_playbook_dir())
    rules = store.load_rules(language)
    if not rules:
        console.print(f"[yellow]No rules for '{language}'.[/]")
        return
    for r in rules:
        console.print(f"- {r}")


def _coverage_eval_gate(
    rules_before: list[MasterRule], rules_after: list[MasterRule]
) -> bool:
    """A deterministic, offline pass@1 proxy for the Pruner merge (06 §6.3).

    A merge regresses pass@1 if it *erases coverage of a failure class* the
    playbook previously addressed: the runtime would lose the rule that handled
    that class. So the gate refuses any merge whose Master Rules drop a
    root-cause class present before. (It never blocks the first prune, which has
    no prior rules to regress.)
    """
    before_classes = {r.root_cause_class for r in rules_before if r.rule}
    after_classes = {r.root_cause_class for r in rules_after if r.rule}
    return before_classes <= after_classes


@playbook_app.command("prune")
def playbook_prune(
    language: str = typer.Argument("python"),
    playbook_dir: str | None = typer.Option(None, "--playbook-dir"),
    eval_gate: bool = typer.Option(
        True,
        "--eval-gate/--no-eval-gate",
        help="Prediction-gate the merge: refuse if pass@1 coverage regresses "
        "(06 §6.3). Use --no-eval-gate to force an unguarded rewrite.",
    ),
) -> None:
    """Merge overlapping deltas into Master Rules (the ACE Pruner).

    The merge is a destructive rewrite of the durable-memory plane, so by default
    it is prediction-gated: a merge that drops coverage of a previously-handled
    failure class is refused (06 §6.3, "does pass@1 hold after pruning?").
    """
    from autocode.anvil.teacher.playbook import (
        PlaybookStore,
        PruneRegressionError,
        default_playbook_dir,
    )

    store = PlaybookStore(Path(playbook_dir) if playbook_dir else default_playbook_dir())
    gate = _coverage_eval_gate if eval_gate else None
    try:
        result = store.prune(language, eval_gate=gate)
    except PruneRegressionError as exc:
        console.print(f"[red]Refused:[/] {exc}")
        raise typer.Exit(1) from exc
    console.print(
        f"[green]Pruned[/] {language}: {result.deltas_in} deltas -> {result.rules_out} Master Rules"
    )


@teacher_app.command("verify")
def verify_cmd(
    repo: str = typer.Argument(..., help="Repo/sandbox dir to verify."),
    language: str = typer.Option("python", "--language"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Run the deterministic outcome oracle on a repo's working tree."""
    from autocode.anvil.teacher import verifier

    profile = verifier.DEFAULT_PROFILES.get(language, verifier.DEFAULT_PROFILES["generic"])
    verdict = verifier.verify(repo, profile=profile)
    if json_output:
        console.print_json(json.dumps(verdict.to_dict()))
    else:
        console.print(f"label=[bold]{verdict.label}[/] oracle_strength={verdict.oracle_strength}")
        console.print(
            f"  diff_applies={verdict.diff_applies} build={verdict.build_passed} "
            f"tests(p={verdict.tests.passed},f={verdict.tests.failed},r={verdict.tests.regressed}) "
            f"lint={verdict.lint_clean} types={verdict.types_clean}"
        )


def build_teacher_app() -> typer.Typer:
    return teacher_app


__all__ = ["teacher_app", "build_teacher_app"]
