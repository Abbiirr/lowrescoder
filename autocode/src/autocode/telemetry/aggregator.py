"""Read and summarize local telemetry JSONL files."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from autocode.telemetry.store import telemetry_root


@dataclass(frozen=True)
class TelemetrySummary:
    total_events: int
    by_kind: dict[str, int]
    by_session: dict[str, int]


class TelemetryAggregator:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or telemetry_root()

    def events(
        self,
        *,
        kind: str | None = None,
        session_id: str | None = None,
        since: date | None = None,
    ) -> list[dict[str, Any]]:
        rows = []
        for event in self._iter_events(since=since):
            if kind and event.get("kind") != kind:
                continue
            if session_id and event.get("session_id") != session_id:
                continue
            rows.append(event)
        return rows

    def summary(self, *, since: date | None = None) -> TelemetrySummary:
        by_kind: Counter[str] = Counter()
        by_session: Counter[str] = Counter()
        total = 0

        for event in self._iter_events(since=since):
            total += 1
            by_kind[str(event.get("kind", ""))] += 1
            session_id = event.get("session_id")
            if session_id:
                by_session[str(session_id)] += 1

        return TelemetrySummary(
            total_events=total,
            by_kind=dict(by_kind),
            by_session=dict(by_session),
        )

    def drift_summary(
        self,
        *,
        since: date | None = None,
    ) -> dict[tuple[str, str, str], int]:
        """Group drift detections by tool, drift kind, and severity."""
        counts: Counter[tuple[str, str, str]] = Counter()
        for event in self.events(kind="tool_drift_detected", since=since):
            data = event.get("data") or {}
            if not isinstance(data, dict):
                data = {}
            counts[
                (
                    str(data.get("tool_name", "")),
                    str(data.get("drift_kind", "")),
                    str(data.get("severity", "")),
                )
            ] += 1
        return dict(counts)

    def export_jsonl(self, *, since: date | None = None) -> str:
        return "\n".join(json.dumps(event) for event in self._iter_events(since=since))

    def export_csv(self, *, since: date | None = None) -> str:
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["ts", "session_id", "thread_id", "turn_id", "kind", "data"])
        for event in self._iter_events(since=since):
            writer.writerow(
                [
                    event.get("ts"),
                    event.get("session_id"),
                    event.get("thread_id"),
                    event.get("turn_id"),
                    event.get("kind"),
                    json.dumps(event.get("data", {}), separators=(",", ":")),
                ]
            )
        return out.getvalue()

    def _iter_events(self, *, since: date | None = None) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        events: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("events-*.jsonl")):
            if since is not None and _path_event_date(path) < since:
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events


def since_from_window(window: str | None) -> date | None:
    """Convert CLI windows like ``7d``/``30d``/``all`` into a start date."""
    if window is None:
        return None
    value = window.strip().lower()
    if value in {"", "all"}:
        return None
    if value.endswith("d") and value[:-1].isdigit():
        days = max(0, int(value[:-1]))
        return datetime.now(UTC).date() - timedelta(days=days)
    return date.fromisoformat(value)


def _path_event_date(path: Path) -> date:
    stem = path.stem
    if stem.startswith("events-"):
        return date.fromisoformat(stem.removeprefix("events-"))
    return date.min
