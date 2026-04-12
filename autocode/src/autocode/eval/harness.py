"""Eval harness — scenario format, deterministic grader, reporter.

Evaluates context quality strategies against gold-standard task scenarios.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalScenario:
    """Single evaluation scenario with gold-standard answers."""

    id: str
    task_type: str  # "bug_fix", "feature_add", "code_review", "refactor"
    input_description: str
    gold_files: list[str]  # Expected relevant files
    gold_symbols: list[str] = field(default_factory=list)  # Expected relevant symbols
    input_files: list[str] = field(default_factory=list)  # Input context files
    expected_output: str = ""  # Expected result description
    scoring_rubric: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class CuratedContext:
    """Context curated by a strategy for a given scenario."""

    files: list[str]
    symbols: list[str] = field(default_factory=list)
    token_count: int = 0
    raw_content: str = ""


@dataclass
class ContextStrategy:
    """How to curate context for an LLM."""

    name: str  # "l1_only", "l2_only", "l1_l2", "llm_curated"
    curate: Callable[[EvalScenario], CuratedContext] = field(default=lambda s: CuratedContext(files=[]))

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class EvalResult:
    """Result of evaluating one scenario with one strategy."""

    scenario_id: str
    strategy_name: str
    precision: float  # files returned that are relevant / files returned
    recall: float  # relevant files returned / relevant files total
    f1: float
    token_count: int
    files_returned: list[str]
    files_gold: list[str]
    passed: bool = False


@dataclass
class EvalReport:
    """Aggregate evaluation report."""

    results: list[EvalResult] = field(default_factory=list)
    strategy_summaries: dict[str, dict[str, float]] = field(default_factory=dict)

    def add(self, result: EvalResult) -> None:
        """Add a result and update summaries."""
        self.results.append(result)
        name = result.strategy_name
        if name not in self.strategy_summaries:
            self.strategy_summaries[name] = {
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_f1": 0.0,
                "avg_tokens": 0.0,
                "count": 0,
            }
        s = self.strategy_summaries[name]
        n = s["count"]
        s["avg_precision"] = (s["avg_precision"] * n + result.precision) / (n + 1)
        s["avg_recall"] = (s["avg_recall"] * n + result.recall) / (n + 1)
        s["avg_f1"] = (s["avg_f1"] * n + result.f1) / (n + 1)
        s["avg_tokens"] = (s["avg_tokens"] * n + result.token_count) / (n + 1)
        s["count"] = n + 1

    @property
    def pass_rate(self) -> float:
        """Overall pass rate across all results."""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)


def compute_metrics(
    returned: list[str],
    gold: list[str],
) -> tuple[float, float, float]:
    """Compute precision, recall, and F1 for file sets."""
    if not returned and not gold:
        return 1.0, 1.0, 1.0
    if not returned:
        return 0.0, 0.0, 0.0
    if not gold:
        return 0.0, 0.0, 0.0

    returned_set = set(returned)
    gold_set = set(gold)
    true_positives = len(returned_set & gold_set)

    precision = true_positives / len(returned_set) if returned_set else 0.0
    recall = true_positives / len(gold_set) if gold_set else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return precision, recall, f1


class EvalHarness:
    """Runs context quality benchmarks.

    Tests whether L1/L2 context strategies match L4-curated quality
    at zero cost.
    """

    def run(
        self,
        scenarios: list[EvalScenario],
        strategies: list[ContextStrategy],
    ) -> EvalReport:
        """Run all scenarios against all strategies."""
        report = EvalReport()

        for scenario in scenarios:
            for strategy in strategies:
                context = strategy.curate(scenario)
                precision, recall, f1 = compute_metrics(
                    context.files, scenario.gold_files,
                )
                result = EvalResult(
                    scenario_id=scenario.id,
                    strategy_name=strategy.name,
                    precision=precision,
                    recall=recall,
                    f1=f1,
                    token_count=context.token_count,
                    files_returned=context.files,
                    files_gold=scenario.gold_files,
                    passed=f1 >= 0.65,  # M2 gate threshold
                )
                report.add(result)

        return report
