"""Tests for CostDashboard — token usage tracking and reporting."""

from __future__ import annotations

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
