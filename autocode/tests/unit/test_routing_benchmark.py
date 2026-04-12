"""Tests for routing quality benchmark."""

from __future__ import annotations

from autocode.agent.policy_router import PolicyRouter
from autocode.eval.routing_benchmark import (
    ROUTING_SCENARIOS,
    run_routing_benchmark,
)


def test_benchmark_runs() -> None:
    """Benchmark runs and produces results."""
    result = run_routing_benchmark()
    assert result.total == 20
    assert result.correct > 0
    assert result.accuracy > 0


def test_benchmark_high_accuracy() -> None:
    """Default router should get most scenarios correct."""
    result = run_routing_benchmark()
    # L1 and L2 tasks should be perfectly routed
    assert result.accuracy >= 0.6  # at least 60%


def test_cost_savings() -> None:
    """Routing saves cost vs always using L4."""
    result = run_routing_benchmark()
    assert result.cost_savings > 0  # some savings
    assert result.cost_actual < result.cost_if_always_l4


def test_scenarios_exist() -> None:
    """20 scenarios are defined."""
    assert len(ROUTING_SCENARIOS) == 20


def test_custom_router() -> None:
    """Benchmark works with custom router."""
    router = PolicyRouter(external_enabled=True)
    result = run_routing_benchmark(router)
    assert result.total == 20
