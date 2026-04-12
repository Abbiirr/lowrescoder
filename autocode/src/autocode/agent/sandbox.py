"""OS-level process sandboxing for tool execution.

Linux: bubblewrap (bwrap) if available, else restricted env fallback
macOS: sandbox-exec (Seatbelt) profiles if available
Windows: not yet implemented

Note: seccomp is detected but not directly applied — bwrap handles
seccomp internally when available. Direct seccomp-bpf is future work.

Based on patterns from Codex (Seatbelt + bubblewrap) and Goose (permission system).
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum


class SandboxPolicy(StrEnum):
    """Sandbox enforcement level."""

    NONE = "none"  # No sandbox (dangerous)
    READ_ONLY = "read_only"  # Read filesystem, no writes
    WRITABLE_PROJECT = "writable_project"  # Write only in project dir
    FULL_ISOLATION = "full_isolation"  # Full process isolation


@dataclass
class SandboxConfig:
    """Configuration for OS sandbox."""

    policy: SandboxPolicy = SandboxPolicy.WRITABLE_PROJECT
    writable_paths: list[str] = field(default_factory=list)
    readable_paths: list[str] = field(default_factory=list)
    allow_network: bool = False
    timeout_s: int = 30
    project_root: str = ""
    #: When True, refuse to fall back to the restricted-env unsandboxed
    #: path. If no OS sandbox (bwrap / Seatbelt) is available, emit a
    #: SandboxResult with a non-zero exit code and explanatory stderr.
    #: Matches Claude Code's sandbox.failIfUnavailable posture.
    fail_if_unavailable: bool = False


@dataclass
class SandboxResult:
    """Result of a sandboxed command execution."""

    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    sandbox_type: str = "none"
    enforced: bool = False


def detect_sandbox_support() -> dict[str, bool]:
    """Detect available sandbox mechanisms on this platform."""
    system = platform.system().lower()
    support = {
        "bwrap": False,
        "seatbelt": False,
        "seccomp": False,
        "none": True,
    }

    if system == "linux":
        support["bwrap"] = shutil.which("bwrap") is not None
        # seccomp available if kernel supports it
        try:
            with open("/proc/sys/kernel/seccomp/actions_avail") as f:
                support["seccomp"] = bool(f.read().strip())
        except FileNotFoundError:
            pass

    elif system == "darwin":
        support["seatbelt"] = shutil.which("sandbox-exec") is not None

    return support


def _build_bwrap_args(
    command: str,
    config: SandboxConfig,
) -> list[str]:
    """Build bubblewrap (bwrap) command line for Linux sandboxing."""
    args = ["bwrap"]

    # Base filesystem: read-only root
    args.extend(["--ro-bind", "/", "/"])

    # Writable tmpfs for /tmp
    args.extend(["--tmpfs", "/tmp"])

    # Writable project directory
    if config.project_root:
        args.extend(["--bind", config.project_root, config.project_root])

    # Additional writable paths
    for path in config.writable_paths:
        if os.path.exists(path):
            args.extend(["--bind", path, path])

    # Process isolation
    args.extend([
        "--unshare-pid",
        "--die-with-parent",
        "--new-session",
    ])

    # Network isolation (unless explicitly allowed)
    if not config.allow_network:
        args.append("--unshare-net")

    # Dev access (needed for /dev/null, /dev/urandom)
    args.extend(["--dev", "/dev"])
    args.extend(["--proc", "/proc"])

    # Run the command via shell
    args.extend(["--", "sh", "-c", command])

    return args


def _build_seatbelt_profile(config: SandboxConfig) -> str:
    """Build a macOS Seatbelt sandbox profile."""
    rules = ["(version 1)", "(deny default)"]

    # Allow basic operations
    rules.append("(allow process-exec)")
    rules.append("(allow process-fork)")
    rules.append("(allow sysctl-read)")
    rules.append("(allow mach-lookup)")
    rules.append("(allow signal)")

    # Read access
    rules.append('(allow file-read* (subpath "/usr"))')
    rules.append('(allow file-read* (subpath "/bin"))')
    rules.append('(allow file-read* (subpath "/Library"))')
    rules.append('(allow file-read* (subpath "/System"))')
    rules.append('(allow file-read* (subpath "/dev"))')
    rules.append('(allow file-read* (subpath "/private/tmp"))')

    for path in config.readable_paths:
        rules.append(f'(allow file-read* (subpath "{path}"))')

    # Write access (project only)
    if config.project_root:
        rules.append(f'(allow file-write* (subpath "{config.project_root}"))')
        rules.append(f'(allow file-read* (subpath "{config.project_root}"))')

    for path in config.writable_paths:
        rules.append(f'(allow file-write* (subpath "{path}"))')

    # Temp directory
    rules.append('(allow file-write* (subpath "/private/tmp"))')
    rules.append('(allow file-write* (subpath "/tmp"))')

    # Network
    if config.allow_network:
        rules.append("(allow network*)")

    return "\n".join(rules)


def run_sandboxed(
    command: str,
    config: SandboxConfig | None = None,
) -> SandboxResult:
    """Execute a command in an OS sandbox.

    Selects the best available sandbox mechanism for the platform.
    Falls back to unsandboxed execution with a warning if no sandbox
    available — **unless** ``config.fail_if_unavailable`` is True, in
    which case the command refuses to run and returns a non-zero exit
    with an explanatory stderr (Claude Code's ``failIfUnavailable``
    posture, deep-research-report Phase B Item 4).
    """
    cfg = config or SandboxConfig()

    if cfg.policy == SandboxPolicy.NONE:
        return _run_unsandboxed(command, cfg)

    support = detect_sandbox_support()
    system = platform.system().lower()

    # Linux: prefer bwrap
    if system == "linux" and support["bwrap"]:
        return _run_bwrap(command, cfg)

    # macOS: use Seatbelt
    if system == "darwin" and support["seatbelt"]:
        return _run_seatbelt(command, cfg)

    # No OS sandbox available. If the caller asked for fail-closed,
    # refuse rather than silently degrading.
    if cfg.fail_if_unavailable:
        available = [k for k, v in support.items() if v and k != "none"]
        return SandboxResult(
            stdout="",
            stderr=(
                "sandbox.fail_if_unavailable is enabled but no OS sandbox "
                f"is available on this host (system={system}, "
                f"detected={available or 'none'}). Refusing to run "
                "the command in unsandboxed mode. Install bwrap (Linux) "
                "or sandbox-exec (macOS), or set fail_if_unavailable=False "
                "to allow restricted-env fallback."
            ),
            returncode=126,  # 126 = command found but not executable
            sandbox_type="none",
            enforced=False,
        )

    # Fallback: run with basic env restrictions
    return _run_restricted(command, cfg)


def _safe_sandbox_env() -> dict[str, str]:
    """Sanitized environment for all sandbox paths.

    Neutralizes interactive editors and prompts — same hardening
    as the old _safe_shell_env() but applied to all sandbox modes.
    """
    env = os.environ.copy()
    env["GIT_EDITOR"] = "true"
    env["EDITOR"] = "true"
    env["VISUAL"] = "true"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["DEBIAN_FRONTEND"] = "noninteractive"
    return env


def _should_fallback_from_bwrap(stderr: str) -> bool:
    """Return True when bwrap exists but is unusable on this host.

    Some environments expose the binary but block unprivileged user namespaces,
    which makes bwrap fail immediately with permission/setup errors. In that
    case we should degrade to the restricted-env path instead of hard-failing
    every shell command.
    """
    text = (stderr or "").lower()
    if "bwrap" not in text:
        return False
    fallback_markers = (
        "setting up uid map",
        "setting up gid map",
        "permission denied",
        "operation not permitted",
        "no permissions to create new namespace",
        "creating new namespace failed",
    )
    return any(marker in text for marker in fallback_markers)


def _run_bwrap(command: str, config: SandboxConfig) -> SandboxResult:
    """Execute via bubblewrap on Linux."""
    args = _build_bwrap_args(command, config)
    try:
        result = subprocess.run(
            args,
            capture_output=True, text=True,
            timeout=config.timeout_s,
            env=_safe_sandbox_env(),
        )
        if result.returncode != 0 and _should_fallback_from_bwrap(result.stderr):
            return _run_restricted(command, config)
        return SandboxResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            sandbox_type="bwrap",
            enforced=True,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            stderr=f"Sandbox timeout after {config.timeout_s}s",
            returncode=124,
            sandbox_type="bwrap",
            enforced=True,
        )
    except Exception as e:
        return SandboxResult(
            stderr=str(e), returncode=1,
            sandbox_type="bwrap_failed",
            enforced=False,
        )


def _run_seatbelt(command: str, config: SandboxConfig) -> SandboxResult:
    """Execute via sandbox-exec on macOS."""
    profile = _build_seatbelt_profile(config)
    try:
        result = subprocess.run(
            ["sandbox-exec", "-p", profile, "sh", "-c", command],
            capture_output=True, text=True,
            timeout=config.timeout_s,
            env=_safe_sandbox_env(),
        )
        return SandboxResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            sandbox_type="seatbelt",
            enforced=True,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            stderr=f"Sandbox timeout after {config.timeout_s}s",
            returncode=124,
            sandbox_type="seatbelt",
            enforced=True,
        )
    except Exception as e:
        return SandboxResult(
            stderr=str(e), returncode=1,
            sandbox_type="seatbelt_failed",
            enforced=False,
        )


def _run_restricted(command: str, config: SandboxConfig) -> SandboxResult:
    """Fallback: run with restricted environment (no OS sandbox)."""
    env = _safe_sandbox_env()

    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True,
            timeout=config.timeout_s,
            cwd=config.project_root or None,
            env=env,
        )
        return SandboxResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            sandbox_type="restricted_env",
            enforced=False,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            stderr=f"Timeout after {config.timeout_s}s",
            returncode=124,
            sandbox_type="restricted_env",
            enforced=False,
        )


def _run_unsandboxed(command: str, config: SandboxConfig) -> SandboxResult:
    """Run without any sandbox (policy=NONE)."""
    try:
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True,
            timeout=config.timeout_s,
            cwd=config.project_root or None,
        )
        return SandboxResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            sandbox_type="none",
            enforced=False,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            stderr=f"Timeout after {config.timeout_s}s",
            returncode=124,
        )
