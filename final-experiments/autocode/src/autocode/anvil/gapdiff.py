"""Diff a target census against AutoCode's manifest → the gap list (PLAN_05 §2.3).

A target capability is **present** if AutoCode already covers it — by the same id,
a shared surface token, or a curated *alias* (a differently-named equivalent).
Vendor-specific / universal noise (``--help``, ``--chrome``, ``auth`` …) is
**ignored**: it is not a capability gap. Everything else is a **gap**, classified
by category and clean-room suitability so ``propose`` can rank it.

The curated maps below are the only place "judgement" lives; they are data, not
code, and are deliberately conservative — when unsure, a capability is left
uncategorized (and not marked clean-room-suitable) rather than over-claimed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autocode.anvil.census import Capability, Census
from autocode.anvil.teacher.taxonomy import cluster_rank

# Categories whose gaps represent a *missing deterministic tool/capability* —
# the gapdiff analog of the taxonomy's ``tool.missing_capability`` class. Closing
# one of these adds a durable capability rather than a per-call knob, so the
# §3.3 ×3 bias applies (mirrors ``teacher/taxonomy.py:88-98``).
MISSING_CAPABILITY_CATEGORIES: frozenset[str] = frozenset(
    {"tools", "subagents", "workspace", "budget", "permissions"}
)

# Curated aliases: a target capability id -> the AutoCode capability id that
# already covers the same *capability* under a different name.
DEFAULT_ALIASES: dict[str, str] = {
    "flag:output-format": "flag:json",        # puku stream-json ≈ `exec --json` (NDJSON)
    "flag:json-schema": "flag:output-schema",  # structured-output validation
    "flag:resume": "flag:session",            # resume a prior conversation
    "flag:continue": "flag:session",
    "cmd:mcp": "cmd:mcp-serve",               # MCP server management
    "flag:print": "cmd:exec",                 # puku -p headless ≈ `autocode exec`
}

# Vendor-specific or universal-CLI capabilities that are NOT capability gaps.
DEFAULT_IGNORE: frozenset[str] = frozenset({
    "flag:help", "flag:version", "flag:chrome", "flag:no-chrome", "flag:ide",
    "flag:tmux", "flag:betas", "flag:from-pr", "flag:bare", "flag:debug",
    "flag:debug-file", "flag:mcp-debug", "flag:replay-user-messages",
    "flag:include-hook-events", "flag:include-partial-messages", "flag:name",
    "flag:setting-sources", "flag:settings", "flag:file", "flag:plugin-dir",
    "flag:disable-slash-commands", "flag:allow-god-mode", "flag:god-mode",
    "cmd:auth", "cmd:install", "cmd:setup-token", "cmd:update", "cmd:upgrade",
    "cmd:auto-mode", "cmd:agents", "cmd:plugin", "cmd:plugins",
})

# Curated classification for true gaps: id -> (category, cleanroom_suitable, rationale).
# Conservative: only capabilities with a clear, additive, oracle-checkable
# clean-room implementation in AutoCode are marked suitable.
GAP_CLASSIFICATION: dict[str, tuple[str, bool, str]] = {
    "flag:max-budget-usd": (
        "budget", True,
        "Per-run USD spend cap for headless runs. AutoCode `exec` has no budget "
        "guard. Clean-room: a BudgetGuard checked on cost updates that stops the "
        "loop when the cap is reached. Additive, deterministically testable.",
    ),
    "flag:permission-mode": (
        "permissions", True,
        "A permission-mode enum (acceptEdits/bypassPermissions/plan/...). AutoCode "
        "`exec` only exposes a boolean --auto-approve. Clean-room: map the modes "
        "onto the existing ApprovalMode. Additive, pure-logic, testable offline.",
    ),
    "flag:add-dir": (
        "workspace", True,
        "Additional directories tools may access beyond the project root. "
        "Clean-room: an explicit allow-list of extra roots passed to the runner.",
    ),
    "flag:cd": (
        "workspace", True,
        "Run the agent in a different working directory (codex `-C/--cd`). "
        "Clean-room: a per-run HeadlessRunner project_root override.",
    ),
    "flag:system-prompt": (
        "prompts", True,
        "Override the session system prompt. Clean-room: thread an override into "
        "the headless runner's system message.",
    ),
    "flag:append-system-prompt": (
        "prompts", True,
        "Append to the default system prompt. Clean-room: concatenate an extra "
        "system message.",
    ),
    "flag:effort": (
        "reasoning", False,
        "Per-session reasoning effort. AutoCode controls reasoning via config; a "
        "per-invocation override is lower priority and interacts with routing.",
    ),
    "flag:model": (
        "provider", False,
        "Per-invocation model override. AutoCode is config-driven; needs routing "
        "review before exposing per-call.",
    ),
    "flag:fallback-model": (
        "provider", False,
        "Automatic fallback model on overload. Useful but couples to provider "
        "routing; defer.",
    ),
    "flag:provider": (
        "provider", False,
        "Per-invocation provider override; AutoCode selects provider via config.",
    ),
    "flag:agents": (
        "subagents", False,
        "Inline custom-agent definitions. AutoCode has a subagent manager; a JSON "
        "surface needs design review (3 agents = 3x context, edge-cost risk).",
    ),
    "flag:tools": (
        "tools", False,
        "Restrict the available built-in tool set per session. Plausible but needs "
        "a tool-registry filter; defer.",
    ),
    "flag:fork-session": (
        "sessions", False,
        "Fork a session id on resume. Depends on resume support landing first.",
    ),
    "flag:worktree": (
        "sessions", False,
        "Run the session in a fresh git worktree. Larger surface; defer.",
    ),
}

DEFAULT_CLASSIFICATION: tuple[str, bool, str] = (
    "uncategorized", False,
    "No curated clean-room assessment yet; review before proposing.",
)


@dataclass(frozen=True)
class Present:
    """A target capability AutoCode already covers."""

    capability: Capability
    autocode_id: str
    via: str  # "direct" | "surface" | "alias"


@dataclass(frozen=True)
class Gap:
    """A target capability AutoCode lacks."""

    capability: Capability
    category: str
    cleanroom_suitable: bool
    rationale: str
    rank: float = 0.0


@dataclass(frozen=True)
class GapReport:
    target: str
    present: tuple[Present, ...] = ()
    gaps: tuple[Gap, ...] = ()
    ignored: tuple[Capability, ...] = ()

    def gap_ids(self) -> set[str]:
        return {g.capability.id for g in self.gaps}

    def suitable_gaps(self) -> list[Gap]:
        return [g for g in self.gaps if g.cleanroom_suitable]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "summary": {
                "present": len(self.present),
                "gaps": len(self.gaps),
                "cleanroom_suitable": len(self.suitable_gaps()),
                "ignored": len(self.ignored),
            },
            "gaps": [
                {
                    "id": g.capability.id,
                    "kind": g.capability.kind,
                    "surface": list(g.capability.surface),
                    "category": g.category,
                    "cleanroom_suitable": g.cleanroom_suitable,
                    "rank": g.rank,
                    "rationale": g.rationale,
                    "description": g.capability.description,
                }
                for g in self.gaps
            ],
            "present": [
                {"id": p.capability.id, "autocode_id": p.autocode_id, "via": p.via}
                for p in self.present
            ],
            "ignored": [c.id for c in self.ignored],
        }


def _gap_rank(cap: Capability, category: str, cleanroom_suitable: bool) -> float:
    """Rank a gap with the §3.3 missing-capability bias (mirrors taxonomy).

    ``rank = frequency × severity × (1 + is_tool_missing_capability × 2)``

    - **frequency** — how broadly the capability is exposed: the number of
      commands that surface a flag (``metadata["commands"]``), at least 1.
    - **severity** — a clean-room-suitable gap is worth more (it is additive and
      oracle-checkable, so it is shippable now): 1.0 vs 0.5.
    - **is_tool_missing_capability** — the gap closes a *missing deterministic
      tool/capability* (a durable tier-1 fix), so it gets the ×3 bias, exactly
      like a ``tool.missing_capability`` failure cluster.
    """
    commands = cap.metadata.get("commands")
    frequency = len(commands) if isinstance(commands, list) and commands else 1
    severity = 1.0 if cleanroom_suitable else 0.5
    return cluster_rank(
        frequency=frequency,
        severity=severity,
        is_tool_missing_capability=category in MISSING_CAPABILITY_CATEGORIES,
    )


def _manifest_index(manifest: Census) -> tuple[set[str], dict[str, str]]:
    """Return (ids, surface_token -> id) for fast lookup."""
    ids: set[str] = set()
    by_token: dict[str, str] = {}
    for cap in manifest.capabilities:
        ids.add(cap.id)
        for tok in cap.surface:
            if tok.startswith("--"):
                by_token[tok] = cap.id
    return ids, by_token


def gap_diff(
    target: Census,
    manifest: Census,
    *,
    aliases: dict[str, str] | None = None,
    ignore: frozenset[str] | None = None,
    classification: dict[str, tuple[str, bool, str]] | None = None,
) -> GapReport:
    """Diff ``target`` against ``manifest`` into a :class:`GapReport`."""
    aliases = DEFAULT_ALIASES if aliases is None else aliases
    ignore = DEFAULT_IGNORE if ignore is None else ignore
    classification = GAP_CLASSIFICATION if classification is None else classification

    ids, by_token = _manifest_index(manifest)
    present: list[Present] = []
    gaps: list[Gap] = []
    ignored: list[Capability] = []

    for cap in target.capabilities:
        # 1. Same canonical id.
        if cap.id in ids:
            present.append(Present(cap, cap.id, "direct"))
            continue
        # 2. Shared long-flag surface token.
        shared = next((by_token[t] for t in cap.surface if t in by_token), None)
        if shared is not None:
            present.append(Present(cap, shared, "surface"))
            continue
        # 3. Curated alias to an existing AutoCode capability.
        alias_target = aliases.get(cap.id)
        if alias_target is not None and alias_target in ids:
            present.append(Present(cap, alias_target, "alias"))
            continue
        # 4. Vendor / universal noise — not a gap.
        if cap.id in ignore:
            ignored.append(cap)
            continue
        # 5. A real gap.
        category, suitable, rationale = classification.get(cap.id, DEFAULT_CLASSIFICATION)
        rank = _gap_rank(cap, category, suitable)
        gaps.append(Gap(cap, category, suitable, rationale, rank=rank))

    # Rank descending by the §3.3 missing-capability-biased rank, then keep the
    # prior deterministic order (clean-room-suitable, category, id) as the stable
    # tie-break so equal-rank gaps still sort predictably.
    gaps.sort(key=lambda g: (-g.rank, not g.cleanroom_suitable, g.category, g.capability.id))
    return GapReport(
        target=target.target,
        present=tuple(present),
        gaps=tuple(gaps),
        ignored=tuple(ignored),
    )
