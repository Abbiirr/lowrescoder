"""Tests for the hybridcoder → autocode rename and backward compatibility."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
import yaml


class TestAutoCodeImports:
    """Verify that the new 'autocode' import paths work."""

    def test_import_autocode_package(self) -> None:
        import autocode

        assert hasattr(autocode, "__version__")
        assert autocode.__version__ == "0.1.0"

    def test_import_autocode_config(self) -> None:
        from autocode.config import AutoCodeConfig

        config = AutoCodeConfig()
        assert config.llm.provider == "ollama"

    def test_import_autocode_cli(self) -> None:
        from autocode.cli import app

        assert app.info.name == "autocode"

    def test_import_autocode_router(self) -> None:
        from autocode.core.router import RequestRouter

        assert RequestRouter is not None

    def test_import_autocode_llm(self) -> None:
        from autocode.layer4.llm import create_provider

        assert callable(create_provider)


class TestAutoCodeConfigClass:
    """Verify AutoCodeConfig is the primary config class."""

    def test_autocode_config_loads(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AUTOCODE_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)
        from autocode.config import load_config

        config = load_config(project_root=tmp_path)
        assert config.llm.provider == "ollama"

    def test_backward_compat_alias_exists(self) -> None:
        from autocode.config import HybridCoderConfig

        assert HybridCoderConfig is not None
        # Should be the same class
        from autocode.config import AutoCodeConfig

        assert HybridCoderConfig is AutoCodeConfig


class TestLegacyEnvVarFallback:
    """Verify old HYBRIDCODER_* env vars still work with deprecation warning."""

    def test_legacy_provider_env_var(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("HYBRIDCODER_LLM_PROVIDER", "openrouter")
        monkeypatch.delenv("AUTOCODE_LLM_PROVIDER", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from autocode.config import load_config

            config = load_config(project_root=tmp_path)
            assert config.llm.provider == "openrouter"
            deprecation_msgs = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert any("HYBRIDCODER_LLM_PROVIDER" in str(d.message) for d in deprecation_msgs)

    def test_new_env_var_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("AUTOCODE_LLM_PROVIDER", "ollama")
        monkeypatch.setenv("HYBRIDCODER_LLM_PROVIDER", "openrouter")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        from autocode.config import load_config

        config = load_config(project_root=tmp_path)
        assert config.llm.provider == "ollama"


class TestLegacyConfigPathFallback:
    """Verify old .hybridcoder.yaml project config is found with deprecation warning."""

    def test_legacy_project_config_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AUTOCODE_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        # Create only the legacy config file
        legacy_config = tmp_path / ".hybridcoder.yaml"
        legacy_config.write_text(yaml.dump({"llm": {"model": "legacy-model"}}))

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from autocode.config import load_config

            config = load_config(project_root=tmp_path)
            assert config.llm.model == "legacy-model"
            deprecation_msgs = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert any(".hybridcoder.yaml" in str(d.message) for d in deprecation_msgs)

    def test_new_project_config_takes_precedence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AUTOCODE_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        # Create both config files — new one should win
        (tmp_path / ".autocode.yaml").write_text(
            yaml.dump({"llm": {"model": "new-model"}})
        )
        (tmp_path / ".hybridcoder.yaml").write_text(
            yaml.dump({"llm": {"model": "legacy-model"}})
        )

        from autocode.config import load_config

        config = load_config(project_root=tmp_path)
        assert config.llm.model == "new-model"


class TestLegacyGlobalConfigFallback:
    """Verify old ~/.hybridcoder/ global config dir is found with deprecation warning."""

    def test_legacy_global_dir_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When only ~/.hybridcoder/ exists, use it with deprecation warning."""
        import autocode.config as cfg

        new_dir = tmp_path / ".autocode"
        legacy_dir = tmp_path / ".hybridcoder"
        legacy_dir.mkdir()
        legacy_file = legacy_dir / "config.yaml"
        legacy_file.write_text(yaml.dump({"llm": {"model": "global-legacy"}}))

        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_DIR", new_dir)
        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_FILE", new_dir / "config.yaml")
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_DIR", legacy_dir)
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_FILE", legacy_file)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config_dir, config_file = cfg._resolve_global_config()
            assert config_dir == legacy_dir
            assert config_file == legacy_file
            deprecation_msgs = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert any(".hybridcoder" in str(d.message) for d in deprecation_msgs)

    def test_new_global_dir_takes_precedence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both ~/.autocode/ and ~/.hybridcoder/ exist, use new dir, no warning."""
        import autocode.config as cfg

        new_dir = tmp_path / ".autocode"
        new_dir.mkdir()
        legacy_dir = tmp_path / ".hybridcoder"
        legacy_dir.mkdir()

        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_DIR", new_dir)
        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_FILE", new_dir / "config.yaml")
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_DIR", legacy_dir)
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_FILE", legacy_dir / "config.yaml")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config_dir, config_file = cfg._resolve_global_config()
            assert config_dir == new_dir
            deprecation_msgs = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_msgs) == 0

    def test_neither_dir_exists_returns_new(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When neither dir exists, return new path (to be created on first save)."""
        import autocode.config as cfg

        new_dir = tmp_path / ".autocode"
        legacy_dir = tmp_path / ".hybridcoder"
        # Neither exists

        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_DIR", new_dir)
        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_FILE", new_dir / "config.yaml")
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_DIR", legacy_dir)
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_FILE", legacy_dir / "config.yaml")

        config_dir, config_file = cfg._resolve_global_config()
        assert config_dir == new_dir
        assert config_file == new_dir / "config.yaml"

    def test_load_config_uses_legacy_global_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Full integration: load_config reads from legacy global dir when new doesn't exist."""
        import autocode.config as cfg

        new_dir = tmp_path / ".autocode"
        legacy_dir = tmp_path / ".hybridcoder"
        legacy_dir.mkdir()
        (legacy_dir / "config.yaml").write_text(
            yaml.dump({"llm": {"model": "from-legacy-global"}})
        )

        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_DIR", new_dir)
        monkeypatch.setattr(cfg, "_GLOBAL_CONFIG_FILE", new_dir / "config.yaml")
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_DIR", legacy_dir)
        monkeypatch.setattr(cfg, "_LEGACY_CONFIG_FILE", legacy_dir / "config.yaml")
        monkeypatch.delenv("AUTOCODE_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("HYBRIDCODER_LLM_PROVIDER", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            config = cfg.load_config(project_root=tmp_path)
            assert config.llm.model == "from-legacy-global"
            deprecation_msgs = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert any(".hybridcoder" in str(d.message) for d in deprecation_msgs)


class TestNewConfigDefaults:
    """Verify new default paths use .autocode instead of .hybridcoder."""

    def test_default_l3_model_path(self) -> None:
        from autocode.config import AutoCodeConfig

        config = AutoCodeConfig()
        assert ".autocode/" in config.layer3.model_path

    def test_default_db_path(self) -> None:
        from autocode.config import AutoCodeConfig

        config = AutoCodeConfig()
        assert ".autocode/" in config.layer2.db_path

    def test_default_session_db_path(self) -> None:
        from autocode.config import AutoCodeConfig

        config = AutoCodeConfig()
        assert ".autocode/" in config.tui.session_db_path

    def test_global_config_path(self) -> None:
        from autocode.config import get_config_path

        path = get_config_path()
        assert ".autocode" in str(path)


class TestCLIAppName:
    """Verify CLI app is named 'autocode'."""

    def test_cli_app_name(self) -> None:
        from autocode.cli import app

        assert app.info.name == "autocode"

    def test_version_command_output(self) -> None:
        from typer.testing import CliRunner

        from autocode.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "autocode" in result.output
