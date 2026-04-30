"""Cost-aware provider/model router for Layer 4.5.

The router is deliberately deterministic: it classifies the already-routed
task into a model tier, then picks the cheapest provider/model in that tier
using a cache-forward cost hook.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autocode.core.types import RequestType


@dataclass(frozen=True)
class ModelRate:
    """Provider/model price and tier metadata."""

    provider: str
    model: str
    tier: str
    input_per_m: float
    output_per_m: float


@dataclass(frozen=True)
class ProviderSelection:
    """Selected provider/model with explainability metadata."""

    provider: str
    model: str
    tier: str
    reason: str
    estimated_cost_delta: float
    estimated_cost: float


class Layer45Router:
    """Select a Layer 4 provider/model from task class and estimated cost."""

    DEFAULT_TIER_MAP: dict[str, str] = {
        RequestType.SIMPLE_EDIT.value: "cheap",
        RequestType.CHAT.value: "mid",
        RequestType.COMPLEX_TASK.value: "frontier",
        "bug_fix": "mid",
        "refactor": "frontier",
        "architecture": "frontier",
        "planning": "frontier",
    }

    def __init__(
        self,
        *,
        rate_table: list[ModelRate],
        default_tier_map: dict[str, str] | None = None,
        low_confidence_tier: str = "mid",
        fallback_tier: str = "mid",
        low_confidence_threshold: float = 0.5,
    ) -> None:
        if not rate_table:
            raise ValueError("Layer45Router requires at least one model rate")
        self._rate_table = list(rate_table)
        self._default_tier_map = {
            **self.DEFAULT_TIER_MAP,
            **(default_tier_map or {}),
        }
        self._low_confidence_tier = low_confidence_tier
        self._fallback_tier = fallback_tier
        self._low_confidence_threshold = low_confidence_threshold

    @classmethod
    def from_config(cls, config: Any) -> "Layer45Router":
        """Build a router from AutoCode config, preserving current model by default."""
        routing = getattr(config, "routing", None)
        configured_rates = getattr(routing, "model_rates", []) if routing else []
        rates = [
            ModelRate(
                provider=rate.provider,
                model=rate.model,
                tier=rate.tier,
                input_per_m=rate.input_per_m,
                output_per_m=rate.output_per_m,
            )
            for rate in configured_rates
        ]
        if not rates:
            current_provider = getattr(config.llm, "provider", "ollama")
            current_model = getattr(config.llm, "model", "")
            rates = [
                ModelRate(
                    provider=current_provider,
                    model=current_model,
                    tier=tier,
                    input_per_m=0.0,
                    output_per_m=0.0,
                )
                for tier in ("cheap", "mid", "frontier")
            ]
        default_tier_map = getattr(routing, "default_tier_map", None) if routing else None
        low_confidence_tier = (
            getattr(routing, "low_confidence_tier", "mid") if routing else "mid"
        )
        fallback_tier = getattr(routing, "fallback_tier", "mid") if routing else "mid"
        return cls(
            rate_table=rates,
            default_tier_map=default_tier_map,
            low_confidence_tier=low_confidence_tier,
            fallback_tier=fallback_tier,
        )

    def select(
        self,
        task_class: RequestType | str,
        *,
        confidence: float,
        billable_input_cost_factor: float = 1.0,
        estimated_input_tokens: int = 4_000,
        estimated_output_tokens: int = 1_000,
    ) -> ProviderSelection:
        """Return the deterministic provider/model selection for a task."""
        task_key = self._task_key(task_class)
        if confidence < self._low_confidence_threshold:
            tier = self._low_confidence_tier
            reason_prefix = (
                f"low confidence {confidence:.2f}; fallback tier '{tier}' selected"
            )
        else:
            tier = self._default_tier_map.get(task_key, self._fallback_tier)
            reason_prefix = (
                f"configured task tier '{tier}' selected for task_class={task_key}"
            )

        candidates = [rate for rate in self._rate_table if rate.tier == tier]
        if not candidates:
            candidates = list(self._rate_table)
            reason_prefix += "; requested tier unavailable, using full rate table"

        ranked = sorted(
            (
                (
                    self.estimate_cost(
                        rate,
                        billable_input_cost_factor=billable_input_cost_factor,
                        estimated_input_tokens=estimated_input_tokens,
                        estimated_output_tokens=estimated_output_tokens,
                    ),
                    rate,
                )
                for rate in candidates
            ),
            key=lambda item: (item[0], item[1].provider, item[1].model),
        )
        best_cost, best = ranked[0]
        next_best_cost = ranked[1][0] if len(ranked) > 1 else best_cost
        delta = max(0.0, next_best_cost - best_cost)
        reason = (
            f"{reason_prefix}; selected {best.provider}/{best.model}; "
            f"billable_input_cost_factor={billable_input_cost_factor:g}; "
            f"estimated_cost_delta={delta:.6f}"
        )
        return ProviderSelection(
            provider=best.provider,
            model=best.model,
            tier=best.tier,
            reason=reason,
            estimated_cost_delta=delta,
            estimated_cost=best_cost,
        )

    @staticmethod
    def estimate_cost(
        rate: ModelRate,
        *,
        billable_input_cost_factor: float,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
    ) -> float:
        """Estimate USD cost using the C6.G6 cache-multiplier hook."""
        safe_factor = max(0.0, float(billable_input_cost_factor))
        input_cost = (
            max(0, estimated_input_tokens)
            / 1_000_000
            * max(0.0, rate.input_per_m)
            * safe_factor
        )
        output_cost = (
            max(0, estimated_output_tokens) / 1_000_000 * max(0.0, rate.output_per_m)
        )
        return input_cost + output_cost

    @staticmethod
    def _task_key(task_class: RequestType | str) -> str:
        if isinstance(task_class, RequestType):
            return task_class.value
        return str(task_class).strip().lower() or RequestType.CHAT.value
