"""The ACE playbook — durable-memory plane for teacher mode (§4).

ACE (arXiv:2510.04618) solves the two failure modes of a naive memory loop:
**brevity bias** (dropping detail for concise summaries) and **context collapse**
(iterative rewriting erodes detail). The fix is *append-only deltas + periodic
merge*: never blindly rewrite.

This module implements the Curator (append a structured delta), the Pruner
(periodically merge overlapping deltas into concise "Master Rules" *without
deleting the deltas*), and the runtime Loader (read-only at session start).

Storage (normative, §4.2), per-language so it stays scoped::

    .autocode/playbook/
      python.md            # human-facing: Master Rules + rendered deltas
      python.deltas.jsonl  # append-only machine record (the source of truth)
      _meta.json           # delta count, last prune, provenance per rule

The append-only discipline (manifest ``edit_surface: append_only``) is enforced
here structurally: :meth:`PlaybookStore.append_delta` only ever *appends* to the
JSONL source of truth; the ``.md`` is a deterministic, regenerable *view*.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autocode.anvil.teacher.schemas import PlaybookDelta

# An eval gate for the Pruner merge (06 §6.3, "does pass@1 hold after pruning?").
# (rules_before, rules_after) -> True iff pass@1 holds (the merge is safe to commit).
PruneEvalGate = Callable[[list["MasterRule"], list["MasterRule"]], bool]


class PruneRegressionError(Exception):
    """The Pruner merge was refused because the eval gate saw a pass@1 regression."""


def default_playbook_dir(project_root: str | Path | None = None) -> Path:
    """The durable-memory playbook dir for ``project_root`` (default: cwd)."""
    root = Path(project_root) if project_root else Path.cwd()
    return root / ".autocode" / "playbook"


@dataclass
class MasterRule:
    """A merged rule maintained by the Pruner."""

    root_cause_class: str
    trigger: str
    rule: str
    support: int = 1  # how many deltas back this rule
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_cause_class": self.root_cause_class,
            "trigger": self.trigger,
            "rule": self.rule,
            "support": self.support,
            "evidence": self.evidence,
        }


@dataclass
class PruneResult:
    language: str
    deltas_in: int
    rules_out: int
    merged: list[MasterRule]


class PlaybookStore:
    """Per-language ACE playbook reader/writer rooted at a directory."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root else default_playbook_dir()

    # ---- paths -------------------------------------------------------------
    def md_path(self, lang: str) -> Path:
        return self.root / f"{lang}.md"

    def deltas_path(self, lang: str) -> Path:
        return self.root / f"{lang}.deltas.jsonl"

    def meta_path(self) -> Path:
        return self.root / "_meta.json"

    # ---- meta --------------------------------------------------------------
    def _load_meta(self) -> dict[str, Any]:
        p = self.meta_path()
        if p.is_file():
            data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
            return data
        return {"languages": {}}

    def _save_meta(self, meta: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.meta_path().write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    # ---- Curator (append-only) --------------------------------------------
    def append_delta(self, delta: PlaybookDelta) -> None:
        """Append one delta to the JSONL source of truth and regenerate the view."""
        lang = delta.language or "generic"
        self.root.mkdir(parents=True, exist_ok=True)
        with self.deltas_path(lang).open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(delta.to_dict()) + "\n")

        meta = self._load_meta()
        langs = meta.setdefault("languages", {})
        entry = langs.setdefault(lang, {"delta_count": 0, "last_prune": None, "rules": []})
        entry["delta_count"] = int(entry.get("delta_count", 0)) + 1
        self._save_meta(meta)
        self._regenerate_md(lang)

    # ---- read --------------------------------------------------------------
    def read_deltas(self, lang: str) -> list[PlaybookDelta]:
        p = self.deltas_path(lang)
        if not p.is_file():
            return []
        out: list[PlaybookDelta] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(PlaybookDelta.from_dict(json.loads(line)))
        return out

    def master_rules(self, lang: str) -> list[MasterRule]:
        meta = self._load_meta()
        raw = meta.get("languages", {}).get(lang, {}).get("rules", [])
        return [
            MasterRule(
                root_cause_class=r.get("root_cause_class", ""),
                trigger=r.get("trigger", ""),
                rule=r.get("rule", ""),
                support=int(r.get("support", 1)),
                evidence=list(r.get("evidence", [])),
            )
            for r in raw
        ]

    # ---- Loader (runtime, read-only) --------------------------------------
    def load_rules(self, lang: str) -> list[str]:
        """The active rules the runtime should honor for ``lang``.

        Prefers Master Rules (post-prune); falls back to one rule per delta so a
        freshly-curated playbook is useful before the first prune.
        """
        rules = [r.rule for r in self.master_rules(lang) if r.rule]
        if rules:
            return rules
        return [d.rule for d in self.read_deltas(lang) if d.rule]

    def render_prompt_block(self, lang: str) -> str:
        """A compact text block the runtime can inject into the system context."""
        rules = self.load_rules(lang)
        if not rules:
            return ""
        lines = [f"## Playbook ({lang}) — learned rules", ""]
        lines += [f"- {r}" for r in rules]
        return "\n".join(lines) + "\n"

    # ---- Pruner (periodic merge; deltas are preserved) --------------------
    def prune(self, lang: str, *, eval_gate: PruneEvalGate | None = None) -> PruneResult:
        """Merge overlapping deltas into concise Master Rules (anti-brevity-bias).

        Grouping key is ``(root_cause_class, normalized trigger)``; within a group
        the distinct rule texts are preserved (detail is not lost), and the group's
        ``support`` is the number of contributing deltas. The deltas JSONL is left
        untouched — pruning is reversible by simply re-running it.

        ``eval_gate`` (06 §6.3, A.1) is the prediction gate on the destructive
        rewrite: it receives ``(rules_before, rules_after)`` and must return True
        iff pass@1 holds after the merge. When it returns False the merge is
        **refused** — :class:`PruneRegressionError` is raised and nothing is
        written, so the merge can never silently weaken the durable memory. When
        omitted the merge commits unconditionally (backwards-compatible).
        """
        deltas = self.read_deltas(lang)
        rules_before = self.master_rules(lang)
        groups: dict[tuple[str, str], MasterRule] = {}
        for d in deltas:
            key = (d.root_cause_class, _normalize(d.trigger))
            mr = groups.get(key)
            if mr is None:
                groups[key] = MasterRule(
                    root_cause_class=d.root_cause_class,
                    trigger=d.trigger,
                    rule=d.rule,
                    support=1,
                    evidence=[d.evidence_trajectory] if d.evidence_trajectory else [],
                )
            else:
                mr.support += 1
                if d.evidence_trajectory and d.evidence_trajectory not in mr.evidence:
                    mr.evidence.append(d.evidence_trajectory)
                # Preserve a distinct rule by concatenating (anti-brevity); keep the
                # longest, most-detailed phrasing as the canonical rule.
                if d.rule and d.rule not in mr.rule:
                    if len(d.rule) > len(mr.rule):
                        mr.rule = d.rule

        merged = sorted(groups.values(), key=lambda m: m.support, reverse=True)

        # Prediction gate the destructive rewrite (06 §6.3): refuse on regression
        # *before* writing anything, so a bad merge cannot land.
        if eval_gate is not None and not eval_gate(rules_before, merged):
            raise PruneRegressionError(
                f"refusing to prune '{lang}': the eval gate found pass@1 does not hold "
                f"after merging {len(deltas)} deltas into {len(merged)} Master Rules "
                f"(no changes written)."
            )

        meta = self._load_meta()
        entry = meta.setdefault("languages", {}).setdefault(
            lang, {"delta_count": len(deltas), "last_prune": None, "rules": []}
        )
        entry["rules"] = [m.to_dict() for m in merged]
        entry["last_prune"] = {"deltas_in": len(deltas), "rules_out": len(merged)}
        self._save_meta(meta)
        self._regenerate_md(lang)
        return PruneResult(
            language=lang, deltas_in=len(deltas), rules_out=len(merged), merged=merged
        )

    # ---- md view -----------------------------------------------------------
    def _regenerate_md(self, lang: str) -> None:
        deltas = self.read_deltas(lang)
        rules = self.master_rules(lang)
        lines = [
            f"# Playbook: {lang}",
            "",
            "> ACE durable-memory plane. **Master Rules** are Pruner-maintained; "
            "**deltas** are append-only. The runtime loads this read-only at session start.",
            "",
            "## Master Rules",
            "",
        ]
        if rules:
            for r in rules:
                lines.append(
                    f"- **[{r.root_cause_class}]** {r.rule} "
                    f"_(trigger: {r.trigger}; support: {r.support})_"
                )
        else:
            lines.append("_No merged rules yet — run the Pruner once deltas accumulate._")
        lines += ["", "## Deltas (append-only)", ""]
        if not deltas:
            lines.append("_No deltas yet._")
        for d in deltas:
            lines += [
                f"### {d.delta_id} — {d.verdict} — {d.root_cause_class}",
                f"- **trigger:** {d.trigger}",
                f"- **observation:** {d.observation}",
                f"- **rule:** {d.rule}",
                f"- **evidence:** {d.evidence_trajectory}",
                f"- **created:** {d.created}",
                "",
            ]
        self.root.mkdir(parents=True, exist_ok=True)
        self.md_path(lang).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


__all__ = [
    "default_playbook_dir",
    "MasterRule",
    "PruneResult",
    "PruneEvalGate",
    "PruneRegressionError",
    "PlaybookStore",
]
