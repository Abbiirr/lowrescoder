"""Channel B — distillation branch (PLAN_05 §3.1, §3.4).

Consumes the verified-outcome corpus produced by
:mod:`autocode.anvil.copycat.outcome` and renders it as a
teacher-replayable form: one ``dataset.jsonl`` file whose lines are stable
JSON objects (``task``, ``target``, ``diff``, ``verified``, ``sha256``). The
dataset's SHA-256 is deterministic across runs with identical corpus inputs,
which is what the PLAN_05 closing gate (TESTING.md#plan_05) checks.

Refused unless the registry grants ``reuse_scope: weights`` *and* a recorded
per-provider ToS check is present. The eval-oracle branch
(:mod:`autocode.anvil.copycat.outcome`) does not require this gate because it
only *compares* against the corpus — it does not produce training data.

The weight branch is **tier-5 / Phase-7** (PLAN_05 §5 build order; §7 line 450):
the dataset is the input to QLoRA / step-wise OPD on the local 1.5B model,
behind hardware + ToS gates. This module produces the dataset; the trainer
itself is out of scope (hardware-gated, deferred).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autocode.anvil import paths
from autocode.anvil.copycat import outcome
from autocode.anvil.registry import Registry, load_registry

CHANNEL = outcome.CHANNEL  # "outcome" — Channel B drives the same channel
WEIGHTS_SCOPE = "weights"


class DistillError(Exception):
    """A Channel B distillation run was refused."""


@dataclass(frozen=True)
class Dataset:
    """The rendered teacher-replayable form (one ``dataset.jsonl`` file)."""

    path: Path
    line_count: int
    sha256: str
    target: str
    corpus_version: int


def _load_registry_or_raise(root: Path) -> Registry:
    return load_registry(paths.registry_path(root))


def _check_authorization(reg: Registry, target: str) -> None:
    """Refuse distillation unless the registry grants weights + a ToS check."""
    try:
        reg.assert_channel_allowed(target, CHANNEL)
        reg.assert_reuse_scope(target, WEIGHTS_SCOPE)
    except Exception as exc:  # RegistryError, but we re-raise as DistillError
        raise DistillError(
            f"distillation refused for target '{target}': {exc}. "
            f"Channel B distillation requires `reuse_scope: weights` AND a "
            f"recorded per-provider ToS check in registry.yaml."
        ) from exc


def _outcome_to_dataset_line(oc: outcome.Outcome) -> dict[str, Any]:
    """Stable, timestamp-free form of an outcome for the training dataset.

    Excludes ``captured_at`` so two corpora with the same content hash to the
    same dataset.
    """
    return {
        "task_id": oc.task_id,
        "target": oc.target,
        "prompt": "",  # Outcome carries the diff, not the original prompt;
                       # the trainer pairs (task_id, diff_text) — prompt is
                       # recovered from the task registry by id.
        "diff_text": oc.diff.text,
        "diff_files": list(oc.diff.files),
        "verified": oc.verification.label == "verified",
        "verification_summary": oc.verification.summary,
        "sha256": oc.sha256,
        "corpus_version": oc.corpus_version,
    }


def _serialize_dataset_line(line: dict[str, Any]) -> str:
    """Canonical JSON for one dataset line — sort_keys for byte-stable hashing."""
    return json.dumps(line, sort_keys=True, ensure_ascii=False)


def _dataset_sha256(serialized_lines: list[str]) -> str:
    h = hashlib.sha256()
    for line in serialized_lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _latest_outcomes(root: Path) -> tuple[list[outcome.Outcome], int]:
    anvil = paths.anvil_root(root)
    version = outcome.latest_corpus_version(anvil)
    if version == 0:
        return [], 0
    corpus = outcome.corpus_dir(anvil, version)
    return outcome.iter_outcomes(corpus), version


def distill(
    target: str,
    *,
    root: Path | str | None = None,
    registry: Registry | None = None,
    output: Path | str | None = None,
) -> Dataset:
    """Render the latest verified-outcome corpus as a teacher-replayable dataset.

    Refused unless the registry grants ``reuse_scope: weights`` for ``target``
    and a recorded per-provider ToS check is present. The dataset is written to
    ``<anvil>/copycat/outcomes/dataset@<target>.jsonl`` by default, or to
    ``output`` if provided.
    """
    anvil = paths.anvil_root(root)
    reg = registry or _load_registry_or_raise(anvil)
    _check_authorization(reg, target)

    outcomes, version = _latest_outcomes(anvil)
    if not outcomes:
        raise DistillError(
            f"no verified outcomes to distill for target '{target}' "
            f"(corpus@v{version or 1} is empty). Run "
            f"`autocode anvil copycat outcome {target} <task>` first."
        )

    serialized = [_serialize_dataset_line(_outcome_to_dataset_line(oc)) for oc in outcomes]
    sha = _dataset_sha256(serialized)

    if output:
        out_path = Path(output)
    else:
        out_path = outcome.outcomes_root(anvil) / f"dataset@{target}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(serialized) + ("\n" if serialized else ""), encoding="utf-8")

    return Dataset(
        path=out_path,
        line_count=len(serialized),
        sha256=sha,
        target=target,
        corpus_version=version or 1,
    )
