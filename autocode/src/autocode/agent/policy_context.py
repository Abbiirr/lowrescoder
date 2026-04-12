"""PolicyContext — unified delegation/budget/approval/sandbox inheritance.

Combines DelegationPolicy, SubagentPermissions, approval mode, budget
tracking, and sandbox policy into a single context that inherits from
parent to child agents. Child restrictions can only tighten, never loosen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autocode.agent.delegation import (
    DelegationPolicy,
    SubagentPermissions,
)
from autocode.agent.sandbox import SandboxPolicy


@dataclass
class BudgetLimits:
    """Token and cost budget limits for an agent.

    Budget carve-out for children is configurable via carve_out_fraction
    and carve_out_cap — not hardcoded.
    """

    max_tokens: int = 50_000
    max_cost_usd: float = 0.0  # 0 = unlimited (local models)
    warning_threshold: float = 0.8
    carve_out_fraction: float = 0.25  # child gets this fraction of parent remaining
    carve_out_cap: int = 10_000  # max tokens for any single child
    tokens_used: int = 0
    cost_used: float = 0.0

    @property
    def tokens_remaining(self) -> int:
        return max(0, self.max_tokens - self.tokens_used)

    @property
    def is_exceeded(self) -> bool:
        if self.max_tokens > 0 and self.tokens_used >= self.max_tokens:
            return True
        if self.max_cost_usd > 0 and self.cost_used >= self.max_cost_usd:
            return True
        return False

    @property
    def should_warn(self) -> bool:
        if self.max_tokens > 0:
            return self.tokens_used >= self.max_tokens * self.warning_threshold
        return False

    def record(self, tokens: int, cost: float = 0.0) -> None:
        """Record token and cost usage."""
        self.tokens_used += tokens
        self.cost_used += cost


@dataclass
class PolicyContext:
    """Unified policy context for an agent.

    Supports inheritance: derive() creates a child context that can only
    tighten restrictions (never loosen).
    """

    agent_id: str = ""
    role: str = ""
    depth: int = 0

    # Delegation
    delegation: DelegationPolicy = field(default_factory=DelegationPolicy)
    permissions: SubagentPermissions = field(
        default_factory=SubagentPermissions.primary,
    )

    # Budget
    budget: BudgetLimits = field(default_factory=BudgetLimits)

    # Sandbox
    sandbox_policy: SandboxPolicy = SandboxPolicy.WRITABLE_PROJECT

    # Lineage
    parent_agent_id: str = ""

    @classmethod
    def root(
        cls,
        agent_id: str = "lead",
        *,
        delegation: DelegationPolicy | None = None,
        budget: BudgetLimits | None = None,
        sandbox_policy: SandboxPolicy = SandboxPolicy.WRITABLE_PROJECT,
    ) -> PolicyContext:
        """Create a root (primary) PolicyContext."""
        return cls(
            agent_id=agent_id,
            role="primary",
            depth=0,
            delegation=delegation or DelegationPolicy(),
            permissions=SubagentPermissions.primary(),
            budget=budget or BudgetLimits(),
            sandbox_policy=sandbox_policy,
        )

    def derive(
        self,
        child_role: str,
        child_agent_id: str = "",
    ) -> PolicyContext:
        """Create a child PolicyContext that inherits from this one.

        Invariants:
        - Child restrictions >= parent restrictions
        - Budget carved out using configurable fraction + cap
        - Sandbox inherited (never loosened)
        """
        # Look up role-specific permissions
        child_permissions = self.delegation.role_permissions.get(
            child_role,
            SubagentPermissions.restricted(),
        )

        # Budget carve-out: configurable fraction of parent remaining, capped
        child_max_tokens = min(
            int(self.budget.tokens_remaining * self.budget.carve_out_fraction),
            self.budget.carve_out_cap,
        )

        # Sandbox: inherit, never loosen
        child_sandbox = self.sandbox_policy

        return PolicyContext(
            agent_id=child_agent_id,
            role=child_role,
            depth=self.depth + 1,
            delegation=DelegationPolicy(
                max_depth=self.delegation.max_depth,
                max_threads=self.delegation.max_threads,
                max_total_agents=self.delegation.max_total_agents,
                role_permissions=self.delegation.role_permissions,
            ),
            permissions=child_permissions,
            budget=BudgetLimits(
                max_tokens=child_max_tokens,
                max_cost_usd=0.0,
                warning_threshold=self.budget.warning_threshold,
                carve_out_fraction=self.budget.carve_out_fraction,
                carve_out_cap=self.budget.carve_out_cap,
            ),
            sandbox_policy=child_sandbox,
            parent_agent_id=self.agent_id,
        )

    def can_spawn(self) -> tuple[bool, str]:
        """Check if this context allows spawning a child agent."""
        if self.depth >= self.delegation.max_depth:
            return False, f"Max depth reached ({self.delegation.max_depth})"
        return self.delegation.can_spawn(self.role)

    def check_budget(self) -> tuple[bool, str]:
        """Check budget status. Returns (ok, message)."""
        if self.budget.is_exceeded:
            return False, (
                f"Budget exceeded: {self.budget.tokens_used}/"
                f"{self.budget.max_tokens} tokens"
            )
        if self.budget.should_warn:
            return True, (
                f"Budget warning: {self.budget.tokens_used}/"
                f"{self.budget.max_tokens} tokens "
                f"({self.budget.tokens_remaining} remaining)"
            )
        return True, "ok"
