"""Install/Uninstall management for AutoCode.

Handles system-wide installation, PATH registration, config migration,
and clean removal of all AutoCode artifacts.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstallLocation:
    """Where AutoCode is installed."""

    bin_dir: Path  # Where the binary lives
    config_dir: Path  # Where configs are stored
    data_dir: Path  # Where data (models, index) lives
    cache_dir: Path  # Where cache/temp files live

    @classmethod
    def default(cls) -> InstallLocation:
        """Default install locations based on OS."""
        home = Path.home()
        if os.name == "nt":  # Windows
            return cls(
                bin_dir=home / "AppData" / "Local" / "autocode" / "bin",
                config_dir=home / "AppData" / "Local" / "autocode" / "config",
                data_dir=home / "AppData" / "Local" / "autocode" / "data",
                cache_dir=home / "AppData" / "Local" / "autocode" / "cache",
            )
        else:  # POSIX/Linux path — match runtime's ~/.autocode/ path
            return cls(
                bin_dir=home / ".local" / "bin",
                config_dir=home / ".autocode",
                data_dir=home / ".local" / "share" / "autocode",
                cache_dir=home / ".cache" / "autocode",
            )


@dataclass
class InstallResult:
    """Result of install/uninstall operation."""

    success: bool
    message: str
    paths_created: list[str] = field(default_factory=list)
    paths_removed: list[str] = field(default_factory=list)


def get_install_location() -> InstallLocation:
    """Get the default install location for the current platform."""
    return InstallLocation.default()


def check_installed() -> bool:
    """Check if AutoCode is installed system-wide."""
    loc = get_install_location()
    return loc.config_dir.exists()


def is_autocode_on_path() -> bool:
    """Return True when the ``autocode`` executable is discoverable on PATH."""
    return shutil.which("autocode") is not None


def install(location: InstallLocation | None = None) -> InstallResult:
    """Install AutoCode to the system.

    Creates config and data directories. Does NOT copy binaries
    (that's handled by PyInstaller or uv install).
    """
    loc = location or get_install_location()
    created: list[str] = []

    for path in [loc.config_dir, loc.data_dir, loc.cache_dir]:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))

    # Create default config (YAML — canonical format per Phase 7 contract)
    default_config = loc.config_dir / "config.yaml"
    if not default_config.exists():
        default_config.write_text(
            '# AutoCode configuration\n'
            'llm:\n'
            '  provider: ollama\n'
            '  model: qwen3:8b\n'
            '  api_base: http://localhost:11434\n'
            '\n'
            'shell:\n'
            '  timeout: 30\n'
            '  enabled: true\n',
            encoding="utf-8",
        )
        created.append(str(default_config))

    return InstallResult(
        success=True,
        message=f"Installed to {loc.config_dir}",
        paths_created=created,
    )


def uninstall(
    location: InstallLocation | None = None,
    keep_config: bool = False,
) -> InstallResult:
    """Uninstall AutoCode from the system.

    Removes data and cache directories. Optionally keeps config.
    """
    loc = location or get_install_location()
    removed: list[str] = []

    # Remove data and cache
    for path in [loc.data_dir, loc.cache_dir]:
        if path.exists():
            shutil.rmtree(path)
            removed.append(str(path))

    # Optionally remove config
    if not keep_config and loc.config_dir.exists():
        shutil.rmtree(loc.config_dir)
        removed.append(str(loc.config_dir))

    return InstallResult(
        success=True,
        message="AutoCode uninstalled" + (" (config kept)" if keep_config else ""),
        paths_removed=removed,
    )
