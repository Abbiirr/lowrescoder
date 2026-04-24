#!/usr/bin/env python3
"""Broader PTY smoke test for Rust TUI.

Current implemented coverage:
  S1: Backend spawn + on_status (renderer-owned status line)
  S2: /exit clean exit

The older M3/M7/M8/M9 aspirations (streaming, /plan, Ctrl+C idle cancel,
/fork) are intentionally not claimed here until the script implements them.

Run: python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py
Override binary: AUTOCODE_TUI_BIN=<path> python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py
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

SIZES = [(80, 24), (120, 40), (200, 50)]
_HERE = Path(__file__).resolve().parent
RUST_TUI = os.environ.get(
    "AUTOCODE_TUI_BIN",
    str(_HERE.parent.parent / "rtui" / "target" / "release" / "autocode-tui"),
)
MOCK_BACKEND = str(_HERE / "mock_backend.py")
ARTIFACT_DIR = _HERE.parent.parent / "docs" / "qa" / "test-results"
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

BUGS: list[dict] = []
FINDINGS: list[str] = []


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def read_until(
    fd: int,
    *,
    quiet: float = 1.5,
    maxwait: float = 15.0,
    stop_on: str | None = None,
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
            time.sleep(0.2)
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


def send(fd: int, data: bytes, delay: float = 0.1) -> None:
    os.write(fd, data)
    time.sleep(delay)


def log(msg: str) -> None:
    print(msg)
    FINDINGS.append(msg)


def bug(label: str, detail: str, severity: str = "HIGH") -> None:
    BUGS.append({"label": label, "detail": detail, "severity": severity})
    log(f"  [FAIL] [{severity}] {label}")
    log(f"         {detail[:300]}")


def ok(label: str, detail: str = "") -> None:
    log(f"  [PASS] {label}" + (f" — {detail}" if detail else ""))


def spawn(argv: list[str], env_extra: dict[str, str], cols: int, rows: int) -> tuple[int, int]:
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


def wait_for_exit(pid: int, timeout: float = 5.0) -> int | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            wpid, status = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:
                return os.waitstatus_to_exitcode(status)
        except ChildProcessError:
            return 0
        time.sleep(0.1)
    return None


def ready_surface_visible(text: str) -> bool:
    if "● ready" not in text:
        return False
    return (
        "Ready for the next task." in text
        or "Describe a change, ask a question" in text
        or ("Restore" in text and "recent checkpoint" in text)
        or ("recent session" in text and "resume/fork" in text)
        or "workspace preserved" in text
        or "Ctrl+Enter send" in text
    )


def resize_surface_visible(text: str) -> bool:
    return (
        "┌" in text
        and "┐" in text
        and ("tools" in text or "suggest" in text or "ready" in text)
    )


def run_size_smoke(
    cols: int,
    rows: int,
    *,
    resize_targets: list[tuple[int, int]] | None = None,
) -> None:
    log(f"\n[SIZE] {cols}x{rows}")
    fd, pid = spawn(
        [RUST_TUI],
        {"AUTOCODE_PYTHON_CMD": MOCK_BACKEND},
        cols,
        rows,
    )

    exit_code = None
    try:
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = strip_ansi(raw)

        if "tools" in text and "openrouter" in text and "suggest" in text:
            ok(f"S1_on_status_{cols}x{rows}", "renderer-owned status line rendered correctly")
        else:
            bug(
                f"S1_on_status_{cols}x{rows}: no renderer-owned status line after 10s",
                f"Got ({len(raw)}B): {text[:500]}",
                "HIGH",
            )

        if ready_surface_visible(text):
            ok(f"S1_ready_surface_{cols}x{rows}", "composer + ready surface visible")
        else:
            bug(
                f"S1_ready_surface_{cols}x{rows}: ready surface missing",
                text[:500],
                "HIGH",
            )

        if "panic" in text.lower() or "thread ''" in text:
            bug(f"S1_no_panic_{cols}x{rows}: Rust panic detected", text[:300], "CRITICAL")
        else:
            ok(f"S1_no_panic_{cols}x{rows}", "no panic in output")

        for target_cols, target_rows in resize_targets or []:
            _set_winsize(fd, target_rows, target_cols)
            os.kill(pid, signal.SIGWINCH)
            time.sleep(0.2)
            resized_raw = read_until(fd, quiet=1.5, maxwait=8.0)
            resized_text = strip_ansi(resized_raw)
            label = f"S1_resize_{cols}x{rows}_to_{target_cols}x{target_rows}"
            if "panic" in resized_text.lower() or "thread ''" in resized_text:
                bug(label, resized_text[:300], "CRITICAL")
            elif ready_surface_visible(resized_text):
                ok(label, "resize redraw preserved the ready surface")
            else:
                send(fd, b"\x0c", delay=0.2)  # Ctrl+L forces a full redraw
                forced_raw = read_until(fd, quiet=1.5, maxwait=8.0)
                forced_text = strip_ansi(forced_raw)
                if ready_surface_visible(forced_text):
                    ok(label, "resize remained usable after forced redraw")
                elif resize_surface_visible(resized_text) or resize_surface_visible(forced_text):
                    ok(label, "resize preserved shell/status redraw and process usability")
                else:
                    bug(label, (resized_text + "\n---FORCED REDRAW---\n" + forced_text)[:500], "HIGH")

        send(fd, b"/exit\r", delay=0.5)
        exit_code = wait_for_exit(pid, timeout=5.0)
        pid = None

        if exit_code is None:
            bug(f"S2_clean_exit_{cols}x{rows}: process did not exit within 5s after /exit", "", "HIGH")
        elif exit_code == 0:
            ok(f"S2_clean_exit_{cols}x{rows}", "exited with code 0")
        else:
            bug(f"S2_clean_exit_{cols}x{rows}: exit code {exit_code} (expected 0)", "", "HIGH")

    finally:
        if pid is not None:
            kill_proc(pid, fd)
        else:
            try:
                os.close(fd)
            except OSError:
                pass


def run_smoke() -> None:
    log("=" * 70)
    log("PTY Smoke Test — Rust TUI (multi-size + resize coverage)")
    log(f"Rust TUI binary: {RUST_TUI}")
    log(f"Mock backend:    {MOCK_BACKEND}")
    log(f"Terminal sizes:  {', '.join(f'{c}x{r}' for c, r in SIZES)}")
    log("=" * 70)

    if not Path(RUST_TUI).is_file():
        log(f"\n  SKIP: Rust binary not found at {RUST_TUI}")
        log("  Build with: cargo build --release --manifest-path autocode/rtui/Cargo.toml")
        sys.exit(2)

    for cols, rows in SIZES:
        resize_targets = [(80, 24), (200, 50)] if (cols, rows) == (120, 40) else None
        run_size_smoke(cols, rows, resize_targets=resize_targets)

    # Report
    log("\n" + "=" * 70)
    log(f"DONE — {len(BUGS)} bugs found")
    log("=" * 70)
    if not BUGS:
        log("  All checks passed.")
    else:
        for b in BUGS:
            log(f"  [{b['severity']}] {b['label']}")

    # Artifact
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    artifact = ARTIFACT_DIR / f"{ts}-rust-m1-pty-smoke.md"
    with open(artifact, "w") as f:
        f.write("# PTY Smoke Test — Rust TUI (multi-size + resize coverage)\n\n")
        f.write(f"**Date:** {datetime.now(UTC).isoformat()}  \n")
        f.write(f"**Rust TUI binary:** `{RUST_TUI}`  \n")
        f.write(f"**Sizes:** `{', '.join(f'{c}x{r}' for c, r in SIZES)}`  \n")
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
        sys.exit(1)


if __name__ == "__main__":
    run_smoke()
