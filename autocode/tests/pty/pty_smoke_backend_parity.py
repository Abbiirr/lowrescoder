#!/usr/bin/env python3
"""Focused PTY smoke test for backend parity (Tasks A-D).

Covers:
  - Go TUI startup reaches a usable prompt (or timeout fallback)
  - Ctrl+K palette opens
  - /model picker opens (expected, not unsolicited)
  - No panic, traceback, queue leak, or unsolicited picker
  - No fatal red error banners from backend stderr

Produces an artifact under autocode/docs/qa/test-results/.

Run: python3 autocode/tests/pty/pty_smoke_backend_parity.py
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

COLS, ROWS = 160, 50
GO_TUI = str(Path(__file__).resolve().parent.parent.parent / "build" / "autocode-tui")
MOCK_BACKEND = str(Path(__file__).resolve().parent / "mock_backend.py")
ARTIFACT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "qa" / "test-results"
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

BUGS: list[dict] = []
FINDINGS: list[str] = []


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def read_until(
    fd: int, *, quiet: float = 1.5, maxwait: float = 30.0, stop_on: str | None = None
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
        except OSError as e:
            if e.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        buf += chunk
        last_data = time.monotonic()
        if stop_on and stop_on.encode() in buf:
            # Drain one more chunk only if output is actually ready; a blind
            # blocking read can hang the whole PTY probe after a successful match.
            time.sleep(0.3)
            r2, _, _ = select.select([fd], [], [], 0)
            if r2:
                try:
                    buf += os.read(fd, 8192)
                except OSError:
                    pass
            break
    return buf


def strip_ansi(raw: bytes) -> str:
    return ANSI_RE.sub("", raw.decode("utf-8", errors="replace"))


def send(fd: int, text: str, delay: float = 0.05) -> None:
    os.write(fd, text.replace("\n", "\r").encode())
    time.sleep(delay)


def log(msg: str) -> None:
    print(msg)
    FINDINGS.append(msg)


def bug(label: str, detail: str, severity: str = "HIGH") -> None:
    entry = {"label": label, "detail": detail, "severity": severity}
    BUGS.append(entry)
    log(f"  [FAIL] [{severity}] {label}")
    log(f"         {detail[:300]}")


def ok(label: str, detail: str = "") -> None:
    msg = f"  [PASS] {label}" + (f" — {detail}" if detail else "")
    log(msg)


def check(label: str, raw: bytes) -> str:
    text = strip_ansi(raw)

    if "Select a model" in text and all(
        marker not in label.lower() for marker in ("/model", "model_picker")
    ):
        bug(f"{label}: model picker appeared unexpectedly (unsolicited)", text[:300], "CRITICAL")

    for m in re.findall(r"\(queued \d+ pending\)", text):
        bug(f"{label}: queue state leaked: {m!r}", text[:300], "CRITICAL")

    if "panic:" in text or ("goroutine" in text and "runtime error" in text):
        bug(f"{label}: Go panic detected", text[:400], "CRITICAL")

    if re.search(r"Traceback \(most recent", text):
        bug(f"{label}: Python traceback in output", text[:400], "CRITICAL")

    return text


def spawn(argv: list[str], env_extra: dict[str, str] | None = None) -> tuple[int, int]:
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
        env = {**os.environ, "TERM": "xterm-256color", "COLUMNS": str(COLS), "LINES": str(ROWS)}
        if env_extra:
            env.update(env_extra)
        os.execve(argv[0], argv, env)
        sys.exit(1)
    os.close(slave_fd)
    return master_fd, pid


def kill(pid: int, fd: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.3)
        os.kill(pid, signal.SIGKILL)
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
    log("PTY Smoke Test — Backend Parity (Tasks A-D)")
    log(f"Go TUI binary: {GO_TUI}")
    log(f"Terminal size: {COLS}x{ROWS}")
    log("=" * 70)

    if not Path(GO_TUI).is_file():
        log(f"\n  SKIP: Go TUI binary not found at {GO_TUI}")
        log("  Build with: cd autocode/cmd/autocode-tui && go build -o ../../build/autocode-tui .")
        return

    fd, pid = spawn([GO_TUI], env_extra={"AUTOCODE_PYTHON_CMD": MOCK_BACKEND})

    try:
        # S1: Startup
        log("\n[S1] Startup render")
        raw = read_until(fd, quiet=2.0, maxwait=15.0, stop_on="AutoCode")
        text = check("S1_startup", raw)
        if "AutoCode" in text:
            ok("S1_startup", "AutoCode header visible")
        else:
            bug(
                "S1_startup: no AutoCode header after 15s",
                f"Got ({len(raw)}B): {text[:200]}",
                "CRITICAL",
            )

        # Allow mock backend status + warning to settle into the UI.
        time.sleep(0.5)
        raw = read_until(fd, quiet=1.0, maxwait=5.0)
        text = check("S1_backend_status", raw)
        if "Error: [backend] WARNING" in text:
            bug(
                "S1_backend_status: warning rendered as fatal error banner",
                text[:300],
                "HIGH",
            )
        elif "⚠" in text or "mock backend" in text.lower():
            ok("S1_backend_status", "warning/status rendered without fatal banner")
        else:
            ok("S1_backend_status", "no fatal backend warning banner observed")

        # S2: normal chat turn
        log("\n[S2] Normal chat turn")
        send(fd, "hello\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=12.0, stop_on="mock backend")
        text = check("S2_chat", raw)
        if "mock backend" in text or "Hello" in text:
            ok("S2_chat", "chat response visible")
        else:
            bug("S2_chat: response not visible", f"Output ({len(raw)}B): {text[:200]}", "HIGH")

        # S3: Ctrl+K palette
        log("\n[S3] Ctrl+K command palette")
        send(fd, "\x0b", delay=0.5)
        raw = read_until(fd, quiet=1.0, maxwait=5.0, stop_on="Palette")
        text = check("S3_ctrl_k", raw)
        if "Palette" in text or "Command" in text or "\u25c6" in text:
            ok("S3_ctrl_k", "palette opened")
            send(fd, "\x1b", delay=0.3)
            read_until(fd, quiet=0.5, maxwait=2.0)
        else:
            bug("S3_ctrl_k: palette did not open", f"Output: {text[:200]}", "HIGH")

        # S4: /model picker (expected, not unsolicited)
        log("\n[S4] /model picker")
        send(fd, "/model\n", delay=0.2)
        raw = read_until(fd, quiet=1.5, maxwait=10.0, stop_on="Select a model")
        text = check("S4_model_picker", raw)
        if "Select a model" in text:
            ok("S4_model_picker", "picker opened as expected")
            send(fd, "\x1b", delay=0.3)
            read_until(fd, quiet=0.5, maxwait=2.0)
        else:
            bug(
                "S4_model_picker: /model did not open picker",
                f"Output ({len(raw)}B): {text[:200]}",
                "HIGH",
            )

        # S5: Clean exit via /exit
        log("\n[S5] Clean exit")
        send(fd, "/exit\n", delay=0.3)
        time.sleep(1.0)

    finally:
        kill(pid, fd)

    # Final report
    log("\n" + "=" * 70)
    log(f"DONE — {len(BUGS)} bugs found")
    log("=" * 70)

    if not BUGS:
        log("  All checks passed.")
    else:
        for b in BUGS:
            log(f"  [{b['severity']}] {b['label']}")

    # Write artifact
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    artifact = ARTIFACT_DIR / f"{ts}-backend-parity-pty-smoke.md"
    with open(artifact, "w") as f:
        f.write("# PTY Smoke Test — Backend Parity (Tasks A-D)\n\n")
        f.write(f"**Date:** {datetime.now(UTC).isoformat()}  \n")
        f.write(f"**Go TUI binary:** `{GO_TUI}`  \n")
        f.write(f"**Terminal size:** {COLS}x{ROWS}  \n")
        f.write(f"**Bugs found:** {len(BUGS)}  \n\n")
        if BUGS:
            f.write("| # | Severity | Label | Detail |\n")
            f.write("|---|----------|-------|--------|\n")
            for i, b in enumerate(BUGS, 1):
                f.write(f"| {i} | {b['severity']} | {b['label']} | {b['detail'][:80]} |\n")
            f.write("\n")
        f.write("## Full Findings Log\n\n```\n")
        f.write("\n".join(FINDINGS))
        f.write("\n```\n")
    log(f"\n  Artifact: {artifact}")
    if BUGS:
        raise SystemExit(1)


if __name__ == "__main__":
    run_smoke()
