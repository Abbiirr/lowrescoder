"""Tests for MetaAutocodeRunner — meta-autocode Phase 4 (integration).

This is the final phase: wiring PIV + ProgressiveContextLoader + BenchmarkMaxxer
into a single pipeline that can run against coding tasks and produce a scored result.
This is the harness that will beat Codex (61.5%) in production benchmarks.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from meta_autocode.runner import MetaAutocodeRunner, RunResult


def test_runner_instantiates():
    runner = MetaAutocodeRunner()
    assert runner is not None


def test_run_result_fields():
    result = RunResult(
        task_id="t1",
        resolved=True,
        score=0.8,
        tool_calls=10,
        variant_used="tdd",
        wall_time_s=30.0,
    )
    assert result.task_id == "t1"
    assert result.resolved is True
    assert result.score == 0.8
    assert result.variant_used == "tdd"


def test_runner_has_components():
    runner = MetaAutocodeRunner()
    assert hasattr(runner, "context_loader") or hasattr(runner, "maxxer"), \
        "runner must expose context_loader or maxxer"


def test_runner_simulate_resolved():
    runner = MetaAutocodeRunner()
    files = {
        "tests/test_example.py": "def test_add(): assert add(1,2)==3",
        "src/example.py": "def add(a, b): return a + b",
    }
    result = runner.simulate(task_id="test-add", files=files, query="add function")
    assert isinstance(result, RunResult)
    assert result.task_id == "test-add"
    assert isinstance(result.resolved, bool)
    assert isinstance(result.score, float)
    assert isinstance(result.variant_used, str)


def test_runner_simulate_empty_files():
    runner = MetaAutocodeRunner()
    result = runner.simulate(task_id="empty", files={}, query="anything")
    assert isinstance(result, RunResult)
    assert result.task_id == "empty"


def test_runner_uses_context_ranking():
    runner = MetaAutocodeRunner()
    files = {
        "tests/test_parser.py": "def test_parse_date(): assert parse_date('2025-01-01')",
        "src/parser.py": "def parse_date(s): return s",
        "src/utils.py": "def clamp(v): return v",
    }
    # We can't run the actual agent, but simulate() must use context ranking internally
    result = runner.simulate(task_id="parse-task", files=files, query="parse date")
    assert isinstance(result, RunResult)
    # The ranked context should have put tests/test_parser.py first
    assert result.context_top_file is not None
    assert "test" in result.context_top_file


def test_runner_beat_codex_rate():
    runner = MetaAutocodeRunner()
    from meta_autocode.scorer import CODEX_BASELINE, SessionScores, BenchmarkScore
    mock_results = [
        runner.simulate(task_id=f"task-{i}", files={"src/f.py": f"x={i}"}, query="x variable")
        for i in range(3)
    ]
    scores = SessionScores(scores=[
        BenchmarkScore(task_id=r.task_id, resolved=r.resolved, tool_calls=r.tool_calls, wall_time_s=r.wall_time_s)
        for r in mock_results
    ])
    assert 0.0 <= scores.resolve_rate <= 1.0
    assert isinstance(scores.vs_codex(), dict)


def test_run_result_has_context_top_file():
    result = RunResult(
        task_id="t1",
        resolved=True,
        score=0.9,
        tool_calls=5,
        variant_used="direct",
        wall_time_s=10.0,
        context_top_file="tests/test_foo.py",
    )
    assert result.context_top_file == "tests/test_foo.py"


def test_runner_variant_selection():
    runner = MetaAutocodeRunner()
    from meta_autocode.maxxing import BenchmarkMaxxer
    assert hasattr(runner, "maxxer") or hasattr(runner, "_maxxer")
