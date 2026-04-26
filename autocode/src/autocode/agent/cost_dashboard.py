"""Cost Dashboard — token breakdown per agent, per task, local vs cloud.

Provides visibility into where tokens are being spent across
the multi-agent system.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostEntry:
    """A single cost tracking entry."""

    agent_id: str
    task_id: str
    layer: str  # "l1", "l2", "l3", "l4", "external"
    tokens_in: int = 0
    cached_input_tokens: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    is_local: bool = True
    provider_model: str = ""

    @property
    def total_input_tokens(self) -> int:
        return self.tokens_in + self.cached_input_tokens

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.tokens_out


class CostDashboard:
    """Tracks and reports token usage across agents and tasks.

    Zero-cost local operations are tracked for visibility.
    Cloud operations are tracked with estimated USD cost.
    """

    # Cost per 1M tokens (approximate, varies by provider)
    COST_PER_M_TOKENS: dict[str, float] = {
        "l1": 0.0,
        "l2": 0.0,
        "l3": 0.0,
        "l4": 0.0,
        "external": 3.0,  # ~$3/M tokens average cloud cost
    }
    CACHED_COST_PER_M_TOKENS: dict[str, float] = {
        "l1": 0.0,
        "l2": 0.0,
        "l3": 0.0,
        "l4": 0.0,
        "external": 0.3,  # cache reads are typically ~10% of prompt cost
    }

    def __init__(self) -> None:
        self._entries: list[CostEntry] = []
        self._warned_threshold_usd: float | None = None

    def record(
        self,
        agent_id: str,
        task_id: str,
        layer: str,
        tokens_in: int = 0,
        cached_input_tokens: int = 0,
        tokens_out: int = 0,
        provider_model: str | None = None,
    ) -> None:
        """Record token usage for an agent/task."""
        is_local = layer in ("l1", "l2", "l3", "l4")
        cost_per_m = self.COST_PER_M_TOKENS.get(layer, 0.0)
        cached_cost_per_m = self.CACHED_COST_PER_M_TOKENS.get(layer, 0.0)
        tokens_in = max(0, int(tokens_in))
        cached_input_tokens = max(0, int(cached_input_tokens))
        tokens_out = max(0, int(tokens_out))
        input_cost = (
            (tokens_in / 1_000_000) * cost_per_m
            + (cached_input_tokens / 1_000_000) * cached_cost_per_m
        )
        output_cost = (tokens_out / 1_000_000) * cost_per_m
        cost = input_cost + output_cost

        self._entries.append(CostEntry(
            agent_id=agent_id,
            task_id=task_id,
            layer=layer,
            tokens_in=tokens_in,
            cached_input_tokens=cached_input_tokens,
            tokens_out=tokens_out,
            cost_usd=cost,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            is_local=is_local,
            provider_model=provider_model or agent_id,
        ))

    @property
    def entries(self) -> tuple[CostEntry, ...]:
        """Recorded cost entries."""
        return tuple(self._entries)

    @property
    def total_tokens(self) -> int:
        """Total tokens across all entries."""
        return sum(e.total_tokens for e in self._entries)

    @property
    def total_cost(self) -> float:
        """Total estimated cost in USD."""
        return sum(e.cost_usd for e in self._entries)

    @property
    def input_cost(self) -> float:
        """Total estimated input-side cost in USD."""
        return sum(e.input_cost_usd for e in self._entries)

    @property
    def output_cost(self) -> float:
        """Total estimated output-side cost in USD."""
        return sum(e.output_cost_usd for e in self._entries)

    @property
    def total_uncached_input_tokens(self) -> int:
        """Input tokens charged at regular prompt rate."""
        return sum(e.tokens_in for e in self._entries)

    @property
    def total_cached_input_tokens(self) -> int:
        """Input tokens charged at cache-read rate."""
        return sum(e.cached_input_tokens for e in self._entries)

    @property
    def total_input_tokens(self) -> int:
        """All input tokens, including cached prompt reads."""
        return self.total_uncached_input_tokens + self.total_cached_input_tokens

    @property
    def total_output_tokens(self) -> int:
        """All generated output tokens."""
        return sum(e.tokens_out for e in self._entries)

    @property
    def cache_hit_ratio(self) -> float:
        """Ratio of cached prompt tokens to all prompt tokens."""
        total_input = self.total_input_tokens
        if total_input <= 0:
            return 0.0
        return self.total_cached_input_tokens / total_input

    @property
    def estimated_cache_savings_usd(self) -> float:
        """Estimated savings versus paying full prompt rate for cached tokens."""
        savings = 0.0
        for entry in self._entries:
            regular = self.COST_PER_M_TOKENS.get(entry.layer, 0.0)
            cached = self.CACHED_COST_PER_M_TOKENS.get(entry.layer, 0.0)
            savings += (entry.cached_input_tokens / 1_000_000) * max(0.0, regular - cached)
        return savings

    def check_limit(self, threshold_usd: float | None) -> tuple[bool, float, float]:
        """Return whether the session cost limit was newly crossed.

        The warning is one-shot per threshold. If the user raises the threshold,
        the dashboard can warn again only once the new threshold is crossed.
        """
        total_usd = self.total_cost
        if threshold_usd is None or threshold_usd <= 0:
            return False, total_usd, 0.0

        threshold = float(threshold_usd)
        already_warned = (
            self._warned_threshold_usd is not None
            and threshold <= self._warned_threshold_usd
        )
        crossed = total_usd >= threshold and not already_warned
        if crossed:
            self._warned_threshold_usd = threshold
        return crossed, total_usd, threshold

    @property
    def local_tokens(self) -> int:
        """Tokens used by local models (free)."""
        return sum(e.total_tokens for e in self._entries if e.is_local)

    @property
    def cloud_tokens(self) -> int:
        """Tokens used by cloud models (paid)."""
        return sum(e.total_tokens for e in self._entries if not e.is_local)

    def by_agent(self) -> dict[str, int]:
        """Token usage grouped by agent."""
        result: dict[str, int] = {}
        for e in self._entries:
            result[e.agent_id] = result.get(e.agent_id, 0) + e.total_tokens
        return result

    def by_task(self) -> dict[str, int]:
        """Token usage grouped by task."""
        result: dict[str, int] = {}
        for e in self._entries:
            result[e.task_id] = result.get(e.task_id, 0) + e.total_tokens
        return result

    def by_layer(self) -> dict[str, int]:
        """Token usage grouped by layer."""
        result: dict[str, int] = {}
        for e in self._entries:
            result[e.layer] = result.get(e.layer, 0) + e.total_tokens
        return result

    def by_provider_model(self) -> dict[str, dict[str, float]]:
        """Usage grouped by provider/model label."""
        result: dict[str, dict[str, float]] = {}
        for entry in self._entries:
            key = entry.provider_model or entry.agent_id
            bucket = result.setdefault(key, {"tokens": 0.0, "cost": 0.0})
            bucket["tokens"] += entry.total_tokens
            bucket["cost"] += entry.cost_usd
        return result

    def summary(self) -> str:
        """Human-readable cost summary."""
        lines = ["Cost Dashboard", "=" * 40]
        lines.append(f"Total tokens: {self.total_tokens:,}")
        lines.append(f"  Local (free): {self.local_tokens:,}")
        lines.append(f"  Cloud (paid): {self.cloud_tokens:,}")
        lines.append(f"Estimated cost: ${self.total_cost:.4f}")

        by_agent = self.by_agent()
        if by_agent:
            lines.append("\nPer agent:")
            for agent, tokens in sorted(by_agent.items(), key=lambda x: -x[1]):
                lines.append(f"  {agent}: {tokens:,} tokens")

        by_layer = self.by_layer()
        if by_layer:
            lines.append("\nPer layer:")
            for layer, tokens in sorted(by_layer.items()):
                cost = (tokens / 1_000_000) * self.COST_PER_M_TOKENS.get(layer, 0)
                lines.append(f"  {layer}: {tokens:,} tokens (${cost:.4f})")

        return "\n".join(lines)
