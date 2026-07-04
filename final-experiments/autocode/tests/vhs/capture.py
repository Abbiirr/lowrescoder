"""Spawn the Go TUI in a PTY and capture raw ANSI output for one scenario.

Shape matches the existing `tests/pty/*` scripts so the mock backend wiring
stays identical. Rather than asserting on text, this module returns the
captured bytes for the renderer to consume.
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
from pathlib import Path


@dataclass
class Scenario:
    """One scripted scenario the renderer will turn into a snapshot."""

    name: str
    # Each entry is either a string (sent as-is) or a float (seconds to sleep)
    steps: list[str | float] = field(default_factory=list)
    # How long to drain PTY output after the last step before killing the process
    drain_quiet_s: float = 1.2
    drain_maxwait_s: float = 6.0
    # PTY geometry
    columns: int = 160
    lines: int = 50
    # Whether to send an explicit Ctrl+D before teardown to encourage clean exit
    graceful_exit: bool = True


def _winsize(fd: int, lines: int, columns: int) -> None:
    fcntl.ioctl(
        fd, termios.TIOCSWINSZ, struct.pack("HHHH", lines, columns, 0, 0)
    )


def _spawn(
    argv: list[str], *, columns: int, lines: int, env_extra: dict | None = None,
) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    _winsize(master_fd, lines, columns)
    _winsize(slave_fd, lines, columns)
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
            "COLUMNS": str(columns),
            "LINES": str(lines),
        }
        if env_extra:
            env.update(env_extra)
        os.execve(argv[0], argv, env)
        sys.exit(1)
    os.close(slave_fd)
    return master_fd, pid


def _read_drain(
    fd: int, *, quiet: float, maxwait: float,
) -> bytes:
    buf = b""
    deadline = time.monotonic() + maxwait
    last = time.monotonic()
    while time.monotonic() < deadline:
        timeout = max(0.05, min(quiet, deadline - time.monotonic()))
        r, _, _ = select.select([fd], [], [], timeout)
        if not r:
            if time.monotonic() - last >= quiet:
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
        buf += chunk
        last = time.monotonic()
    return buf


def _kill(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        time.sleep(0.3)
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def capture_scenario(
    binary: Path,
    scenario: Scenario,
    *,
    env_extra: dict | None = None,
) -> bytes:
    """Run one scripted scenario against ``binary`` and return raw ANSI bytes.

    The returned bytes include the full render history: initial boot frame,
    each step's output, and the final drain. Feeding this stream through
    ``pyte`` applies every cursor move / clear / repaint, so the final
    Screen state reflects what a user would actually see.
    """
    fd, pid = _spawn(
        [str(binary)],
        columns=scenario.columns,
        lines=scenario.lines,
        env_extra=env_extra,
    )
    captured = bytearray()
    try:
        # Initial drain so the TUI has a chance to render its header BEFORE
        # we start typing. Keep the bytes so pyte sees the startup frame.
        captured += _read_drain(fd, quiet=1.0, maxwait=4.0)

        for step in scenario.steps:
            if isinstance(step, float | int):
                time.sleep(float(step))
                # Also drain anything emitted during the sleep window.
                captured += _read_drain(fd, quiet=0.4, maxwait=float(step) + 1.0)
                continue
            os.write(fd, step.encode("utf-8"))
            time.sleep(0.2)
            captured += _read_drain(fd, quiet=0.4, maxwait=2.0)

        # Optional graceful exit BEFORE kill — Ctrl+D
        if scenario.graceful_exit:
            try:
                os.write(fd, b"\x04")
            except OSError:
                pass

        captured += _read_drain(
            fd, quiet=scenario.drain_quiet_s, maxwait=scenario.drain_maxwait_s,
        )
        return bytes(captured)
    finally:
        _kill(pid)
        try:
            os.close(fd)
        except OSError:
            pass
