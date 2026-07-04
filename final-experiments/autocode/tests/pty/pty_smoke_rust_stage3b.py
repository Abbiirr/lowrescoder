#!/usr/bin/env python3
"""PTY smoke test for Stage 3B inspection surfaces.

Checks:
  - task/subagent panel renders after Ctrl+T
  - concurrent tool panel renders args/result details
  - followup queue count + panel render while streaming after Ctrl+Q
  - /exit still exits cleanly afterwards

Run: python3 autocode/tests/pty/pty_smoke_rust_stage3b.py
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

sys.path.insert(0, str((_HERE := Path(__file__).resolve().parents[1] / "tui-comparison").resolve()))
from predicates import render_screen  # type: ignore[import-not-found]

COLS, ROWS = 160, 50
CTRL_Q = b"\x11"
CTRL_T = b"\x14"
_HERE = Path(__file__).resolve().parent
RUST_TUI = os.environ.get(
    "AUTOCODE_TUI_BIN",
    str(_HERE.parent.parent / "rtui" / "target" / "release" / "autocode-tui"),
)
MOCK_BACKEND = str(_HERE / "mock_backend.py")
ARTIFACT_DIR = _HERE.parent.parent / "docs" / "qa" / "test-results"
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

BUGS: list[dict[str, str]] = []
FINDINGS: list[str] = []


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def read_until(
    fd: int, *, quiet: float = 1.0, maxwait: float = 8.0, stop_on: str | None = None
) -> bytes:
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
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        buf += chunk
        last_data = time.monotonic()
        if stop_on and stop_on.encode() in buf:
            break
    return buf


def strip_ansi(raw: bytes) -> str:
    return ANSI_RE.sub("", raw.decode("utf-8", errors="replace"))


def screen_text(raw: bytes) -> str:
    _, text = render_screen(raw, ROWS, COLS)
    return text


def send(fd: int, data: bytes, delay: float = 0.1) -> None:
    os.write(fd, data)
    time.sleep(delay)


def log(msg: str) -> None:
    print(msg)
    FINDINGS.append(msg)


def ok(label: str, detail: str = "") -> None:
    log(f"  [PASS] {label}" + (f" — {detail}" if detail else ""))


def bug(label: str, detail: str, severity: str = "HIGH") -> None:
    BUGS.append({"label": label, "detail": detail, "severity": severity})
    log(f"  [FAIL] [{severity}] {label}")
    if detail:
        log(f"         {detail[:300]}")


def spawn(argv: list[str], env_extra: dict[str, str]) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    _set_winsize(master_fd, ROWS, COLS)
    _set_winsize(slave_fd, ROWS, COLS)
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
            "COLUMNS": str(COLS),
            "LINES": str(ROWS),
            **env_extra,
        }
        os.execve(argv[0], argv, env)
        sys.exit(1)
    os.close(slave_fd)
    return master_fd, pid


def kill_proc(pid: int, fd: int) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
            time.sleep(0.2)
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


def run_smoke() -> None:
    log("=" * 70)
    log("PTY Smoke Test — Rust Stage 3B Inspection Surfaces")
    log(f"Rust TUI binary: {RUST_TUI}")
    log(f"Mock backend:    {MOCK_BACKEND}")
    log(f"Terminal size:   {COLS}x{ROWS}")
    log("=" * 70)

    if not Path(RUST_TUI).is_file():
        log(f"\n  SKIP: Rust binary not found at {RUST_TUI}")
        sys.exit(2)

    fd, pid = spawn([RUST_TUI], {"AUTOCODE_PYTHON_CMD": MOCK_BACKEND})
    exit_code = None
    session_raw = b""
    try:
        log("\n[S1] Startup")
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        session_raw += raw
        text = screen_text(session_raw)
        if all(marker in text for marker in ("tools", "openrouter", "suggest")):
            ok("S1_on_status", "status line rendered")
        else:
            bug("S1_on_status", text, "HIGH")

        log("\n[S2] Task + tool panels")
        send(fd, b"__PANELS__ trigger\r", delay=0.2)
        raw = read_until(fd, quiet=1.0, maxwait=4.0)
        send(fd, CTRL_T, delay=0.2)
        raw += read_until(fd, quiet=1.0, maxwait=2.0)
        session_raw += raw
        text = screen_text(session_raw)
        if all(marker in text for marker in ("Tasks", "Build release", "coder")):
            ok("S2_task_panel", "task/subagent panel visible")
        else:
            bug("S2_task_panel", text, "HIGH")
        if all(marker in text for marker in ("Tools", "write_file", "args:", "result: ok")):
            ok("S2_tool_panel", "tool args/result visible")
        else:
            bug("S2_tool_panel", text, "HIGH")

        log("\n[S3] Followup queue")
        send(fd, b"__SLOW__ hold queue\r", delay=0.2)
        send(fd, b"first queued\r", delay=0.1)
        send(fd, b"second queued\r", delay=0.1)
        send(fd, CTRL_Q, delay=0.1)
        raw = read_until(fd, quiet=0.6, maxwait=1.5)
        session_raw += raw
        text = screen_text(session_raw)
        if "Queued: 2" in text and "Followups" in text and "first queued" in text:
            ok("S3_followup_queue", "queue count and panel visible while streaming")
        else:
            bug("S3_followup_queue", text, "HIGH")

        log("\n[S4] /exit clean exit")
        time.sleep(3.0)
        send(fd, b"/exit\r", delay=0.2)
        _ = read_until(fd, quiet=1.0, maxwait=5.0)

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                wpid, status = os.waitpid(pid, os.WNOHANG)
                if wpid == pid:
                    exit_code = os.waitstatus_to_exitcode(status)
                    pid = None
                    break
            except ChildProcessError:
                exit_code = 0
                pid = None
                break
            time.sleep(0.1)
        if exit_code == 0:
            ok("S4_clean_exit", "exited with code 0")
        else:
            bug("S4_clean_exit", f"exit_code={exit_code}", "HIGH")
    finally:
        if pid is not None:
            kill_proc(pid, fd)
        try:
            os.close(fd)
        except OSError:
            pass

    log("\n" + "=" * 70)
    log(f"DONE — {len(BUGS)} bugs found")
    log("=" * 70)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    artifact = ARTIFACT_DIR / f"{ts}-rust-stage3b-pty-smoke.md"
    with open(artifact, "w", encoding="utf-8") as fh:
        fh.write("# PTY Smoke Test — Rust Stage 3B Inspection Surfaces\n\n")
        fh.write(f"**Date:** {datetime.now(UTC).isoformat()}  \n")
        fh.write(f"**Rust TUI binary:** `{RUST_TUI}`  \n")
        fh.write(f"**Bugs found:** {len(BUGS)}  \n\n")
        if BUGS:
            fh.write("| # | Severity | Label | Detail |\n")
            fh.write("|---|----------|-------|--------|\n")
            for idx, issue in enumerate(BUGS, 1):
                fh.write(
                    f"| {idx} | {issue['severity']} | {issue['label']} | {issue['detail'][:120]} |\n"
                )
            fh.write("\n")
        fh.write("## Full Findings Log\n\n```\n")
        fh.write("\n".join(FINDINGS))
        fh.write("\n```\n")

    log(f"\n  Artifact: {artifact}")
    if BUGS:
        sys.exit(1)


if __name__ == "__main__":
    run_smoke()
