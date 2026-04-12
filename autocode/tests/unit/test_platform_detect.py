"""Tests for platform detection."""

from __future__ import annotations

from autocode.packaging.platform_detect import PlatformInfo, detect_platform


def test_detect_platform_returns_info() -> None:
    """detect_platform returns a PlatformInfo with basic fields."""
    info = detect_platform()
    assert info.os_name in ("linux", "darwin", "windows")
    assert info.arch
    assert info.python_version
    assert "3.11" in info.python_version or "3.12" in info.python_version or "3.13" in info.python_version


def test_platform_info_recommended_mode() -> None:
    """recommended_mode based on VRAM/RAM."""
    # Full mode: enough VRAM
    full = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", vram_free_mb=6000, ram_free_mb=16000)
    assert full.recommended_mode == "full"

    # Lite mode: no GPU but enough RAM
    lite = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", vram_free_mb=0, ram_free_mb=8000)
    assert lite.recommended_mode == "lite"

    # Cloud mode: insufficient resources
    cloud = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", vram_free_mb=0, ram_free_mb=2000)
    assert cloud.recommended_mode == "cloud"


def test_can_run_l3() -> None:
    """L3 needs 1GB VRAM or 4GB RAM."""
    with_gpu = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", vram_free_mb=1500)
    assert with_gpu.can_run_l3

    with_ram = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", ram_free_mb=8000)
    assert with_ram.can_run_l3

    neither = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", vram_free_mb=500, ram_free_mb=2000)
    assert not neither.can_run_l3


def test_can_run_l4() -> None:
    """L4 needs 5GB VRAM or 16GB RAM."""
    with_gpu = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", vram_free_mb=6000)
    assert with_gpu.can_run_l4

    no_gpu = PlatformInfo(os_name="linux", os_version="", arch="x86_64", python_version="3.11.0", vram_free_mb=2000, ram_free_mb=8000)
    assert not no_gpu.can_run_l4


def test_detect_ram() -> None:
    """RAM detection works on current machine."""
    info = detect_platform()
    assert info.ram_total_mb > 0


def test_detect_disk() -> None:
    """Disk space detection works."""
    info = detect_platform()
    assert info.disk_free_gb > 0


def test_detect_git() -> None:
    """Git detection works on current machine."""
    info = detect_platform()
    assert info.git_installed
    assert "git version" in info.git_version
