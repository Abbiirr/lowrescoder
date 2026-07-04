"""The ``autocode anvil`` command surface — copycat mode's manual MVP (§6).

    autocode anvil copycat registry                 # list authorized targets
    autocode anvil copycat census <target>          # write census/<target>.yaml
    autocode anvil copycat gap-diff <target>         # diff vs AutoCode manifest
    autocode anvil copycat propose <target> <cap>    # draft a clean-room bundle
    autocode anvil gate <bundle_id>                  # run the bundle's checks
    autocode anvil promote <bundle_id>               # record the promotion

Every channel is registry-gated (the hard gate). The operator is the gate at
every step — manual-first by design (§6.1).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from autocode.anvil import paths
from autocode.anvil import targets as anvil_targets
from autocode.anvil.census import Census
from autocode.anvil.copycat import distill as channel_b_distill
from autocode.anvil.copycat import outcome as channel_b_outcome
from autocode.anvil.copycat.distill import DistillError
from autocode.anvil.copycat.outcome import OutcomeError, Task
from autocode.anvil.gapdiff import gap_diff
from autocode.anvil.gate import GateError, gate
from autocode.anvil.manifest import autocode_manifest
from autocode.anvil.promote import PromoteError, promote
from autocode.anvil.propose import ProposeError, propose
from autocode.anvil.registry import Registry, RegistryError, load_registry
from autocode.anvil.teacher import cost as edge_cost

console = Console()

anvil_app = typer.Typer(
    help="Anvil — AutoCode's offline harness-evolution engine (PLAN_04/PLAN_05).",
    no_args_is_help=True,
)
copycat_app = typer.Typer(
    help="Copycat mode (PLAN_05): capability acquisition via structural imitation.",
    no_args_is_help=True,
)
anvil_app.add_typer(copycat_app, name="copycat")

_CHANNEL = "structural"
_SCOPE = "structure_only"


def _enforce_or_exit(
    reg: Registry,
    target: str,
    *,
    channel: str = _CHANNEL,
    scope: str = _SCOPE,
) -> None:
    try:
        reg.assert_channel_allowed(target, channel)
        reg.assert_reuse_scope(target, scope)
    except RegistryError as exc:
        console.print(f"[red]Refused by registry:[/] {exc}")
        raise typer.Exit(2) from exc

_ROOT_OPT = typer.Option(
    None, "--anvil-root", help="Anvil data root (default: <repo>/anvil or AUTOCODE_ANVIL_ROOT)."
)


def _load_registry_or_exit(root: Path) -> Registry:
    reg_path = paths.registry_path(root)
    try:
        return load_registry(reg_path)
    except RegistryError as exc:
        console.print(f"[red]Registry error:[/] {exc}")
        console.print(f"[dim]Expected registry at {reg_path}[/]")
        raise typer.Exit(2) from exc


def _load_or_collect_census(root: Path, target: str) -> Census:
    path = paths.census_path(root, target)
    if path.is_file():
        return Census.read_yaml(path)
    return anvil_targets.collect_census(target)


@copycat_app.command("registry")
def registry_cmd(anvil_root: str | None = _ROOT_OPT) -> None:
    """List the authorized copycat targets."""
    root = paths.anvil_root(anvil_root)
    reg = _load_registry_or_exit(root)
    table = Table(title="Anvil copycat — authorized targets")
    table.add_column("id")
    table.add_column("channels")
    table.add_column("reuse_scope")
    table.add_column("source")
    for tid, target in sorted(reg.targets.items()):
        table.add_row(tid, ", ".join(target.channel), target.reuse_scope, target.source)
    console.print(table)


@copycat_app.command("census")
def census_cmd(
    target: str = typer.Argument(..., help="Target id from the registry (e.g. puku-cli)."),
    anvil_root: str | None = _ROOT_OPT,
) -> None:
    """Census a target's observable surface -> anvil/copycat/census/<target>.yaml."""
    root = paths.anvil_root(anvil_root)
    reg = _load_registry_or_exit(root)
    _enforce_or_exit(reg, target)
    if not anvil_targets.has_collector(target):
        console.print(f"[red]No census collector for target '{target}'.[/]")
        raise typer.Exit(2)

    census = anvil_targets.collect_census(target)
    out = census.write_yaml(paths.census_path(root, target))
    console.print(
        f"[green]Censused[/] {target} "
        f"(v{census.target_version or '?'}) via {census.source}: "
        f"[bold]{len(census.capabilities)}[/] capabilities -> {out}"
    )


@copycat_app.command("gap-diff")
def gap_diff_cmd(
    target: str = typer.Argument(..., help="Target id from the registry."),
    anvil_root: str | None = _ROOT_OPT,
    json_output: bool = typer.Option(False, "--json", help="Emit the gap report as JSON."),
) -> None:
    """Diff a target census against AutoCode's manifest; print the gap list."""
    root = paths.anvil_root(anvil_root)
    reg = _load_registry_or_exit(root)
    _enforce_or_exit(reg, target)

    census = _load_or_collect_census(root, target)
    report = gap_diff(census, autocode_manifest())

    if json_output:
        console.print_json(json.dumps(report.to_dict()))
        return

    console.print(
        f"[bold]{target}[/] vs AutoCode: "
        f"{len(report.present)} present, [yellow]{len(report.gaps)} gaps[/] "
        f"({len(report.suitable_gaps())} clean-room-suitable), "
        f"{len(report.ignored)} ignored."
    )
    table = Table(title=f"Gaps — capabilities AutoCode lacks ({target})")
    table.add_column("capability")
    table.add_column("surface")
    table.add_column("category")
    table.add_column("clean-room?")
    for g in report.gaps:
        table.add_row(
            g.capability.id,
            " ".join(g.capability.surface),
            g.category,
            "[green]yes[/]" if g.cleanroom_suitable else "no",
        )
    console.print(table)
    if report.suitable_gaps():
        console.print(
            "[dim]Propose one with: "
            f"autocode anvil copycat propose {target} <capability-id>[/]"
        )


@copycat_app.command("propose")
def propose_cmd(
    target: str = typer.Argument(..., help="Target id from the registry."),
    capability: str = typer.Argument(..., help="Capability id (e.g. flag:permission-mode)."),
    anvil_root: str | None = _ROOT_OPT,
) -> None:
    """Draft a clean-room patch bundle for a capability."""
    root = paths.anvil_root(anvil_root)
    reg = _load_registry_or_exit(root)
    _enforce_or_exit(reg, target)

    census = _load_or_collect_census(root, target)
    report = gap_diff(census, autocode_manifest())
    try:
        bundle = propose(report=report, census=census, capability_id=capability, root=root)
    except ProposeError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(2) from exc

    console.print(f"[green]Drafted[/] {bundle.bundle_id} -> {bundle.path}")
    console.print(f"  capability : {capability} ({'open gap' if bundle.is_open_gap else 'landed'})")
    console.print(f"  manifest   : {bundle.spec.manifest_entry} (tier {bundle.spec.tier})")
    console.print(
        f"[dim]Next: autocode anvil gate {bundle.bundle_id} "
        f"&& autocode anvil promote {bundle.bundle_id}[/]"
    )


@copycat_app.command("outcome")
def outcome_cmd(
    target: str = typer.Argument(..., help="Target id (must permit the 'outcome' channel)."),
    task_id: str = typer.Argument(..., help="Task id; becomes the outcome file name."),
    prompt: str = typer.Option("", "--prompt", help="Task prompt."),
    check_plan: list[str] = typer.Option(
        [],
        "--check",
        help="Test path in the check plan (repeatable). The verifier runs `uv run pytest <these>`.",
    ),
    anvil_root: str | None = _ROOT_OPT,
) -> None:
    """Channel B — drive target on task, capture the verified diff to the corpus.

    Drives an authorized target, captures the observable final artifact (the
    diff), and persists it under ``anvil/copycat/outcomes/corpus@v<N>/<task>.json``
    iff the verifier labels it ``verified``. Unverified diffs are dropped. The
    per-target rate limit (default 50/day) is enforced before the target is
    driven.
    """
    root = paths.anvil_root(anvil_root)
    reg = _load_registry_or_exit(root)
    _enforce_or_exit(reg, target, channel=channel_b_outcome.CHANNEL, scope=channel_b_outcome.SCOPE)

    task = Task(task_id=task_id, prompt=prompt, check_plan=tuple(check_plan))
    try:
        oc = channel_b_outcome.capture(target, task, root=root, registry=reg)
    except OutcomeError as exc:
        console.print(f"[red]Channel B capture refused:[/] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        f"[green]Verified[/] outcome for task '{oc.task_id}' "
        f"(target={oc.target}, corpus@v{oc.corpus_version}): {oc.sha256[:12]}"
    )
    console.print(
        f"  file : {channel_b_outcome.corpus_dir(root, oc.corpus_version) / (task_id + '.json')}"
    )
    console.print(f"  label: {oc.verification.label} ({oc.verification.summary})")


@copycat_app.command("distill")
def distill_cmd(
    target: str = typer.Argument(..., help="Target id (must grant reuse_scope: weights)."),
    anvil_root: str | None = _ROOT_OPT,
) -> None:
    """Channel B — render the latest verified-outcome corpus as a dataset.jsonl.

    Refused unless the registry grants ``reuse_scope: weights`` for ``target``
    *and* a recorded per-provider ToS check is present. The dataset's SHA-256 is
    deterministic across runs with identical corpus inputs (the PLAN_05 closing
    gate checks this).
    """
    root = paths.anvil_root(anvil_root)
    reg = _load_registry_or_exit(root)
    # The distill branch checks both channel + weights + ToS itself; we do not
    # call _enforce_or_exit here because the scope is "weights", not "outcomes".

    try:
        dataset = channel_b_distill.distill(target, root=root, registry=reg)
    except DistillError as exc:
        console.print(f"[red]Channel B distill refused:[/] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        f"[green]Distilled[/] {dataset.line_count} verified outcomes for "
        f"'{dataset.target}' (corpus@v{dataset.corpus_version}) -> {dataset.path}"
    )
    console.print(f"  dataset sha256: {dataset.sha256}")


def _bundle_dir(root: Path, bundle_id: str) -> Path:
    return paths.patch_bundles_dir(root) / bundle_id


@anvil_app.command("gate")
def gate_cmd(
    bundle_id: str = typer.Argument(..., help="Patch bundle id (e.g. pb_001)."),
    baseline_trajectories: str | None = typer.Option(
        None,
        "--baseline-trajectories",
        help="JSONL trajectory store for the pre-change baseline. Pass with "
        "--candidate-trajectories to measure + enforce the edge-cost guards.",
    ),
    candidate_trajectories: str | None = typer.Option(
        None,
        "--candidate-trajectories",
        help="JSONL trajectory store for the candidate (post-change) run.",
    ),
    anvil_root: str | None = _ROOT_OPT,
) -> None:
    """Apply a bundle's check plan and score its prediction.

    When both ``--baseline-trajectories`` and ``--candidate-trajectories`` are
    given, the three mandatory edge-cost guards (L4 share, latency_p50,
    tokens_per_task) are measured and folded into ``no_regression`` — a candidate
    whose tests pass but whose edge cost regresses fails the gate and cannot be
    promoted. Without them the gate runs tests only and records
    ``edge_cost_measured: False`` (honest, not a free pass).
    """
    root = paths.anvil_root(anvil_root)

    verdict = None
    if baseline_trajectories or candidate_trajectories:
        if not (baseline_trajectories and candidate_trajectories):
            console.print(
                "[red]Edge-cost measurement needs BOTH "
                "--baseline-trajectories and --candidate-trajectories.[/]"
            )
            raise typer.Exit(2)
        try:
            base = edge_cost.measure(edge_cost.trajectories_from_jsonl(baseline_trajectories))
            cand = edge_cost.measure(edge_cost.trajectories_from_jsonl(candidate_trajectories))
        except edge_cost.EdgeCostError as exc:
            console.print(f"[red]Edge-cost measurement failed:[/] {exc}")
            raise typer.Exit(2) from exc
        verdict = edge_cost.compare(base, cand)

    try:
        result = gate(_bundle_dir(root, bundle_id), edge_cost_verdict=verdict)
    except GateError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(2) from exc
    status = "[green]PASS[/]" if result.passed else "[red]FAIL[/]"
    console.print(f"{status} {result.bundle_id}: {result.summary}")
    console.print(f"  command: {result.command}")
    console.print(f"  report : {result.eval_report_path}")
    if verdict is None:
        console.print(
            "  edge-cost: [yellow]not measured[/] "
            "(pass --baseline-trajectories + --candidate-trajectories to enforce)"
        )
    elif verdict.overall_no_regression:
        console.print("  edge-cost: [green]no regression[/]")
    else:
        regressed = [g.guard for g in verdict.guards if not g.no_regression]
        console.print(f"  edge-cost: [red]REGRESSION[/] on {', '.join(regressed)}")
    if not result.passed:
        raise typer.Exit(1)


@anvil_app.command("promote")
def promote_cmd(
    bundle_id: str = typer.Argument(..., help="Patch bundle id (e.g. pb_001)."),
    anvil_root: str | None = _ROOT_OPT,
) -> None:
    """Record a gated bundle's promotion in the immutable audit log."""
    root = paths.anvil_root(anvil_root)
    timestamp = datetime.now(UTC).isoformat()
    try:
        entry = promote(_bundle_dir(root, bundle_id), root=root, timestamp=timestamp)
    except PromoteError as exc:
        console.print(f"[red]Refused:[/] {exc}")
        raise typer.Exit(1) from exc
    console.print(
        f"[green]Promoted[/] {entry['bundle_id']}: {entry['manifest_entry']} "
        f"(inspired by {entry['target']}::{entry['capability_id']}, "
        f"reuse_scope={entry['reuse_scope']})"
    )
    console.print(f"  audit  : {paths.audit_log_path(root)}")


def build_anvil_app() -> typer.Typer:
    return anvil_app
