"""Tests for ProviderRegistry — multi-model provider management."""

from __future__ import annotations

from unittest.mock import MagicMock

from autocode.agent.identity import ModelSpec
from autocode.agent.provider_registry import ProviderRegistry


def test_register_and_get() -> None:
    """Register a provider and retrieve it by name."""
    reg = ProviderRegistry()
    mock_provider = MagicMock()
    spec = ModelSpec.l4_default()

    reg.register("ollama_l4", spec, mock_provider)
    assert reg.get("ollama_l4") is mock_provider


def test_get_unknown_returns_none() -> None:
    """Unknown provider returns None."""
    reg = ProviderRegistry()
    assert reg.get("nonexistent") is None


def test_get_by_layer() -> None:
    """Get first provider matching a layer."""
    reg = ProviderRegistry()
    mock_l3 = MagicMock()
    mock_l4 = MagicMock()

    reg.register("l3", ModelSpec.l3_default(), mock_l3)
    reg.register("l4", ModelSpec.l4_default(), mock_l4)

    assert reg.get_by_layer(3) is mock_l3
    assert reg.get_by_layer(4) is mock_l4
    assert reg.get_by_layer(2) is None


def test_loaded_count() -> None:
    """Track number of loaded providers."""
    reg = ProviderRegistry()
    assert reg.loaded_count == 0

    reg.register("a", ModelSpec.l4_default(), MagicMock())
    assert reg.loaded_count == 1

    reg.register("b", ModelSpec.l3_default(), MagicMock())
    assert reg.loaded_count == 2


def test_unload() -> None:
    """Unload reduces loaded count."""
    reg = ProviderRegistry()
    reg.register("test", ModelSpec.l4_default(), MagicMock())
    assert reg.loaded_count == 1

    reg.unload("test")
    assert reg.loaded_count == 0


def test_max_loaded_eviction() -> None:
    """Evicts oldest when max loaded exceeded."""
    reg = ProviderRegistry()
    reg.MAX_LOADED = 2

    reg.register("a", ModelSpec.l4_default(), MagicMock())
    reg.register("b", ModelSpec.l3_default(), MagicMock())

    # Asking for a third should trigger eviction
    spec = ModelSpec.cloud()
    result = reg.get_for_spec(spec)
    # After eviction, loaded count should be < MAX
    assert reg.loaded_count <= reg.MAX_LOADED


def test_providers_list() -> None:
    """List registered provider names."""
    reg = ProviderRegistry()
    reg.register("ollama", ModelSpec.l4_default(), MagicMock())
    reg.register("openrouter", ModelSpec.cloud(), MagicMock())

    assert set(reg.providers) == {"ollama", "openrouter"}


def test_cleanup() -> None:
    """Cleanup unloads all providers."""
    reg = ProviderRegistry()
    mock = MagicMock()
    mock.cleanup = MagicMock()
    reg.register("test", ModelSpec.l4_default(), mock)

    reg.cleanup()
    assert reg.loaded_count == 0
    mock.cleanup.assert_called_once()


def test_get_for_spec_existing() -> None:
    """get_for_spec returns existing matching provider."""
    reg = ProviderRegistry()
    mock = MagicMock()
    spec = ModelSpec(provider="ollama", model="qwen3:8b", layer=4)
    reg.register("ollama", spec, mock)

    result = reg.get_for_spec(spec)
    assert result is mock
