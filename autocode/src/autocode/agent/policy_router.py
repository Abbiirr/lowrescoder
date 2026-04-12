"""Policy Router — deterministic escalation chain.

Routes tasks through L1 → L2 → L3 → L4 → external based on
complexity and capability. Ensures LLM-as-last-resort principle.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RoutingLayer(StrEnum):
    """Intelligence layers in escalation order."""

    L1 = "l1"  # tree-sitter, LSP — deterministic
    L2 = "l2"  # BM25 + vector search — retrieval
    L3_LOCAL = "l3_local"  # Small model, constrained gen
    L4_LOCAL = "l4_local"  # Full reasoning model
    EXTERNAL = "external"  # Cloud API (opt-in, costs $$)


@dataclass
class RoutingDecision:
    """Result of policy routing."""

    layer: RoutingLayer
    reason: str
    estimated_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass
class PolicyRouter:
    """Deterministic policy router.

    Escalation order: L1 → L2 → L3_local → L4_local → external.
    External is opt-in only (disabled by default).
    """

    order: list[RoutingLayer] = field(
        default_factory=lambda: [
            RoutingLayer.L1,
            RoutingLayer.L2,
            RoutingLayer.L3_LOCAL,
            RoutingLayer.L4_LOCAL,
        ],
    )
    external_enabled: bool = False
    external_budget: int = 10000  # max tokens for external

    def route(self, task_type: str, complexity: str = "low") -> RoutingDecision:
        """Route a task to the appropriate layer.

        Simple heuristic based on task type and complexity:
        - Symbol lookup, find references → L1
        - Code search, file discovery → L2
        - Simple edits, structured output → L3
        - Planning, reasoning, multi-file → L4
        - Complex multi-file + cloud fallback → External (if enabled)
        """
        # L1 tasks (deterministic, zero cost)
        l1_tasks = {
            "find_definition", "find_references", "list_symbols",
            "parse_ast", "syntax_check",
        }
        if task_type in l1_tasks:
            return RoutingDecision(
                layer=RoutingLayer.L1,
                reason=f"Deterministic L1 tool: {task_type}",
            )

        # L2 tasks (retrieval, zero cost)
        l2_tasks = {"search_code", "find_files", "semantic_search"}
        if task_type in l2_tasks:
            return RoutingDecision(
                layer=RoutingLayer.L2,
                reason=f"Retrieval L2 tool: {task_type}",
            )

        # Complexity-based escalation
        if complexity == "low":
            return RoutingDecision(
                layer=RoutingLayer.L3_LOCAL,
                reason="Low complexity — constrained L3 generation",
                estimated_tokens=500,
            )

        if complexity == "medium":
            return RoutingDecision(
                layer=RoutingLayer.L4_LOCAL,
                reason="Medium complexity — full L4 reasoning",
                estimated_tokens=2000,
            )

        # High complexity
        if complexity == "high" and self.external_enabled:
            return RoutingDecision(
                layer=RoutingLayer.EXTERNAL,
                reason="High complexity — external cloud model",
                estimated_tokens=4000,
                estimated_cost=0.01,
            )

        # Fall back to L4 local even for high complexity if external disabled
        return RoutingDecision(
            layer=RoutingLayer.L4_LOCAL,
            reason="High complexity — L4 local (external disabled)",
            estimated_tokens=4000,
        )

    def can_escalate(self, current: RoutingLayer) -> bool:
        """Check if further escalation is possible."""
        try:
            idx = self.order.index(current)
            if idx < len(self.order) - 1:
                return True
            return self.external_enabled and current != RoutingLayer.EXTERNAL
        except ValueError:
            return False

    def next_layer(self, current: RoutingLayer) -> RoutingLayer | None:
        """Get the next layer in escalation order."""
        try:
            idx = self.order.index(current)
            if idx < len(self.order) - 1:
                return self.order[idx + 1]
            if self.external_enabled and current != RoutingLayer.EXTERNAL:
                return RoutingLayer.EXTERNAL
        except ValueError:
            pass
        return None
