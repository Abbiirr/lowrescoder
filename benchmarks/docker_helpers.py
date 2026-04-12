"""Docker container lifecycle helpers for SWE-bench benchmarks.

Provides container management so setup and grading run in Docker
with the correct Python version, while the agent runs on the host
with access to Ollama and local tools via a volume mount.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any


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


def make_container_name(task_id: str, lane: str, run_id: str = "") -> str:
    """Build a unique, Docker-safe container name from task_id + lane + run_id."""
    raw = f"bench-{lane}-{task_id}"
    if run_id:
        raw = f"{raw}-{run_id}"
    # Docker names: [a-zA-Z0-9][a-zA-Z0-9_.-]
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "-", raw)
    # Must start with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = "c" + sanitized
    # Docker limit is 128 chars; keep it short
    return sanitized[:128]


def inspect_container_state(name: str) -> dict[str, Any]:
    """Return best-effort Docker container state for diagnostics."""
    try:
        proc = subprocess.run(
            [
                "docker",
                "inspect",
                name,
                "--format",
                (
                    "status={{.State.Status}} "
                    "exit={{.State.ExitCode}} "
                    "oom={{.State.OOMKilled}} "
                    "error={{.State.Error}}"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return {
                "container_name": name,
                "inspect_error": proc.stderr.strip() or proc.stdout.strip(),
            }
        fields: dict[str, str] = {}
        for chunk in proc.stdout.strip().split():
            if "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            fields[key] = value
        exit_code = fields.get("exit")
        return {
            "container_name": name,
            "status": fields.get("status", ""),
            "exit_code": int(exit_code) if exit_code and exit_code.isdigit() else None,
            "oom_killed": fields.get("oom") == "true",
            "error": fields.get("error", ""),
        }
    except Exception as exc:
        return {
            "container_name": name,
            "inspect_error": str(exc),
        }


def ensure_container_name_available(name: str) -> None:
    """Remove any stale container with the target name before startup.

    Container names are already scoped by lane/task/run_id. If the same name
    exists here, it is leftover state from an earlier crashed or interrupted
    attempt of the same run and is safe to clear.
    """
    try:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception:
        pass


def start_container(
    name: str,
    python_version: str,
    sandbox: str,
) -> subprocess.CompletedProcess[str]:
    """Start a detached container with the sandbox volume-mounted at /work.

    Uses python:{ver}-slim as the base image. The container stays alive
    via ``tail -f /dev/null`` so we can ``docker exec`` into it.
    """
    ensure_container_name_available(name)
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
    safe_directory_preamble = (
        "git config --global --add safe.directory '*' >/dev/null 2>&1 || true; "
    )
    cmd = ["docker", "exec"]
    if workdir:
        cmd += ["-w", workdir]
    cmd += [
        name,
        "bash",
        "-c",
        f"{safe_directory_preamble}set -o pipefail; {command}",
    ]
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
    )


def install_build_deps(
    name: str,
    *,
    profile: str = "full",
) -> subprocess.CompletedProcess[str]:
    """Install task-appropriate build dependencies inside the container.

    Profiles:
    - ``full``: SWE-bench style bootstrap for tasks that may compile extensions
    - ``git-only``: install git for lightweight fixture tasks that manipulate repos
    - ``none``: skip pre-bootstrap entirely and rely on task setup commands
    """
    if profile == "none":
        return subprocess.CompletedProcess(
            args=["docker", "exec", name],
            returncode=0,
            stdout="skipped build deps (profile=none)",
            stderr="",
        )
    if profile == "git-only":
        return docker_exec(
            name,
            "apt-get update -qq && "
            "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git",
            timeout=300,
        )
    if profile == "full":
        return docker_exec(
            name,
            "apt-get update -qq && "
            "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
            "gcc g++ make git "
            "python3-dev "
            "pkg-config && "
            "pip install -q Cython numpy pytest",
            timeout=900,
        )
    raise ValueError(f"Unknown build deps profile: {profile}")


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
