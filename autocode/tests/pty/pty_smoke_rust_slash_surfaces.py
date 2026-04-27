#!/usr/bin/env python3
"""PTY smoke coverage for high-risk Rust TUI slash surfaces.

Run: python3 autocode/tests/pty/pty_smoke_rust_slash_surfaces.py
Override binary: AUTOCODE_TUI_BIN=<path> python3 autocode/tests/pty/pty_smoke_rust_slash_surfaces.py
"""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import re
import select
import signal
import struct
import sys
import termios
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
RUST_TUI = os.environ.get(
    "AUTOCODE_TUI_BIN",
    str(_HERE.parent.parent / "rtui" / "target" / "release" / "autocode-tui"),
)
MOCK_BACKEND = str(_HERE / "mock_backend.py")
ARTIFACT_DIR = _HERE.parent.parent / "docs" / "qa" / "test-results"
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


@dataclass(frozen=True)
class SlashSurfaceCase:
    command: str
    expected_any: tuple[str, ...]
    note: str


SLASH_SURFACE_CASES: tuple[SlashSurfaceCase, ...] = (
    SlashSurfaceCase(
        "/help",
        ("Slash Commands", "/help", "Show available commands"),
        "command palette",
    ),
    SlashSurfaceCase("/plan", ("Plan", "planning", "draft"), "plan detail surface"),
    SlashSurfaceCase("/tasks", ("Tasks", "task", "backend"), "tasks detail surface"),
    SlashSurfaceCase("/grep", ("Search", "grep", "results"), "grep/search detail surface"),
    SlashSurfaceCase("/review", ("Review", "Evidence", "approval"), "review detail surface"),
    SlashSurfaceCase("/diff", ("Diff", "hunk", "file"), "diff detail surface"),
    SlashSurfaceCase("/restore", ("Restore", "checkpoint", "snapshot"), "restore browser"),
    SlashSurfaceCase("/cc", ("command", "Subagents", "queue"), "command center"),
    SlashSurfaceCase(
        "/escalation",
        ("Escalation", "Protected", "write"),
        "escalation detail surface",
    ),
    SlashSurfaceCase("/multi", ("multi", "Queue", "concurrent"), "multi-agent detail surface"),
)

FINDINGS: list[str] = []
BUGS: list[str] = []


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _strip_ansi(raw: bytes) -> str:
    return ANSI_RE.sub("", raw.decode("utf-8", errors="replace"))


def _read_until(fd: int, *, quiet: float = 0.9, maxwait: float = 8.0) -> bytes:
    buf = b""
    deadline = time.monotonic() + maxwait
    last_data = time.monotonic()
    while True:
        now = time.monotonic()
        if now >= deadline:
            break
        wait = min(quiet - (now - last_data), deadline - now)
        if wait <= 0:
            if time.monotonic() - last_data >= quiet:
                break
            continue
        r, _, _ = select.select([fd], [], [], wait)
        if not r:
            if time.monotonic() - last_data >= quiet:
                break
            continue
        try:
            chunk = os.read(fd, 8192)
        except OSError as e:
            if e.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        buf += chunk
        last_data = time.monotonic()
    return buf


def _send(fd: int, data: bytes, delay: float = 0.15) -> None:
    os.write(fd, data)
    time.sleep(delay)


def _spawn(cols: int = 140, rows: int = 40) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    _set_winsize(master_fd, rows, cols)
    _set_winsize(slave_fd, rows, cols)
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
            "COLUMNS": str(cols),
            "LINES": str(rows),
            "AUTOCODE_PYTHON_CMD": MOCK_BACKEND,
            "AUTOCODE_MOCK_SUPPRESS_STARTUP_WARNING": "1",
        }
        os.execve(RUST_TUI, [RUST_TUI], env)
        sys.exit(1)
    os.close(slave_fd)
    return master_fd, pid


def _kill(pid: int | None, fd: int | None) -> None:
    if pid is not None:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.kill(pid, sig)
                time.sleep(0.1)
            except OSError:
                pass
        try:
            os.waitpid(pid, os.WNOHANG)
        except OSError:
            pass
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass


def _log(message: str) -> None:
    print(message)
    FINDINGS.append(message)


def _run_case(case: SlashSurfaceCase) -> None:
    fd: int | None = None
    pid: int | None = None
    try:
        fd, pid = _spawn()
        startup = _strip_ansi(_read_until(fd, quiet=1.2, maxwait=10.0))
        if "● ready" not in startup:
            BUGS.append(f"{case.command}: TUI did not reach ready state")
            _log(f"[FAIL] {case.command}: no ready state")
            return

        _send(fd, case.command.encode() + b"\r", delay=0.25)
        text = _strip_ansi(_read_until(fd, quiet=1.2, maxwait=8.0))
        haystack = startup + "\n" + text
        if any(token in haystack for token in case.expected_any):
            _log(f"[PASS] {case.command}: {case.note}")
        else:
            BUGS.append(f"{case.command}: expected one of {case.expected_any}")
            _log(f"[FAIL] {case.command}: expected one of {case.expected_any}")
            _log(haystack[-800:])
    finally:
        _kill(pid, fd)


def _write_artifact() -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    artifact = ARTIFACT_DIR / f"{ts}-pty-slash-surfaces-smoke.md"
    with artifact.open("w") as f:
        f.write("# PTY Slash Surfaces Smoke\n\n")
        f.write(f"**Date:** {datetime.now(UTC).isoformat()}  \n")
        f.write(f"**Rust TUI binary:** `{RUST_TUI}`  \n")
        f.write(f"**Mock backend:** `{MOCK_BACKEND}`  \n")
        f.write(f"**Cases:** `{', '.join(case.command for case in SLASH_SURFACE_CASES)}`  \n")
        f.write(f"**Bugs found:** {len(BUGS)}  \n\n")
        f.write("## Findings\n\n```text\n")
        f.write("\n".join(FINDINGS))
        f.write("\n```\n")
        if BUGS:
            f.write("\n## Bugs\n\n")
            for bug in BUGS:
                f.write(f"- {bug}\n")
    return artifact


def run_smoke() -> None:
    _log("=" * 70)
    _log("PTY Slash Surfaces Smoke — Rust TUI")
    _log(f"Rust TUI binary: {RUST_TUI}")
    _log(f"Mock backend:    {MOCK_BACKEND}")
    _log("=" * 70)

    if not Path(RUST_TUI).is_file():
        _log(f"SKIP: Rust binary not found at {RUST_TUI}")
        sys.exit(2)

    for case in SLASH_SURFACE_CASES:
        _run_case(case)

    artifact = _write_artifact()
    _log(f"Artifact: {artifact}")
    if BUGS:
        sys.exit(1)


if __name__ == "__main__":
    run_smoke()
