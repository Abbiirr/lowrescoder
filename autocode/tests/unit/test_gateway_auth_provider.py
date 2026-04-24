from __future__ import annotations

from autocode.config import AutoCodeConfig
from autocode.layer4.llm import OpenRouterProvider


def _clear_gateway_env(monkeypatch) -> None:
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


def test_openrouter_provider_uses_litellm_master_key_when_openrouter_key_missing(
    monkeypatch,
) -> None:
    _clear_gateway_env(monkeypatch)
    monkeypatch.setenv("LITELLM_MASTER_KEY", "master-key")

    provider = OpenRouterProvider(AutoCodeConfig())

    assert provider.api_key == "master-key"


def test_openrouter_provider_prefers_litellm_api_key_over_other_gateway_keys(
    monkeypatch,
) -> None:
    _clear_gateway_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "master-key")
    monkeypatch.setenv("LITELLM_API_KEY", "litellm-key")

    provider = OpenRouterProvider(AutoCodeConfig())

    assert provider.api_key == "litellm-key"


def test_openrouter_provider_uses_openrouter_key_for_remote_openrouter_api_base(
    monkeypatch,
) -> None:
    _clear_gateway_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "master-key")
    monkeypatch.setenv("LITELLM_API_KEY", "litellm-key")

    config = AutoCodeConfig()
    config.llm.api_base = "https://openrouter.ai/api/v1"
    provider = OpenRouterProvider(config)

    assert provider.api_key == "openrouter-key"
