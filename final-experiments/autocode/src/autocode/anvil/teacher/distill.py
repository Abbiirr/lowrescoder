"""G5 distiller — turn recorded trajectories into a layered evidence corpus.

PLAN_04 §7 Phase 3 (line 462) and ``04_ARCHITECTURE.md`` §4.2.2 name the
distiller as the missing layer between the trajectory recorder (G2) and the
teacher's :func:`~autocode.anvil.teacher.loop.teach` propose step. It:

1. Reads :class:`~autocode.anvil.teacher.schemas.Trajectory` records (failed
   ones, by default — successes don't need fixing) plus an optional attribution
   of :class:`~autocode.anvil.teacher.schemas.RootCause` per trajectory.
2. Clusters them by ``(language, root_cause_class)`` — the same vocabulary the
   :mod:`~autocode.anvil.teacher.taxonomy` module normatively specifies.
3. Ranks clusters by the taxonomy's
   :func:`~autocode.anvil.teacher.taxonomy.cluster_rank` rule
   (``frequency × severity × (1 + is_tool_missing_capability × 2)``).
4. Emits a *layered* per-cluster evidence digest:

   * **Layer 0** — trajectory metadata (ids, task instructions, verdicts).
   * **Layer 1** — root-cause attribution (class, evidence step, explanation).
   * **Layer 2** — aggregated cluster metrics (frequency, severity, layer
     distribution, sample trajectory ids).
   * **Layer 3** — fix recommendation (the taxonomy's ``fix_tier`` and
     ``component_kind`` for this class — the manifest entry a harness_fix would
     target).

Output: per-language per-cluster JSON files under
``$AUTOCODE_HOME/teacher/distilled/<lang>/<root_cause>.json`` plus a top-level
``corpus.json`` index. The operator surfaces this with
``autocode anvil teacher sense`` (PLAN_04 §6 line 393).
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from autocode.anvil import paths
from autocode.anvil.teacher import cost as edge_cost
from autocode.anvil.teacher.schemas import Layer, RootCause, Trajectory, VerdictLabel
from autocode.anvil.teacher.taxonomy import (
    FAILURE_TABLE,
    RootCauseClass,
    cluster_rank,
    fix_info,
)


class DistillError(Exception):
    """Distillation was refused (no input trajectories, no attribution)."""


# ---------------------------------------------------------------------------
# Input attribution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttributedTrajectory:
    """A trajectory plus the distiller's required attribution.

    The distiller needs (a) a root-cause class and (b) a language to cluster on.
    Both come from the teaching packet the reflector emits; for tests or
    batch-only flows they can be supplied directly.
    """

    trajectory: Trajectory
    root_cause: RootCause
    language: str = "python"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trajectory": self.trajectory.to_dict(),
            "root_cause": self.root_cause.to_dict(),
            "language": self.language,
        }


def _severity_for(verdict_label: str) -> float:
    """Map a verdict label to a [0, 1] severity used by cluster_rank.

    An ``error`` is the worst (the harness crashed); ``fail`` is a normal
    failure; ``partial`` is a near-miss (still worth fixing); ``success``
    shouldn't reach the distiller (we filter earlier) but maps to 0 so it
    contributes nothing if it slips through.
    """
    return {
        VerdictLabel.ERROR.value: 1.0,
        VerdictLabel.FAIL.value: 0.8,
        VerdictLabel.PARTIAL.value: 0.4,
        VerdictLabel.SUCCESS.value: 0.0,
    }.get(verdict_label, 0.5)


# ---------------------------------------------------------------------------
# Output: layered evidence corpus
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClusterLayer0:
    """Sample trajectory metadata for one cluster."""

    trajectory_id: str
    task_instruction: str
    verdict_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClusterLayer1:
    """Root-cause attribution summary for one cluster (constant within a cluster)."""

    root_cause_class: str
    evidence_step: int
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClusterLayer2:
    """Aggregated metrics for one cluster."""

    frequency: int
    severity: float
    rank: float
    layer_distribution_L4: float  # noqa: N815 - matches the guard string
    latency_p50: float
    tokens_per_task: float
    sample_trajectory_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frequency": self.frequency,
            "severity": self.severity,
            "rank": self.rank,
            "layer_distribution_L4": self.layer_distribution_L4,
            "latency_p50": self.latency_p50,
            "tokens_per_task": self.tokens_per_task,
            "sample_trajectory_ids": list(self.sample_trajectory_ids),
        }


@dataclass(frozen=True)
class ClusterLayer3:
    """The fix recommendation the teacher's propose step will target."""

    fix_tier: int
    component_kind: str
    manifest_target_hint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DistilledCluster:
    """One ranked cluster's full layered evidence digest."""

    language: str
    root_cause_class: str
    layer0: tuple[ClusterLayer0, ...]
    layer1: ClusterLayer1
    layer2: ClusterLayer2
    layer3: ClusterLayer3

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "root_cause_class": self.root_cause_class,
            "layer0_evidence": [entry.to_dict() for entry in self.layer0],
            "layer1_attribution": self.layer1.to_dict(),
            "layer2_metrics": self.layer2.to_dict(),
            "layer3_fix": self.layer3.to_dict(),
        }


@dataclass(frozen=True)
class DistilledCorpus:
    """The full output of one distillation pass."""

    clusters: tuple[DistilledCluster, ...]
    generated_at: str
    trajectory_count: int
    source: str = "trajectory-store"

    def to_dict(self) -> dict[str, Any]:
        return {
            "clusters": [c.to_dict() for c in self.clusters],
            "generated_at": self.generated_at,
            "trajectory_count": self.trajectory_count,
            "source": self.source,
        }

    def by_language(self, language: str) -> tuple[DistilledCluster, ...]:
        return tuple(c for c in self.clusters if c.language == language)

    def top(self, n: int = 3) -> tuple[DistilledCluster, ...]:
        """The top-N ranked clusters across all languages."""
        return tuple(
            sorted(self.clusters, key=lambda c: c.layer2.rank, reverse=True)[:n]
        )


# ---------------------------------------------------------------------------
# Distillation driver
# ---------------------------------------------------------------------------


def _cluster_key(attr: AttributedTrajectory) -> tuple[str, str]:
    return (attr.language, attr.root_cause.category)


def distill(
    attributed: Sequence[AttributedTrajectory],
    *,
    generated_at: str = "",
    source: str = "trajectory-store",
) -> DistilledCorpus:
    """Cluster attributed trajectories into a ranked layered-evidence corpus.

    The output is sorted by :func:`~autocode.anvil.teacher.taxonomy.cluster_rank`
    descending, so ``corpus.top(N)`` returns the highest-leverage clusters the
    teacher should propose fixes for first.
    """
    if not attributed:
        raise DistillError(
            "no attributed trajectories to distill — the recorder has no failed "
            "trajectories on record, or the propose step was called before any run."
        )

    grouped: dict[tuple[str, str], list[AttributedTrajectory]] = defaultdict(list)
    for attr in attributed:
        grouped[_cluster_key(attr)].append(attr)

    clusters: list[DistilledCluster] = []
    for (language, rc_class), members in grouped.items():
        trajectories = [m.trajectory for m in members]
        verdict_labels = [m.trajectory.outcome.label for m in members]
        # Severity is the mean across the cluster's verdicts.
        severity = sum(_severity_for(v) for v in verdict_labels) / len(verdict_labels)
        is_tool_missing = rc_class == RootCauseClass.TOOL_MISSING_CAPABILITY.value
        rank = cluster_rank(
            frequency=len(members),
            severity=severity,
            is_tool_missing_capability=is_tool_missing,
        )

        # Layer 2 edge-cost metrics on this cluster's trajectories.
        try:
            ec = edge_cost.measure(trajectories)
            l4 = ec.layer_distribution_L4
            lat = ec.latency_p50
            tok = ec.tokens_per_task
        except edge_cost.EdgeCostError:
            l4 = lat = tok = 0.0

        # Layer 3 fix recommendation from the taxonomy table.
        info = fix_info(rc_class)
        fix_tier = info.fix_tier if info else 0
        component_kind = info.component_kind if info else "unknown"
        manifest_target_hint = f"{component_kind}:{rc_class}"

        layer0 = tuple(
            ClusterLayer0(
                trajectory_id=m.trajectory.trajectory_id,
                task_instruction=m.trajectory.task.instruction[:200],
                verdict_label=m.trajectory.outcome.label,
            )
            for m in members
        )
        sample = tuple(m.trajectory.trajectory_id for m in members[:10])

        clusters.append(
            DistilledCluster(
                language=language,
                root_cause_class=rc_class,
                layer0=layer0,
                layer1=ClusterLayer1(
                    root_cause_class=rc_class,
                    evidence_step=members[0].root_cause.evidence_step,
                    explanation=members[0].root_cause.explanation,
                ),
                layer2=ClusterLayer2(
                    frequency=len(members),
                    severity=round(severity, 6),
                    rank=round(rank, 6),
                    layer_distribution_L4=round(l4, 6),
                    latency_p50=round(lat, 6),
                    tokens_per_task=round(tok, 6),
                    sample_trajectory_ids=sample,
                ),
                layer3=ClusterLayer3(
                    fix_tier=fix_tier,
                    component_kind=component_kind,
                    manifest_target_hint=manifest_target_hint,
                ),
            )
        )

    clusters.sort(key=lambda c: c.layer2.rank, reverse=True)
    return DistilledCorpus(
        clusters=tuple(clusters),
        generated_at=generated_at,
        trajectory_count=len(attributed),
        source=source,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def distilled_root(root: Path | str | None = None) -> Path:
    """``<anvil>/teacher/distilled/`` — the distiller's output root."""
    return paths.anvil_root(root) / "teacher" / "distilled"


def write_corpus(corpus: DistilledCorpus, root: Path | str | None = None) -> Path:
    """Persist a distilled corpus as per-language per-cluster JSON + an index.

    Returns the index path (``corpus.json``). Existing cluster files are
    overwritten; cluster files for classes no longer present are *not* deleted
    (the distiller is append-friendly, mirroring the playbook's discipline).
    """
    base = distilled_root(root)
    base.mkdir(parents=True, exist_ok=True)

    by_lang: dict[str, list[DistilledCluster]] = defaultdict(list)
    for cluster in corpus.clusters:
        by_lang[cluster.language].append(cluster)

    for language, clusters in by_lang.items():
        lang_dir = base / language
        lang_dir.mkdir(parents=True, exist_ok=True)
        for cluster in clusters:
            # File name: the root-cause class with dots replaced by underscores
            # (e.g. ``tool_missing_capability.json``).
            stem = cluster.root_cause_class.replace(".", "_") or "none"
            (lang_dir / f"{stem}.json").write_text(
                json.dumps(cluster.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )

    index_path = base / "corpus.json"
    index_path.write_text(json.dumps(corpus.to_dict(), indent=2) + "\n", encoding="utf-8")
    return index_path


def read_corpus(root: Path | str | None = None) -> DistilledCorpus | None:
    """Read the most recent distilled corpus from disk (or ``None`` if absent)."""
    index = distilled_root(root) / "corpus.json"
    if not index.is_file():
        return None
    data = json.loads(index.read_text(encoding="utf-8"))
    clusters: list[DistilledCluster] = []
    for c in data.get("clusters", []):
        l0 = tuple(
            ClusterLayer0(
                trajectory_id=entry["trajectory_id"],
                task_instruction=entry["task_instruction"],
                verdict_label=entry["verdict_label"],
            )
            for entry in c.get("layer0_evidence", [])
        )
        l1_raw = c.get("layer1_attribution", {})
        l2_raw = c.get("layer2_metrics", {})
        l3_raw = c.get("layer3_fix", {})
        clusters.append(
            DistilledCluster(
                language=c.get("language", ""),
                root_cause_class=c.get("root_cause_class", ""),
                layer0=l0,
                layer1=ClusterLayer1(
                    root_cause_class=l1_raw.get("root_cause_class", ""),
                    evidence_step=int(l1_raw.get("evidence_step", -1)),
                    explanation=l1_raw.get("explanation", ""),
                ),
                layer2=ClusterLayer2(
                    frequency=int(l2_raw.get("frequency", 0)),
                    severity=float(l2_raw.get("severity", 0.0)),
                    rank=float(l2_raw.get("rank", 0.0)),
                    layer_distribution_L4=float(l2_raw.get("layer_distribution_L4", 0.0)),
                    latency_p50=float(l2_raw.get("latency_p50", 0.0)),
                    tokens_per_task=float(l2_raw.get("tokens_per_task", 0.0)),
                    sample_trajectory_ids=tuple(l2_raw.get("sample_trajectory_ids", []) or []),
                ),
                layer3=ClusterLayer3(
                    fix_tier=int(l3_raw.get("fix_tier", 0)),
                    component_kind=l3_raw.get("component_kind", ""),
                    manifest_target_hint=l3_raw.get("manifest_target_hint", ""),
                ),
            )
        )
    return DistilledCorpus(
        clusters=tuple(clusters),
        generated_at=data.get("generated_at", ""),
        trajectory_count=int(data.get("trajectory_count", 0)),
        source=data.get("source", ""),
    )


# ---------------------------------------------------------------------------
# Teaching-packet ingestion (the production input path)
# ---------------------------------------------------------------------------


def attributed_from_packets(
    packets: Iterable[Any],
) -> list[AttributedTrajectory]:
    """Build the distiller's input from teaching packets + their trajectories.

    Each ``packet`` is expected to expose ``trajectory``, ``root_cause`` and
    ``language`` attributes — i.e. a tuple of
    ``(TeachingPacket, Trajectory, language)`` or any duck-typed equivalent.
    """
    out: list[AttributedTrajectory] = []
    for entry in packets:
        if isinstance(entry, AttributedTrajectory):
            out.append(entry)
            continue
        if isinstance(entry, tuple) and len(entry) == 3:
            tj, rc, lang = entry
            out.append(AttributedTrajectory(trajectory=tj, root_cause=rc, language=lang))
            continue
        # Duck-typed: TeachingPacket carries root_cause; pair with a trajectory.
        if hasattr(entry, "root_cause") and hasattr(entry, "trajectory_id"):
            # Caller forgot to pass the trajectory — derive a minimal stub.
            from autocode.anvil.teacher.schemas import Verdict

            stub = Trajectory(
                trajectory_id=getattr(entry, "trajectory_id", ""),
                task=__import__("autocode.anvil.teacher.schemas", fromlist=["Task"]).Task(
                    instruction=""
                ),
                outcome=getattr(entry, "verdict", Verdict(label="fail")),
            )
            out.append(
                AttributedTrajectory(
                    trajectory=stub,
                    root_cause=entry.root_cause,
                    language=getattr(entry, "language", "python"),
                )
            )
    return out


# Re-exported for type-checkers; not on a hot path.
__all__extras__ = (Layer, FAILURE_TABLE)
