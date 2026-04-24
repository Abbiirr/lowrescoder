#!/usr/bin/env python3
"""End-to-end PTY smoke against the REAL Python backend + real LLM gateway.

This validates the current Rust TUI contract, not the deleted Go-era header:

- renderer-owned status lane appears (`tools | openrouter | suggest`)
- non-LLM slash commands work against the live backend (`/help`, `/cost`)
- a real chat turn completes against the configured gateway
- command discovery remains usable while a real chat turn is in flight

The harness keys off ANSI-stripped stream tokens, not a final-screen layout.
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
KITTY_CSI_U = re.compile(rb"\x1b\[[?>=<0-9;:]*u")
BUGS: list[dict] = []
LOG: list[str] = []
AUTH_ENV_VARS = ("LITELLM_API_KEY", "LITELLM_MASTER_KEY", "OPENROUTER_API_KEY")


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg, flush=True)


def bug(label: str, detail: str, severity: str = "HIGH") -> None:
    BUGS.append({"label": label, "detail": detail, "severity": severity})
    log(f"  ❌ [{severity}] {label}: {detail[:200]}")


def ok(label: str, detail: str = "") -> None:
    log(f"  ✓ {label}" + (f" — {detail}" if detail else ""))


def strip(raw: bytes) -> str:
    cleaned = KITTY_CSI_U.sub(b"", raw)
    text = ANSI.sub("", cleaned.decode("utf-8", errors="replace"))
    return text.replace("\r", "\n")


def ready_surface_visible(text: str) -> bool:
    return (
        "openrouter" in text
        and "suggest" in text
        and ("● ready" in text or "Describe a change, ask a question" in text)
    )


def command_palette_visible(text: str) -> bool:
    return ("Slash Commands" in text or "Command Palette" in text) and any(
        token in text for token in ("/help", "/model", "/cost", "/plan")
    )


def unhealthy_runtime(text: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in (
            "requests timed out",
            "panic:",
            "traceback",
            "backend not responding",
            "authentication error",
        )
    )


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

    auth_source = next((name for name in AUTH_ENV_VARS if os.environ.get(name, "").strip()), None)
    if auth_source:
        ok("E2E_auth_env", f"using {auth_source}")
    else:
        bug(
            "E2E_auth_env_missing",
            "set one of LITELLM_API_KEY, LITELLM_MASTER_KEY, or OPENROUTER_API_KEY",
            "CRITICAL",
        )
        return 1

    # Spawn real TUI (NO mock backend — real subprocess)
    fd, pid = spawn([RUST_TUI])
    try:
        # Wait for ready surface + backend-connected status line
        raw = read_until(fd, quiet=2.0, maxwait=20.0, stop_on=b"suggest")
        text = strip(raw)
        if ready_surface_visible(text):
            ok("E2E_ready", "status line + prompt visible")
        else:
            bug("E2E_ready", f"no ready surface after 20s: {text[:300]}", "CRITICAL")
            return 1

        # Send a non-LLM slash command that exercises the JSON-RPC path
        os.write(fd, b"/help\r")
        time.sleep(0.4)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = strip(raw)
        if unhealthy_runtime(text):
            bug("E2E_help_runtime", f"runtime failure on /help: {text[:300]}", "CRITICAL")
        elif any(w in text.lower() for w in ("help", "command", "/model", "/diff")):
            ok("E2E_help", "help response rendered")
        else:
            bug("E2E_help_empty", f"no visible help text: {text[:200]}", "HIGH")

        # Send /cost — another non-LLM command that exercises session store
        os.write(fd, b"/cost\r")
        time.sleep(0.4)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = strip(raw)
        if unhealthy_runtime(text):
            bug("E2E_cost_runtime", f"runtime failure on /cost: {text[:300]}", "CRITICAL")
        elif any(w in text for w in ("Session", "tokens", "usage", "Messages")):
            ok("E2E_cost", "cost response rendered")
        else:
            bug("E2E_cost_empty", f"no visible cost text: {text[:200]}", "MEDIUM")

        # Start a real chat turn, then immediately request the command palette.
        # This verifies backend-owned command discovery remains usable while
        # a real turn is in flight instead of wedging behind the chat request.
        log("\n[chat] sending live turn and probing async command discovery")
        os.write(fd, b"Count from 1 to 20, one number per line, then say OK.\r")
        time.sleep(1.5)
        os.write(fd, b"/")
        time.sleep(0.2)
        raw = read_until(fd, quiet=2.0, maxwait=15.0, stop_on=b"Slash Commands")
        text = strip(raw)
        if unhealthy_runtime(text):
            bug("E2E_async_palette_runtime", f"runtime failure during live-turn palette probe: {text[:400]}", "CRITICAL")
        elif command_palette_visible(text):
            ok("E2E_async_palette", "command palette loaded during live turn")
        else:
            bug(
                "E2E_async_palette_missing",
                f"palette did not render command entries during live turn: {text[:400]}",
                "HIGH",
            )

        # Close the palette if it is open, then wait for the live turn to finish.
        os.write(fd, b"\x1b")
        time.sleep(0.2)
        raw = read_until(fd, quiet=3.0, maxwait=60.0, stop_on=b"OK")
        text = strip(raw)
        if unhealthy_runtime(text):
            bug("E2E_chat_runtime", f"runtime failure on live chat: {text[:400]}", "CRITICAL")
        elif "OK" in text or len(raw) > 500:
            ok("E2E_chat", f"chat turn completed ({len(raw)} bytes)")
        else:
            bug("E2E_chat_incomplete", f"no visible live-turn completion: {text[:400]}", "HIGH")

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
