"""Tests for Layer 4.5 cost-aware provider routing."""

from __future__ import annotations

from autocode.core.types import RequestType


def _rate_table():
    from autocode.layer4_5.router import ModelRate

    return [
        ModelRate(
            provider="openrouter",
            model="cheap-fast",
            tier="cheap",
            input_per_m=0.20,
            output_per_m=0.80,
        ),
        ModelRate(
            provider="openrouter",
            model="mid-balanced",
            tier="mid",
            input_per_m=0.60,
            output_per_m=1.20,
        ),
        ModelRate(
            provider="openrouter",
            model="frontier-best",
            tier="frontier",
            input_per_m=3.00,
            output_per_m=10.00,
        ),
    ]


def test_small_edit_routes_to_cheapest_tier() -> None:
    from autocode.layer4_5.router import Layer45Router

    router = Layer45Router(rate_table=_rate_table())
    selection = router.select(RequestType.SIMPLE_EDIT, confidence=0.9)

    assert selection.tier == "cheap"
    assert selection.model == "cheap-fast"
    assert selection.reason
    assert selection.estimated_cost_delta >= 0.0


def test_refactor_routes_to_frontier_tier() -> None:
    from autocode.layer4_5.router import Layer45Router

    router = Layer45Router(rate_table=_rate_table())
    selection = router.select("refactor", confidence=0.9)

    assert selection.tier == "frontier"
    assert selection.model == "frontier-best"
    assert "refactor" in selection.reason


def test_ambiguous_task_uses_configured_default_tier() -> None:
    from autocode.layer4_5.router import Layer45Router

    router = Layer45Router(
        rate_table=_rate_table(),
        default_tier_map={"chat": "cheap", "complex_task": "frontier"},
    )
    selection = router.select(RequestType.CHAT, confidence=0.9)

    assert selection.tier == "cheap"
    assert "configured" in selection.reason


def test_low_confidence_uses_fallback_path() -> None:
    from autocode.layer4_5.router import Layer45Router

    router = Layer45Router(rate_table=_rate_table(), low_confidence_tier="mid")
    selection = router.select("refactor", confidence=0.25)

    assert selection.tier == "mid"
    assert "low confidence" in selection.reason


def test_billable_factor_one_preserves_default_selection() -> None:
    from autocode.layer4_5.router import Layer45Router

    router = Layer45Router(rate_table=_rate_table())

    default = router.select(RequestType.SIMPLE_EDIT, confidence=0.9)
    explicit = router.select(
        RequestType.SIMPLE_EDIT,
        confidence=0.9,
        billable_input_cost_factor=1.0,
    )

    assert explicit == default


def test_low_billable_factor_shifts_to_cache_friendly_model_within_tier() -> None:
    from autocode.layer4_5.router import Layer45Router, ModelRate

    router = Layer45Router(rate_table=[
        ModelRate(
            provider="openrouter",
            model="low-input",
            tier="cheap",
            input_per_m=1.0,
            output_per_m=4.0,
        ),
        ModelRate(
            provider="openrouter",
            model="cache-friendly",
            tier="cheap",
            input_per_m=8.0,
            output_per_m=0.2,
        ),
    ])

    selection = router.select(
        RequestType.SIMPLE_EDIT,
        confidence=0.9,
        billable_input_cost_factor=0.3,
        estimated_input_tokens=1_000_000,
        estimated_output_tokens=1_000_000,
    )

    assert selection.model == "cache-friendly"
    assert "billable_input_cost_factor=0.3" in selection.reason


def test_high_billable_factor_shifts_away_from_cache_write_premium() -> None:
    from autocode.layer4_5.router import Layer45Router, ModelRate

    router = Layer45Router(rate_table=[
        ModelRate(
            provider="openrouter",
            model="low-input",
            tier="cheap",
            input_per_m=1.0,
            output_per_m=4.0,
        ),
        ModelRate(
            provider="openrouter",
            model="cache-friendly",
            tier="cheap",
            input_per_m=8.0,
            output_per_m=0.2,
        ),
    ])

    selection = router.select(
        RequestType.SIMPLE_EDIT,
        confidence=0.9,
        billable_input_cost_factor=1.25,
        estimated_input_tokens=1_000_000,
        estimated_output_tokens=1_000_000,
    )

    assert selection.model == "low-input"
    assert "billable_input_cost_factor=1.25" in selection.reason


def test_cost_dashboard_groups_entries_by_routing_tier() -> None:
    from autocode.agent.cost_dashboard import CostDashboard

    dashboard = CostDashboard()
    dashboard.record("agent", "t1", "external", 100, 0, 50, "cheap-fast", routing_tier="cheap")
    dashboard.record("agent", "t2", "external", 200, 0, 75, "frontier-best", routing_tier="frontier")

    breakdown = dashboard.by_routing_tier()

    assert breakdown["cheap"]["tokens"] == 150
    assert breakdown["frontier"]["tokens"] == 275
    assert breakdown["frontier"]["cost"] > breakdown["cheap"]["cost"]


def test_router_builds_from_config_model_rates() -> None:
    from autocode.config import AutoCodeConfig, RoutingModelRateConfig
    from autocode.layer4_5.router import Layer45Router

    config = AutoCodeConfig()
    config.routing.model_rates = [
        RoutingModelRateConfig(
            provider="openrouter",
            model="frontier-best",
            tier="frontier",
            input_per_m=3.0,
            output_per_m=10.0,
        )
    ]

    router = Layer45Router.from_config(config)
    selection = router.select(RequestType.COMPLEX_TASK, confidence=0.9)

    assert selection.provider == "openrouter"
    assert selection.model == "frontier-best"


def test_backend_server_applies_layer45_selection_before_provider_creation() -> None:
    from autocode.backend.server import BackendServer
    from autocode.config import AutoCodeConfig, RoutingModelRateConfig

    config = AutoCodeConfig()
    config.layer1.enabled = False
    config.layer2.enabled = False
    config.layer3.enabled = False
    config.routing.model_rates = [
        RoutingModelRateConfig(
            provider="openrouter",
            model="frontier-best",
            tier="frontier",
            input_per_m=3.0,
            output_per_m=10.0,
        )
    ]
    server = BackendServer(config=config)

    layer, request_type, _force = server._select_chat_layer(
        "plan the architecture for a multi service migration with risk analysis"
    )

    assert layer == 4
    assert request_type == RequestType.COMPLEX_TASK.value
    assert config.llm.provider == "openrouter"
    assert config.llm.model == "frontier-best"
    assert server._last_provider_selection is not None
    assert server._last_provider_selection.reason
