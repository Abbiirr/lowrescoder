"""Infrastructure classifier for AI verification harness.

Detects harness/provider failures that should be classified as INFRA_FAIL
rather than agent FAIL: empty turns, rate-limit/429 errors, per-turn
timeouts, whole-scenario timeouts, sandbox setup failures, and
grading-command execution failures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class InfraClassification:
    is_infra_fail: bool
    reason: str = ""
    signals: list[str] = field(default_factory=list)


_RATE_LIMIT_PATTERNS = (
    "429",
    "rate limit",
    "rate_limit",
    "too many requests",
    "quota exceeded",
    "resource exhausted",
    "capacity",
    "blocked http",
    "read timeout",
    "connection timeout",
    "timed out",
    "timeouterror",
    "gateway",
    "service unavailable",
    "503",
    "502",
    "internal server error",
    "empty response",
)

_SANDBOX_FAILURE_PATTERNS = (
    "sandbox",
    "permission denied",
    "could not resolve",
    "executable not found",
    "command not found",
)

_GRADING_COMMAND_SETUP_PATTERNS = (
    "can't open file",
    "no such file or directory",
)

_MISSING_DEPENDENCY_PATTERNS = (
    "modulenotfounderror: no module named",
    "importerror: no module named",
)

_KNOWN_GRADING_DEPENDENCY_MODULES = {
    "playwright",
    "selenium",
}


def classify_infra(
    *,
    events: list[dict[str, Any]] | None = None,
    error: str = "",
    turn_count: int = 0,
    max_turns: int = 0,
    check_output: str = "",
    transcript_lines: list[str] | None = None,
) -> InfraClassification:
    signals: list[str] = []
    reasons: list[str] = []

    if _has_rate_limit_signals(events or [], error):
        signals.append("rate_limit_detected")
        reasons.append("provider rate limit or gateway error detected")

    if _has_empty_turn(events or [], turn_count):
        signals.append("empty_turn")
        reasons.append("empty turn: no tool events, no assistant message, zero usage")

    if _has_timeout(error, events or []):
        signals.append("timeout")
        reasons.append("agent or turn timeout detected")

    if _has_sandbox_failure(error):
        signals.append("sandbox_failure")
        reasons.append("sandbox setup or execution environment failure")

    if _has_grading_command_setup_failure(check_output):
        signals.append("grading_command_failure")
        reasons.append("grading command itself could not start — setup error, not agent-caused")

    if _has_missing_dependency_failure(check_output):
        signals.append("missing_dependency")
        reasons.append("grading dependency missing — environment setup error, not agent-caused")

    if signals:
        return InfraClassification(
            is_infra_fail=True,
            reason="; ".join(reasons),
            signals=signals,
        )

    return InfraClassification(is_infra_fail=False)


def _has_rate_limit_signals(events: list[dict], error: str) -> bool:
    combined = error.lower()
    for event in events:
        if event.get("type") == "error":
            combined += " " + (event.get("message", "") or "").lower()
    for pattern in _RATE_LIMIT_PATTERNS:
        if pattern in combined:
            return True
    return False


def _has_empty_turn(events: list[dict], turn_count: int) -> bool:
    if turn_count > 0:
        return False
    has_tool = any(
        e.get("type") in ("tool_call_completed", "tool_call_failed")
        or (e.get("type") == "item_started" and e.get("kind") == "tool_execution")
        for e in events
    )
    has_message = any(
        e.get("type") == "item_started" and e.get("kind") == "agent_message"
        for e in events
    )
    has_usage = any(
        e.get("type") == "turn_completed" and e.get("usage", {}).get("output_tokens", 0) > 0
        for e in events
    )
    return not (has_tool or has_message or has_usage)


def _has_timeout(error: str, events: list[dict]) -> bool:
    if "timeout" in error.lower():
        return True
    if "timed out" in error.lower():
        return True
    for event in events:
        if event.get("type") == "error" and "timeout" in (event.get("message", "") or "").lower():
            return True
    return False


def _has_sandbox_failure(error: str) -> bool:
    lower = error.lower()
    for pattern in _SANDBOX_FAILURE_PATTERNS:
        if pattern in lower:
            return True
    return False


def _has_grading_command_setup_failure(check_output: str) -> bool:
    lines = check_output.strip().splitlines()
    if not lines:
        return False
    first_line = lines[0].lower()
    for pattern in _GRADING_COMMAND_SETUP_PATTERNS:
        if pattern in first_line:
            return True
    return False


def _has_missing_dependency_failure(check_output: str) -> bool:
    lower = check_output.lower()
    if not lower.strip():
        return False
    if not any(pattern in lower for pattern in _MISSING_DEPENDENCY_PATTERNS):
        return False
    missing_modules = {
        match.group("module").split(".")[0]
        for match in re.finditer(
            r"(?:modulenotfounderror|importerror):\s+no module named ['\"]?(?P<module>[a-zA-Z0-9_.-]+)",
            lower,
        )
    }
    return bool(missing_modules & _KNOWN_GRADING_DEPENDENCY_MODULES)
