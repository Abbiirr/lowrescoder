"""Multi-model provider registry.

Manages LLM providers with lazy loading and VRAM constraints.
Max 2 models loaded simultaneously (L3 + L4).
Sequential loading on 8GB VRAM: load Architect → unload → load Editor → unload.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autocode.agent.identity import ModelSpec


@dataclass
class ProviderInfo:
    """Metadata about a loaded provider."""

    spec: ModelSpec
    provider: Any  # LLMProvider or L3Provider
    loaded: bool = True


class ProviderRegistry:
    """Manages LLM providers with lazy loading and VRAM budget.

    Constraint: max 2 models loaded at once (L3 + L4).
    On 8GB VRAM, use sequential loading only.
    """

    MAX_LOADED: int = 2

    def __init__(self) -> None:
        self._providers: dict[str, ProviderInfo] = {}
        self._load_order: list[str] = []

    def register(self, name: str, spec: ModelSpec, provider: Any) -> None:
        """Register a provider with its model spec."""
        self._providers[name] = ProviderInfo(spec=spec, provider=provider)
        self._load_order.append(name)

    def get(self, name: str) -> Any | None:
        """Get a provider by name."""
        info = self._providers.get(name)
        return info.provider if info else None

    def get_by_layer(self, layer: int) -> Any | None:
        """Get the first provider matching a layer."""
        for info in self._providers.values():
            if info.spec.layer == layer and info.loaded:
                return info.provider
        return None

    def get_for_spec(self, spec: ModelSpec) -> Any | None:
        """Get or create a provider matching a model spec."""
        # Check existing providers
        for info in self._providers.values():
            if (
                info.spec.provider == spec.provider
                and info.spec.model == spec.model
                and info.loaded
            ):
                return info.provider

        # Would need to create — check VRAM budget
        loaded_count = sum(1 for i in self._providers.values() if i.loaded)
        if loaded_count >= self.MAX_LOADED:
            # Evict oldest loaded provider
            self._evict_oldest()

        return None  # Caller must create and register

    @property
    def loaded_count(self) -> int:
        """Number of currently loaded providers."""
        return sum(1 for i in self._providers.values() if i.loaded)

    @property
    def providers(self) -> list[str]:
        """List of registered provider names."""
        return list(self._providers.keys())

    def unload(self, name: str) -> None:
        """Unload a provider to free VRAM."""
        if name in self._providers:
            info = self._providers[name]
            if hasattr(info.provider, "cleanup"):
                info.provider.cleanup()
            info.loaded = False

    def _evict_oldest(self) -> None:
        """Evict the oldest loaded provider to make room."""
        for name in self._load_order:
            info = self._providers.get(name)
            if info and info.loaded:
                self.unload(name)
                return

    def cleanup(self) -> None:
        """Unload all providers."""
        for name in list(self._providers.keys()):
            self.unload(name)
