"""PTY capture driver with DSR responder.

Small standalone module (doesn't inherit from ``tests/vhs/capture.py``
so the two suites stay independent) that:

1. forks a PTY,
2. runs a launcher's argv inside it with per-launcher env overrides,
3. reads raw ANSI bytes until a quiet deadline,
4. passes every chunk through the DSR responder so child TUIs that
   query the terminal (e.g. codex) don't hang,
5. returns the collected bytes + the DSR-served log for profile.yaml.

The driver never assumes what the output should look like. That's
the predicate layer's job.
"""
from __future__ import annotations

import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import time
from dataclasses import dataclass, field

try:
    from .dsr_responder import DsrResponder  # package-style import
except ImportError:
    from dsr_responder import DsrResponder  # direct-path import fallback


@dataclass
class CaptureResult:
    raw: bytes
    dsr_shim_version: str
    dsr_responses_served: list[str]
    exit_code: int | None
    wall_seconds: float


@dataclass
class CaptureOptions:
    """One capture run's spec — launcher argv + window + timing."""

    argv: list[str]
    cols: int = 160
    rows: int = 50
    boot_budget_s: float = 4.0  # initial drain before any scripted input
    drain_quiet_s: float = 1.2
    drain_maxwait_s: float = 6.0
    env_extra: dict[str, str] = field(default_factory=dict)
    # Scripted steps — float = sleep seconds, str = bytes to send
    steps: list[float | str] = field(default_factory=list)


def _winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _spawn(opts: CaptureOptions) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    _winsize(master_fd, opts.rows, opts.cols)
    _winsize(slave_fd, opts.rows, opts.cols)
    pid = os.fork()
    if pid == 0:
        os.setsid()
        fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
        for fd in (0, 1, 2):
            os.dup2(slave_fd, fd)
        os.close(master_fd)
        os.close(slave_fd)
        env = {
            **os.environ,
            "TERM": "xterm-256color",
            "COLUMNS": str(opts.cols),
            "LINES": str(opts.rows),
        }
        env.update(opts.env_extra)
        try:
            os.execvpe(opts.argv[0], opts.argv, env)
        except Exception as e:
            sys.stderr.write(f"exec failed: {e}\n")
            os._exit(127)
    os.close(slave_fd)
    return master_fd, pid


def _read_with_dsr(
    fd: int, *, quiet_s: float, maxwait_s: float, responder: DsrResponder
) -> bytes:
    buf = bytearray()
    deadline = time.monotonic() + maxwait_s
    last = time.monotonic()
    while time.monotonic() < deadline:
        timeout = max(0.05, min(quiet_s, deadline - time.monotonic()))
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            if time.monotonic() - last >= quiet_s:
                break
            continue
        try:
            chunk = os.read(fd, 8192)
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        responder.process(chunk)  # side effect: writes DSR responses back
        buf += chunk
        last = time.monotonic()
    return bytes(buf)


def capture(opts: CaptureOptions) -> CaptureResult:
    """Run one capture; return raw bytes + DSR log."""
    started = time.monotonic()
    fd, pid = _spawn(opts)
    responder = DsrResponder(pty_fd=fd)
    captured = bytearray()
    exit_code: int | None = None
    try:
        # Initial boot drain before any scripted input
        captured += _read_with_dsr(
            fd,
            quiet_s=1.0,
            maxwait_s=opts.boot_budget_s,
            responder=responder,
        )
        # Scripted steps
        for step in opts.steps:
            if isinstance(step, (float, int)):
                time.sleep(float(step))
                captured += _read_with_dsr(
                    fd,
                    quiet_s=0.4,
                    maxwait_s=float(step) + 1.0,
                    responder=responder,
                )
                continue
            os.write(fd, step.encode("utf-8"))
            time.sleep(0.2)
            captured += _read_with_dsr(
                fd,
                quiet_s=0.4,
                maxwait_s=2.0,
                responder=responder,
            )
        # Final drain
        captured += _read_with_dsr(
            fd,
            quiet_s=opts.drain_quiet_s,
            maxwait_s=opts.drain_maxwait_s,
            responder=responder,
        )
    finally:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.2)
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            _, status = os.waitpid(pid, os.WNOHANG)
            if os.WIFEXITED(status):
                exit_code = os.WEXITSTATUS(status)
            elif os.WIFSIGNALED(status):
                exit_code = -os.WTERMSIG(status)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass

    return CaptureResult(
        raw=bytes(captured),
        dsr_shim_version=DsrResponder.shim_version,
        dsr_responses_served=list(responder.served),
        exit_code=exit_code,
        wall_seconds=time.monotonic() - started,
    )
