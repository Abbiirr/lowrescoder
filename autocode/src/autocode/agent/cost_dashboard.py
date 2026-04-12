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
    tokens_out: int = 0
    cost_usd: float = 0.0
    is_local: bool = True

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


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

    def __init__(self) -> None:
        self._entries: list[CostEntry] = []

    def record(
        self,
        agent_id: str,
        task_id: str,
        layer: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """Record token usage for an agent/task."""
        is_local = layer in ("l1", "l2", "l3", "l4")
        cost_per_m = self.COST_PER_M_TOKENS.get(layer, 0.0)
        total = tokens_in + tokens_out
        cost = (total / 1_000_000) * cost_per_m

        self._entries.append(CostEntry(
            agent_id=agent_id,
            task_id=task_id,
            layer=layer,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            is_local=is_local,
        ))

    @property
    def total_tokens(self) -> int:
        """Total tokens across all entries."""
        return sum(e.total_tokens for e in self._entries)

    @property
    def total_cost(self) -> float:
        """Total estimated cost in USD."""
        return sum(e.cost_usd for e in self._entries)

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
