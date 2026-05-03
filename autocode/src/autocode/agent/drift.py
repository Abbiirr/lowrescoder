"""Lightweight drift detectors for long-running agent sessions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

DriftSeverity = Literal["low", "medium", "high"]
Sensitivity = Literal["low", "medium", "high"]


def args_hash(args: dict[str, Any]) -> str:
    encoded = json.dumps(args, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SchemaSnapshot:
    tool_name: str
    args_hash: str
    schema_hash: str
    captured_at: datetime
    sample_size: int
    shape: Any = field(compare=False)


@dataclass(frozen=True)
class DriftWarning:
    kind: str
    severity: DriftSeverity
    recommendation: str
    diff: Any | None = None
    tool_name: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    prior_seen_at: datetime | None = None
    fact_source: str | None = None
    age_days: int | None = None


class SchemaDriftDetector:
    """Detect structural drift in repeated tool outputs for identical args."""

    def __init__(
        self,
        *,
        sensitivity: Sensitivity = "medium",
        enabled: bool = True,
    ) -> None:
        self.sensitivity = sensitivity
        self.enabled = enabled
        self._snapshots: dict[tuple[str, str], SchemaSnapshot] = {}

    def observe(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
    ) -> DriftWarning | None:
        if not self.enabled:
            return None
        hashed_args = args_hash(args)
        new_shape = self._compute_shape(result)
        new_hash = _shape_hash(new_shape)
        key = (tool_name, hashed_args)
        prior = self._snapshots.get(key)
        self._snapshots[key] = SchemaSnapshot(
            tool_name=tool_name,
            args_hash=hashed_args,
            schema_hash=new_hash,
            captured_at=datetime.now(UTC),
            sample_size=1 if prior is None else prior.sample_size + 1,
            shape=new_shape,
        )
        if prior is None or prior.schema_hash == new_hash:
            return None
        diff = self._diff_shapes(prior.shape, new_shape)
        if not self._meets_sensitivity_threshold(diff):
            return None
        return DriftWarning(
            kind="schema_drift",
            tool_name=tool_name,
            args=args,
            prior_seen_at=prior.captured_at,
            diff=diff,
            severity=self._severity(diff),
            recommendation=(
                f"The shape of {tool_name} results changed since "
                f"{prior.captured_at.isoformat()}. Verify assumptions about "
                "the returned data structure before proceeding."
            ),
        )

    def _compute_shape(self, value: Any, depth: int = 0, max_depth: int = 3) -> Any:
        if depth > max_depth:
            return {"__truncated": True}
        if isinstance(value, dict):
            return {
                str(key): self._compute_shape(item, depth + 1, max_depth)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, list):
            if not value:
                return ["__empty"]
            return [self._compute_shape(item, depth + 1, max_depth) for item in value[:3]]
        return type(value).__name__

    def _diff_shapes(self, prior: Any, new: Any) -> dict[str, Any]:
        return _diff_shapes(prior, new)

    def _meets_sensitivity_threshold(self, diff: dict[str, Any]) -> bool:
        if not diff:
            return False
        if self.sensitivity == "high":
            return bool(diff.get("missing") or diff.get("type_changes") or diff.get("added"))
        if self.sensitivity == "medium":
            return bool(diff.get("missing") or diff.get("type_changes"))
        return bool(diff.get("missing"))

    @staticmethod
    def _severity(diff: dict[str, Any]) -> DriftSeverity:
        if diff.get("missing"):
            return "high"
        if diff.get("type_changes"):
            return "medium"
        return "low"


class ContextStalenessDetector:
    """Warn when remembered topic facts are older than the configured threshold."""

    DEFAULT_THRESHOLD = timedelta(days=7)

    def __init__(
        self,
        memory_fs: Any,
        threshold: timedelta = DEFAULT_THRESHOLD,
        *,
        enabled: bool = True,
    ) -> None:
        self._memory_fs = memory_fs
        self._threshold = threshold
        self.enabled = enabled

    def check_fact_freshness(self, fact_topic: str) -> DriftWarning | None:
        if not self.enabled:
            return None
        topic_path = Path(self._memory_fs.topics_dir) / f"{fact_topic}.md"
        if not topic_path.exists():
            return None
        age = datetime.now(UTC) - datetime.fromtimestamp(topic_path.stat().st_mtime, UTC)
        if age <= self._threshold:
            return None
        return DriftWarning(
            kind="context_staleness",
            fact_source=fact_topic,
            age_days=age.days,
            severity="medium",
            recommendation=(
                f"Topic '{fact_topic}' was last updated {age.days} days ago. "
                "Verify against current code before acting on remembered facts."
            ),
        )


class ToolConsistencyDetector:
    """Detect inconsistent results from deterministic tools within one turn."""

    DETERMINISTIC_TOOLS = {"read_file", "list_files", "git_status", "list_symbols"}

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._turn_observations: dict[tuple[str, str], Any] = {}

    def reset_turn(self) -> None:
        self._turn_observations.clear()

    def observe(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: Any,
    ) -> DriftWarning | None:
        if not self.enabled or tool_name not in self.DETERMINISTIC_TOOLS:
            return None
        key = (tool_name, args_hash(args))
        prior = self._turn_observations.get(key)
        if prior is not None and prior != result:
            return DriftWarning(
                kind="tool_inconsistency",
                tool_name=tool_name,
                args=args,
                severity="high",
                recommendation=(
                    f"{tool_name} returned different results within the same turn. "
                    "The underlying state may have changed; re-read current state "
                    "before relying on previous output."
                ),
            )
        self._turn_observations[key] = result
        return None


def format_drift_warning(warning: DriftWarning) -> str:
    diff = json.dumps(warning.diff, indent=2, sort_keys=True) if warning.diff else "(none)"
    return (
        f"[Drift detected — {warning.kind}, severity {warning.severity}]\n"
        f"{warning.recommendation}\n"
        f"Diff: {diff}\n"
        "Acknowledge this warning in your next response and adjust accordingly."
    )


def _shape_hash(shape: Any) -> str:
    encoded = json.dumps(shape, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _diff_shapes(prior: Any, new: Any, path: str = "$") -> dict[str, Any]:
    diff: dict[str, list[dict[str, Any]]] = {
        "missing": [],
        "added": [],
        "type_changes": [],
    }
    _collect_diff(prior, new, path, diff)
    return {key: value for key, value in diff.items() if value}


def _collect_diff(
    prior: Any,
    new: Any,
    path: str,
    diff: dict[str, list[dict[str, Any]]],
) -> None:
    if isinstance(prior, dict) and isinstance(new, dict):
        prior_keys = set(prior)
        new_keys = set(new)
        for key in sorted(prior_keys - new_keys):
            diff["missing"].append({"path": f"{path}.{key}", "prior": prior[key]})
        for key in sorted(new_keys - prior_keys):
            diff["added"].append({"path": f"{path}.{key}", "new": new[key]})
        for key in sorted(prior_keys & new_keys):
            _collect_diff(prior[key], new[key], f"{path}.{key}", diff)
        return
    if isinstance(prior, list) and isinstance(new, list):
        if prior and new:
            _collect_diff(prior[0], new[0], f"{path}[]", diff)
        elif prior != new:
            diff["type_changes"].append({"path": path, "prior": prior, "new": new})
        return
    if prior != new:
        diff["type_changes"].append({"path": path, "prior": prior, "new": new})
