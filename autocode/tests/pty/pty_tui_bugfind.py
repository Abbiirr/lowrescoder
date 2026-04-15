#!/usr/bin/env python3
"""
PTY-based TUI bug finder for autocode Go TUI.

Tests the REAL Go TUI binary in a pseudo-terminal, captures raw ANSI output,
and reports every bug and anomaly. Documents findings for the test procedure log.

Run: python3 autocode/tests/pty/pty_tui_bugfind.py
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

# ── Config ────────────────────────────────────────────────────────────────────
GO_TUI = "/home/bs01763/projects/ai/lowrescoder/autocode/cmd/autocode-tui/autocode-tui"
PY_CHAT = ["/home/bs01763/.local/bin/autocode", "chat"]
COLS, ROWS = 160, 50
ANSI = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

BUGS: list[dict] = []
FINDINGS: list[str] = []

# ── PTY helpers ───────────────────────────────────────────────────────────────

def _set_winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def read_until(fd: int, *, quiet: float = 1.5, maxwait: float = 30.0,
               stop_on: str | None = None) -> bytes:
    """Read until quiet_secs of silence, maxwait exceeded, or stop_on string found."""
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
            if e.errno in (errno.EIO, errno.EBADF, errno.EIO):
                break
            raise
        if not chunk:
            break
        buf += chunk
        last_data = time.monotonic()
        if stop_on and stop_on.encode() in buf:
            # Drain a little more only if bytes are ready; otherwise the PTY
            # harness can block forever after a successful stop-on match.
            time.sleep(0.3)
            r2, _, _ = select.select([fd], [], [], 0)
            if r2:
                try:
                    buf += os.read(fd, 8192)
                except OSError:
                    pass
            break
    return buf


def strip(raw: bytes) -> str:
    return ANSI.sub("", raw.decode("utf-8", errors="replace"))


def send(fd: int, text: str, delay: float = 0.05) -> None:
    os.write(fd, text.replace("\n", "\r").encode())
    time.sleep(delay)


def log(msg: str) -> None:
    print(msg)
    FINDINGS.append(msg)


def bug(label: str, detail: str, severity: str = "HIGH") -> None:
    entry = {"label": label, "detail": detail, "severity": severity}
    BUGS.append(entry)
    log(f"\n  ❌ [{severity}] {label}")
    log(f"     {detail[:300]}")


def ok(label: str, detail: str = "") -> None:
    msg = f"  ✓ {label}" + (f" — {detail}" if detail else "")
    log(msg)


def info(label: str, detail: str = "") -> None:
    msg = f"  ℹ {label}" + (f": {detail}" if detail else "")
    log(msg)


# ── Check helpers ─────────────────────────────────────────────────────────────

def check(label: str, raw: bytes, *,
          must_contain: list[str] | None = None,
          must_not_contain: list[str] | None = None,
          severity: str = "HIGH") -> str:
    text = strip(raw)

    for pat in (must_contain or []):
        if pat not in text:
            bug(f"{label}: missing '{pat}'", f"Output ({len(raw)}B): {text[:300]}", severity)

    for pat in (must_not_contain or []):
        if pat in text:
            bug(f"{label}: unexpected '{pat}'", f"Output ({len(raw)}B): {text[:300]}", severity)

    # Universal checks
    if "Select a model" in text:
        bug(f"{label}: model picker appeared unexpectedly",
            f"Output: {text[:300]}", "CRITICAL")

    if "Select a provider" in text:
        bug(f"{label}: provider picker appeared unexpectedly",
            f"Output: {text[:300]}", "HIGH")

    for m in re.findall(r'\(queued \d+ pending\)', text):
        bug(f"{label}: queue state leaked into visible output",
            f"Found: {m!r}  Full: {text[:300]}", "CRITICAL")

    if "panic:" in text or ("goroutine" in text and "runtime error" in text):
        bug(f"{label}: Go panic in output", text[:400], "CRITICAL")

    if re.search(r'Traceback \(most recent', text):
        bug(f"{label}: Python traceback in output", text[:400], "CRITICAL")

    # Old spinner verb
    if "Thinking\u2026" in text or "Thinking..." in text:
        bug(f"{label}: old 'Thinking…' spinner text still present (verb rotation not applied)",
            text[:200], "MEDIUM")

    return text


# ── Spawn ─────────────────────────────────────────────────────────────────────

def spawn(argv: list[str]) -> tuple[int, int]:
    """Fork a child into a PTY. Returns (master_fd, child_pid)."""
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


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITE A — Go TUI (autocode-tui binary)
# ═════════════════════════════════════════════════════════════════════════════

def suite_go_tui() -> None:
    log("\n" + "═" * 70)
    log("SUITE A — Go TUI (autocode-tui)")
    log("═" * 70)

    fd, pid = spawn([GO_TUI])

    try:
        # ── A1: Startup render ────────────────────────────────────────────────
        log("\n[A1] Startup render — wait up to 10s for AutoCode header")
        raw = read_until(fd, quiet=2.0, maxwait=10.0, stop_on="AutoCode")
        text = check("A1_startup", raw)
        if "AutoCode" in text:
            ok("A1_startup", "header appeared")
        else:
            bug("A1_startup: no AutoCode header after 10s",
                f"Got ({len(raw)} bytes): {text[:200]}", "CRITICAL")

        # ── A2: Ctrl+K palette — must open immediately ────────────────────────
        log("\n[A2] Ctrl+K command palette")
        send(fd, "\x0b", delay=0.5)  # Ctrl+K
        raw = read_until(fd, quiet=1.0, maxwait=5.0, stop_on="Palette")
        text = check("A2_ctrl_k", raw)
        if "Palette" in text or "Command" in text or "◆" in text:
            ok("A2_ctrl_k", "palette opened")
            send(fd, "\x1b", delay=0.3)   # Escape to close
            read_until(fd, quiet=0.5, maxwait=2.0)
        else:
            bug("A2_ctrl_k: Ctrl+K did not open command palette",
                f"Output: {text[:200]}", "HIGH")
            info("A2", f"raw bytes: {list(raw[:20])}")

        # ── A3: /model — must open picker (no LLM needed) ────────────────────
        log("\n[A3] /model picker")
        send(fd, "/model\n", delay=0.2)
        raw = read_until(fd, quiet=1.5, maxwait=10.0, stop_on="Select a model")
        text = check("A3_model_picker", raw,
                     must_not_contain=["panic"])
        if "Select a model" in text:
            ok("A3_model_picker", "picker opened as expected")
            send(fd, "\x1b", delay=0.3)  # Escape
            read_until(fd, quiet=0.5, maxwait=2.0)
        else:
            bug("A3_model_picker: /model did not open picker",
                f"Output ({len(raw)}B): {text[:200]}", "HIGH")

        # ── A4: /diff — no LLM, just git ─────────────────────────────────────
        log("\n[A4] /diff command")
        send(fd, "/diff\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("A4_diff", raw)
        # diff should return git diff output or "No changes"
        if any(w in text for w in ["diff", "changes", "Diff", "git", "---", "+++"]):
            ok("A4_diff", f"got diff content ({len(raw)} bytes)")
        else:
            bug("A4_diff: /diff returned no recognizable output",
                f"Output: {text[:200]}", "MEDIUM")

        # ── A5: /cost — reads session store, no LLM ──────────────────────────
        log("\n[A5] /cost command")
        send(fd, "/cost\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("A5_cost", raw)
        if any(w in text for w in ["Session Usage", "Messages", "tokens", "Estimated"]):
            ok("A5_cost", "usage info returned")
        else:
            bug("A5_cost: /cost returned no usage info",
                f"Output: {text[:200]}", "HIGH")

        # ── A6: /undo — no checkpoints, should say so ─────────────────────────
        log("\n[A6] /undo command")
        send(fd, "/undo\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("A6_undo", raw)
        if any(w in text for w in ["undo", "Nothing", "checkpoint", "Undo"]):
            ok("A6_undo", "undo responded appropriately")
        else:
            bug("A6_undo: /undo returned nothing recognizable",
                f"Output: {text[:200]}", "MEDIUM")

        # ── A7: /export ────────────────────────────────────────────────────────
        log("\n[A7] /export command")
        send(fd, "/export /tmp/autocode_pty_export.md\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("A7_export", raw)
        if any(w in text for w in ["Exported", "export", "session"]):
            ok("A7_export", "export confirmed")
        else:
            bug("A7_export: /export no confirmation",
                f"Output: {text[:200]}", "MEDIUM")

        # ── A8: /help ─────────────────────────────────────────────────────────
        log("\n[A8] /help command")
        send(fd, "/help\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("A8_help", raw)
        if any(w in text for w in ["help", "command", "Commands", "Help"]):
            ok("A8_help", "help responded")
        else:
            bug("A8_help: /help returned nothing",
                f"Output: {text[:200]}", "MEDIUM")

        # ── A9: Slash completion in composer ──────────────────────────────────
        log("\n[A9] Slash completion (type '/')")
        send(fd, "/", delay=0.5)
        raw = read_until(fd, quiet=1.0, maxwait=4.0)
        text = check("A9_slash_completion", raw, severity="LOW")
        if any(w in text for w in ["help", "model", "diff", "undo", "cost"]):
            ok("A9_slash_completion", "completions appeared")
        else:
            bug("A9_slash_completion: no completions shown after '/'",
                f"Output: {text[:200]}", "LOW")
        send(fd, "\x7f", delay=0.2)  # Backspace to clear

        # ── A10: Rapid enter (empty sends) — should not crash ─────────────────
        log("\n[A10] Rapid empty Enter presses (should not crash)")
        for _ in range(5):
            send(fd, "\n", delay=0.1)
        raw = read_until(fd, quiet=1.0, maxwait=5.0)
        text = check("A10_rapid_enter", raw, severity="LOW")
        if "panic" not in text and "runtime error" not in text:
            ok("A10_rapid_enter", "no crash on rapid empty enter")
        else:
            bug("A10_rapid_enter: crash on rapid empty enter", text[:300], "CRITICAL")

        # ── A11: Ctrl+C — should show interrupt, not crash ────────────────────
        log("\n[A11] Ctrl+C interrupt during idle")
        send(fd, "\x03", delay=0.5)  # Ctrl+C
        raw = read_until(fd, quiet=1.0, maxwait=4.0)
        text = check("A11_ctrl_c", raw, severity="LOW")
        # Ctrl+C in idle should clear the composer or do nothing (not quit)
        if "panic" in text:
            bug("A11_ctrl_c: panic on Ctrl+C", text[:300], "CRITICAL")
        else:
            ok("A11_ctrl_c", f"no crash ({len(raw)} bytes)")

        # ── A12: Very long input ──────────────────────────────────────────────
        log("\n[A12] Very long input (500 chars)")
        long_msg = "a" * 500
        send(fd, long_msg, delay=0.3)
        raw = read_until(fd, quiet=1.0, maxwait=5.0)
        text = check("A12_long_input", raw, severity="LOW")
        if "panic" not in text:
            ok("A12_long_input", "no crash on 500-char input")
        else:
            bug("A12_long_input: crash on long input", text[:300], "CRITICAL")
        # Clear the long input
        send(fd, "\x15", delay=0.2)  # Ctrl+U (clear line)

        # ── A13: Arrow keys in idle (should not open pickers) ─────────────────
        log("\n[A13] Arrow keys in idle state")
        send(fd, "\x1b[A", delay=0.2)  # Up arrow
        send(fd, "\x1b[B", delay=0.2)  # Down arrow
        send(fd, "\x1b[C", delay=0.2)  # Right
        send(fd, "\x1b[D", delay=0.2)  # Left
        raw = read_until(fd, quiet=0.8, maxwait=3.0)
        text = check("A13_arrow_keys", raw, severity="LOW")
        if "Select a model" in text or "Select a provider" in text:
            bug("A13_arrow_keys: picker opened by arrow keys in idle state",
                text[:200], "HIGH")
        else:
            ok("A13_arrow_keys", "no unexpected picker on arrow keys")

        # ── A14: /model then type filter + escape ─────────────────────────────
        log("\n[A14] /model picker — type to filter, then Escape")
        send(fd, "/model\n", delay=0.2)
        raw1 = read_until(fd, quiet=1.5, maxwait=8.0, stop_on="Select a model")
        t1 = strip(raw1)
        if "Select a model" in t1:
            # Type a filter
            send(fd, "cod", delay=0.3)
            raw2 = read_until(fd, quiet=1.0, maxwait=3.0)
            t2 = strip(raw2)
            if "coding" not in t2 and "cod" not in t2.lower():
                bug("A14_model_filter: typing in picker doesn't filter",
                    f"After typing 'cod': {t2[:200]}", "HIGH")
            else:
                ok("A14_model_filter", "filter works in model picker")
            # Escape
            send(fd, "\x1b", delay=0.3)
            read_until(fd, quiet=0.5, maxwait=2.0)
        else:
            info("A14", "skipped — /model didn't open picker (see A3)")

    finally:
        kill(pid, fd)


# ═════════════════════════════════════════════════════════════════════════════
# TEST SUITE B — Python inline chat (autocode chat)
# ═════════════════════════════════════════════════════════════════════════════

def suite_py_chat() -> None:
    log("\n" + "═" * 70)
    log("SUITE B — Python inline chat (autocode chat)")
    log("═" * 70)

    fd, pid = spawn(PY_CHAT)

    try:
        # ── B1: Startup ───────────────────────────────────────────────────────
        log("\n[B1] Startup — wait for prompt")
        raw = read_until(fd, quiet=2.0, maxwait=15.0, stop_on="AutoCode")
        text = check("B1_startup", raw)
        if "AutoCode" in text or "autocode" in text.lower() or "❯" in text or ">" in text:
            ok("B1_startup", f"started ({len(raw)} bytes)")
        else:
            bug("B1_startup: no prompt after 15s", f"Got: {text[:200]}", "CRITICAL")

        # ── B2: /cost ─────────────────────────────────────────────────────────
        log("\n[B2] /cost in Python inline")
        send(fd, "/cost\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("B2_cost_py", raw)
        if any(w in text for w in ["Session Usage", "tokens", "Messages", "Estimated"]):
            ok("B2_cost_py", "usage returned")
        else:
            bug("B2_cost_py: /cost returned nothing in Python inline",
                f"Output: {text[:200]}", "HIGH")

        # ── B3: /diff ─────────────────────────────────────────────────────────
        log("\n[B3] /diff in Python inline")
        send(fd, "/diff\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("B3_diff_py", raw)
        if any(w in text for w in ["diff", "changes", "---", "+++"]):
            ok("B3_diff_py", "diff output returned")
        else:
            bug("B3_diff_py: /diff returned nothing in Python inline",
                f"Output: {text[:200]}", "HIGH")

        # ── B4: /undo ─────────────────────────────────────────────────────────
        log("\n[B4] /undo in Python inline")
        send(fd, "/undo\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("B4_undo_py", raw)
        if any(w in text for w in ["undo", "Nothing", "checkpoint", "Undo"]):
            ok("B4_undo_py", "undo responded")
        else:
            bug("B4_undo_py: /undo returned nothing in Python inline",
                f"Output: {text[:200]}", "HIGH")

        # ── B5: /model ────────────────────────────────────────────────────────
        log("\n[B5] /model in Python inline")
        send(fd, "/model\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = check("B5_model_py", raw)
        if any(w in text for w in ["model", "Model", "current", "available"]):
            ok("B5_model_py", "model responded")
        else:
            bug("B5_model_py: /model returned nothing in Python inline",
                f"Output: {text[:200]}", "MEDIUM")

        # ── B6: @file expansion ───────────────────────────────────────────────
        log("\n[B6] @file mention expansion")
        send(fd, "show me @autocode/src/autocode/agent/tools.py briefly\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=15.0)
        text = check("B6_file_expansion", raw)
        if "[File:" in text or "tools" in text.lower():
            ok("B6_file_expansion", "@file expanded into message")
        else:
            bug("B6_file_expansion: @file mention not expanded",
                f"Output: {text[:200]}", "HIGH")

        # ── B7: todo_write tool availability ─────────────────────────────────
        log("\n[B7] todo_write tool registration check")
        send(fd, "use todo_write to plan: step 1, step 2\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=20.0, stop_on="Session Summary")
        text = check("B7_todo_write", raw)
        if any(w in text for w in ["todo", "Todo", "plan", "step"]):
            ok("B7_todo_write", "todo_write appears to be wired")
        else:
            info("B7_todo_write", f"inconclusive ({len(raw)}B): {text[:100]}")

        # ── B8: RulesLoader always-on ─────────────────────────────────────────
        log("\n[B8] RulesLoader — rules injected at session start?")
        # We can probe this by asking the model if it has read CLAUDE.md
        send(fd, "what is the project invariant about LLM usage?\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=30.0, stop_on="Session Summary")
        text = check("B8_rules_loader", raw)
        if any(w in text for w in ["LLM", "last resort", "deterministic", "layer"]):
            ok("B8_rules_loader", "model knows CLAUDE.md invariants — RulesLoader active")
        else:
            bug("B8_rules_loader: model doesn't seem to know project invariants",
                f"Output: {text[:300]}", "MEDIUM")

    finally:
        send(fd, "/exit\n", delay=0.3)
        time.sleep(0.5)
        kill(pid, fd)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    log("=" * 70)
    log("AutoCode PTY Bug Finder — Full Suite")
    log(f"Go TUI: {GO_TUI}")
    log(f"Python: {' '.join(PY_CHAT)}")
    log(f"Terminal size: {COLS}x{ROWS}")
    log("=" * 70)

    suite_go_tui()
    suite_py_chat()

    # ── Final report ─────────────────────────────────────────────────────────
    log("\n" + "═" * 70)
    log(f"DONE — {len(BUGS)} bugs found")
    log("═" * 70)

    by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
    for b in BUGS:
        by_severity.get(b["severity"], by_severity["LOW"]).append(b)

    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if by_severity[sev]:
            log(f"\n  {sev} ({len(by_severity[sev])})")
            for b in by_severity[sev]:
                log(f"    • {b['label']}")
                log(f"      {b['detail'][:120]}")

    if not BUGS:
        log("  No bugs detected.")

    # Write findings to disk
    out = "/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/pty-tui-bug-report.md"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("# PTY TUI Bug Report\n\n")
        f.write("**Date:** 2026-04-13  \n")
        f.write("**Tester:** PTY automated (pty_tui_bugfind.py)  \n")
        f.write(f"**Go TUI binary:** `{GO_TUI}`  \n")
        f.write(f"**Python chat:** `{' '.join(PY_CHAT)}`  \n\n")
        f.write(f"## Summary\n\n{len(BUGS)} bugs found.\n\n")
        f.write("| # | Severity | Label | Detail |\n")
        f.write("|---|---------|-------|--------|\n")
        for i, b in enumerate(BUGS, 1):
            f.write(f"| {i} | {b['severity']} | {b['label']} | {b['detail'][:80]} |\n")
        f.write("\n## Full Findings Log\n\n```\n")
        f.write("\n".join(FINDINGS))
        f.write("\n```\n")
    log(f"\n  Report written: {out}")


if __name__ == "__main__":
    main()
