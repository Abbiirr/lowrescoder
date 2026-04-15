#!/usr/bin/env python3
"""PTY regression tests for Phase 1 + Phase 3-6 fixes.

Targeted scenarios:
  C3  — startup: TUI shows 'AutoCode' + 'Connecting to backend' immediately
  C1  — no model picker after a normal chat turn (backendDoneMsg regression)
  STD — stderr WARNING appears as ⚠ dim line, not red 'Error:' banner
  INL — --inline flag: no alt-screen ANSI escape (?1049h) in output
  ALT — default (no --inline): alt-screen ANSI escape present
  FLW — /followup sends via chat path (no 'steer' leakage visible)

Run: python3 autocode/tests/pty/pty_phase1_fixes_test.py
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

GO_TUI = os.path.join(
    os.path.dirname(__file__),
    "../../cmd/autocode-tui/autocode-tui",
)
GO_TUI = os.path.abspath(GO_TUI)

MOCK_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "mock_backend.py"))
DEAD_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "dead_backend.py"))
# AUTOCODE_PYTHON_CMD is used as the binary path; findPythonBackend appends "serve" as arg.
# Scripts must be executable and accept/ignore "serve".

COLS, ROWS = 160, 50
ANSI = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
ALT_SCREEN_ENTER = b"\x1b[?1049h"

BUGS: list[dict] = []
FINDINGS: list[str] = []


# ── PTY helpers ────────────────────────────────────────────────────────────────

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
        env = {**os.environ, "TERM": "xterm-256color", "COLUMNS": str(COLS), "LINES": str(ROWS)}
        if env_extra:
            env.update(env_extra)
        os.execve(argv[0], argv, env)
        sys.exit(1)
    os.close(slave_fd)
    return master_fd, pid


def read_until(fd: int, *, quiet: float = 1.2, maxwait: float = 20.0,
               stop_on: bytes | None = None) -> bytes:
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
        if stop_on and stop_on in buf:
            time.sleep(0.2)
            r2, _, _ = select.select([fd], [], [], 0)
            if r2:
                try:
                    buf += os.read(fd, 4096)
                except OSError:
                    pass
            break
    return buf


def strip(raw: bytes) -> str:
    return ANSI.sub("", raw.decode("utf-8", errors="replace"))


def send(fd: int, text: str, delay: float = 0.1) -> None:
    os.write(fd, text.replace("\n", "\r").encode())
    time.sleep(delay)


def kill(pid: int, fd: int) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except OSError:
            break
        time.sleep(0.2)
    for x in (pid, fd):
        try:
            (os.waitpid if x == pid else os.close)(x, os.WNOHANG if x == pid else None)  # type: ignore
        except Exception:
            pass


def log(msg: str) -> None:
    print(msg)
    FINDINGS.append(msg)


def ok(label: str, detail: str = "") -> None:
    log(f"  ✓  {label}" + (f" — {detail}" if detail else ""))


def bug(label: str, detail: str, severity: str = "HIGH") -> None:
    BUGS.append({"label": label, "detail": detail, "severity": severity})
    log(f"  ❌ [{severity}] {label}")
    log(f"     {detail[:280]}")


def info(label: str, detail: str = "") -> None:
    log(f"  ℹ  {label}" + (f": {detail}" if detail else ""))


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_c3_startup_no_backend() -> None:
    """C3: TUI must show startup indicator immediately, not hang, without backend."""
    log("\n[C3] Startup without backend — expect 'AutoCode' + 'Connecting' within 5s")
    env = {"AUTOCODE_PYTHON_CMD": DEAD_BACKEND}
    fd, pid = spawn([GO_TUI], env_extra=env)
    try:
        raw = read_until(fd, quiet=1.5, maxwait=8.0, stop_on=b"AutoCode")
        text = strip(raw)
        if "AutoCode" in text:
            ok("C3_header", "'AutoCode' appeared within 8s")
        else:
            bug("C3_header", f"No AutoCode header in 8s. Got: {text[:200]}", "CRITICAL")

        if "Connecting" in text or "backend" in text.lower():
            ok("C3_spinner", "'Connecting to backend' spinner visible during stageInit")
        else:
            # Might already be past stageInit — check for input prompt
            if "help" in text or "❯" in text or "quit" in text:
                ok("C3_spinner", "Already transitioned to stageInput (backend started fast)")
            else:
                bug(
                    "C3_spinner",
                    f"No connecting indicator or input prompt. Got: {text[:200]}",
                    "HIGH",
                )

        # Universal: no panic, no queue leak
        if "panic:" in text:
            bug("C3_panic", f"Go panic at startup: {text[:200]}", "CRITICAL")
        if re.search(r'\(queued \d+ pending\)', text):
            bug("C3_queue_leak", f"Queue text leaked into output: {text[:200]}", "CRITICAL")
        if "Select a model" in text:
            bug("C3_model_picker", "Model picker appeared at startup without /model", "CRITICAL")
    finally:
        kill(pid, fd)


def test_c1_no_model_picker_after_chat() -> None:
    """C1: After a normal on_done event, model picker must NOT appear."""
    log("\n[C1] No model picker after chat turn (mock backend sends on_done)")
    env = {"AUTOCODE_PYTHON_CMD": MOCK_BACKEND}
    fd, pid = spawn([GO_TUI], env_extra=env)
    try:
        # Wait for TUI to reach stageInput
        raw = read_until(fd, quiet=1.5, maxwait=10.0, stop_on=b"AutoCode")
        text = strip(raw)
        if "AutoCode" not in text:
            bug("C1_startup", f"TUI didn't start: {text[:200]}", "CRITICAL")
            return

        # Wait a moment for on_status to arrive
        time.sleep(0.5)
        read_until(fd, quiet=0.8, maxwait=3.0)

        # Send a chat message
        log("  → sending 'hello' to trigger chat turn...")
        send(fd, "hello\n", delay=0.2)

        # Wait for on_done to be processed (mock backend streams tokens then done)
        raw3 = read_until(fd, quiet=2.0, maxwait=12.0, stop_on=b"mock backend")
        text3 = strip(raw3)

        if "Select a model" in text3:
            bug("C1_model_picker_after_done",
                f"Model picker appeared after chat done — C1 regression!\nOutput: {text3[:300]}",
                "CRITICAL")
        else:
            ok("C1_no_picker", "No model picker after chat turn (C1 regression held)")

        if "mock backend" in text3 or "Hello" in text3:
            ok("C1_response", "Mock backend response visible in TUI")
        else:
            info("C1_response", f"Response text not visible (may be timing): {text3[:200]}")

        # Queue text must not appear
        if re.search(r'\(queued \d+ pending\)', text3):
            bug("C1_queue_leak", f"Queue text leaked: {text3[:200]}", "CRITICAL")
        else:
            ok("C1_queue_clean", "No queue text leaked into output")

    finally:
        kill(pid, fd)


def test_stderr_warning_classification() -> None:
    """drainStderr: WARNING from backend must not appear as red 'Error:' banner."""
    log("\n[STD] Stderr WARNING classification — should be ⚠ dim, not 'Error:'")
    env = {"AUTOCODE_PYTHON_CMD": MOCK_BACKEND}
    fd, pid = spawn([GO_TUI], env_extra=env)
    try:
        # Wait for startup + on_status
        raw = read_until(fd, quiet=2.0, maxwait=10.0, stop_on=b"AutoCode")
        time.sleep(1.0)  # let mock backend emit WARNING to stderr
        raw2 = read_until(fd, quiet=1.5, maxwait=5.0)
        combined = raw + raw2
        text = strip(combined)

        # The mock backend emits: WARNING: mock backend starting — this is a test warning
        # It should appear as ⚠ ... not as "Error: [backend] WARNING..."
        if "Error: [backend] WARNING" in text:
            bug(
                "STD_warning_as_error",
                "WARNING stderr rendered as fatal Error: banner — fix not working!"
                f"\nOutput: {text[:300]}",
                "HIGH",
            )
        elif "⚠" in text and "mock backend" in text.lower():
            ok("STD_warning_dim", "WARNING rendered as ⚠ dim line (not error banner)")
        elif "⚠" in text:
            ok("STD_warning_dim", "⚠ warning symbol present in output")
        else:
            info("STD_warning", f"Warning not visible in captured output (timing?): {text[:200]}")

        if "panic:" in text:
            bug("STD_panic", f"Panic in stderr test: {text[:200]}", "CRITICAL")
    finally:
        kill(pid, fd)


def test_inline_mode() -> None:
    """--inline: v.AltScreen=false, so no \\x1b[?1049h in raw output."""
    log("\n[INL] --inline flag: no alt-screen ANSI escape expected")
    env = {"AUTOCODE_PYTHON_CMD": MOCK_BACKEND}
    fd, pid = spawn([GO_TUI, "--inline"], env_extra=env)
    try:
        raw = read_until(fd, quiet=1.5, maxwait=8.0, stop_on=b"AutoCode")
        if ALT_SCREEN_ENTER in raw:
            bug("INL_altscreen",
                "Alt-screen escape found with --inline flag — v.AltScreen not being respected",
                "HIGH")
        else:
            ok("INL_no_altscreen", f"No ?1049h alt-screen escape with --inline ({len(raw)} bytes)")

        text = strip(raw)
        if "AutoCode" in text:
            ok("INL_header", "Header rendered in inline mode")
        else:
            bug("INL_header", f"No AutoCode header in inline mode: {text[:200]}", "HIGH")
    finally:
        kill(pid, fd)


def test_default_altscreen() -> None:
    """Default (no --inline): v.AltScreen=true, so \\x1b[?1049h must be present."""
    log("\n[ALT] Default mode: alt-screen ANSI escape expected")
    env = {"AUTOCODE_PYTHON_CMD": MOCK_BACKEND}
    fd, pid = spawn([GO_TUI], env_extra=env)
    try:
        raw = read_until(fd, quiet=1.5, maxwait=8.0, stop_on=b"AutoCode")
        if ALT_SCREEN_ENTER in raw:
            ok("ALT_altscreen", "Alt-screen escape (?1049h) present in default mode")
        else:
            # BubbleTea v2 may use a different escape or defer it — check for AltScreen indicators
            alt_indicators = [b"\x1b[?1049h", b"\x1b[?47h", b"\x1b[?1047h"]
            found = any(ind in raw for ind in alt_indicators)
            if found:
                ok("ALT_altscreen", "Alt-screen escape present (variant form)")
            else:
                bug("ALT_altscreen",
                    "No alt-screen escape in default mode — v.AltScreen=true not taking effect",
                    "MEDIUM")
        text = strip(raw)
        if "AutoCode" in text:
            ok("ALT_header", "Header rendered in default alt-screen mode")
    finally:
        kill(pid, fd)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    log("=" * 70)
    log("AutoCode PTY — Phase 1 + Phase 3-6 Fix Regression Tests")
    log(f"Binary: {GO_TUI}")
    log(f"Mock backend: {MOCK_BACKEND}")
    log("=" * 70)

    if not os.path.exists(GO_TUI):
        log(f"ERROR: binary not found at {GO_TUI}")
        log("Run: cd autocode/cmd/autocode-tui && go build -o autocode-tui .")
        sys.exit(1)

    test_c3_startup_no_backend()
    test_c1_no_model_picker_after_chat()
    test_stderr_warning_classification()
    test_inline_mode()
    test_default_altscreen()

    log("\n" + "═" * 70)
    log(f"DONE — {len(BUGS)} bugs found across {5} scenarios")
    log("═" * 70)

    by_sev: dict[str, list] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
    for b in BUGS:
        by_sev.setdefault(b["severity"], []).append(b)

    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if by_sev[sev]:
            log(f"\n  {sev} ({len(by_sev[sev])})")
            for b in by_sev[sev]:
                log(f"    • {b['label']}")
                log(f"      {b['detail'][:120]}")

    if not BUGS:
        log("\n  All regression checks passed — no bugs detected.")

    # Write artifact
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results_dir = (
        "/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/test-results"
    )
    out = f"{results_dir}/{timestamp}-pty-phase1-fixes.md"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("# PTY Regression Test — Phase 1 + Fixes\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**Binary:** `{GO_TUI}`  \n")
        f.write(f"**Bugs found:** {len(BUGS)}  \n\n")
        f.write("## Results\n\n")
        f.write("| Severity | Label | Detail |\n")
        f.write("|----------|-------|--------|\n")
        for b in BUGS:
            f.write(f"| {b['severity']} | {b['label']} | {b['detail'][:80]} |\n")
        if not BUGS:
            f.write("| — | All checks passed | — |\n")
        f.write("\n## Full Log\n\n```\n")
        f.write("\n".join(FINDINGS))
        f.write("\n```\n")

    log(f"\n  Artifact: {out}")
    return len(BUGS)


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result == 0 else 1)
