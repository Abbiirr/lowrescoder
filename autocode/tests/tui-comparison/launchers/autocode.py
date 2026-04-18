"""Autocode launcher spec for tui-comparison Track 1.

Keeps autocode-specific launch knowledge (binary path, env, boot
budget, ready-marker heuristic) isolated from the capture driver.

Two modes:
- **live** (default): uses the real Python backend via PATH discovery.
  Requires LITELLM_MASTER_KEY + reachable gateway. Used by scenarios
  that test backend integration (none in the initial 2-scenario set —
  both startup and first-prompt-text use mock for determinism).
- **mock**: points AUTOCODE_PYTHON_CMD at `tests/pty/mock_backend.py`,
  the existing JSON-RPC mock. Deterministic, no gateway, no flake.
  Preferred for the Track 1 regression harness.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

TOOL = "autocode"


@dataclass
class LaunchSpec:
    tool: str
    argv: list[str]
    boot_budget_s: float
    env_extra: dict[str, str]
    tool_version: str


def find_binary() -> Path:
    """Locate the autocode TUI binary.

    Priority order matches the repo convention: build/ (canonical) →
    explicit env override → ~/.local/bin/autocode (uv-tool install
    wrapper).
    """
    env_override = os.environ.get("AUTOCODE_TUI_BIN")
    if env_override and Path(env_override).exists():
        return Path(env_override)
    build_path = Path(__file__).resolve().parents[3] / "build" / "autocode-tui"
    if build_path.exists():
        return build_path
    # Fallback — the wrapper
    fallback = Path.home() / ".local" / "bin" / "autocode"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        "autocode TUI binary not found; set AUTOCODE_TUI_BIN or run "
        "`go build -o autocode/build/autocode-tui ./autocode/cmd/autocode-tui`"
    )


def _pty_backend_path(name: str) -> Path:
    """Locate a backend stub from tests/pty/."""
    return Path(__file__).resolve().parents[2] / "pty" / name


def _mock_backend_path() -> Path:
    return _pty_backend_path("mock_backend.py")


def spec(
    *,
    use_mock_backend: bool = True,
    backend_script: str = "mock_backend.py",
    boot_budget_s: float = 6.0,
) -> LaunchSpec:
    """Build a LaunchSpec for the autocode TUI.

    ``backend_script`` selects which file under ``tests/pty/`` is
    plugged in via ``AUTOCODE_PYTHON_CMD``. Current options:

    - ``mock_backend.py`` (default) — deterministic JSON-RPC mock.
    - ``silent_backend.py`` — never sends on_status; used to trigger
      the TUI's startup-timeout path (Phase 2 Scenario 4).

    ``boot_budget_s`` is the capture driver's post-spawn settle window.
    For startup-timeout scenarios it must exceed the TUI's
    ``startupTimeoutDuration`` (15s) so the timeout fires inside the
    capture.
    """
    bin_path = find_binary()
    env_extra: dict[str, str] = {
        "LITELLM_MASTER_KEY": os.environ.get("LITELLM_MASTER_KEY", ""),
    }
    if use_mock_backend:
        backend_path = _pty_backend_path(backend_script)
        if not backend_path.exists():
            raise FileNotFoundError(
                f"backend script not found at {backend_path}; "
                f"use_mock_backend=True but {backend_script!r} is missing"
            )
        # findPythonBackend looks at AUTOCODE_PYTHON_CMD first and ALWAYS
        # appends "serve" as the sole arg, so the file must be executable
        # with a shebang. Both mock_backend.py and silent_backend.py carry
        # `#!/usr/bin/env python3` and ignore their argv.
        env_extra["AUTOCODE_PYTHON_CMD"] = str(backend_path)
    return LaunchSpec(
        tool=TOOL,
        argv=[str(bin_path)],
        boot_budget_s=boot_budget_s,
        env_extra=env_extra,
        tool_version="0.1.0",
    )
