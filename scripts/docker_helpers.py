"""Docker container lifecycle helpers for SWE-bench benchmarks.

Provides container management so setup and grading run in Docker
with the correct Python version, while the agent runs on the host
with access to Ollama and local tools via a volume mount.
"""

from __future__ import annotations

import os
import re
import subprocess


def docker_available() -> bool:
    """Check that the Docker CLI exists and the daemon is reachable."""
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def make_container_name(task_id: str, lane: str) -> str:
    """Build a unique, Docker-safe container name from task_id + lane."""
    raw = f"bench-{lane}-{task_id}"
    # Docker names: [a-zA-Z0-9][a-zA-Z0-9_.-]
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "-", raw)
    # Must start with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = "c" + sanitized
    # Docker limit is 128 chars; keep it short
    return sanitized[:128]


def start_container(
    name: str,
    python_version: str,
    sandbox: str,
) -> subprocess.CompletedProcess[str]:
    """Start a detached container with the sandbox volume-mounted at /work.

    Uses python:{ver}-slim as the base image. The container stays alive
    via ``tail -f /dev/null`` so we can ``docker exec`` into it.
    """
    image = f"python:{python_version}-slim"
    cmd = [
        "docker", "run", "-d",
        "--name", name,
        "-v", f"{sandbox}:/work",
        "-w", "/work",
        image,
        "tail", "-f", "/dev/null",
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
    )


def docker_exec(
    name: str,
    command: str,
    *,
    timeout: int = 300,
    workdir: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command inside the container with bash + pipefail.

    Returns the CompletedProcess so callers can inspect returncode,
    stdout, and stderr.
    """
    cmd = ["docker", "exec"]
    if workdir:
        cmd += ["-w", workdir]
    cmd += [
        name,
        "bash", "-c", f"set -o pipefail; {command}",
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )


def install_build_deps(name: str) -> subprocess.CompletedProcess[str]:
    """Install common build dependencies inside the container.

    Installs system packages (gcc, g++, make, git, python3-dev) and
    Python build tools (Cython, numpy, pytest) needed for C extension
    compilation (e.g. scikit-learn, matplotlib) and grading.
    """
    return docker_exec(
        name,
        "apt-get update -qq && "
        "apt-get install -y -qq "
        "gcc g++ make git "
        "python3-dev "
        "pkg-config && "
        "pip install -q Cython numpy pytest",
        timeout=300,
    )


def fix_permissions(name: str) -> None:
    """Chown /work to the host user's UID:GID so the host can write files.

    Called after setup completes so git operations on the host succeed.
    """
    uid = os.getuid()
    gid = os.getgid()
    try:
        docker_exec(
            name,
            f"chown -R {uid}:{gid} /work",
            timeout=60,
        )
    except Exception:
        pass  # best-effort


def stop_and_remove(name: str) -> None:
    """Stop and remove a container. Best-effort, never raises."""
    for action in ("stop", "rm"):
        try:
            subprocess.run(
                ["docker", action, name],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception:
            pass


def get_image_digest(python_version: str) -> str:
    """Return the local image digest for reproducibility tracking."""
    image = f"python:{python_version}-slim"
    try:
        proc = subprocess.run(
            ["docker", "image", "inspect", image,
             "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return "unknown"
