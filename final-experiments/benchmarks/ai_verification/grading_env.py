"""Shared subprocess environment for deterministic grading commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def grading_env() -> dict[str, str]:
    """Return an env that can run repo-local grading modules from a sandbox cwd."""
    env = os.environ.copy()
    venv_bin = Path(sys.executable).parent
    existing_path = env.get("PATH", "")
    env["PATH"] = f"{venv_bin}:{existing_path}"

    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{REPO_ROOT}:{existing_pythonpath}" if existing_pythonpath else str(REPO_ROOT)
    return env
