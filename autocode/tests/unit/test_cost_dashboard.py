"""Tests for CostDashboard — token usage tracking and reporting."""

from __future__ import annotations

import pytest

from autocode.agent.cost_dashboard import CostDashboard


def test_record_and_totals() -> None:
    """Recording entries updates totals."""
    dash = CostDashboard()
    dash.record("scout", "task-1", "l1", tokens_in=100, tokens_out=0)
    dash.record("architect", "task-1", "l4", tokens_in=500, tokens_out=200)

    assert dash.total_tokens == 800
    assert dash.local_tokens == 800
    assert dash.cloud_tokens == 0
    assert dash.total_cost == 0.0  # all local


def test_cloud_cost() -> None:
    """Cloud tokens have estimated cost."""
    dash = CostDashboard()
    dash.record("external", "task-1", "external", tokens_in=500000, tokens_out=500000)

    assert dash.cloud_tokens == 1_000_000
    assert dash.total_cost == 3.0  # $3/M tokens


def test_by_agent() -> None:
    """Group by agent."""
    dash = CostDashboard()
    dash.record("scout", "t1", "l1", tokens_in=100)
    dash.record("scout", "t2", "l1", tokens_in=200)
    dash.record("architect", "t1", "l4", tokens_in=500)

    by_agent = dash.by_agent()
    assert by_agent["scout"] == 300
    assert by_agent["architect"] == 500


def test_by_task() -> None:
    """Group by task."""
    dash = CostDashboard()
    dash.record("scout", "task-1", "l1", tokens_in=100)
    dash.record("arch", "task-1", "l4", tokens_in=500)
    dash.record("scout", "task-2", "l2", tokens_in=200)

    by_task = dash.by_task()
    assert by_task["task-1"] == 600
    assert by_task["task-2"] == 200


def test_by_layer() -> None:
    """Group by layer."""
    dash = CostDashboard()
    dash.record("a", "t1", "l1", tokens_in=100)
    dash.record("a", "t1", "l4", tokens_in=500)
    dash.record("a", "t2", "l4", tokens_in=300)

    by_layer = dash.by_layer()
    assert by_layer["l1"] == 100
    assert by_layer["l4"] == 800


def test_summary() -> None:
    """Summary contains key information."""
    dash = CostDashboard()
    dash.record("scout", "t1", "l1", tokens_in=1000)
    dash.record("arch", "t1", "l4", tokens_in=5000, tokens_out=2000)

    summary = dash.summary()
    assert "8,000" in summary  # total
    assert "Local (free)" in summary
    assert "$0.0000" in summary  # all local = free
    assert "scout" in summary
    assert "arch" in summary


def test_mixed_local_cloud() -> None:
    """Mixed local and cloud usage."""
    dash = CostDashboard()
    dash.record("scout", "t1", "l1", tokens_in=1000)
    dash.record("cloud", "t1", "external", tokens_in=2000, tokens_out=1000)

    assert dash.local_tokens == 1000
    assert dash.cloud_tokens == 3000
    assert dash.total_cost > 0


def test_check_limit_unset_never_fires() -> None:
    """Unset cost limit never reports a threshold crossing."""
    dash = CostDashboard()
    dash.record("cloud", "t1", "external", tokens_in=1_000_000)

    crossed, total_usd, threshold_usd = dash.check_limit(None)

    assert crossed is False
    assert total_usd == 3.0
    assert threshold_usd == 0.0


def test_check_limit_fires_once_until_threshold_raised_and_re_crossed() -> None:
    """Cost limit warning fires once, then fires again only for a raised limit."""
    dash = CostDashboard()
    dash.record("cloud", "t1", "external", tokens_in=2_000_000)

    assert dash.check_limit(5.0) == (True, 6.0, 5.0)
    assert dash.check_limit(5.0) == (False, 6.0, 5.0)
    assert dash.check_limit(10.0) == (False, 6.0, 10.0)

    dash.record("cloud", "t1", "external", tokens_in=2_000_000)

    assert dash.check_limit(10.0) == (True, 12.0, 10.0)
    assert dash.check_limit(10.0) == (False, 12.0, 10.0)


def test_check_limit_returns_current_total_and_threshold_before_crossing() -> None:
    """Limit check exposes current total and threshold for warning formatting."""
    dash = CostDashboard()
    dash.record("cloud", "t1", "external", tokens_in=1_000_000)

    crossed, total_usd, threshold_usd = dash.check_limit(5.0)

    assert crossed is False
    assert total_usd == 3.0
    assert threshold_usd == 5.0


def test_record_with_cached_input_tokens() -> None:
    """Cached prompt tokens are tracked separately and priced at cache-read rate."""
    dash = CostDashboard()

    dash.record(
        "cloud",
        "t1",
        "external",
        tokens_in=1_000,
        cached_input_tokens=9_000,
        tokens_out=500,
    )

    assert dash.total_uncached_input_tokens == 1_000
    assert dash.total_cached_input_tokens == 9_000
    assert dash.total_input_tokens == 10_000
    assert dash.total_output_tokens == 500
    assert dash.total_tokens == 10_500
    assert dash.cache_hit_ratio == 0.9
    assert dash.input_cost == pytest.approx(0.0057)
    assert dash.output_cost == pytest.approx(0.0015)
    assert dash.total_cost == pytest.approx(0.0072)


def test_estimated_cache_savings_calculation() -> None:
    """Cache savings report the delta from full-price prompt tokens."""
    dash = CostDashboard()

    dash.record(
        "cloud",
        "t1",
        "external",
        tokens_in=1_000,
        cached_input_tokens=9_000,
    )

    assert dash.estimated_cache_savings_usd == pytest.approx(0.0243)


def test_cache_hit_ratio_zero_when_no_input() -> None:
    """Cache hit ratio is stable when no input tokens were recorded."""
    dash = CostDashboard()

    dash.record("cloud", "t1", "external", tokens_out=500)

    assert dash.cache_hit_ratio == 0.0
