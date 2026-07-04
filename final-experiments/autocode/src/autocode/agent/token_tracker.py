"""Session-level token usage tracking.

Tracks prompt and completion tokens across multiple LLM calls,
with per-provider breakdown (L3 vs L4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenUsage:
    """Token counts for a single API call or accumulated session."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_input_tokens: int = 0
    cache_creation_tokens: int = 0
    reasoning_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def billable_input_cost_factor(self) -> float:
        """Weighted prompt-cost multiplier including cache reads/writes."""
        if self.prompt_tokens <= 0:
            return 1.0
        regular_tokens = max(0, self.prompt_tokens - self.cached_input_tokens)
        weighted = (
            regular_tokens
            + self.cached_input_tokens * 0.10
            + self.cache_creation_tokens * 1.25
        )
        return round(weighted / self.prompt_tokens, 3)


@dataclass
class TokenTracker:
    """Accumulates token usage across a session, with per-provider breakdown."""

    _totals: TokenUsage = field(default_factory=TokenUsage)
    _by_provider: dict[str, TokenUsage] = field(default_factory=dict)
    _call_count: int = 0

    cost_dashboard: Any = field(default=None, repr=False)
    cost_limit_usd: float | None = field(default=None, repr=False)
    _agent_id: str = field(default="default", repr=False)
    _task_id: str = field(default="", repr=False)
    _last_cost_limit_warning: tuple[float, float] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        provider: str = "default",
        cached_input_tokens: int = 0,
        cache_creation_tokens: int = 0,
        reasoning_tokens: int = 0,
    ) -> None:
        """Record token usage from an API call."""
        cached_input_tokens = min(max(0, int(cached_input_tokens)), max(0, int(prompt_tokens)))
        cache_creation_tokens = max(0, int(cache_creation_tokens))
        reasoning_tokens = max(0, int(reasoning_tokens))
        self._totals.prompt_tokens += prompt_tokens
        self._totals.completion_tokens += completion_tokens
        self._totals.cached_input_tokens += cached_input_tokens
        self._totals.cache_creation_tokens += cache_creation_tokens
        self._totals.reasoning_tokens += reasoning_tokens
        self._call_count += 1

        if provider not in self._by_provider:
            self._by_provider[provider] = TokenUsage()
        self._by_provider[provider].prompt_tokens += prompt_tokens
        self._by_provider[provider].completion_tokens += completion_tokens
        self._by_provider[provider].cached_input_tokens += cached_input_tokens
        self._by_provider[provider].cache_creation_tokens += cache_creation_tokens
        self._by_provider[provider].reasoning_tokens += reasoning_tokens

        # Forward to CostDashboard if wired
        if self.cost_dashboard is not None:
            layer = self._provider_to_layer(provider)
            uncached_prompt_tokens = max(0, prompt_tokens - cached_input_tokens)
            self.cost_dashboard.record(
                agent_id=self._agent_id,
                task_id=self._task_id or "session",
                layer=layer,
                tokens_in=uncached_prompt_tokens,
                cached_input_tokens=cached_input_tokens,
                tokens_out=completion_tokens,
                provider_model=provider,
            )
            crossed, total_usd, threshold_usd = self.cost_dashboard.check_limit(
                self.cost_limit_usd
            )
            if crossed:
                self._last_cost_limit_warning = (total_usd, threshold_usd)

    def record_cache(
        self,
        provider: str,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> None:
        """Record cache usage that arrives outside the normal usage block."""
        cache_read_tokens = max(0, int(cache_read_tokens))
        cache_write_tokens = max(0, int(cache_write_tokens))
        self._totals.cached_input_tokens += cache_read_tokens
        self._totals.cache_creation_tokens += cache_write_tokens

        if provider not in self._by_provider:
            self._by_provider[provider] = TokenUsage()
        self._by_provider[provider].cached_input_tokens += cache_read_tokens
        self._by_provider[provider].cache_creation_tokens += cache_write_tokens

    @staticmethod
    def _provider_to_layer(provider: str) -> str:
        """Map provider name to cost layer."""
        p = provider.lower()
        if "openrouter" in p or "external" in p:
            return "external"
        if "llama" in p or "l3" in p:
            return "l3"
        return "l4"  # default for ollama and others

    @property
    def total(self) -> TokenUsage:
        """Total token usage across all providers."""
        return self._totals

    @property
    def call_count(self) -> int:
        """Number of API calls tracked."""
        return self._call_count

    def by_provider(self, provider: str) -> TokenUsage:
        """Token usage for a specific provider."""
        return self._by_provider.get(provider, TokenUsage())

    def to_snapshot(self) -> dict[str, Any]:
        """Serialize counters for session persistence."""
        return {
            "prompt_tokens": self._totals.prompt_tokens,
            "completion_tokens": self._totals.completion_tokens,
            "cached_input_tokens": self._totals.cached_input_tokens,
            "cache_creation_tokens": self._totals.cache_creation_tokens,
            "reasoning_tokens": self._totals.reasoning_tokens,
            "call_count": self._call_count,
            "per_provider": {
                provider: {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "cached_input_tokens": usage.cached_input_tokens,
                    "cache_creation_tokens": usage.cache_creation_tokens,
                    "reasoning_tokens": usage.reasoning_tokens,
                }
                for provider, usage in self._by_provider.items()
            },
        }

    def load_snapshot(self, snapshot: dict[str, Any] | None) -> None:
        """Hydrate counters from a persisted session snapshot."""
        if not snapshot:
            return
        self._totals = TokenUsage(
            prompt_tokens=int(snapshot.get("prompt_tokens") or 0),
            completion_tokens=int(snapshot.get("completion_tokens") or 0),
            cached_input_tokens=int(snapshot.get("cached_input_tokens") or 0),
            cache_creation_tokens=int(snapshot.get("cache_creation_tokens") or 0),
            reasoning_tokens=int(snapshot.get("reasoning_tokens") or 0),
        )
        self._call_count = int(snapshot.get("call_count") or 0)
        self._by_provider.clear()
        per_provider = snapshot.get("per_provider") or {}
        if isinstance(per_provider, dict):
            for provider, raw in per_provider.items():
                if not isinstance(raw, dict):
                    continue
                self._by_provider[str(provider)] = TokenUsage(
                    prompt_tokens=int(raw.get("prompt_tokens") or 0),
                    completion_tokens=int(raw.get("completion_tokens") or 0),
                    cached_input_tokens=int(raw.get("cached_input_tokens") or 0),
                    cache_creation_tokens=int(raw.get("cache_creation_tokens") or 0),
                    reasoning_tokens=int(raw.get("reasoning_tokens") or 0),
                )

    @property
    def providers(self) -> list[str]:
        """List of providers with recorded usage."""
        return list(self._by_provider.keys())

    def pop_cost_limit_warning(self) -> tuple[float, float] | None:
        """Return and clear the latest cost limit warning, if any."""
        warning = self._last_cost_limit_warning
        self._last_cost_limit_warning = None
        return warning

    def summary(self) -> str:
        """Human-readable summary of token usage."""
        parts = [
            f"Tokens: {self._totals.total_tokens:,} "
            f"(prompt: {self._totals.prompt_tokens:,}, "
            f"completion: {self._totals.completion_tokens:,})",
            f"API calls: {self._call_count}",
        ]
        if len(self._by_provider) > 1:
            for provider, usage in sorted(self._by_provider.items()):
                parts.append(
                    f"  {provider}: {usage.total_tokens:,} tokens"
                )
        if self._totals.cached_input_tokens or self._totals.cache_creation_tokens:
            parts.append(
                "Cache: "
                f"{self._totals.cached_input_tokens:,} reads, "
                f"{self._totals.cache_creation_tokens:,} writes, "
                f"{self._totals.billable_input_cost_factor:.3f}x effective input"
            )
        if self._totals.reasoning_tokens:
            parts.append(f"Reasoning: {self._totals.reasoning_tokens:,} tokens")
        return "\n".join(parts)

    def reset(self) -> None:
        """Reset all counters."""
        self._totals = TokenUsage()
        self._by_provider.clear()
        self._call_count = 0
        self._last_cost_limit_warning = None
