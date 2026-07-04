"""Draft a clean-room capability proposal as a patch bundle (PLAN_05 §2.3, §6).

``propose`` turns a gap (or an already-landed capability) into a reviewable
patch bundle under ``anvil/patch_bundles/pb_NNN/``:

  - ``decision.md``           — the human-readable clean-room rationale.
  - ``proposal.md``           — the capability spec (what AutoCode should build).
  - ``prediction_contract.yaml`` — the claim + mandatory edge-cost guards.
  - ``manifest_delta.yaml``   — the manifest entry the capability adds.
  - ``bundle.json``           — machine metadata, incl. the gate ``check_plan``.

The hard rule (PLAN_05 §2.5): structural imitation produces *new AutoCode
components evaluated on the oracle, never vendored third-party code*. The bundle
records what was studied and inspired; the diff itself is clean-room.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from autocode.anvil import paths
from autocode.anvil.census import Capability, Census
from autocode.anvil.gapdiff import GapReport


class ProposeError(Exception):
    """propose was called for a capability with no curated clean-room spec."""


@dataclass(frozen=True)
class ProposalSpec:
    """A curated clean-room proposal for one puku-cli capability."""

    capability_id: str
    title: str
    tier: int  # 1=tool, 2=middleware, 3=playbook (PLAN_05 escalation ladder)
    manifest_entry: str
    summary: str
    implementation_notes: str
    check_plan: tuple[str, ...]
    status: str  # "implemented" | "planned"


# Curated proposals. The two already landed in this change have a real check
# plan (their tests are the executable oracle the gate runs); the rest are
# planned next-cycle targets with an empty check plan until implemented.
CLEANROOM_PROPOSALS: dict[str, ProposalSpec] = {
    "flag:permission-mode": ProposalSpec(
        capability_id="flag:permission-mode",
        title="Headless permission-mode enum on `autocode exec`",
        tier=1,
        manifest_entry="cli.exec.permission_mode",
        summary=(
            "Expose a session permission *enum* "
            "(acceptEdits|bypassPermissions|default|dontAsk|plan|auto) on headless "
            "`exec`, generalizing the boolean `--auto-approve`."
        ),
        implementation_notes=(
            "Clean-room: map the puku-cli mode names onto AutoCode's existing "
            "ApprovalMode in autocode.agent.permission_mode; thread the resolution "
            "through HeadlessRunner. No puku-cli source is read or copied — only "
            "its public `--help` surface."
        ),
        check_plan=(
            "tests/unit/test_permission_mode.py",
            "tests/unit/test_exec_copycat_features.py",
        ),
        status="implemented",
    ),
    "flag:max-budget-usd": ProposalSpec(
        capability_id="flag:max-budget-usd",
        title="Per-run USD spend cap on `autocode exec`",
        tier=1,
        manifest_entry="cli.exec.max_budget_usd",
        summary=(
            "Expose a per-invocation USD cost cap on headless `exec` that overrides "
            "agent.cost_limit_usd — a CLI surface for AutoCode's existing cost-limit "
            "engine."
        ),
        implementation_notes=(
            "Clean-room: HeadlessRunner gains a max_budget_usd override applied to "
            "the AgentLoop's existing cost-limit machinery. Enforcement is unchanged; "
            "only the CLI surface is new."
        ),
        check_plan=("tests/unit/test_exec_copycat_features.py",),
        status="implemented",
    ),
    "flag:output-format": ProposalSpec(
        capability_id="flag:output-format",
        title="Single-result + stream output formats on `autocode exec`",
        tier=1,
        manifest_entry="cli.exec.output_format",
        summary=(
            "text | json | stream-json output for headless `exec` (puku-cli "
            "`--output-format`). 'json' folds the NDJSON event stream into one "
            "consolidated result object; 'stream-json' is the existing --json path."
        ),
        implementation_notes=(
            "Clean-room: a pure collapse_ndjson_to_result helper folds the existing "
            "event stream into a single result object; the --json / stream-json "
            "streaming path is unchanged (additive)."
        ),
        check_plan=(
            "tests/unit/test_output_format.py",
            "tests/unit/test_cli.py",
        ),
        status="implemented",
    ),
    "flag:cd": ProposalSpec(
        capability_id="flag:cd",
        title="Run-in-directory (`--cd`) on `autocode exec`",
        tier=1,
        manifest_entry="cli.exec.cd",
        summary=(
            "Run the agent in a different working directory (codex `-C/--cd <DIR>`). "
            "The first feature copied clean-room from the *codex* target."
        ),
        implementation_notes=(
            "Clean-room: `exec --cd` validates the directory and passes it as "
            "HeadlessRunner's existing project_root. Additive; default = cwd."
        ),
        check_plan=(
            "tests/unit/test_exec_copycat_features.py",
            "tests/unit/test_cli.py",
        ),
        status="implemented",
    ),
    "flag:add-dir": ProposalSpec(
        capability_id="flag:add-dir",
        title="Additional tool-access directories on `autocode exec`",
        tier=1,
        manifest_entry="cli.exec.add_dir",
        summary=(
            "Allow tools to access directories beyond the project root, via an "
            "explicit allow-list (puku-cli `--add-dir`)."
        ),
        implementation_notes=(
            "Clean-room: validate_path gains an opt-in extra_roots allow-list "
            "(empty by default = unchanged sandbox), threaded through the file "
            "tools, create_default_registry, HeadlessRunner and `exec --add-dir`."
        ),
        check_plan=(
            "tests/unit/test_add_dir.py",
            "tests/unit/test_file_tools.py",
            "tests/unit/test_exec_copycat_features.py",
        ),
        status="implemented",
    ),
    "flag:system-prompt": ProposalSpec(
        capability_id="flag:system-prompt",
        title="System-prompt override on `autocode exec`",
        tier=2,
        manifest_entry="cli.exec.system_prompt",
        summary="Override the session system prompt (puku-cli `--system-prompt`).",
        implementation_notes=(
            "Clean-room: a pure finalize_system_prompt helper replaces the stable "
            "persona region while preserving AutoCode's dynamic runtime suffix; "
            "threaded through AgentLoop -> create_orchestrator -> HeadlessRunner."
        ),
        check_plan=(
            "tests/unit/test_system_prompt_override.py",
            "tests/unit/test_exec_copycat_features.py",
        ),
        status="implemented",
    ),
    "flag:append-system-prompt": ProposalSpec(
        capability_id="flag:append-system-prompt",
        title="Append-system-prompt on `autocode exec`",
        tier=2,
        manifest_entry="cli.exec.append_system_prompt",
        summary="Append text to the default system prompt (puku-cli `--append-system-prompt`).",
        implementation_notes=(
            "Clean-room: the same finalize_system_prompt helper concatenates extra "
            "instructions after the assembled prompt; no puku-cli code copied."
        ),
        check_plan=(
            "tests/unit/test_system_prompt_override.py",
            "tests/unit/test_exec_copycat_features.py",
        ),
        status="implemented",
    ),
}


@dataclass(frozen=True)
class Bundle:
    """The in-memory view of a written patch bundle."""

    bundle_id: str
    path: Path
    spec: ProposalSpec
    is_open_gap: bool

    def metadata(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(
            (self.path / "bundle.json").read_text(encoding="utf-8")
        )
        return data


def _prediction_contract(spec: ProposalSpec, target: str) -> dict[str, Any]:
    return {
        "capability": spec.manifest_entry,
        "tier": spec.tier,
        "inspired_by": {
            "target": target,
            "channel": "structural",
            "capability": spec.capability_id,
        },
        "claim": (
            f"Adds capability '{spec.manifest_entry}' with all check-plan tests "
            f"passing and no regression on existing exec behavior."
        ),
        # Edge-cost guards are mandatory (PLAN_05 §0.3.6).
        "no_regression_on": ["layer_distribution.L4", "latency_p50", "tokens_per_task"],
        "check_plan": list(spec.check_plan),
    }


def available_capabilities() -> list[str]:
    return sorted(CLEANROOM_PROPOSALS)


def propose(
    *,
    report: GapReport,
    census: Census,
    capability_id: str,
    root: Path | None = None,
    bundle_id: str | None = None,
    created_by: str = "anvil-copycat",
) -> Bundle:
    """Draft a clean-room patch bundle for ``capability_id``.

    The capability must have a curated clean-room spec. Whether it is currently
    an open gap or already landed is recorded (the gate still verifies it).
    """
    spec = CLEANROOM_PROPOSALS.get(capability_id)
    if spec is None:
        known = ", ".join(available_capabilities())
        raise ProposeError(
            f"no clean-room proposal for '{capability_id}' "
            f"(curated proposals: {known})"
        )

    anvil = paths.anvil_root(root)
    bundle_id = bundle_id or paths.next_bundle_id(anvil)
    bundle_path = paths.patch_bundles_dir(anvil) / bundle_id
    bundle_path.mkdir(parents=True, exist_ok=True)

    is_open_gap = capability_id in report.gap_ids()
    cap = _find_capability(census, capability_id)
    surface = " ".join(cap.surface) if cap else capability_id

    contract = _prediction_contract(spec, census.target)
    (bundle_path / "prediction_contract.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    (bundle_path / "manifest_delta.yaml").write_text(
        yaml.safe_dump(
            {"add": [{"id": spec.manifest_entry, "tier": spec.tier, "surface": surface}]},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (bundle_path / "proposal.md").write_text(_proposal_md(spec, census, surface), encoding="utf-8")
    (bundle_path / "decision.md").write_text(
        _decision_md(spec, census, surface, is_open_gap), encoding="utf-8"
    )

    metadata = {
        "bundle_id": bundle_id,
        "capability_id": capability_id,
        "manifest_entry": spec.manifest_entry,
        "tier": spec.tier,
        "target": census.target,
        "channel": "structural",
        "reuse_scope": "structure_only",
        "status": "proposed",
        "is_open_gap": is_open_gap,
        "implementation_status": spec.status,
        "check_plan": list(spec.check_plan),
        "created_by": created_by,
    }
    (bundle_path / "bundle.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )

    return Bundle(bundle_id=bundle_id, path=bundle_path, spec=spec, is_open_gap=is_open_gap)


def _find_capability(census: Census, capability_id: str) -> Capability | None:
    return next((c for c in census.capabilities if c.id == capability_id), None)


def _proposal_md(spec: ProposalSpec, census: Census, surface: str) -> str:
    return (
        f"# Clean-room proposal: {spec.title}\n\n"
        f"**Target:** `{census.target}` (channel: structural; reuse_scope: structure_only)\n\n"
        f"**Inspired-by capability:** `{spec.capability_id}` — `{surface}`\n\n"
        f"**Manifest entry:** `{spec.manifest_entry}` (tier {spec.tier})\n\n"
        f"## Capability\n\n{spec.summary}\n\n"
        f"## Implementation (clean-room)\n\n{spec.implementation_notes}\n\n"
        f"## Hard rule\n\nStructural imitation produces a *new AutoCode component "
        f"evaluated on the oracle*, never vendored {census.target} code.\n"
    )


def _decision_md(spec: ProposalSpec, census: Census, surface: str, is_open_gap: bool) -> str:
    state = "open gap" if is_open_gap else "already landed; gate re-verifies"
    return (
        f"# decision: {spec.title}\n\n"
        f"- **Bundle status at draft:** proposed ({state})\n"
        f"- **Target studied:** `{census.target}` — observable surface only "
        f"(`{census.source}`)\n"
        f"- **Capability inspired-by:** `{spec.capability_id}` (`{surface}`)\n"
        f"- **Implementation status:** {spec.status}\n"
        f"- **Reuse scope:** `structure_only` — no {census.target} source copied.\n\n"
        f"## Why this is clean-room\n\n{spec.implementation_notes}\n\n"
        f"## Gate / promote\n\n"
        f"`autocode anvil gate {{bundle}}` runs the check plan "
        f"({', '.join(spec.check_plan) or 'none — planned'}) as the executable "
        f"oracle. `autocode anvil promote {{bundle}}` records the promotion in the "
        f"immutable audit log only if the prediction was met with no edge-cost "
        f"regression.\n"
    )
