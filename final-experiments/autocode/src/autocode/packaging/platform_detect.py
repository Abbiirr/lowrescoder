"""Platform detection — OS, GPU, VRAM, and system capabilities.

Auto-detects the runtime environment and configures AutoCode accordingly.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class PlatformInfo:
    """Detected platform information."""

    os_name: str  # "linux", "darwin", "windows"
    os_version: str
    arch: str  # "x86_64", "arm64"
    python_version: str
    gpu_available: bool = False
    gpu_name: str = ""
    vram_total_mb: int = 0
    vram_free_mb: int = 0
    ram_total_mb: int = 0
    ram_free_mb: int = 0
    disk_free_gb: float = 0.0
    ollama_installed: bool = False
    ollama_version: str = ""
    git_installed: bool = False
    git_version: str = ""

    @property
    def can_run_l3(self) -> bool:
        """Can run L3 models (needs ~1GB VRAM or CPU fallback)."""
        return self.vram_free_mb >= 1000 or self.ram_free_mb >= 4000

    @property
    def can_run_l4(self) -> bool:
        """Can run L4 models (needs ~5GB VRAM or ~16GB RAM)."""
        return self.vram_free_mb >= 5000 or self.ram_free_mb >= 16000

    @property
    def recommended_mode(self) -> str:
        """Recommended operation mode based on hardware."""
        if self.can_run_l4:
            return "full"  # L3 + L4 local
        if self.can_run_l3:
            return "lite"  # L3 local only, L4 via gateway
        return "cloud"  # All via gateway/cloud


def detect_platform() -> PlatformInfo:
    """Detect current platform capabilities."""
    info = PlatformInfo(
        os_name=platform.system().lower(),
        os_version=platform.version(),
        arch=platform.machine(),
        python_version=platform.python_version(),
    )

    # GPU detection
    _detect_gpu(info)

    # RAM detection
    _detect_ram(info)

    # Disk space
    _detect_disk(info)

    # Ollama
    _detect_ollama(info)

    # Git
    _detect_git(info)

    return info


def _detect_gpu(info: PlatformInfo) -> None:
    """Detect NVIDIA GPU and VRAM."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                info.gpu_available = True
                info.gpu_name = parts[0].strip()
                info.vram_total_mb = int(parts[1].strip())
                info.vram_free_mb = int(parts[2].strip())
    except Exception:
        pass


def _detect_ram(info: PlatformInfo) -> None:
    """Detect system RAM."""
    try:
        if info.os_name == "linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        info.ram_total_mb = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        info.ram_free_mb = int(line.split()[1]) // 1024
        elif info.os_name == "darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                info.ram_total_mb = int(result.stdout.strip()) // (1024 * 1024)
                info.ram_free_mb = info.ram_total_mb // 2  # approximate
    except Exception:
        pass


def _detect_disk(info: PlatformInfo) -> None:
    """Detect free disk space."""
    try:
        usage = shutil.disk_usage(os.getcwd())
        info.disk_free_gb = usage.free / (1024 ** 3)
    except Exception:
        pass


def _detect_ollama(info: PlatformInfo) -> None:
    """Detect Ollama installation."""
    if shutil.which("ollama"):
        info.ollama_installed = True
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                info.ollama_version = result.stdout.strip()
        except Exception:
            pass


def _detect_git(info: PlatformInfo) -> None:
    """Detect git installation."""
    if shutil.which("git"):
        info.git_installed = True
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                info.git_version = result.stdout.strip()
        except Exception:
            pass
