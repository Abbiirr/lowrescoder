"""Tests for CostDashboard — token usage tracking and reporting."""

from __future__ import annotations

import warnings

import pytest

from autocode.agent.cost_dashboard import CostDashboard


def _record(
    dash: CostDashboard,
    agent_id: str,
    task_id: str,
    layer: str,
    **kwargs: object,
) -> None:
    """Record usage on the non-deprecated path unless a test overrides it."""
    kwargs.setdefault("provider_model", agent_id)
    dash.record(agent_id, task_id, layer, **kwargs)


def test_record_and_totals() -> None:
    """Recording entries updates totals."""
    dash = CostDashboard()
    _record(dash, "scout", "task-1", "l1", tokens_in=100, tokens_out=0)
    _record(dash, "architect", "task-1", "l4", tokens_in=500, tokens_out=200)

    assert dash.total_tokens == 800
    assert dash.local_tokens == 800
    assert dash.cloud_tokens == 0
    assert dash.total_cost == 0.0  # all local


def test_cloud_cost() -> None:
    """Cloud tokens have estimated cost."""
    dash = CostDashboard()
    _record(dash, "external", "task-1", "external", tokens_in=500000, tokens_out=500000)

    assert dash.cloud_tokens == 1_000_000
    assert dash.total_cost == 3.0  # $3/M tokens


def test_claude_model_uses_separate_input_and_output_rates() -> None:
    """Claude output must not use the old flat $3/M external estimate."""
    dash = CostDashboard()

    dash.record(
        "cloud",
        "task-1",
        "external",
        tokens_in=1_000_000,
        tokens_out=1_000_000,
        provider_model="openrouter / anthropic/claude-3.5-sonnet",
    )

    assert dash.input_cost == pytest.approx(3.0)
    assert dash.output_cost == pytest.approx(15.0)
    assert dash.total_cost == pytest.approx(18.0)


def test_claude_opus_model_uses_opus_rates() -> None:
    """Known Claude Opus labels use the Opus family rates, not Sonnet defaults."""
    dash = CostDashboard()

    dash.record(
        "cloud",
        "task-1",
        "external",
        tokens_in=1_000_000,
        tokens_out=1_000_000,
        provider_model="anthropic/claude-opus-4-7",
    )

    assert dash.input_cost == pytest.approx(5.0)
    assert dash.output_cost == pytest.approx(25.0)
    assert dash.total_cost == pytest.approx(30.0)


def test_unknown_external_model_uses_legacy_external_average() -> None:
    """Unknown external models keep the deterministic legacy fallback."""
    dash = CostDashboard()

    dash.record(
        "cloud",
        "task-1",
        "external",
        tokens_in=500_000,
        tokens_out=500_000,
        provider_model="openrouter / vendor/unknown-model",
    )

    assert dash.input_cost == pytest.approx(1.5)
    assert dash.output_cost == pytest.approx(1.5)
    assert dash.total_cost == pytest.approx(3.0)


def test_missing_provider_model_warns_and_falls_back_to_agent_id() -> None:
    """Missing provider_model is deprecated but still groups by agent id."""
    dash = CostDashboard()

    with pytest.warns(DeprecationWarning, match="provider_model"):
        dash.record(
            "cloud-agent",
            "task-1",
            "external",
            tokens_in=250_000,
            tokens_out=250_000,
            provider_model=None,
        )

    assert dash.by_provider_model()["cloud-agent"]["tokens"] == 500_000
    assert dash.total_cost == pytest.approx(1.5)


def test_explicit_provider_model_does_not_warn() -> None:
    """Callers with explicit provider/model labels are on the non-deprecated path."""
    dash = CostDashboard()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        dash.record(
            "cloud",
            "task-1",
            "external",
            tokens_in=250_000,
            tokens_out=250_000,
            provider_model="openai/gpt-future",
        )

    assert [warning for warning in caught if warning.category is DeprecationWarning] == []


@pytest.mark.parametrize("provider_model", ["", "openai/gpt-future", "not-a-model"])
def test_external_model_fallback_is_deterministic_for_missing_unknown_or_malformed_labels(
    provider_model: str | None,
) -> None:
    """Missing, unknown, and malformed external labels never crash or return NaN."""
    dash = CostDashboard()

    dash.record(
        "cloud",
        "task-1",
        "external",
        tokens_in=250_000,
        tokens_out=250_000,
        provider_model=provider_model,
    )

    assert dash.input_cost == pytest.approx(0.75)
    assert dash.output_cost == pytest.approx(0.75)
    assert dash.total_cost == pytest.approx(1.5)


def test_by_agent() -> None:
    """Group by agent."""
    dash = CostDashboard()
    _record(dash, "scout", "t1", "l1", tokens_in=100)
    _record(dash, "scout", "t2", "l1", tokens_in=200)
    _record(dash, "architect", "t1", "l4", tokens_in=500)

    by_agent = dash.by_agent()
    assert by_agent["scout"] == 300
    assert by_agent["architect"] == 500


def test_by_task() -> None:
    """Group by task."""
    dash = CostDashboard()
    _record(dash, "scout", "task-1", "l1", tokens_in=100)
    _record(dash, "arch", "task-1", "l4", tokens_in=500)
    _record(dash, "scout", "task-2", "l2", tokens_in=200)

    by_task = dash.by_task()
    assert by_task["task-1"] == 600
    assert by_task["task-2"] == 200


def test_by_layer() -> None:
    """Group by layer."""
    dash = CostDashboard()
    _record(dash, "a", "t1", "l1", tokens_in=100)
    _record(dash, "a", "t1", "l4", tokens_in=500)
    _record(dash, "a", "t2", "l4", tokens_in=300)

    by_layer = dash.by_layer()
    assert by_layer["l1"] == 100
    assert by_layer["l4"] == 800


def test_summary() -> None:
    """Summary contains key information."""
    dash = CostDashboard()
    _record(dash, "scout", "t1", "l1", tokens_in=1000)
    _record(dash, "arch", "t1", "l4", tokens_in=5000, tokens_out=2000)

    summary = dash.summary()
    assert "8,000" in summary  # total
    assert "Local (free)" in summary
    assert "$0.0000" in summary  # all local = free
    assert "scout" in summary
    assert "arch" in summary


def test_mixed_local_cloud() -> None:
    """Mixed local and cloud usage."""
    dash = CostDashboard()
    _record(dash, "scout", "t1", "l1", tokens_in=1000)
    _record(dash, "cloud", "t1", "external", tokens_in=2000, tokens_out=1000)

    assert dash.local_tokens == 1000
    assert dash.cloud_tokens == 3000
    assert dash.total_cost > 0


def test_check_limit_unset_never_fires() -> None:
    """Unset cost limit never reports a threshold crossing."""
    dash = CostDashboard()
    _record(dash, "cloud", "t1", "external", tokens_in=1_000_000)

    crossed, total_usd, threshold_usd = dash.check_limit(None)

    assert crossed is False
    assert total_usd == 3.0
    assert threshold_usd == 0.0


def test_check_limit_fires_once_until_threshold_raised_and_re_crossed() -> None:
    """Cost limit warning fires once, then fires again only for a raised limit."""
    dash = CostDashboard()
    _record(dash, "cloud", "t1", "external", tokens_in=2_000_000)

    assert dash.check_limit(5.0) == (True, 6.0, 5.0)
    assert dash.check_limit(5.0) == (False, 6.0, 5.0)
    assert dash.check_limit(10.0) == (False, 6.0, 10.0)

    _record(dash, "cloud", "t1", "external", tokens_in=2_000_000)

    assert dash.check_limit(10.0) == (True, 12.0, 10.0)
    assert dash.check_limit(10.0) == (False, 12.0, 10.0)


def test_check_limit_returns_current_total_and_threshold_before_crossing() -> None:
    """Limit check exposes current total and threshold for warning formatting."""
    dash = CostDashboard()
    _record(dash, "cloud", "t1", "external", tokens_in=1_000_000)

    crossed, total_usd, threshold_usd = dash.check_limit(5.0)

    assert crossed is False
    assert total_usd == 3.0
    assert threshold_usd == 5.0


def test_record_with_cached_input_tokens() -> None:
    """Cached prompt tokens are tracked separately and priced at cache-read rate."""
    dash = CostDashboard()

    _record(
        dash,
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

    _record(
        dash,
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

    _record(dash, "cloud", "t1", "external", tokens_out=500)

    assert dash.cache_hit_ratio == 0.0
