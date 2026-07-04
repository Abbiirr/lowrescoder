"""Tests for P3d structured eval judge."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.judge import LLMJudge  # noqa: E402


def test_judge_parse_scores_validates_score_range():
    scores = LLMJudge.parse_scores(
        {
            "correctness": {
                "score": 0.75,
                "justification": "mostly correct",
                "evidence": "tests",
            }
        },
        ["correctness"],
    )

    assert scores["correctness"].score == 0.75


def test_judge_parse_scores_rejects_out_of_range_score():
    with pytest.raises(ValueError, match="out of range"):
        LLMJudge.parse_scores(
            {
                "correctness": {
                    "score": 1.5,
                    "justification": "bad",
                    "evidence": "none",
                }
            },
            ["correctness"],
        )


@pytest.mark.asyncio
async def test_judge_uses_temperature_zero_prompt():
    prompts: list[str] = []

    async def provider(prompt: str) -> str:
        prompts.append(prompt)
        return """
        {
          "correctness": {
            "score": 1.0,
            "justification": "tests passed",
            "evidence": "pytest"
          },
          "minimality": {
            "score": 0.8,
            "justification": "small diff",
            "evidence": "diff"
          }
        }
        """

    judge = LLMJudge(provider, model="strong-judge", temperature=0.0)
    scores = await judge.score(["correctness", "minimality"], diff="diff", test_output="ok")

    assert scores["minimality"].score == 0.8
    assert "Temperature: 0.0" in prompts[0]
