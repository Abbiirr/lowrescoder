"""Tests for eval harness: scenario format, metrics, harness runner."""

from __future__ import annotations

from autocode.eval.harness import (
    ContextStrategy,
    CuratedContext,
    EvalHarness,
    EvalScenario,
    compute_metrics,
)


def test_compute_metrics_perfect() -> None:
    """Perfect match: precision=1, recall=1, F1=1."""
    p, r, f1 = compute_metrics(["a.py", "b.py"], ["a.py", "b.py"])
    assert p == 1.0
    assert r == 1.0
    assert f1 == 1.0


def test_compute_metrics_partial() -> None:
    """Partial match gives correct precision/recall."""
    p, r, f1 = compute_metrics(["a.py", "b.py", "c.py"], ["a.py", "b.py"])
    assert p == 2 / 3  # 2 relevant out of 3 returned
    assert r == 1.0  # all gold files found
    assert f1 >= 0.8


def test_compute_metrics_empty() -> None:
    """Empty inputs handled gracefully."""
    p, r, f1 = compute_metrics([], ["a.py"])
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0

    p2, r2, f12 = compute_metrics([], [])
    assert p2 == 1.0  # vacuously true


def test_eval_scenario_creation() -> None:
    """EvalScenario holds all required fields."""
    scenario = EvalScenario(
        id="bugfix-001",
        task_type="bug_fix",
        input_description="Fix the null pointer exception in UserService",
        gold_files=["src/user_service.py", "src/database.py"],
        gold_symbols=["UserService.get_user", "Database.query"],
    )
    assert scenario.id == "bugfix-001"
    assert len(scenario.gold_files) == 2


def test_eval_harness_runs() -> None:
    """Harness runs scenarios against strategies and produces report."""
    scenarios = [
        EvalScenario(
            id="test-1",
            task_type="bug_fix",
            input_description="Fix bug",
            gold_files=["a.py", "b.py"],
        ),
    ]

    # Perfect strategy
    perfect = ContextStrategy(
        name="perfect",
        curate=lambda s: CuratedContext(files=s.gold_files, token_count=100),
    )
    # Empty strategy
    empty = ContextStrategy(
        name="empty",
        curate=lambda s: CuratedContext(files=[], token_count=0),
    )

    harness = EvalHarness()
    report = harness.run(scenarios, [perfect, empty])

    assert len(report.results) == 2
    assert report.results[0].f1 == 1.0  # perfect
    assert report.results[0].passed  # F1 >= 0.65
    assert report.results[1].f1 == 0.0  # empty
    assert not report.results[1].passed


def test_eval_report_pass_rate() -> None:
    """Report calculates overall pass rate."""
    scenarios = [
        EvalScenario(id=f"t-{i}", task_type="bug_fix", input_description="fix", gold_files=["a.py"])
        for i in range(4)
    ]

    # Strategy that returns the right file
    good = ContextStrategy(
        name="good",
        curate=lambda s: CuratedContext(files=["a.py"], token_count=50),
    )

    harness = EvalHarness()
    report = harness.run(scenarios, [good])

    assert report.pass_rate == 1.0
    assert report.strategy_summaries["good"]["avg_f1"] == 1.0


def test_eval_report_strategy_summaries() -> None:
    """Report tracks per-strategy averages."""
    scenarios = [
        EvalScenario(id="s1", task_type="bug_fix", input_description="fix", gold_files=["a.py", "b.py"]),
    ]

    partial = ContextStrategy(
        name="partial",
        curate=lambda s: CuratedContext(files=["a.py"], token_count=200),
    )

    harness = EvalHarness()
    report = harness.run(scenarios, [partial])

    summary = report.strategy_summaries["partial"]
    assert summary["avg_recall"] == 0.5  # found 1 of 2
    assert summary["avg_precision"] == 1.0  # 1 returned, 1 relevant
    assert summary["count"] == 1
