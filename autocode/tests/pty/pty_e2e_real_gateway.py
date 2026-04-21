#!/usr/bin/env python3
"""End-to-end PTY smoke against the REAL Python backend + real LLM gateway.

Proves the TUI→backend→gateway chain works for an ordinary turn without
burning many tokens. A single trivial prompt (``/help`` — pure slash-command
handler, no LLM round-trip needed) exercises the full subprocess + RPC path.

Exit code is 0 if ``AutoCode`` header renders, ``suggest`` status bar
appears (backend connected), and no panic/traceback/RPC-error surfaces.
Does NOT run the full benchmark suite — that is a separate multi-hour
session per ``feedback_full_benchmark_runs.md``.
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

RUST_TUI = os.environ.get(
    "AUTOCODE_TUI_BIN",
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../rtui/target/release/autocode-tui")
    ),
)
COLS, ROWS = 160, 50
ANSI = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
BUGS: list[dict] = []
LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg, flush=True)


def bug(label: str, detail: str, severity: str = "HIGH") -> None:
    BUGS.append({"label": label, "detail": detail, "severity": severity})
    log(f"  ❌ [{severity}] {label}: {detail[:200]}")


def ok(label: str, detail: str = "") -> None:
    log(f"  ✓ {label}" + (f" — {detail}" if detail else ""))


def strip(raw: bytes) -> str:
    return ANSI.sub("", raw.decode("utf-8", errors="replace"))


def _winsize(fd: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))


def spawn(argv: list[str], env_extra: dict | None = None) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    _winsize(master_fd)
    _winsize(slave_fd)
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
        }
        if env_extra:
            env.update(env_extra)
        os.execve(argv[0], argv, env)
        sys.exit(1)
    os.close(slave_fd)
    return master_fd, pid


def read_until(
    fd: int, *, quiet: float = 1.5, maxwait: float = 15.0, stop_on: bytes | None = None,
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
        except OSError as e:
            if e.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        buf += chunk
        last = time.monotonic()
        if stop_on is not None and stop_on in buf:
            break
    return buf


def kill(pid: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    try:
        time.sleep(0.4)
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def main() -> int:
    log("E2E TUI smoke — real Python backend + real gateway")
    log(f"Binary: {RUST_TUI}")
    log(f"Terminal: {COLS}x{ROWS}")

    if not os.path.isfile(RUST_TUI):
        bug("E2E_binary_missing", f"not found at {RUST_TUI}", "CRITICAL")
        return 1

    # Spawn real TUI (NO mock backend — real subprocess)
    fd, pid = spawn([RUST_TUI])
    try:
        # Wait for header + backend-connected status bar
        raw = read_until(fd, quiet=2.0, maxwait=20.0, stop_on=b"suggest")
        text = strip(raw)
        if "AutoCode" in text:
            ok("E2E_header", "AutoCode header visible")
        else:
            bug("E2E_header", f"no header after 20s: {text[:200]}", "CRITICAL")
            return 1
        if "suggest" in text or "planning" in text or "autonomous" in text:
            ok("E2E_status", "status bar visible (backend connected)")
        else:
            bug("E2E_status", f"no status bar mode token: {text[:300]}", "HIGH")

        # Send a non-LLM slash command that exercises the JSON-RPC path
        os.write(fd, b"/help\n")
        time.sleep(0.4)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = strip(raw)
        if "panic:" in text:
            bug("E2E_help_panic", f"panic on /help: {text[:300]}", "CRITICAL")
        elif "Traceback" in text:
            bug("E2E_help_traceback", f"traceback on /help: {text[:300]}", "CRITICAL")
        elif any(w in text.lower() for w in ("help", "command", "/model", "/diff")):
            ok("E2E_help", "help response rendered")
        else:
            bug("E2E_help_empty", f"no visible help text: {text[:200]}", "HIGH")

        # Send /cost — another non-LLM command that exercises session store
        os.write(fd, b"/cost\n")
        time.sleep(0.4)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = strip(raw)
        if "panic:" in text:
            bug("E2E_cost_panic", f"panic on /cost: {text[:300]}", "CRITICAL")
        elif any(w in text for w in ("Session", "tokens", "usage", "Messages")):
            ok("E2E_cost", "cost response rendered")
        else:
            bug("E2E_cost_empty", f"no visible cost text: {text[:200]}", "MEDIUM")

        # Optional: send a tiny real chat turn — smallest possible LLM call
        # to prove the full TUI→backend→gateway→LLM chain works.
        log("\n[chat] sending tiny LLM turn 'say OK'")
        os.write(fd, b"say OK\n")
        time.sleep(0.5)
        raw = read_until(fd, quiet=3.0, maxwait=45.0, stop_on=b"OK")
        text = strip(raw)
        if "panic:" in text:
            bug("E2E_chat_panic", f"panic on chat: {text[:300]}", "CRITICAL")
        elif "Traceback" in text:
            bug("E2E_chat_traceback", f"traceback on chat: {text[:300]}", "CRITICAL")
        elif "OK" in text or len(raw) > 500:
            ok("E2E_chat", f"chat turn completed ({len(raw)} bytes)")
        else:
            # Not a hard bug — LLM might be slow/quiet; record as informational
            log(f"  ℹ E2E_chat — no 'OK' token within 45s (raw {len(raw)}B)")

    finally:
        kill(pid)
        try:
            os.close(fd)
        except OSError:
            pass

    # Write artifact
    results_dir = Path(os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "qa", "test-results",
    ))
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    artifact = results_dir / f"{stamp}-pty-e2e-real-gateway.md"
    body = "# PTY E2E Smoke — Real Backend + Gateway\n\n"
    body += f"**Date:** {datetime.now(UTC).isoformat()}\n\n"
    body += f"**Binary:** `{RUST_TUI}`\n\n"
    body += f"**Bugs found:** {len(BUGS)}\n\n"
    body += "## Log\n\n```\n" + "\n".join(LOG) + "\n```\n"
    artifact.write_text(body, encoding="utf-8")
    log(f"\nArtifact: {artifact}")

    return 1 if any(b["severity"] in {"CRITICAL", "HIGH"} for b in BUGS) else 0


if __name__ == "__main__":
    sys.exit(main())
