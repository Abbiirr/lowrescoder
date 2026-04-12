"""Tests for install/uninstall management."""

from __future__ import annotations

from pathlib import Path

import pytest

from autocode.packaging.installer import (
    InstallLocation,
    InstallResult,
    install,
    is_autocode_on_path,
    uninstall,
)


def test_install_location_default() -> None:
    """Default location uses standard XDG/AppData paths."""
    loc = InstallLocation.default()
    assert loc.bin_dir.is_absolute()
    assert loc.config_dir.is_absolute()
    assert loc.data_dir.is_absolute()


def test_install_creates_dirs(tmp_path: Path) -> None:
    """Install creates config, data, and cache directories."""
    loc = InstallLocation(
        bin_dir=tmp_path / "bin",
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
    )
    result = install(loc)

    assert result.success
    assert loc.config_dir.exists()
    assert loc.data_dir.exists()
    assert loc.cache_dir.exists()
    assert len(result.paths_created) >= 3


def test_install_creates_default_config(tmp_path: Path) -> None:
    """Install creates a default config.yaml."""
    loc = InstallLocation(
        bin_dir=tmp_path / "bin",
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
    )
    install(loc)

    config_file = loc.config_dir / "config.yaml"
    assert config_file.exists()
    content = config_file.read_text()
    assert "llm:" in content
    assert "ollama" in content
    assert "localhost:11434" in content


def test_uninstall_removes_dirs(tmp_path: Path) -> None:
    """Uninstall removes data and cache dirs."""
    loc = InstallLocation(
        bin_dir=tmp_path / "bin",
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
    )
    install(loc)
    result = uninstall(loc)

    assert result.success
    assert not loc.data_dir.exists()
    assert not loc.cache_dir.exists()
    assert not loc.config_dir.exists()


def test_uninstall_keep_config(tmp_path: Path) -> None:
    """Uninstall with keep_config preserves config dir."""
    loc = InstallLocation(
        bin_dir=tmp_path / "bin",
        config_dir=tmp_path / "config",
        data_dir=tmp_path / "data",
        cache_dir=tmp_path / "cache",
    )
    install(loc)
    result = uninstall(loc, keep_config=True)

    assert result.success
    assert loc.config_dir.exists()  # kept
    assert not loc.data_dir.exists()  # removed
    assert "config kept" in result.message


def test_install_result_structure() -> None:
    """InstallResult has expected fields."""
    result = InstallResult(
        success=True,
        message="OK",
        paths_created=["/a", "/b"],
    )
    assert result.success
    assert len(result.paths_created) == 2


def test_is_autocode_on_path_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATH check returns True when autocode executable is discoverable."""
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/autocode" if name == "autocode" else None)
    assert is_autocode_on_path()


def test_is_autocode_on_path_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATH check returns False when autocode executable is missing."""
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert not is_autocode_on_path()
