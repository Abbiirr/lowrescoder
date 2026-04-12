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

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class TokenTracker:
    """Accumulates token usage across a session, with per-provider breakdown."""

    _totals: TokenUsage = field(default_factory=TokenUsage)
    _by_provider: dict[str, TokenUsage] = field(default_factory=dict)
    _call_count: int = 0

    _cost_dashboard: Any = field(default=None, repr=False)
    _agent_id: str = field(default="default", repr=False)
    _task_id: str = field(default="", repr=False)

    def record(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        provider: str = "default",
    ) -> None:
        """Record token usage from an API call."""
        self._totals.prompt_tokens += prompt_tokens
        self._totals.completion_tokens += completion_tokens
        self._call_count += 1

        if provider not in self._by_provider:
            self._by_provider[provider] = TokenUsage()
        self._by_provider[provider].prompt_tokens += prompt_tokens
        self._by_provider[provider].completion_tokens += completion_tokens

        # Forward to CostDashboard if wired
        if self._cost_dashboard is not None:
            layer = self._provider_to_layer(provider)
            self._cost_dashboard.record(
                agent_id=self._agent_id,
                task_id=self._task_id or "session",
                layer=layer,
                tokens_in=prompt_tokens,
                tokens_out=completion_tokens,
            )

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

    @property
    def providers(self) -> list[str]:
        """List of providers with recorded usage."""
        return list(self._by_provider.keys())

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
        return "\n".join(parts)

    def reset(self) -> None:
        """Reset all counters."""
        self._totals = TokenUsage()
        self._by_provider.clear()
        self._call_count = 0
