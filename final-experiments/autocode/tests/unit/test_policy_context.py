"""Tests for PolicyContext — unified delegation/budget/approval/sandbox inheritance."""

from __future__ import annotations

import pytest

from autocode.agent.delegation import (
    DelegationPolicy,
    PermissionRule,
    SubagentPermissions,
)
from autocode.agent.policy_context import BudgetLimits, PolicyContext
from autocode.agent.sandbox import SandboxPolicy


# ── BudgetLimits ──


class TestBudgetLimits:
    def test_default_budget(self) -> None:
        b = BudgetLimits()
        assert b.max_tokens == 50_000
        assert b.tokens_used == 0
        assert not b.is_exceeded
        assert not b.should_warn

    def test_record_tokens(self) -> None:
        b = BudgetLimits(max_tokens=100)
        b.record(50)
        assert b.tokens_used == 50
        assert b.tokens_remaining == 50

    def test_is_exceeded(self) -> None:
        b = BudgetLimits(max_tokens=100)
        b.record(100)
        assert b.is_exceeded

    def test_should_warn_at_threshold(self) -> None:
        b = BudgetLimits(max_tokens=100, warning_threshold=0.8)
        b.record(79)
        assert not b.should_warn
        b.record(1)
        assert b.should_warn  # 80/100 = 80%

    def test_tokens_remaining(self) -> None:
        b = BudgetLimits(max_tokens=200)
        b.record(50)
        assert b.tokens_remaining == 150

    def test_tokens_remaining_never_negative(self) -> None:
        b = BudgetLimits(max_tokens=100)
        b.record(200)
        assert b.tokens_remaining == 0

    def test_cost_tracking(self) -> None:
        b = BudgetLimits(max_cost_usd=1.0)
        b.record(100, cost=0.5)
        assert not b.is_exceeded
        b.record(100, cost=0.6)
        assert b.is_exceeded


# ── PolicyContext Creation ──


class TestPolicyContextCreation:
    def test_root_context_defaults(self) -> None:
        ctx = PolicyContext.root(agent_id="lead")
        assert ctx.agent_id == "lead"
        assert ctx.depth == 0
        assert ctx.parent_agent_id == ""
        assert not ctx.budget.is_exceeded

    def test_root_context_with_custom_values(self) -> None:
        ctx = PolicyContext.root(
            agent_id="lead",
            budget=BudgetLimits(max_tokens=10_000),
            sandbox_policy=SandboxPolicy.READ_ONLY,
        )
        assert ctx.budget.max_tokens == 10_000
        assert ctx.sandbox_policy == SandboxPolicy.READ_ONLY


# ── Derive (Inheritance) ──


class TestPolicyContextDerive:
    def test_derive_sets_child_depth(self) -> None:
        parent = PolicyContext.root(agent_id="lead")
        child = parent.derive("scout", child_agent_id="scout-1")
        assert child.depth == 1
        assert child.parent_agent_id == "lead"

    def test_derive_restricts_budget(self) -> None:
        parent = PolicyContext.root(
            agent_id="lead",
            budget=BudgetLimits(max_tokens=40_000),
        )
        child = parent.derive("scout")
        # Default: 25% of parent remaining, capped at 10k
        assert child.budget.max_tokens == 10_000  # min(40000*0.25, 10000)

    def test_derive_budget_configurable(self) -> None:
        parent = PolicyContext.root(
            agent_id="lead",
            budget=BudgetLimits(
                max_tokens=40_000,
                carve_out_fraction=0.5,
                carve_out_cap=20_000,
            ),
        )
        child = parent.derive("engineer")
        assert child.budget.max_tokens == 20_000  # min(40000*0.5, 20000)

    def test_derive_inherits_sandbox(self) -> None:
        parent = PolicyContext.root(
            agent_id="lead",
            sandbox_policy=SandboxPolicy.WRITABLE_PROJECT,
        )
        child = parent.derive("scout")
        assert child.sandbox_policy == SandboxPolicy.WRITABLE_PROJECT

    def test_derive_uses_role_permissions(self) -> None:
        parent = PolicyContext.root(agent_id="lead")
        child = parent.derive("scout")
        # Scout should be read_only
        assert child.permissions.file_write == PermissionRule.DENY

    def test_derive_falls_back_to_restricted(self) -> None:
        parent = PolicyContext.root(agent_id="lead")
        child = parent.derive("unknown_role")
        assert child.permissions.file_write == PermissionRule.ASK

    def test_sandbox_never_loosens(self) -> None:
        parent = PolicyContext.root(
            agent_id="lead",
            sandbox_policy=SandboxPolicy.READ_ONLY,
        )
        child = parent.derive("engineer")
        # Even engineer can't loosen to WRITABLE
        assert child.sandbox_policy == SandboxPolicy.READ_ONLY


# ── can_spawn ──


class TestPolicyContextCanSpawn:
    def test_can_spawn_within_limits(self) -> None:
        ctx = PolicyContext.root(agent_id="lead")
        ok, reason = ctx.can_spawn()
        assert ok

    def test_cannot_spawn_at_max_depth(self) -> None:
        parent = PolicyContext.root(agent_id="lead")
        child = parent.derive("scout", "s1")
        grandchild = child.derive("scout", "s2")
        # Default max_depth=2, grandchild is depth=2
        ok, reason = grandchild.can_spawn()
        assert not ok
        assert "depth" in reason.lower()


# ── check_budget ──


class TestPolicyContextCheckBudget:
    def test_budget_ok(self) -> None:
        ctx = PolicyContext.root(agent_id="lead")
        ok, msg = ctx.check_budget()
        assert ok
        assert msg == "ok"

    def test_budget_warning(self) -> None:
        ctx = PolicyContext.root(
            agent_id="lead",
            budget=BudgetLimits(max_tokens=100, warning_threshold=0.8),
        )
        ctx.budget.record(85)
        ok, msg = ctx.check_budget()
        assert ok  # warning, not exceeded
        assert "warning" in msg.lower()

    def test_budget_exceeded(self) -> None:
        ctx = PolicyContext.root(
            agent_id="lead",
            budget=BudgetLimits(max_tokens=100),
        )
        ctx.budget.record(100)
        ok, msg = ctx.check_budget()
        assert not ok
        assert "exceeded" in msg.lower()


# ── Inheritance Chain ──


class TestPolicyContextInheritanceChain:
    def test_three_level_inheritance(self) -> None:
        root = PolicyContext.root(
            agent_id="lead",
            budget=BudgetLimits(max_tokens=40_000),
        )
        child = root.derive("engineer", "eng-1")
        grandchild = child.derive("scout", "scout-1")
        assert grandchild.depth == 2
        assert grandchild.parent_agent_id == "eng-1"

    def test_budget_shrinks_at_each_level(self) -> None:
        root = PolicyContext.root(
            agent_id="lead",
            budget=BudgetLimits(max_tokens=40_000),
        )
        child = root.derive("engineer", "eng-1")
        grandchild = child.derive("scout", "scout-1")
        assert grandchild.budget.max_tokens < child.budget.max_tokens
        assert child.budget.max_tokens < root.budget.max_tokens
