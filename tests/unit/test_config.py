"""Tests for HybridCoder configuration system."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hybridcoder.config import (
    HybridCoderConfig,
    LLMConfig,
    check_config,
    load_config,
    save_config,
)


class TestConfigDefaults:
    """Test default configuration values."""

    def test_default_provider_is_ollama(self) -> None:
        config = HybridCoderConfig()
        assert config.llm.provider == "ollama"

    def test_default_model_is_qwen3(self) -> None:
        config = HybridCoderConfig()
        assert config.llm.model == "qwen3:8b"

    def test_default_temperature(self) -> None:
        config = HybridCoderConfig()
        assert config.llm.temperature == 0.2

    def test_all_layers_enabled_by_default(self) -> None:
        config = HybridCoderConfig()
        assert config.layer1.enabled is True
        assert config.layer2.enabled is True
        assert config.layer3.enabled is True
        assert config.layer4.enabled is True

    def test_edit_defaults(self) -> None:
        config = HybridCoderConfig()
        assert config.edit.format == "whole_file"
        assert config.edit.fuzzy_threshold == 0.8
        assert config.edit.auto_commit is True

    def test_shell_defaults(self) -> None:
        config = HybridCoderConfig()
        assert "pytest" in config.shell.allowed_commands
        assert "rm -rf" in config.shell.blocked_commands
        assert config.shell.allow_network is False

    def test_ui_defaults(self) -> None:
        config = HybridCoderConfig()
        assert config.ui.stream_output is True
        assert config.ui.confirm_edits is True


class TestConfigValidation:
    """Test Pydantic validation on config fields."""

    def test_temperature_bounds(self) -> None:
        with pytest.raises(Exception):
            LLMConfig(temperature=-1.0)
        with pytest.raises(Exception):
            LLMConfig(temperature=3.0)

    def test_valid_providers(self) -> None:
        LLMConfig(provider="ollama")
        LLMConfig(provider="openrouter")
        with pytest.raises(Exception):
            LLMConfig(provider="invalid")  # type: ignore[arg-type]


class TestConfigYAML:
    """Test YAML save/load."""

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        config = HybridCoderConfig()
        config.llm.model = "test-model"
        config.ui.verbose = True

        path = save_config(config, tmp_path / "config.yaml")
        assert path.exists()

        with open(path) as f:
            data = yaml.safe_load(f)

        loaded = HybridCoderConfig.model_validate(data)
        assert loaded.llm.model == "test-model"
        assert loaded.ui.verbose is True

    def test_load_from_project_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        project_config = tmp_path / ".hybridcoder.yaml"
        project_config.write_text(
            yaml.dump({"llm": {"model": "custom-model", "temperature": 0.5}})
        )
        config = load_config(project_root=tmp_path)
        assert config.llm.model == "custom-model"
        assert config.llm.temperature == 0.5

    def test_load_missing_yaml_returns_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        config = load_config(project_root=tmp_path)
        assert config.llm.model == "qwen3:8b"


class TestConfigEnvOverrides:
    """Test environment variable overrides."""

    def test_provider_env_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("HYBRIDCODER_LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        config = load_config(project_root=tmp_path)
        assert config.llm.provider == "openrouter"

    def test_openrouter_env_configures_api_base(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("HYBRIDCODER_LLM_PROVIDER", "openrouter")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.setenv("OPENROUTER_MODEL", "test/model")
        config = load_config(project_root=tmp_path)
        assert config.llm.api_base == "https://openrouter.ai/api/v1"
        assert config.llm.model == "test/model"

    def test_no_openrouter_without_explicit_opt_in(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        config = load_config(project_root=tmp_path)
        assert config.llm.provider == "ollama"  # local-first default


class TestConfigCheck:
    """Test configuration validation warnings."""

    def test_ollama_bad_url(self) -> None:
        config = HybridCoderConfig()
        config.llm.api_base = "not-a-url"
        warnings = check_config(config)
        assert any("URL" in w for w in warnings)

    def test_openrouter_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        config = HybridCoderConfig()
        config.llm.provider = "openrouter"
        warnings = check_config(config)
        assert any("OPENROUTER_API_KEY" in w for w in warnings)

    def test_clean_config_no_warnings(self) -> None:
        config = HybridCoderConfig()
        config.layer3.enabled = False  # Skip L3 model check
        warnings = check_config(config)
        assert len(warnings) == 0


class TestOpenRouterApiBase:
    """Test OpenRouter api_base auto-correction."""

    def test_yaml_openrouter_gets_correct_api_base(self, tmp_path: Path) -> None:
        """If YAML sets provider=openrouter, api_base should auto-correct from Ollama default."""
        project_config = tmp_path / ".hybridcoder.yaml"
        project_config.write_text(yaml.dump({"llm": {"provider": "openrouter"}}))
        config = load_config(project_root=tmp_path)
        assert config.llm.api_base == "https://openrouter.ai/api/v1"

    def test_yaml_openrouter_preserves_custom_api_base(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If YAML sets both provider and api_base, don't override."""
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        project_config = tmp_path / ".hybridcoder.yaml"
        project_config.write_text(
            yaml.dump({"llm": {"provider": "openrouter", "api_base": "https://custom.api/v1"}})
        )
        config = load_config(project_root=tmp_path)
        assert config.llm.api_base == "https://custom.api/v1"
