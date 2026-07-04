"""Tests for PolicyRouter — deterministic escalation chain."""

from __future__ import annotations

from autocode.agent.policy_router import PolicyRouter, RoutingLayer


def test_l1_tasks_routed_to_l1() -> None:
    """Deterministic tasks go to L1."""
    router = PolicyRouter()
    for task in ["find_definition", "find_references", "list_symbols", "syntax_check"]:
        decision = router.route(task)
        assert decision.layer == RoutingLayer.L1


def test_l2_tasks_routed_to_l2() -> None:
    """Search tasks go to L2."""
    router = PolicyRouter()
    for task in ["search_code", "find_files"]:
        decision = router.route(task)
        assert decision.layer == RoutingLayer.L2


def test_low_complexity_to_l3() -> None:
    """Low complexity tasks go to L3."""
    router = PolicyRouter()
    decision = router.route("edit_code", complexity="low")
    assert decision.layer == RoutingLayer.L3_LOCAL


def test_medium_complexity_to_l4() -> None:
    """Medium complexity tasks go to L4."""
    router = PolicyRouter()
    decision = router.route("plan_refactor", complexity="medium")
    assert decision.layer == RoutingLayer.L4_LOCAL


def test_high_complexity_external_disabled() -> None:
    """High complexity stays L4 when external disabled."""
    router = PolicyRouter(external_enabled=False)
    decision = router.route("multi_file_rewrite", complexity="high")
    assert decision.layer == RoutingLayer.L4_LOCAL


def test_high_complexity_external_enabled() -> None:
    """High complexity goes external when enabled."""
    router = PolicyRouter(external_enabled=True)
    decision = router.route("multi_file_rewrite", complexity="high")
    assert decision.layer == RoutingLayer.EXTERNAL
    assert decision.estimated_cost > 0


def test_escalation_chain() -> None:
    """Can escalate through the chain."""
    router = PolicyRouter()
    assert router.can_escalate(RoutingLayer.L1)
    assert router.can_escalate(RoutingLayer.L2)
    assert router.can_escalate(RoutingLayer.L3_LOCAL)
    assert not router.can_escalate(RoutingLayer.L4_LOCAL)  # last in chain


def test_escalation_with_external() -> None:
    """External adds one more escalation level."""
    router = PolicyRouter(external_enabled=True)
    assert router.can_escalate(RoutingLayer.L4_LOCAL)
    assert not router.can_escalate(RoutingLayer.EXTERNAL)


def test_next_layer() -> None:
    """Next layer follows escalation order."""
    router = PolicyRouter()
    assert router.next_layer(RoutingLayer.L1) == RoutingLayer.L2
    assert router.next_layer(RoutingLayer.L2) == RoutingLayer.L3_LOCAL
    assert router.next_layer(RoutingLayer.L3_LOCAL) == RoutingLayer.L4_LOCAL
    assert router.next_layer(RoutingLayer.L4_LOCAL) is None


def test_zero_cost_local() -> None:
    """Local routing has zero estimated cost."""
    router = PolicyRouter()
    for task_type in ["find_definition", "search_code"]:
        decision = router.route(task_type)
        assert decision.estimated_cost == 0.0
