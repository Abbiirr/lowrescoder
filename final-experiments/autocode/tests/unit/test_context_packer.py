"""Tests for context packer strategies."""

from __future__ import annotations

from autocode.eval.context_packer import (
    ALL_STRATEGIES,
    L1_L2_STRATEGY,
    L1_STRATEGY,
    L2_STRATEGY,
    LLM_STRATEGY,
)
from autocode.eval.harness import EvalHarness, EvalScenario


def _make_scenario() -> EvalScenario:
    return EvalScenario(
        id="test-bugfix",
        task_type="bug_fix",
        input_description="Fix the user service database query",
        gold_files=["src/user_service.py", "src/database.py"],
        gold_symbols=["UserService.get_user", "Database.query"],
    )


def test_l1_strategy_uses_symbols() -> None:
    """L1 strategy finds files via symbol matching."""
    scenario = _make_scenario()
    result = L1_STRATEGY.curate(scenario)
    # Should find files matching symbol names
    assert isinstance(result.files, list)
    assert result.token_count >= 0


def test_l2_strategy_uses_keywords() -> None:
    """L2 strategy finds files via description keyword matching."""
    scenario = _make_scenario()
    result = L2_STRATEGY.curate(scenario)
    assert isinstance(result.files, list)
    # "database" is in description and in filename
    assert "src/database.py" in result.files


def test_l1_l2_union() -> None:
    """L1+L2 returns union of both, no duplicates."""
    scenario = _make_scenario()
    result = L1_L2_STRATEGY.curate(scenario)
    assert len(result.files) == len(set(result.files))  # no dupes


def test_llm_strategy_returns_gold() -> None:
    """LLM strategy returns all gold files (simulated best case)."""
    scenario = _make_scenario()
    result = LLM_STRATEGY.curate(scenario)
    assert set(result.files) == set(scenario.gold_files)
    assert result.token_count > L1_STRATEGY.curate(scenario).token_count


def test_all_strategies_exist() -> None:
    """ALL_STRATEGIES has 4 strategies."""
    assert len(ALL_STRATEGIES) == 4
    names = {s.name for s in ALL_STRATEGIES}
    assert names == {"simulated_l1", "simulated_l2", "simulated_l1_l2", "oracle_llm_baseline"}


def test_harness_with_all_strategies() -> None:
    """EvalHarness runs all 4 strategies on a scenario."""
    scenario = _make_scenario()
    harness = EvalHarness()
    report = harness.run([scenario], ALL_STRATEGIES)

    assert len(report.results) == 4
    assert len(report.strategy_summaries) == 4
    # LLM strategy should have perfect recall (returns gold)
    llm_result = next(r for r in report.results if r.strategy_name == "oracle_llm_baseline")
    assert llm_result.recall == 1.0
    assert llm_result.f1 == 1.0
