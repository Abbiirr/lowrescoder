#!/usr/bin/env python3
"""PTY smoke for Rust TUI `/restore` navigation and confirmation."""
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


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _strip(raw: bytes) -> str:
    return ANSI_RE.sub("", raw.decode("utf-8", errors="replace"))


def _read_until(fd: int, needle: str, *, maxwait: float = 12.0) -> str:
    buf = b""
    deadline = time.monotonic() + maxwait
    while time.monotonic() < deadline:
        r, _, _ = select.select([fd], [], [], 0.25)
        if not r:
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
        text = _strip(buf)
        if needle in text:
            return text
    return _strip(buf)


def _send(fd: int, data: bytes, delay: float = 0.2) -> None:
    os.write(fd, data)
    time.sleep(delay)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _spawn(cols: int = 120, rows: int = 40) -> tuple[int, int]:
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


def _cleanup(pid: int | None, fd: int) -> None:
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
    try:
        os.close(fd)
    except OSError:
        pass


def main() -> None:
    if not Path(RUST_TUI).is_file():
        print(f"SKIP: Rust binary not found at {RUST_TUI}")
        sys.exit(2)

    findings: list[str] = []
    bugs: list[str] = []
    debug_frames: list[tuple[str, str]] = []
    fd, pid = _spawn()
    try:
        text = _read_until(fd, "● ready")
        debug_frames.append(("ready", text[-1200:]))
        if "● ready" in text:
            findings.append("PASS ready surface rendered")
        else:
            bugs.append("ready surface did not render")

        _send(fd, b"/restore\r")
        text = _read_until(fd, "mock-cp-new")
        debug_frames.append(("restore-list", text[-1200:]))
        compact = _compact(text)
        if "selected:mock-cp-new" in compact:
            findings.append("PASS restore list populated with selectable checkpoint rows")
        else:
            bugs.append("restore list did not render checkpoint rows")

        _send(fd, b"\x1b[B")
        text = _read_until(fd, "mock-cp-old")
        debug_frames.append(("restore-down", text[-1200:]))
        compact = _compact(text)
        if "mock-cp-old" in compact and "▶" in compact:
            findings.append("PASS down-arrow moved restore selection")
        else:
            bugs.append("down-arrow did not move restore selection")

        _send(fd, b"\r")
        text = _read_until(fd, "CONFIRM RESTORE")
        debug_frames.append(("restore-confirm", text[-1200:]))
        compact = _compact(text)
        if "CONFIRMRESTORE" in compact and "beforeriskyedit" in compact:
            findings.append("PASS restore confirmation modal rendered")
        else:
            bugs.append("confirmation modal did not render")

        _send(fd, b"\r")
        text = _read_until(fd, "mock-cp-old")
        debug_frames.append(("restore-result", text[-1200:]))
        compact = _compact(text)
        if "mock-cp-old" in compact and "4messages" in compact and "2toolcalls" in compact:
            findings.append("PASS checkpoint.restore feedback rendered in transcript")
        else:
            bugs.append("restore transcript feedback missing")

        _send(fd, b"/exit\r")
        time.sleep(0.5)
        try:
            waited_pid, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            waited_pid, status = pid, 0
        if waited_pid == pid:
            exit_code = os.waitstatus_to_exitcode(status)
            pid = None
            if exit_code == 0:
                findings.append("PASS clean exit after restore interaction")
            else:
                bugs.append(f"unexpected exit code {exit_code}")
    finally:
        _cleanup(pid, fd)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    artifact = ARTIFACT_DIR / f"{ts}-restore-interaction-pty-smoke.md"
    artifact.write_text(
        "# PTY Smoke — Rust TUI Restore Interaction\n\n"
        f"**Date:** {datetime.now(UTC).isoformat()}  \n"
        f"**Rust TUI binary:** `{RUST_TUI}`  \n"
        f"**Mock backend:** `{MOCK_BACKEND}`  \n"
        f"**Bugs found:** {len(bugs)}  \n\n"
        "## Findings\n\n"
        + "\n".join(f"- {line}" for line in findings)
        + ("\n\n## Bugs\n\n" + "\n".join(f"- {bug}" for bug in bugs) if bugs else "")
        + "\n\n## Debug Frames\n\n"
        + "\n\n".join(
            f"### {label}\n\n```text\n{frame}\n```" for label, frame in debug_frames
        )
        + "\n",
    )
    print(f"Artifact: {artifact}")
    if bugs:
        for bug in bugs:
            print(f"FAIL: {bug}")
        sys.exit(1)
    print("PASS: restore interaction smoke")


if __name__ == "__main__":
    main()
