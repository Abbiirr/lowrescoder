"""Verification gate and evidence tracking for the AutoCode harness.

Provides:
- VerifyResult: structured verification evidence
- Hard verification gate middleware
- verify.json parsing
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    command: str
    exit_code: int
    duration_ms: int = 0
    summary: str = ""

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


@dataclass
class VerifyResult:
    """Structured verification evidence from verify.json."""

    timestamp: str = ""
    checks: list[CheckResult] = field(default_factory=list)
    all_passed: bool = False
    total_duration_ms: int = 0

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> VerifyResult:
        checks = [
            CheckResult(
                name=c.get("name", ""),
                command=c.get("command", ""),
                exit_code=c.get("exit_code", 1),
                duration_ms=c.get("duration_ms", 0),
                summary=c.get("summary", ""),
            )
            for c in data.get("checks", [])
        ]
        return cls(
            timestamp=data.get("timestamp", ""),
            checks=checks,
            all_passed=data.get("all_passed", False),
            total_duration_ms=data.get("total_duration_ms", 0),
        )

    @classmethod
    def from_file(cls, path: Path) -> VerifyResult | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_json(data)
        except (json.JSONDecodeError, OSError):
            return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "checks": [
                {
                    "name": c.name,
                    "command": c.command,
                    "exit_code": c.exit_code,
                    "duration_ms": c.duration_ms,
                    "summary": c.summary,
                }
                for c in self.checks
            ],
            "all_passed": self.all_passed,
            "total_duration_ms": self.total_duration_ms,
        }


VERIFY_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["checks", "all_passed"],
    "properties": {
        "timestamp": {"type": "string"},
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "command", "exit_code"],
                "properties": {
                    "name": {"type": "string"},
                    "command": {"type": "string"},
                    "exit_code": {"type": "integer"},
                    "duration_ms": {"type": "integer"},
                    "summary": {"type": "string"},
                },
            },
        },
        "all_passed": {"type": "boolean"},
        "total_duration_ms": {"type": "integer"},
    },
}


class VerificationEvidence:
    """Tracks verification state during an agent session."""

    def __init__(self) -> None:
        self._needed: bool = False
        self._satisfied: bool = False
        self._result: VerifyResult | None = None
        self._retries: int = 0
        self._max_retries: int = 3

    @property
    def needed(self) -> bool:
        return self._needed

    @property
    def satisfied(self) -> bool:
        return self._satisfied

    @property
    def result(self) -> VerifyResult | None:
        return self._result

    def mark_needed(self) -> None:
        self._needed = True
        self._satisfied = False

    def submit_evidence(self, result: VerifyResult) -> None:
        self._result = result
        if result.all_passed:
            self._satisfied = True

    def record_retry(self) -> bool:
        """Record a retry attempt. Returns True if more retries allowed."""
        self._retries += 1
        return self._retries <= self._max_retries

    def should_block_completion(self) -> bool:
        """Returns True if completion should be blocked."""
        if not self._needed:
            return False
        if self._satisfied:
            return False
        return self._retries <= self._max_retries
