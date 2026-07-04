"""Routing quality benchmark — validate PolicyRouter decisions.

Tests whether the PolicyRouter correctly assigns tasks to the
optimal layer, measuring correct-layer %, escalation depth, and
cost savings vs always-L4.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from autocode.agent.policy_router import PolicyRouter, RoutingLayer


@dataclass
class RoutingScenario:
    """A task with a known optimal routing layer."""

    task_type: str
    complexity: str
    expected_layer: RoutingLayer
    description: str = ""


@dataclass
class RoutingBenchmarkResult:
    """Result of running the routing benchmark."""

    total: int = 0
    correct: int = 0
    by_layer: dict[str, int] = field(default_factory=dict)
    cost_if_always_l4: int = 0
    cost_actual: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    @property
    def cost_savings(self) -> float:
        if self.cost_if_always_l4 == 0:
            return 0.0
        return 1.0 - (self.cost_actual / self.cost_if_always_l4)


# 20 scenarios with known optimal layer
ROUTING_SCENARIOS = [
    # L1 tasks (deterministic, zero cost)
    RoutingScenario("find_definition", "low", RoutingLayer.L1, "Go-to-definition"),
    RoutingScenario("find_references", "low", RoutingLayer.L1, "Find all references"),
    RoutingScenario("list_symbols", "low", RoutingLayer.L1, "List file symbols"),
    RoutingScenario("parse_ast", "low", RoutingLayer.L1, "Parse AST"),
    RoutingScenario("syntax_check", "low", RoutingLayer.L1, "Syntax check"),
    # L2 tasks (retrieval, zero cost)
    RoutingScenario("search_code", "low", RoutingLayer.L2, "Code search"),
    RoutingScenario("find_files", "low", RoutingLayer.L2, "Find files"),
    RoutingScenario("semantic_search", "low", RoutingLayer.L2, "Semantic search"),
    # L3 tasks (constrained gen, low cost)
    RoutingScenario("fix_typo", "low", RoutingLayer.L3_LOCAL, "Fix a typo"),
    RoutingScenario("add_import", "low", RoutingLayer.L3_LOCAL, "Add missing import"),
    RoutingScenario("format_code", "low", RoutingLayer.L3_LOCAL, "Format code"),
    RoutingScenario("rename_var", "low", RoutingLayer.L3_LOCAL, "Rename variable"),
    # L4 tasks (full reasoning)
    RoutingScenario("plan_refactor", "medium", RoutingLayer.L4_LOCAL, "Plan refactoring"),
    RoutingScenario("debug_crash", "medium", RoutingLayer.L4_LOCAL, "Debug crash"),
    RoutingScenario("write_tests", "medium", RoutingLayer.L4_LOCAL, "Write test suite"),
    RoutingScenario("code_review", "medium", RoutingLayer.L4_LOCAL, "Review code"),
    RoutingScenario("architecture", "high", RoutingLayer.L4_LOCAL, "Design architecture"),
    RoutingScenario("multi_file_fix", "high", RoutingLayer.L4_LOCAL, "Multi-file bug fix"),
    RoutingScenario("security_audit", "high", RoutingLayer.L4_LOCAL, "Security audit"),
    RoutingScenario("perf_optimize", "high", RoutingLayer.L4_LOCAL, "Performance optimization"),
]

# Estimated token cost per layer
LAYER_COST = {
    RoutingLayer.L1: 0,
    RoutingLayer.L2: 0,
    RoutingLayer.L3_LOCAL: 500,
    RoutingLayer.L4_LOCAL: 2000,
    RoutingLayer.EXTERNAL: 4000,
}


def run_routing_benchmark(
    router: PolicyRouter | None = None,
) -> RoutingBenchmarkResult:
    """Run the routing benchmark against 20 scenarios."""
    r = router or PolicyRouter()
    result = RoutingBenchmarkResult(total=len(ROUTING_SCENARIOS))

    for scenario in ROUTING_SCENARIOS:
        decision = r.route(scenario.task_type, scenario.complexity)
        if decision.layer == scenario.expected_layer:
            result.correct += 1

        layer_name = decision.layer.value
        result.by_layer[layer_name] = result.by_layer.get(layer_name, 0) + 1
        result.cost_actual += LAYER_COST.get(decision.layer, 2000)
        result.cost_if_always_l4 += LAYER_COST[RoutingLayer.L4_LOCAL]

    return result
