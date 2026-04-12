"""Tests for PyInstaller packaging configuration."""

from __future__ import annotations

from pathlib import Path


def test_spec_file_exists() -> None:
    """PyInstaller spec file exists."""
    spec = Path(__file__).resolve().parents[2] / "autocode.spec"
    assert spec.exists(), f"Spec file not found at {spec}"


def test_spec_file_valid_python() -> None:
    """Spec file is valid Python syntax."""
    spec = Path(__file__).resolve().parents[2] / "autocode.spec"
    content = spec.read_text()
    # Should be parseable (basic syntax check)
    compile(content, str(spec), "exec")


def test_main_module_exists() -> None:
    """__main__.py entry point exists."""
    main_path = Path(__file__).resolve().parents[2] / "src" / "autocode" / "__main__.py"
    assert main_path.exists()
    content = main_path.read_text()
    assert "app" in content  # calls app() from cli


def test_all_hidden_imports_importable() -> None:
    """All modules listed in hiddenimports are importable."""
    importable = [
        "autocode.cli",
        "autocode.config",
        "autocode.agent.identity",
        "autocode.agent.bus",
        "autocode.agent.llmloop",
        "autocode.agent.sop_runner",
        "autocode.agent.policy_router",
        "autocode.agent.cost_dashboard",
        "autocode.agent.token_tracker",
        "autocode.agent.completion",
        "autocode.agent.multi_edit",
        "autocode.agent.team",
        "autocode.agent.provider_registry",
        "autocode.eval.harness",
        "autocode.eval.context_packer",
        "autocode.external.tracker",
        "autocode.external.mcp_server",
        "autocode.external.config_merge",
        "autocode.packaging.platform_detect",
        "autocode.packaging.bootstrap",
        "autocode.packaging.installer",
        "autocode.doctor",
    ]
    import importlib
    for module_name in importable:
        mod = importlib.import_module(module_name)
        assert mod is not None, f"Failed to import {module_name}"
