"""Record a gated patch bundle's promotion in the immutable audit log (§6, §9.5).

Promotion is operator-gated: a bundle may be promoted only after the gate scored
its prediction as *met* with no edge-cost regression. Every promotion appends one
JSONL line to ``anvil/audit_log.jsonl`` — the machine record that pairs with the
bundle's human-readable ``decision.md``. The log is append-only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autocode.anvil import paths
from autocode.anvil.registry import GateComponentError, assert_not_gate_component


class PromoteError(Exception):
    """Promotion was refused (ungated bundle, or prediction not met)."""


def promote(
    bundle_dir: str | Path,
    *,
    root: Path | None = None,
    timestamp: str = "",
    operator: str = "operator",
) -> dict[str, Any]:
    bundle_dir = Path(bundle_dir)
    meta_path = bundle_dir / "bundle.json"
    if not meta_path.is_file():
        raise PromoteError(f"not a patch bundle (no bundle.json): {bundle_dir}")
    meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))

    # Gate-component lockout (07 §7.2): a bundle that targets a gate component can
    # never be promoted, even if some other path scored it. Defense-in-depth with
    # the same check at gate time.
    try:
        assert_not_gate_component(meta.get("manifest_entry"), meta.get("target"))
    except GateComponentError as exc:
        raise PromoteError(str(exc)) from exc

    score_path = bundle_dir / "prediction_score.json"
    if not score_path.is_file():
        raise PromoteError(
            f"bundle {meta.get('bundle_id')} has not been gated "
            f"(run `autocode anvil gate` first)."
        )
    score: dict[str, Any] = json.loads(score_path.read_text(encoding="utf-8"))
    if not score.get("met"):
        raise PromoteError(
            f"refusing to promote {meta.get('bundle_id')}: prediction not met "
            f"(gate returncode {score.get('returncode')})."
        )
    # The edge-cost guard is the program's "edge cost can't regress" invariant
    # (PLAN_04 §0.3.6). The gate folds a measured verdict into ``no_regression``;
    # block here so a candidate whose tests pass but whose L4/latency/tokens
    # regress cannot be promoted. ``no_regression`` defaults to True for legacy
    # scores and for bundles gated without trajectory data (``edge_cost_measured:
    # False``), keeping structural-only bundles promotable.
    if not score.get("no_regression", True):
        guards = ", ".join(score.get("no_regression_on", [])) or "a mandatory guard"
        raise PromoteError(
            f"refusing to promote {meta.get('bundle_id')}: edge-cost regression — "
            f"tests pass but {guards} regressed (see {score_path.name})."
        )

    anvil = paths.anvil_root(root)
    entry = {
        "bundle_id": meta.get("bundle_id"),
        "capability_id": meta.get("capability_id"),
        "manifest_entry": meta.get("manifest_entry"),
        "target": meta.get("target"),
        "channel": meta.get("channel"),
        "reuse_scope": meta.get("reuse_scope"),
        "promoted_on": timestamp,
        "operator": operator,
        # Record whether the edge-cost guard was actually measured so the log
        # never implies a guard it did not check (the false-green the audit flagged).
        "eval": {
            "met": True,
            "no_regression": bool(score.get("no_regression", True)),
            "edge_cost_measured": bool(score.get("edge_cost_measured", False)),
        },
        "decision_ref": str(bundle_dir / "decision.md"),
    }

    log_path = paths.audit_log_path(anvil)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry) + "\n")

    meta["status"] = "promoted"
    meta["promoted_on"] = timestamp
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return entry
