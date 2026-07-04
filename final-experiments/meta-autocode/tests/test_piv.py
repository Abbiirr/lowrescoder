"""Tests for EnhancedPIVStrategy — meta-autocode Phase 1."""
import pytest
import sys
from pathlib import Path

# Allow running from fixture root or with pytest
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from meta_autocode.piv import EnhancedPIVStrategy, PIVPlan, PIVResult
from meta_autocode.scorer import SessionScores, BenchmarkScore, CODEX_BASELINE


def test_strategy_has_describe():
    s = EnhancedPIVStrategy()
    desc = s.describe()
    assert isinstance(desc, str), "describe() must return a string"
    assert "PLAN" in desc, "describe() must mention PLAN phase"
    assert "IMPLEMENT" in desc, "describe() must mention IMPLEMENT phase"
    assert "VALIDATE" in desc, "describe() must mention VALIDATE phase"
    assert len(desc) > 100, "describe() must be substantive (>100 chars)"


def test_strategy_overlay_has_required_keys():
    s = EnhancedPIVStrategy()
    overlay = s.get_overlay()
    assert isinstance(overlay, dict)
    assert "max_edit_retries" in overlay, "overlay must have max_edit_retries"
    assert "additional_prompt_guidance" in overlay, "overlay must have additional_prompt_guidance"
    assert overlay["require_verifier_signal_before_retry"] is True, \
        "overlay must require verifier signal before retry"
    assert overlay["additional_prompt_guidance"], "additional_prompt_guidance must be non-empty"


def test_piv_plan_structure():
    plan = PIVPlan(
        task_description="Fix wrong port in config.yaml",
        files_to_read=["config.yaml", "test_app.py"],
        changes_needed=[{
            "file": "config.yaml",
            "description": "Change port from 9090 to 8080",
            "reason": "test expects 8080"
        }],
        test_files=["test_app.py"],
        verify_command="./verify.sh",
    )
    assert plan.task_description == "Fix wrong port in config.yaml"
    assert len(plan.changes_needed) == 1
    assert plan.changes_needed[0]["file"] == "config.yaml"
    assert plan.verify_command == "./verify.sh"


def test_piv_result_tracks_phases():
    result = PIVResult(phase="validate", success=True, tool_calls_used=8)
    assert result.success is True
    assert result.tool_calls_used == 8
    assert result.iterations == 1
    assert result.error_output == ""


def test_scorer_resolve_rate():
    session = SessionScores()
    session.scores.append(BenchmarkScore("b27", resolved=True, tool_calls=8, wall_time_s=14.0))
    session.scores.append(BenchmarkScore("b24", resolved=True, tool_calls=15, wall_time_s=42.0))
    session.scores.append(BenchmarkScore("b20", resolved=False, tool_calls=0, wall_time_s=16.0,
                                          failure_type="INFRA_FAIL"))
    assert session.resolve_rate == pytest.approx(2 / 3)
    assert session.avg_tool_calls == pytest.approx(11.5)


def test_beats_codex_when_all_resolved():
    """A session with 6/6 resolved must beat Codex's 61.5%."""
    session = SessionScores()
    for i in range(6):
        session.scores.append(BenchmarkScore(
            f"task-{i}", resolved=True, tool_calls=10, wall_time_s=30.0
        ))
    comparison = session.vs_codex()
    assert comparison["meta_autocode_rate"] == pytest.approx(1.0)
    assert comparison["beats_codex"] is True
    assert comparison["delta"] > 0.0
    assert comparison["codex_baseline"] == pytest.approx(0.615)


def test_codex_baseline_is_documented():
    """Baseline must be locked in — 61.5% functionality, >0 SWE-bench."""
    assert CODEX_BASELINE["functionality"] == pytest.approx(0.615), \
        "Codex functionality baseline must be 61.5% (MindStudio 2025)"
    assert CODEX_BASELINE["swe_bench_verified"] > 0


def test_max_iterations_is_three():
    """PIV loop must cap at 3 iterations to prevent infinite loops."""
    assert EnhancedPIVStrategy.MAX_ITERATIONS == 3


def test_empty_session_safe():
    """Empty session must not crash and must show 0% resolve rate."""
    session = SessionScores()
    assert session.resolve_rate == 0.0
    assert session.avg_tool_calls == 0.0
    vs = session.vs_codex()
    assert vs["beats_codex"] is False
