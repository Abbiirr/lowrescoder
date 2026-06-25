"""Structured LLM-judge parsing for eval cases."""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


JudgeProvider = Callable[[str], str | Mapping[str, Any] | Awaitable[str | Mapping[str, Any]]]


@dataclass(frozen=True, slots=True)
class CriterionScore:
    """One criterion score returned by the judge."""

    score: float
    justification: str
    evidence: str


class LLMJudge:
    """LLM-as-judge wrapper with strict structured-output validation."""

    def __init__(
        self,
        provider: JudgeProvider | None = None,
        *,
        model: str = "coding-judge",
        temperature: float = 0.0,
    ) -> None:
        self.provider = provider
        self.model = model
        self.temperature = temperature

    async def score(
        self,
        criteria: Sequence[str],
        *,
        diff: str = "",
        test_output: str = "",
        final_response: str = "",
    ) -> dict[str, CriterionScore]:
        """Score criteria using the provider and validate the structured JSON."""

        if self.provider is None:
            return {
                criterion: CriterionScore(
                    score=1.0,
                    justification="No judge provider configured; deterministic pass placeholder.",
                    evidence="provider_unconfigured",
                )
                for criterion in criteria
            }
        prompt = self._build_prompt(criteria, diff, test_output, final_response)
        raw = self.provider(prompt)
        if inspect.isawaitable(raw):
            raw = await raw
        return self.parse_scores(raw, criteria)

    @staticmethod
    def parse_scores(
        raw: str | Mapping[str, Any],
        criteria: Sequence[str],
    ) -> dict[str, CriterionScore]:
        """Parse and validate judge JSON."""

        try:
            parsed = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Judge response must be valid JSON") from exc
        if not isinstance(parsed, Mapping):
            raise ValueError("Judge response must be a JSON object")

        scores: dict[str, CriterionScore] = {}
        for criterion in criteria:
            item = parsed.get(criterion)
            if not isinstance(item, Mapping):
                raise ValueError(f"Judge response missing criterion: {criterion}")
            score = float(item.get("score", -1.0))
            if score < 0.0 or score > 1.0:
                raise ValueError(f"Judge score out of range for {criterion}: {score}")
            scores[criterion] = CriterionScore(
                score=score,
                justification=str(item.get("justification") or ""),
                evidence=str(item.get("evidence") or ""),
            )
        return scores

    def _build_prompt(
        self,
        criteria: Sequence[str],
        diff: str,
        test_output: str,
        final_response: str,
    ) -> str:
        criteria_json = json.dumps(list(criteria))
        return (
            "You are an AutoCode eval judge. Return only JSON with one object "
            "per criterion. Each criterion object must contain score "
            "(0.0-1.0), justification, and evidence.\n"
            f"Model: {self.model}\n"
            f"Temperature: {self.temperature}\n"
            f"Criteria: {criteria_json}\n\n"
            f"Diff:\n{diff}\n\n"
            f"Test output:\n{test_output}\n\n"
            f"Final response:\n{final_response}\n"
        )


__all__ = ["CriterionScore", "LLMJudge"]

