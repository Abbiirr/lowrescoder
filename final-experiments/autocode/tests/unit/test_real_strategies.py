"""Tests for real context packing strategies."""

from __future__ import annotations

from pathlib import Path

from autocode.eval.harness import EvalHarness, EvalScenario
from autocode.eval.real_strategies import (
    create_l1_l2_real_strategy,
    create_l1_real_strategy,
    create_l2_real_strategy,
)


def _make_repo(tmp_path: Path) -> Path:
    """Create a small test repo."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "class UserService:\n"
        "    def get_user(self, uid):\n"
        "        return {'id': uid}\n"
    )
    (tmp_path / "src" / "database.py").write_text(
        "class Database:\n"
        "    def query(self, sql):\n"
        "        return []\n"
    )
    (tmp_path / "src" / "utils.py").write_text(
        "def format_date(d):\n"
        "    return str(d)\n"
    )
    return tmp_path


def test_l1_real_finds_symbol_matches(tmp_path: Path) -> None:
    """Real L1 strategy finds files via description keywords, not gold labels."""
    repo = _make_repo(tmp_path)
    strategy = create_l1_real_strategy(repo)

    # Description mentions "UserService" which matches a symbol in app.py
    scenario = EvalScenario(
        id="test", task_type="bug_fix",
        input_description="Fix the UserService get_user method",
        gold_files=["src/app.py"],
        gold_symbols=["UserService.get_user"],
    )

    result = strategy.curate(scenario)
    # Should find app.py because "UserService" is in description AND in file
    assert any("app.py" in f for f in result.files)
    assert result.token_count > 0


def test_l2_real_finds_keyword_matches(tmp_path: Path) -> None:
    """Real L2 strategy finds files with matching content."""
    repo = _make_repo(tmp_path)
    strategy = create_l2_real_strategy(repo)

    scenario = EvalScenario(
        id="test", task_type="bug_fix",
        input_description="Fix the database query method",
        gold_files=["src/database.py"],
    )

    result = strategy.curate(scenario)
    # Should find database.py since "query" appears in its content
    assert any("database" in f for f in result.files)


def test_l1_l2_combined(tmp_path: Path) -> None:
    """Combined L1+L2 returns union without duplicates."""
    repo = _make_repo(tmp_path)
    strategy = create_l1_l2_real_strategy(repo)

    scenario = EvalScenario(
        id="test", task_type="bug_fix",
        input_description="Fix the user service database query",
        gold_files=["src/app.py", "src/database.py"],
        gold_symbols=["UserService"],
    )

    result = strategy.curate(scenario)
    assert len(result.files) == len(set(result.files))  # no dupes


def test_real_strategies_dont_leak_gold(tmp_path: Path) -> None:
    """Real strategies search repo files, not gold labels."""
    repo = _make_repo(tmp_path)
    strategy = create_l1_real_strategy(repo)

    # Gold file doesn't exist in repo
    scenario = EvalScenario(
        id="test", task_type="bug_fix",
        input_description="Fix the payment processor",
        gold_files=["src/payments.py"],  # doesn't exist
        gold_symbols=["PaymentProcessor"],
    )

    result = strategy.curate(scenario)
    # Should NOT return payments.py since it doesn't exist
    assert "src/payments.py" not in result.files


def test_changing_gold_labels_doesnt_change_retrieval(tmp_path: Path) -> None:
    """Regression: changing gold labels must NOT change retrieval output.

    Per Codex Entry 830: gold labels should only affect scoring,
    never the candidate generation.
    """
    repo = _make_repo(tmp_path)
    strategy = create_l1_real_strategy(repo)

    # Same description, different gold labels
    scenario_a = EvalScenario(
        id="test", task_type="bug_fix",
        input_description="Fix the database query method",
        gold_files=["src/database.py"],
        gold_symbols=["Database.query"],
    )
    scenario_b = EvalScenario(
        id="test", task_type="bug_fix",
        input_description="Fix the database query method",
        gold_files=["src/app.py"],  # different gold
        gold_symbols=["UserService.get_user"],  # different gold
    )

    result_a = strategy.curate(scenario_a)
    result_b = strategy.curate(scenario_b)

    # Same description → same retrieval, regardless of gold labels
    assert set(result_a.files) == set(result_b.files)


def test_eval_harness_with_real_strategies(tmp_path: Path) -> None:
    """EvalHarness works with real strategies against actual repo."""
    repo = _make_repo(tmp_path)

    strategies = [
        create_l1_real_strategy(repo),
        create_l2_real_strategy(repo),
        create_l1_l2_real_strategy(repo),
    ]

    scenarios = [
        EvalScenario(
            id="s1", task_type="bug_fix",
            input_description="Fix the database query",
            gold_files=["src/database.py"],
            gold_symbols=["Database.query"],
        ),
    ]

    harness = EvalHarness()
    report = harness.run(scenarios, strategies)
    assert len(report.results) == 3
    assert len(report.strategy_summaries) == 3
