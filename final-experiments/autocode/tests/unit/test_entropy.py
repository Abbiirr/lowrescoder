import pytest

from autocode.agent.entropy import (
    ENTROPY_AUDIT_PROMPT,
    EntropyAuditor,
    EntropyKind,
    EntropySeverity,
    build_entropy_auditor,
)
from autocode.agent.prompts import STABLE_INSTRUCTIONS
from autocode.config import EntropyAuditConfig
from autocode.layer4.llm import LLMResponse


@pytest.mark.asyncio
async def test_entropy_audit_detects_naming_drift_and_emits_telemetry() -> None:
    prompts: list[str] = []
    events: list[tuple[str, dict]] = []

    async def executor(prompt: str) -> str:
        prompts.append(prompt)
        return """
        {
          "incidents": [
            {
              "severity": "high",
              "kind": "naming_drift",
              "description": "state_token and stateToken are both used for the same value.",
              "evidence": "messages 1 and 2"
            }
          ],
          "recommendation": "Pick one spelling before editing."
        }
        """

    auditor = EntropyAuditor(executor, telemetry_emit=lambda k, d: events.append((k, d)))
    report = await auditor.maybe_audit(
        10,
        [
            {"role": "user", "content": "Add state_token to the cookie"},
            {"role": "assistant", "content": "I'll add stateToken to the auth flow"},
        ],
    )

    assert report is not None
    assert prompts and "state_token" in prompts[0]
    assert report.incidents[0].severity == EntropySeverity.HIGH
    assert report.incidents[0].kind == EntropyKind.NAMING_DRIFT
    assert "rollback" in (report.warning_message() or "").lower()
    assert events == [
        (
            "entropy_audit_completed",
            {"severity_max": "high", "incident_count": 1},
        )
    ]


@pytest.mark.asyncio
async def test_entropy_audit_cadence_and_message_window() -> None:
    calls: list[str] = []

    async def executor(prompt: str) -> str:
        calls.append(prompt)
        return {"incidents": [], "recommendation": None}

    auditor = EntropyAuditor(executor)
    assert await auditor.maybe_audit(9, [{"role": "user", "content": "early"}]) is None

    messages = [{"role": "user", "content": f"message {idx}"} for idx in range(25)]
    report = await auditor.maybe_audit(10, messages)

    assert report is not None
    assert len(calls) == 1
    assert "message 5" in calls[0]
    assert "message 4" not in calls[0]
    assert await auditor.maybe_audit(19, messages) is None


@pytest.mark.asyncio
async def test_entropy_audit_skips_when_cost_cap_reached() -> None:
    calls = 0

    async def executor(prompt: str) -> str:
        nonlocal calls
        calls += 1
        return {"incidents": [], "recommendation": None}

    auditor = EntropyAuditor(executor)

    assert await auditor.maybe_audit(10, [], cost_cap_reached=True) is None
    assert calls == 0


def test_entropy_auditor_parses_decision_reversal() -> None:
    report = EntropyAuditor.parse_response(
        {
            "incidents": [
                {
                    "severity": "medium",
                    "kind": "decision_reversal",
                    "description": (
                        "The plan changed from JWT to cookies without acknowledging the reversal."
                    ),
                    "evidence": "turns 4 and 11",
                }
            ],
            "recommendation": "State why the recommendation changed before continuing.",
        }
    )

    assert report.incidents[0].severity == EntropySeverity.MEDIUM
    assert report.incidents[0].kind == EntropyKind.DECISION_REVERSAL
    assert report.should_inject_warning


def test_entropy_auditor_malformed_response_returns_medium_incident() -> None:
    report = EntropyAuditor.parse_response("not json")

    assert report.incidents[0].severity == EntropySeverity.MEDIUM
    assert report.incidents[0].kind == EntropyKind.FACT_CONFLICT
    assert report.should_inject_warning


def test_anti_entropy_prompt_is_in_stable_instructions() -> None:
    assert "## Internal consistency" in STABLE_INSTRUCTIONS
    assert "do not reverse it" in STABLE_INSTRUCTIONS.lower()
    assert "Output JSON" in ENTROPY_AUDIT_PROMPT


def test_entropy_audit_config_defaults_to_disabled() -> None:
    config = EntropyAuditConfig()

    assert config.enabled is False
    assert config.model_alias == "coding"
    assert config.audit_interval_turns == 10
    assert config.max_messages_audited == 20


def test_build_entropy_auditor_returns_none_when_disabled() -> None:
    auditor = build_entropy_auditor(
        provider=object(),
        config=EntropyAuditConfig(enabled=False),
    )

    assert auditor is None


def test_build_entropy_auditor_honors_disable_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTOCODE_DISABLE_ENTROPY", "true")

    auditor = build_entropy_auditor(
        provider=object(),
        config=EntropyAuditConfig(enabled=True),
    )

    assert auditor is None


@pytest.mark.asyncio
async def test_build_entropy_auditor_wraps_provider_with_configured_limits() -> None:
    class FakeProvider:
        def __init__(self) -> None:
            self.messages: list[dict] | None = None
            self.reasoning_enabled: bool | None = None

        async def generate_with_tools(
            self,
            messages: list[dict],
            tools: list[dict],
            *,
            reasoning_enabled: bool = True,
            **_: object,
        ) -> LLMResponse:
            assert tools == []
            self.messages = messages
            self.reasoning_enabled = reasoning_enabled
            return LLMResponse(
                content=(
                    '{"incidents":[{"severity":"medium","kind":"fact_conflict",'
                    '"description":"turns disagree","evidence":"turn 2"}],'
                    '"recommendation":"Inspect recent context."}'
                )
            )

    provider = FakeProvider()
    events: list[tuple[str, dict]] = []
    auditor = build_entropy_auditor(
        provider=provider,
        config=EntropyAuditConfig(
            enabled=True,
            audit_interval_turns=3,
            max_messages_audited=2,
        ),
        telemetry_emit=lambda kind, data: events.append((kind, data)),
    )

    assert auditor is not None
    report = await auditor.maybe_audit(
        3,
        [
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "new-a"},
            {"role": "assistant", "content": "new-b"},
        ],
    )

    assert report is not None
    assert report.severity_max == EntropySeverity.MEDIUM
    assert provider.reasoning_enabled is False
    assert provider.messages is not None
    assert provider.messages[0]["role"] == "user"
    assert "user: old" not in provider.messages[0]["content"]
    assert "new-a" in provider.messages[0]["content"]
    assert "new-b" in provider.messages[0]["content"]
    assert events == [
        (
            "entropy_audit_completed",
            {"severity_max": "medium", "incident_count": 1},
        )
    ]
