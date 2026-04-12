"""Tests for Orchestrator — wires PolicyRouter, AgentBus, SOPRunner, CostDashboard."""

from __future__ import annotations

from autocode.agent.orchestrator import Orchestrator
from autocode.agent.identity import AgentRegistry
from autocode.agent.policy_router import PolicyRouter, RoutingLayer
from autocode.agent.sop_runner import SOPPipeline


def test_orchestrator_creates_with_defaults() -> None:
    """Orchestrator initializes with default components."""
    orch = Orchestrator()
    assert orch.registry is not None
    assert orch.router is not None
    assert orch.bus is not None
    assert orch.cost is not None


def test_route_task_l1() -> None:
    """L1 tasks routed to scout agent."""
    orch = Orchestrator()
    decision = orch.route_task("find_definition")
    assert decision.layer == RoutingLayer.L1


def test_route_task_l4() -> None:
    """Complex tasks routed to L4."""
    orch = Orchestrator()
    decision = orch.route_task("plan_refactor", complexity="medium")
    assert decision.layer == RoutingLayer.L4_LOCAL


def test_dispatch_sends_to_bus() -> None:
    """Dispatch sends message to AgentBus."""
    orch = Orchestrator()
    result = orch.dispatch("Find the bug", task_type="find_definition")
    assert result["success"]
    assert result["agent"] == "scout"
    assert result["layer"] == "l1"
    assert orch.bus.message_count >= 1


def test_dispatch_tracks_cost() -> None:
    """Dispatch records cost in dashboard."""
    orch = Orchestrator()
    orch.dispatch("Fix something", task_type="edit_code", complexity="medium")
    assert orch.cost.total_tokens > 0


def test_dispatch_no_agent() -> None:
    """Dispatch fails gracefully when no agent available."""
    orch = Orchestrator(registry=AgentRegistry())  # empty registry
    result = orch.dispatch("Do something")
    assert not result["success"]
    assert "No agent" in result["error"]


def test_run_pipeline_bugfix() -> None:
    """Run a bugfix pipeline through the orchestrator."""
    orch = Orchestrator()
    pipeline = SOPPipeline.bugfix()
    result = orch.run_pipeline(
        pipeline,
        context={"task": "Fix the null pointer"},
        task_id="bug-123",
    )
    assert result.steps_completed == len(pipeline.steps)
    # Bus should have messages from pipeline execution
    assert orch.bus.message_count > 0


def test_orchestrator_summary() -> None:
    """Summary includes key metrics."""
    orch = Orchestrator()
    orch.dispatch("Test task", task_type="search_code")
    summary = orch.summary
    assert "Agents:" in summary
    assert "Messages:" in summary
    assert "Total tokens:" in summary


def test_pipeline_posts_results_to_bus() -> None:
    """Each pipeline step posts results to the bus."""
    orch = Orchestrator()
    pipeline = SOPPipeline.bugfix()
    orch.run_pipeline(pipeline, context={"task": "fix"}, task_id="t1")

    thread = orch.bus.get_thread("t1")
    # Should have REQUEST + RESULT messages for each step
    assert len(thread) >= len(pipeline.steps)
