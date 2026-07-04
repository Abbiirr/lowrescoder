"""Prompt-cache keepalive scheduler primitives."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any

from autocode.agent.cost_dashboard import CostDashboard


@dataclass(frozen=True)
class PromptCacheKeepaliveConfig:
    """Local deterministic keepalive settings."""

    enabled: bool = True
    interval_seconds: int = 300

    def should_enable_for_provider(self, provider_label: str) -> bool:
        """Enable only for provider/model labels that expose prompt caching."""
        label = provider_label.lower()
        return self.enabled and ("anthropic/claude" in label or "claude-" in label)


class PromptCacheKeepalive:
    """Periodically touches the stable prompt prefix to keep provider cache warm."""

    def __init__(
        self,
        *,
        provider: Any,
        static_prompt: str,
        cost_dashboard: CostDashboard | None = None,
        provider_label: str = "",
        config: PromptCacheKeepaliveConfig | None = None,
    ) -> None:
        self.provider = provider
        self.static_prompt = static_prompt
        self.cost_dashboard = cost_dashboard
        self.provider_label = provider_label or str(getattr(provider, "model", ""))
        self.config = config or PromptCacheKeepaliveConfig()
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.running or not self.config.should_enable_for_provider(self.provider_label):
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="autocode-prompt-cache-keepalive")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                await asyncio.wait_for(
                    self._stopped.wait(),
                    timeout=float(self.config.interval_seconds),
                )
            except TimeoutError:
                await self.tick()

    async def tick(self) -> None:
        """Send one keepalive request and record cache-read usage when exposed."""
        response = await self.provider.generate_with_tools(
            [{"role": "system", "content": self.static_prompt}],
            [],
            reasoning_enabled=False,
        )
        usage = getattr(response, "usage", None) or {}
        if self.cost_dashboard is None:
            return
        self.cost_dashboard.record(
            "prompt-cache-keepalive",
            "keepalive",
            "external",
            tokens_in=int(usage.get("prompt_tokens", 0) or 0),
            cached_input_tokens=int(usage.get("cached_input_tokens", 0) or 0),
            tokens_out=int(usage.get("completion_tokens", 0) or 0),
            provider_model=self.provider_label,
        )
