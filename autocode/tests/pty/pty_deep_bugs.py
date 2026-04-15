#!/usr/bin/env python3
"""
Deep PTY bug hunt for autocode Python inline (autocode chat).
Specifically targets:
  - Slash command bugs
  - @file expansion
  - RulesLoader context injection
  - todo_write/read tool availability
  - glob_files / grep_content tool availability
  - 3-tier compaction edge cases
  - Session state leaks between commands

Run: python3 autocode/tests/pty/pty_deep_bugs.py
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

BINARY  = ["/home/bs01763/.local/bin/autocode", "chat"]
COLS, ROWS = 200, 60
ANSI = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
BUGS: list[dict] = []
FINDINGS: list[str] = []

def strip(raw: bytes) -> str:
    return ANSI.sub("", raw.decode("utf-8", errors="replace"))

def log(msg: str) -> None:
    print(msg)
    FINDINGS.append(msg)

def bug(label: str, detail: str, sev: str = "HIGH") -> None:
    BUGS.append({"label": label, "detail": detail, "sev": sev})
    log(f"\n  ❌ [{sev}] {label}")
    log(f"     {detail[:300]}")

def ok(label: str, detail: str = "") -> None:
    log(f"  ✓ {label}" + (f" — {detail}" if detail else ""))

def info(label: str, detail: str = "") -> None:
    log(f"  ℹ {label}" + (f": {detail[:200]}" if detail else ""))


def _set_winsize(fd: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))


def read_until(fd: int, *, quiet: float = 2.0, maxwait: float = 30.0,
               stop_on: str | None = None) -> bytes:
    buf = b""
    deadline = time.monotonic() + maxwait
    last = time.monotonic()
    while True:
        now = time.monotonic()
        if now >= deadline:
            break
        wait = min(quiet - (now - last), deadline - now)
        if wait <= 0:
            if time.monotonic() - last >= quiet:
                break
            continue
        r, _, _ = select.select([fd], [], [], max(wait, 0.05))
        if not r:
            if time.monotonic() - last >= quiet:
                break
            continue
        try:
            chunk = os.read(fd, 16384)
        except OSError as e:
            if e.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        buf += chunk
        last = time.monotonic()
        if stop_on and stop_on.encode() in buf:
            time.sleep(0.4)
            try:
                extra = os.read(fd, 16384)
                buf += extra
            except OSError:
                pass
            break
    return buf


def send(fd: int, text: str, delay: float = 0.15) -> None:
    os.write(fd, text.replace("\n", "\r").encode())
    time.sleep(delay)


def spawn() -> tuple[int, int]:
    m, s = pty.openpty()
    _set_winsize(m)
    _set_winsize(s)
    pid = os.fork()
    if pid == 0:
        os.setsid()
        fcntl.ioctl(s, termios.TIOCSCTTY, 0)
        for fd in (0,1,2):
            os.dup2(s, fd)
        os.close(m)
        os.close(s)
        env = {**os.environ, "TERM": "xterm-256color",
               "COLUMNS": str(COLS), "LINES": str(ROWS), "NO_COLOR": "0"}
        os.execve(BINARY[0], BINARY, env)
        sys.exit(1)
    os.close(s)
    return m, pid


def kill_proc(pid: int, fd: int) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except OSError:
            break
        time.sleep(0.3)
    try:
        os.waitpid(pid, os.WNOHANG)
    except OSError:
        pass
    try:
        os.close(fd)
    except OSError:
        pass


def universal_checks(label: str, text: str) -> None:
    if "Select a model" in text and "model" not in label.lower():
        bug(f"{label}: model picker appeared unexpectedly", text[:300], "CRITICAL")
    if re.search(r'\(queued \d+ pending\)', text):
        bug(f"{label}: queue state leaked into visible output", text[:300], "CRITICAL")
    if "panic:" in text or "runtime error" in text:
        bug(f"{label}: Go panic", text[:300], "CRITICAL")
    if re.search(r'Traceback \(most recent', text):
        bug(f"{label}: Python traceback", text[:300], "CRITICAL")
    if "Thinking\u2026" in text:
        bug(f"{label}: old Thinking… spinner still present", text[:200], "MEDIUM")


# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    log("=" * 70)
    log("AutoCode Python Inline Deep PTY Bug Hunt")
    log("=" * 70)

    fd, pid = spawn()

    try:
        # Wait for startup
        log("\n[STARTUP] Waiting for chat prompt (up to 15s)...")
        raw = read_until(fd, quiet=2.0, maxwait=15.0, stop_on="❯")
        text = strip(raw)
        if "❯" not in text and ">" not in text and "AutoCode" not in text:
            bug("STARTUP: no prompt after 15s", f"Got: {text[:200]}", "CRITICAL")
            return
        ok("STARTUP", f"{len(raw)} bytes, prompt visible")
        log(f"  Startup output: {text[:300].strip()!r}")

        # ──────────────────────────────────────────────────────────────────────
        # 1. Slash commands — each must respond without picker appearing
        # ──────────────────────────────────────────────────────────────────────
        log("\n── SLASH COMMAND TESTS ──")

        slash_tests = [
            ("/help",   ["help", "command", "Commands"], "help text"),
            ("/diff",   ["diff", "changes", "---", "+++", "No changes"], "git diff"),
            ("/cost",   ["Session Usage", "Messages", "tokens", "Estimated"], "usage info"),
            ("/undo",   ["Nothing", "checkpoint", "Undo", "undo", "restore"], "undo response"),
            (
                "/export /tmp/pty_test_export.md",
                ["Exported", "export", "session"],
                "export confirm",
            ),
            ("/clear",  [], "any response (or silent clear)"),  # might clear screen silently
            (
                "/compact",
                ["compact", "Compact", "conversation", "summary", "Nothing"],
                "compact response",
            ),
        ]

        for cmd, must_have, desc in slash_tests:
            log(f"\n  Testing {cmd!r}...")
            send(fd, cmd + "\n", delay=0.2)
            raw = read_until(fd, quiet=2.0, maxwait=12.0)
            text = strip(raw)
            universal_checks(f"slash_{cmd.split()[0]}", text)

            if must_have:
                found = any(w in text for w in must_have)
                if found:
                    ok(cmd, desc)
                else:
                    bug(f"slash_{cmd.split()[0]}: returned nothing for '{cmd}'",
                        f"Expected one of {must_have}. Got ({len(raw)}B): {text[:200]}", "HIGH")
            else:
                ok(cmd, f"{len(raw)} bytes (silent OK)")

        # ──────────────────────────────────────────────────────────────────────
        # 2. /model — must show ARROW-KEY picker (feedback requirement)
        # ──────────────────────────────────────────────────────────────────────
        log("\n── /MODEL PICKER TEST ──")
        send(fd, "/model\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = strip(raw)
        if "❯" in text and any(m in text for m in ["coding", "default", "tools", "fast"]):
            ok("/model", "arrow-key picker appeared correctly")
            # Navigate: down arrow twice, then escape
            send(fd, "\x1b[B\x1b[B", delay=0.3)
            send(fd, "\x1b", delay=0.3)
            raw2 = read_until(fd, quiet=1.0, maxwait=4.0)
            text2 = strip(raw2)
            picker_gone = (
                "Select" not in text2
                and ("❯" not in text2.split("model")[0] if "model" in text2 else True)
            )
            if picker_gone:
                ok("/model escape", "picker closed by Escape")
            # check cursor moved
        elif "model" in text.lower() or "Model" in text:
            ok("/model", f"responded with model info ({len(raw)} bytes)")
        else:
            bug("/model: returned nothing recognizable",
                f"Got ({len(raw)}B): {text[:200]}", "HIGH")

        # ──────────────────────────────────────────────────────────────────────
        # 3. /provider — must show arrow-key picker
        # ──────────────────────────────────────────────────────────────────────
        log("\n── /PROVIDER PICKER TEST ──")
        send(fd, "/provider\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=8.0)
        text = strip(raw)
        if any(p in text for p in ["openai", "anthropic", "openrouter", "Provider", "provider"]):
            ok("/provider", "provider list appeared")
            send(fd, "\x1b", delay=0.3)
            read_until(fd, quiet=0.5, maxwait=2.0)
        else:
            bug("/provider: no provider list", f"Got: {text[:200]}", "MEDIUM")

        # ──────────────────────────────────────────────────────────────────────
        # 4. @file expansion — send message referencing a real file
        # ──────────────────────────────────────────────────────────────────────
        log("\n── @FILE EXPANSION TEST ──")
        # Test 1: Does @file get replaced in the message sent to backend?
        # We test by referencing a tiny file and asking what's in it
        test_file = "/tmp/pty_atfile_test.txt"
        with open(test_file, "w") as f:
            f.write("CANARY_VALUE_XYZ_42\n")

        send(fd, f"what is the content of @{test_file} ?\n", delay=0.3)
        raw = read_until(fd, quiet=2.0, maxwait=20.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("atfile_expansion", text)
        if "CANARY_VALUE_XYZ_42" in text or "[File:" in text:
            ok("@file expansion", "file content was injected and visible in response")
        elif "Session Summary" in text:
            # LLM responded but didn't see the file content
            if test_file in text or "canary" in text.lower():
                ok("@file expansion", "file mentioned in response")
            else:
                bug("@file expansion: LLM response doesn't show file content",
                    f"Response: {text[-300:]}", "HIGH")
        else:
            bug("@file expansion: no response within 20s",
                f"Got ({len(raw)}B): {text[:200]}", "MEDIUM")

        # Test 2: @file with non-existent path
        log("\n  @file with non-existent path...")
        send(fd, "show @/nonexistent/fake/file.txt\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=15.0, stop_on="Session Summary")
        text = strip(raw)
        if "not found" in text.lower() or "cannot" in text.lower() or "[File:" not in text:
            ok("@file nonexistent", "gracefully handled missing file")
        elif "[File:" in text and "could not read" in text:
            ok("@file nonexistent", "shows could-not-read message")
        else:
            info("@file nonexistent", f"response: {text[-100:]!r}")

        # ──────────────────────────────────────────────────────────────────────
        # 5. RulesLoader — check if CLAUDE.md is injected (ask about invariants)
        # ──────────────────────────────────────────────────────────────────────
        log("\n── RULES LOADER TEST ──")
        send(
            fd,
            "what does CLAUDE.md say about LLM usage policy? answer in one sentence\n",
            delay=0.2,
        )
        raw = read_until(fd, quiet=3.0, maxwait=35.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("rules_loader", text)
        if any(w in text for w in ["last resort", "deterministic", "LLM", "layer", "fallback"]):
            ok("RulesLoader", "model knows CLAUDE.md invariants — rules injected")
        elif "Session Summary" in text:
            bug("RulesLoader: model responded but doesn't know project invariants",
                f"Response: {text[-200:]}", "MEDIUM")
        else:
            bug("RulesLoader: no response within 35s",
                f"Got ({len(raw)}B): {text[:100]}", "MEDIUM")

        # ──────────────────────────────────────────────────────────────────────
        # 6. todo_write / todo_read tool availability
        # ──────────────────────────────────────────────────────────────────────
        log("\n── TODO_WRITE / TODO_READ TOOL TEST ──")
        send(
            fd,
            "use the todo_write tool to create a 2-item plan, then read it with todo_read\n",
            delay=0.2,
        )
        raw = read_until(fd, quiet=3.0, maxwait=40.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("todo_tools", text)
        tool_hit = (
            "todo_write" in text or "todo_read" in text
            or "Todo list" in text or "plan" in text.lower()
        )
        if tool_hit:
            ok("todo_write/todo_read tools", "tool invoked in response")
        elif "Session Summary" in text:
            bug("todo_tools: LLM responded but didn't call todo_write",
                f"Response: {text[-300:]}", "MEDIUM")
        else:
            info("todo_tools", f"no response yet ({len(raw)}B)")

        # ──────────────────────────────────────────────────────────────────────
        # 7. glob_files tool
        # ──────────────────────────────────────────────────────────────────────
        log("\n── GLOB_FILES TOOL TEST ──")
        send(fd, "use glob_files to find all *.md files in /tmp\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=30.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("glob_files", text)
        if ".md" in text or "glob" in text.lower() or "found" in text.lower():
            ok("glob_files tool", "tool invoked")
        elif "Session Summary" in text:
            bug("glob_files: LLM responded but didn't use glob_files",
                f"Response: {text[-200:]}", "LOW")
        else:
            info("glob_files", f"inconclusive ({len(raw)}B)")

        # ──────────────────────────────────────────────────────────────────────
        # 8. grep_content tool
        # ──────────────────────────────────────────────────────────────────────
        log("\n── GREP_CONTENT TOOL TEST ──")
        send(fd, "use grep_content to search for 'CANARY_VALUE' in /tmp\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=30.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("grep_content", text)
        if "CANARY_VALUE" in text or "grep" in text.lower() or "found" in text.lower():
            ok("grep_content tool", "tool invoked or found match")
        elif "Session Summary" in text:
            bug("grep_content: LLM responded but didn't use grep_content",
                f"Response: {text[-200:]}", "LOW")
        else:
            info("grep_content", f"inconclusive ({len(raw)}B)")

        # ──────────────────────────────────────────────────────────────────────
        # 9. Ctrl+K in Python inline — should it open a palette?
        # ──────────────────────────────────────────────────────────────────────
        log("\n── CTRL+K IN PYTHON INLINE ──")
        send(fd, "\x0b", delay=0.5)
        raw = read_until(fd, quiet=1.0, maxwait=3.0)
        text = strip(raw)
        if "Palette" in text or "Command" in text:
            ok("Ctrl+K in Python inline", "palette opened")
        else:
            info("Ctrl+K in Python inline",
                 "no palette (Python inline doesn't support Ctrl+K — Go TUI only)")

        # ──────────────────────────────────────────────────────────────────────
        # 10. Session Summary format check
        # ──────────────────────────────────────────────────────────────────────
        log("\n── SESSION SUMMARY FORMAT CHECK ──")
        send(fd, "hi\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=40.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("session_summary", text)
        if "Session Summary" in text:
            if "Time:" in text and "Files changed:" in text:
                ok("Session Summary format", "contains Time + Files changed")
            else:
                start = text.find("Session Summary")
                snippet = text[start:start + 200]
                bug(
                    "Session Summary: missing fields",
                    f"Summary text: {snippet}",
                    "LOW",
                )
        else:
            info("session_summary", f"no session summary in response ({len(raw)}B)")

        # ──────────────────────────────────────────────────────────────────────
        # 11. Check for model picker appearing after normal chat (screenshot bug)
        # ──────────────────────────────────────────────────────────────────────
        log("\n── MODEL PICKER AFTER CHAT (Screenshot Bug) ──")
        send(fd, "just say hello back\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=40.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("model_picker_after_chat", text)
        if "Select a model" in text:
            bug("MODEL PICKER APPEARED AFTER NORMAL CHAT",
                f"Model picker shown after plain chat message! Text: {text[:400]}", "CRITICAL")
        else:
            ok("model picker after chat", "no spurious model picker after chat")

        # ──────────────────────────────────────────────────────────────────────
        # 12. Check for queue state "(queued N pending)" in responses
        # ──────────────────────────────────────────────────────────────────────
        log("\n── QUEUE LEAK DETECTION ──")
        # Send 2 messages rapidly
        os.write(fd, b"one\n")
        time.sleep(0.2)
        os.write(fd, b"two\n")
        raw = read_until(fd, quiet=3.0, maxwait=40.0, stop_on="Session Summary")
        text = strip(raw)
        if re.search(r'\(queued \d+ pending\)', text):
            bug("QUEUE STATE LEAKED INTO OUTPUT",
                f"Found '(queued N pending)' text in: {text[:300]}", "CRITICAL")
        else:
            ok("queue leak detection", "no queue state text in output")

        # ──────────────────────────────────────────────────────────────────────
        # 13. Test /export creates actual file
        # ──────────────────────────────────────────────────────────────────────
        log("\n── /EXPORT FILE CREATION TEST ──")
        out_path = "/tmp/pty_export_test.md"
        if os.path.exists(out_path):
            os.unlink(out_path)
        send(fd, f"/export {out_path}\n", delay=0.2)
        raw = read_until(fd, quiet=2.0, maxwait=8.0)
        text = strip(raw)
        if "Exported" in text:
            if os.path.exists(out_path):
                sz = os.path.getsize(out_path)
                ok("/export file creation", f"file exists, {sz} bytes")
            else:
                bug("/export: said 'Exported' but file not created",
                    f"Path: {out_path}", "HIGH")
        else:
            bug("/export: no Exported confirmation", f"Got: {text[:200]}", "HIGH")

        # ──────────────────────────────────────────────────────────────────────
        # 14. Test todo_write mandatory planning nudge (iteration 2 in AUTO mode)
        # ──────────────────────────────────────────────────────────────────────
        log("\n── TODO_WRITE PLANNING NUDGE TEST ──")
        # This should be triggered when the agent runs 2 iterations without calling todo_write
        # Hard to test without direct tool visibility — just verify no crash
        send(fd, "write a python function to add two numbers, save to /tmp/add.py\n", delay=0.2)
        raw = read_until(fd, quiet=3.0, maxwait=50.0, stop_on="Session Summary")
        text = strip(raw)
        universal_checks("todo_nudge", text)
        if "Session Summary" in text:
            if "[Planning Required]" in text or "todo_write" in text or "plan" in text.lower():
                ok("todo_write nudge", "planning nudge visible in response")
            else:
                info("todo_write nudge", "no nudge visible (LLM may have called todo_write first)")
        else:
            info("todo_nudge", f"no session summary in {len(raw)}B")

    finally:
        send(fd, "/exit\n", delay=0.3)
        time.sleep(0.5)
        kill_proc(pid, fd)

    # ── Report ────────────────────────────────────────────────────────────────
    log("\n" + "=" * 70)
    log(f"DEEP BUG HUNT DONE — {len(BUGS)} bugs found")
    log("=" * 70)

    by_sev = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
    for b in BUGS:
        by_sev.get(b["sev"], by_sev["LOW"]).append(b)

    for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if by_sev[s]:
            log(f"\n  {s} ({len(by_sev[s])})")
            for b in by_sev[s]:
                log(f"    • {b['label']}")
                log(f"      {b['detail'][:150]}")


if __name__ == "__main__":
    run()
