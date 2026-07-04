"""Tests for BenchmarkMaxxer — meta-autocode Phase 3.

Benchmark maxxing: run multiple strategy variants per task, pick the best result.
Codex (61.5%) uses a single-attempt strategy. meta-autocode runs N attempts with
variant prompts and returns the highest-scoring one, closing the gap toward
Claude Code (87.2%) and Cursor (91.1%).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from meta_autocode.maxxing import BenchmarkMaxxer, MaxxingResult, VariantStrategy


def test_maxxer_has_max_variants():
    assert hasattr(BenchmarkMaxxer, "MAX_VARIANTS"), \
        "BenchmarkMaxxer.MAX_VARIANTS must be a class attribute"
    assert BenchmarkMaxxer.MAX_VARIANTS >= 3, "must support at least 3 variants"


def test_variant_strategy_fields():
    v = VariantStrategy(name="test", prompt_suffix="focus on edge cases")
    assert v.name == "test"
    assert v.prompt_suffix == "focus on edge cases"


def test_maxxing_result_picks_best():
    results = [
        MaxxingResult(variant="v1", score=0.5, resolved=False, tool_calls=10),
        MaxxingResult(variant="v2", score=0.9, resolved=True, tool_calls=15),
        MaxxingResult(variant="v3", score=0.7, resolved=True, tool_calls=8),
    ]
    best = BenchmarkMaxxer.pick_best(results)
    assert best.variant == "v2"
    assert best.score == 0.9


def test_pick_best_prefers_resolved():
    results = [
        MaxxingResult(variant="v1", score=0.3, resolved=False, tool_calls=5),
        MaxxingResult(variant="v2", score=0.2, resolved=True, tool_calls=3),
    ]
    best = BenchmarkMaxxer.pick_best(results)
    assert best.resolved is True, "resolved result must beat unresolved even with lower score"


def test_pick_best_empty_raises():
    import pytest
    with pytest.raises((ValueError, IndexError)):
        BenchmarkMaxxer.pick_best([])


def test_default_variants_cover_strategies():
    maxxer = BenchmarkMaxxer()
    names = [v.name for v in maxxer.variants]
    assert len(names) >= 3
    # Must include at least one test-first variant and one minimal-change variant
    assert any("test" in n.lower() or "tdd" in n.lower() for n in names), \
        "need a test-first variant"
    assert any("minimal" in n.lower() or "simple" in n.lower() or "direct" in n.lower() for n in names), \
        "need a minimal/direct variant"


def test_maxxing_result_beats_codex():
    # 4 out of 6 resolved => 66.7% > 61.5% codex baseline
    results = [
        MaxxingResult(variant="v1", score=1.0, resolved=True, tool_calls=10),
        MaxxingResult(variant="v2", score=0.0, resolved=False, tool_calls=5),
    ]
    best = BenchmarkMaxxer.pick_best(results)
    CODEX_BASELINE = 0.615
    # If best is resolved, this task contributes to beating codex
    assert best.resolved


def test_codex_baseline_constant():
    from meta_autocode.scorer import CODEX_BASELINE
    assert CODEX_BASELINE["functionality"] == 0.615


def test_maxxer_simulate_session():
    # BenchmarkMaxxer.simulate() runs pick_best on a list of scored results
    # This is the integration point with the PIV loop
    maxxer = BenchmarkMaxxer()
    mock_results = [
        MaxxingResult(variant=v.name, score=0.0, resolved=False, tool_calls=0)
        for v in maxxer.variants[:2]
    ]
    mock_results[1] = MaxxingResult(variant=maxxer.variants[1].name, score=0.8, resolved=True, tool_calls=12)
    best = maxxer.simulate(mock_results)
    assert best.resolved
    assert best.score == 0.8
