"""TeamEvalDashboard — offline and live metrics from canonical orchestration events.

Offline usage (reads stored events):
    dashboard = TeamEvalDashboard(event_sink)
    metrics = dashboard.compute(session_id="s1")

Live usage (subscribes to event stream):
    collector = LiveEvalCollector()
    # ... on each event:
    collector.on_event(event)
    print(collector.metrics.to_json())
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from autocode.agent.events import SqliteEventSink


@dataclass
class TeamEvalMetrics:
    """Computed metrics for a session or time window."""

    routing_accuracy: float = 0.0
    delegation_usefulness: float = 0.0
    budget_adherence: float = 0.0
    team_coordination_score: float = 0.0
    task_completion_rate: float = 0.0
    avg_task_duration_ms: float = 0.0
    escalation_rate: float = 0.0
    subagent_success_rate: float = 0.0
    messages_per_task: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "routing_accuracy": self.routing_accuracy,
            "delegation_usefulness": self.delegation_usefulness,
            "budget_adherence": self.budget_adherence,
            "team_coordination_score": self.team_coordination_score,
            "task_completion_rate": self.task_completion_rate,
            "avg_task_duration_ms": self.avg_task_duration_ms,
            "escalation_rate": self.escalation_rate,
            "subagent_success_rate": self.subagent_success_rate,
            "messages_per_task": self.messages_per_task,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class TeamEvalDashboard:
    """Consumes canonical orchestration events and computes team metrics.

    Works offline: reads stored events from SqliteEventSink.
    """

    def __init__(self, event_sink: SqliteEventSink) -> None:
        self._sink = event_sink

    def compute(self, session_id: str) -> TeamEvalMetrics:
        """Compute all metrics for a session."""
        return TeamEvalMetrics(
            task_completion_rate=self._task_completion_rate(session_id),
            subagent_success_rate=self._subagent_success_rate(session_id),
            messages_per_task=self._messages_per_task(session_id),
            escalation_rate=self._escalation_rate(session_id),
            routing_accuracy=self._routing_accuracy(session_id),
        )

    def export_json(self, session_id: str) -> str:
        """Export metrics as JSON string."""
        return self.compute(session_id).to_json()

    # ── Individual Metric Calculators ──

    def _task_completion_rate(self, session_id: str) -> float:
        """Fraction of created tasks that completed successfully."""
        created = self._sink.count(session_id=session_id, event_type="task_created")
        if created == 0:
            return 0.0
        completed = self._sink.count(session_id=session_id, event_type="task_completed")
        return completed / created

    def _subagent_success_rate(self, session_id: str) -> float:
        """Fraction of spawned subagents that completed (vs failed/cancelled)."""
        spawned = self._sink.count(session_id=session_id, event_type="subagent_spawned")
        if spawned == 0:
            return 0.0
        completed = self._sink.count(
            session_id=session_id, event_type="subagent_completed",
        )
        return completed / spawned

    def _messages_per_task(self, session_id: str) -> float:
        """Average number of messages per task."""
        tasks = self._sink.count(session_id=session_id, event_type="task_created")
        if tasks == 0:
            return 0.0
        messages = self._sink.count(session_id=session_id, event_type="message_sent")
        return messages / tasks

    def _escalation_rate(self, session_id: str) -> float:
        """Fraction of created tasks that were escalated."""
        created = self._sink.count(session_id=session_id, event_type="task_created")
        if created == 0:
            return 0.0
        escalated = self._sink.count(
            session_id=session_id, event_type="task_escalated",
        )
        return escalated / created

    def _routing_accuracy(self, session_id: str) -> float:
        """Fraction of routed tasks where the chosen layer matched resolution.

        Compares TASK_ROUTED payload.layer against TASK_COMPLETED
        payload.resolution_layer for tasks that have both events.
        """
        routed = self._sink.query(
            session_id=session_id, event_type="task_routed", limit=1000,
        )
        completed = self._sink.query(
            session_id=session_id, event_type="task_completed", limit=1000,
        )

        if not routed:
            return 0.0

        # Build task_id → resolution_layer map from completed events
        resolution_map: dict[str, str] = {}
        for event in completed:
            payload = json.loads(event.get("payload", "{}"))
            tid = event.get("task_id", "")
            if tid and "resolution_layer" in payload:
                resolution_map[tid] = payload["resolution_layer"]

        if not resolution_map:
            return 0.0

        correct = 0
        compared = 0
        for event in routed:
            payload = json.loads(event.get("payload", "{}"))
            tid = event.get("task_id", "")
            if tid in resolution_map:
                compared += 1
                if payload.get("layer") == resolution_map[tid]:
                    correct += 1

        return correct / compared if compared > 0 else 0.0


class LiveEvalCollector:
    """Subscribes to live orchestration events and updates running metrics.

    Unlike TeamEvalDashboard (which reads stored events), this collector
    maintains in-memory counters updated incrementally on each event.

    Usage:
        collector = LiveEvalCollector()
        collector.on_event(event)  # call for each event
        print(collector.metrics)   # current metrics snapshot
    """

    def __init__(self) -> None:
        self._tasks_created = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._tasks_escalated = 0
        self._subagents_spawned = 0
        self._subagents_completed = 0
        self._subagents_failed = 0
        self._messages_sent = 0

    def on_event(self, event: OrchestratorEvent) -> None:
        """Process a single event and update counters."""
        from autocode.agent.events import EventType

        et = event.event_type
        if et == EventType.TASK_CREATED:
            self._tasks_created += 1
        elif et == EventType.TASK_COMPLETED:
            self._tasks_completed += 1
        elif et == EventType.TASK_FAILED:
            self._tasks_failed += 1
        elif et == EventType.TASK_ESCALATED:
            self._tasks_escalated += 1
        elif et == EventType.SUBAGENT_SPAWNED:
            self._subagents_spawned += 1
        elif et == EventType.SUBAGENT_COMPLETED:
            self._subagents_completed += 1
        elif et == EventType.SUBAGENT_FAILED:
            self._subagents_failed += 1
        elif et == EventType.MESSAGE_SENT:
            self._messages_sent += 1

    @property
    def metrics(self) -> TeamEvalMetrics:
        """Current metrics snapshot computed from running counters."""
        tc_rate = (
            self._tasks_completed / self._tasks_created
            if self._tasks_created > 0
            else 0.0
        )
        sa_rate = (
            self._subagents_completed / self._subagents_spawned
            if self._subagents_spawned > 0
            else 0.0
        )
        msg_per_task = (
            self._messages_sent / self._tasks_created
            if self._tasks_created > 0
            else 0.0
        )
        esc_rate = (
            self._tasks_escalated / self._tasks_created
            if self._tasks_created > 0
            else 0.0
        )

        return TeamEvalMetrics(
            task_completion_rate=tc_rate,
            subagent_success_rate=sa_rate,
            messages_per_task=msg_per_task,
            escalation_rate=esc_rate,
        )

    def reset(self) -> None:
        """Reset all counters."""
        self._tasks_created = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._tasks_escalated = 0
        self._subagents_spawned = 0
        self._subagents_completed = 0
        self._subagents_failed = 0
        self._messages_sent = 0
