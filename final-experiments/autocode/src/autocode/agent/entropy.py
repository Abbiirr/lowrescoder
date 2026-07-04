"""Entropy audit primitives for conversation consistency checks."""

from __future__ import annotations

import inspect
import json
import os
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EntropySeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EntropyKind(StrEnum):
    NAMING_DRIFT = "naming_drift"
    DECISION_REVERSAL = "decision_reversal"
    STALE_REFERENCE = "stale_reference"
    FACT_CONFLICT = "fact_conflict"


ENTROPY_AUDIT_PROMPT = """\
You are an entropy auditor for an AI coding agent's conversation. Look at
the last 20 messages and identify INCONSISTENCIES.

Examples of entropy:
- Variable names that drift between mentions (state_token in turn 3, stateToken in turn 7)
- Decisions reversed without acknowledgment (turn 4: "use JWT" / turn 11: "use cookies")
- File paths that don't exist (mentioned `src/oauth.py` but it's actually `src/auth/oauth.py`)
- Tool results from older turns that describe state that's since changed
- Conflicting facts (turn 2: "test passes" / turn 9: same test failing without explanation)

Output JSON:
{{
  "incidents": [
    {{
      "severity": "low" | "medium" | "high",
      "kind": "naming_drift" | "decision_reversal" | "stale_reference" | "fact_conflict",
      "description": "one sentence",
      "evidence": "quote or message id"
    }}
  ],
  "recommendation": "what to do" | null
}}

Conversation excerpt:
{messages}
"""


EntropyExecutor = Callable[[str], str | Mapping[str, Any] | Awaitable[str | Mapping[str, Any]]]
TelemetryEmit = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True, slots=True)
class EntropyIncident:
    severity: EntropySeverity
    kind: EntropyKind
    description: str
    evidence: str = ""


@dataclass(frozen=True, slots=True)
class EntropyReport:
    incidents: list[EntropyIncident] = field(default_factory=list)
    recommendation: str | None = None
    raw_response: str = ""

    @property
    def severity_max(self) -> EntropySeverity | None:
        if not self.incidents:
            return None
        order = {
            EntropySeverity.LOW: 1,
            EntropySeverity.MEDIUM: 2,
            EntropySeverity.HIGH: 3,
        }
        return max((incident.severity for incident in self.incidents), key=order.get)

    @property
    def should_inject_warning(self) -> bool:
        return self.severity_max in {EntropySeverity.MEDIUM, EntropySeverity.HIGH}

    def warning_message(self) -> str | None:
        severity = self.severity_max
        if severity is None or not self.should_inject_warning:
            return None
        recommendation = self.recommendation or "Review the recent context for contradictions."
        if severity == EntropySeverity.HIGH:
            recommendation += " Consider rollback to the last known-good checkpoint."
        return (
            f"[Entropy audit warning — {severity.value}] "
            f"{len(self.incidents)} consistency issue(s) detected. {recommendation}"
        )


class EntropyAuditor:
    """Run periodic conversation entropy audits through a caller-provided executor."""

    AUDIT_INTERVAL_TURNS = 10
    MAX_MESSAGES_AUDITED = 20

    def __init__(
        self,
        executor: EntropyExecutor,
        *,
        telemetry_emit: TelemetryEmit | None = None,
        audit_interval_turns: int | None = None,
        max_messages_audited: int | None = None,
    ) -> None:
        self.executor = executor
        self.telemetry_emit = telemetry_emit
        self.audit_interval_turns = audit_interval_turns or self.AUDIT_INTERVAL_TURNS
        self.max_messages_audited = max_messages_audited or self.MAX_MESSAGES_AUDITED
        self._last_audit_turn = 0

    async def maybe_audit(
        self,
        current_turn: int,
        messages: Sequence[Mapping[str, Any]],
        *,
        cost_cap_reached: bool = False,
    ) -> EntropyReport | None:
        """Run an audit at the configured cadence and return a parsed report."""

        if cost_cap_reached:
            return None
        audit_interval = self.audit_interval_turns
        if "AUDIT_INTERVAL_TURNS" in self.__dict__:
            # Backwards-compatible test and caller hook: older code adjusted the
            # instance constant directly after construction.
            audit_interval = int(self.__dict__["AUDIT_INTERVAL_TURNS"])
        if current_turn - self._last_audit_turn < audit_interval:
            return None

        prompt = ENTROPY_AUDIT_PROMPT.format(
            messages=self._format_messages(messages[-self.max_messages_audited:]),
        )
        raw = self.executor(prompt)
        if inspect.isawaitable(raw):
            raw = await raw
        self._last_audit_turn = current_turn
        report = self.parse_response(raw)
        if self.telemetry_emit is not None:
            self.telemetry_emit(
                "entropy_audit_completed",
                {
                    "severity_max": report.severity_max.value
                    if report.severity_max else "none",
                    "incident_count": len(report.incidents),
                },
            )
        return report

    @staticmethod
    def parse_response(response: str | Mapping[str, Any]) -> EntropyReport:
        """Parse auditor JSON into a structured report."""

        raw_response = response if isinstance(response, str) else json.dumps(response)
        try:
            parsed = json.loads(response) if isinstance(response, str) else dict(response)
        except json.JSONDecodeError:
            return EntropyReport(
                incidents=[
                    EntropyIncident(
                        severity=EntropySeverity.MEDIUM,
                        kind=EntropyKind.FACT_CONFLICT,
                        description="Entropy auditor returned invalid JSON.",
                        evidence=raw_response,
                    )
                ],
                recommendation="Retry entropy audit or inspect recent context manually.",
                raw_response=raw_response,
            )

        if not isinstance(parsed, Mapping):
            return EntropyReport(raw_response=raw_response)

        incidents: list[EntropyIncident] = []
        for item in parsed.get("incidents", []):
            if not isinstance(item, Mapping):
                continue
            try:
                severity = EntropySeverity(str(item.get("severity", "low")).lower())
                kind = EntropyKind(str(item.get("kind", "fact_conflict")).lower())
            except ValueError:
                continue
            description = str(item.get("description") or "").strip()
            if not description:
                continue
            incidents.append(
                EntropyIncident(
                    severity=severity,
                    kind=kind,
                    description=description,
                    evidence=str(item.get("evidence") or ""),
                )
            )

        recommendation_raw = parsed.get("recommendation")
        recommendation = (
            str(recommendation_raw).strip()
            if recommendation_raw is not None and str(recommendation_raw).strip()
            else None
        )
        return EntropyReport(
            incidents=incidents,
            recommendation=recommendation,
            raw_response=raw_response,
        )

    @staticmethod
    def _format_messages(messages: Sequence[Mapping[str, Any]]) -> str:
        lines: list[str] = []
        for idx, message in enumerate(messages, start=1):
            role = str(message.get("role") or "unknown")
            content = str(message.get("content") or "")
            lines.append(f"{idx}. {role}: {content[:1000]}")
        return "\n".join(lines)


def entropy_disabled_by_env() -> bool:
    """Return true when the production entropy rollback flag is enabled."""

    return os.environ.get("AUTOCODE_DISABLE_ENTROPY", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_entropy_auditor(
    *,
    provider: Any,
    config: Any,
    telemetry_emit: TelemetryEmit | None = None,
) -> EntropyAuditor | None:
    """Build an opt-in provider-backed entropy auditor."""

    if not bool(getattr(config, "enabled", False)):
        return None
    if entropy_disabled_by_env():
        return None

    async def executor(prompt: str) -> str:
        response = await provider.generate_with_tools(
            [{"role": "user", "content": prompt}],
            [],
            reasoning_enabled=False,
        )
        return str(getattr(response, "content", "") or "")

    return EntropyAuditor(
        executor,
        telemetry_emit=telemetry_emit,
        audit_interval_turns=int(getattr(config, "audit_interval_turns", 10) or 10),
        max_messages_audited=int(getattr(config, "max_messages_audited", 20) or 20),
    )


def build_entropy_auditor_for_config(
    *,
    provider: Any,
    autocode_config: Any,
    create_provider_func: Callable[[Any], Any] | None = None,
    telemetry_emit: TelemetryEmit | None = None,
) -> EntropyAuditor | None:
    """Build an entropy auditor from full AutoCode config and provider wiring."""

    config = getattr(getattr(autocode_config, "agent", None), "entropy", None)
    if config is None or not bool(getattr(config, "enabled", False)):
        return None
    if entropy_disabled_by_env():
        return None

    audit_provider = provider
    model_alias = str(getattr(config, "model_alias", "") or "")
    llm_config = getattr(autocode_config, "llm", None)
    current_model = str(getattr(llm_config, "model", "") or "")
    current_provider = str(getattr(llm_config, "provider", "") or "")
    if (
        create_provider_func is not None
        and model_alias
        and model_alias != current_model
        and current_provider == "openrouter"
    ):
        config_copy = autocode_config.model_copy(deep=True)
        config_copy.llm.model = model_alias
        audit_provider = create_provider_func(config_copy)

    return build_entropy_auditor(
        provider=audit_provider,
        config=config,
        telemetry_emit=telemetry_emit,
    )
