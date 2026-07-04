#!/usr/bin/env python3
"""Checkpoint 2 PTY canary for core runtime-visible backend contracts.

Run:
  python3 autocode/tests/pty/pty_smoke_rust_checkpoint2_canary.py
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


def _send(fd: int, text: str, delay: float = 0.2) -> None:
    os.write(fd, text.encode("utf-8") + b"\r")
    time.sleep(delay)


def _spawn(cols: int = 150, rows: int = 44) -> tuple[int, int]:
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


def _write_artifact(findings: list[str], bugs: list[str], frames: list[tuple[str, str]]) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    artifact = ARTIFACT_DIR / f"{ts}-checkpoint2-pty-canary.md"
    artifact.write_text(
        "# Checkpoint 2 PTY Canary\n\n"
        f"**Date:** {datetime.now(UTC).isoformat()}  \n"
        f"**Rust TUI binary:** `{RUST_TUI}`  \n"
        f"**Mock backend:** `{MOCK_BACKEND}`  \n"
        f"**Bugs found:** {len(bugs)}  \n\n"
        "## Findings\n\n"
        + "\n".join(f"- {line}" for line in findings)
        + ("\n\n## Bugs\n\n" + "\n".join(f"- {bug}" for bug in bugs) if bugs else "")
        + "\n\n## Captured Frames\n\n"
        + "\n\n".join(
            f"### {label}\n\n```text\n{frame[-1800:]}\n```" for label, frame in frames
        )
        + "\n",
        encoding="utf-8",
    )
    return artifact


def main() -> int:
    if not Path(RUST_TUI).is_file():
        print(f"SKIP: Rust binary not found at {RUST_TUI}")
        return 2

    findings: list[str] = []
    bugs: list[str] = []
    frames: list[tuple[str, str]] = []
    fd, pid = _spawn()
    try:
        ready = _read_until(fd, "● ready")
        frames.append(("ready", ready))
        if "● ready" in ready:
            findings.append("PASS ready surface rendered")
        else:
            bugs.append("ready surface did not render")

        _send(fd, "hello")
        visible_only = _read_until(fd, "Hello from the mock backend!")
        frames.append(("thinking-off-visible-only", visible_only))
        if "Hello from the mock backend!" in visible_only and "THINKING" not in visible_only:
            findings.append("PASS thinking-off/visible-only turn did not render thinking panel")
        else:
            bugs.append(
                "visible-only turn either missed output or rendered unexpected thinking panel"
            )

        _send(fd, "__THINKING_SPLIT__")
        thinking = _read_until(fd, "final visible answer")
        frames.append(("thinking-on-split", thinking))
        required_thinking_tokens = (
            "THINKING",
            "checking hidden path",
            "VISIBLE OUTPUT",
            "final visible answer",
        )
        if all(token in thinking for token in required_thinking_tokens):
            findings.append(
                "PASS thinking-on split rendered thinking and visible output separately"
            )
        else:
            bugs.append("thinking split did not expose both thinking and visible output")

        _send(fd, "__TOOL_OUTPUT_BUDGET__")
        tool = _read_until(fd, "omitted")
        frames.append(("tool-sequence-budget", tool))
        if all(token in tool for token in ("small_budget_tool", "completed", "omitted")):
            findings.append("PASS tool sequence rendered completed tool and truncation marker")
        else:
            bugs.append("tool sequence did not render required tool/truncation markers")

        _send(fd, "__COST_LIMIT__")
        cost = _read_until(fd, "Cost limit warning rendered")
        frames.append(("cost-limit-warning", cost))
        if "Session cost limit reached" in cost and "$0.0010 threshold" in cost:
            findings.append("PASS cost-limit crossing warning rendered")
        else:
            bugs.append("cost-limit crossing warning did not render")

        _send(fd, "/exit")
        time.sleep(0.5)
    finally:
        _cleanup(pid, fd)

    artifact = _write_artifact(findings, bugs, frames)
    print(f"Artifact: {artifact}")
    if bugs:
        for bug in bugs:
            print(f"FAIL: {bug}")
        return 1
    print("PASS: checkpoint2 PTY canary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
