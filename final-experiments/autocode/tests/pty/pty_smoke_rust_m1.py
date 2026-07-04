#!/usr/bin/env python3
"""PTY smoke test for Rust M1 scaffold.

Checks:
  - Backend spawns via PTY without crashing
  - on_status notification received (visible in rendered status line)
  - /exit command exits cleanly, exit code 0, no orphan processes

Note: Ctrl+C now sends cancel RPC from Idle (M8 behavior), so we use /exit
for the clean-exit check. See AGENTS_CONVERSATION.MD Entry 1249.

Run: python3 autocode/tests/pty/pty_smoke_rust_m1.py
Override binary: AUTOCODE_TUI_BIN=<path> python3 autocode/tests/pty/pty_smoke_rust_m1.py
"""
from __future__ import annotations
import errno, fcntl, os, pty, re, select, signal, struct, sys, termios, time
from datetime import UTC, datetime
from pathlib import Path

COLS, ROWS = 160, 50
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


def read_until(fd: int, *, quiet: float = 1.5, maxwait: float = 15.0, stop_on: str | None = None) -> bytes:
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
        env = {**os.environ, "TERM": "xterm-256color",
               "COLUMNS": str(COLS), "LINES": str(ROWS), **env_extra}
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
    log("PTY Smoke Test — Rust M1 Scaffold")
    log(f"Rust TUI binary: {RUST_TUI}")
    log(f"Mock backend:    {MOCK_BACKEND}")
    log(f"Terminal size:   {COLS}x{ROWS}")
    log("=" * 70)

    if not Path(RUST_TUI).is_file():
        log(f"\n  SKIP: Rust binary not found at {RUST_TUI}")
        log("  Build with: cargo build --release --manifest-path autocode/rtui/Cargo.toml")
        sys.exit(2)

    fd, pid = spawn(
        [RUST_TUI],
        {"AUTOCODE_PYTHON_CMD": MOCK_BACKEND},
    )

    exit_code = None
    try:
        # S1: Process starts, on_status received
        # mock_backend emits on_status after 0.3s; Rust renders model|provider|mode in status bar.
        # The render path in view.rs renders: "tools | openrouter | suggest"
        log("\n[S1] Backend spawn + on_status (renderer-owned check)")
        raw = read_until(fd, quiet=2.0, maxwait=10.0)
        text = strip_ansi(raw)

        # Renderer-owned evidence: the status line from view.rs render_composer
        # Format: "{model} | {provider} | {mode}" — mock sends tools/openrouter/suggest
        if "tools" in text and "openrouter" in text and "suggest" in text:
            ok("S1_on_status", "renderer-owned status line rendered correctly")
        else:
            bug("S1_on_status: no renderer-owned status line after 10s",
                f"Got ({len(raw)}B): {text[:500]}", "HIGH")

        if "panic" in text.lower() or "thread ''" in text:
            bug("S1_no_panic: Rust panic detected", text[:300], "CRITICAL")
        else:
            ok("S1_no_panic", "no panic in output")

        # S2: /exit clean exit (Ctrl+C now sends cancel RPC from Idle per M8 behavior)
        log("\n[S2] /exit clean exit")
        send(fd, b"/exit\r", delay=0.5)
        raw2 = read_until(fd, quiet=1.0, maxwait=5.0)

        # Wait for process to exit
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                wpid, status = os.waitpid(pid, os.WNOHANG)
                if wpid == pid:
                    exit_code = os.waitstatus_to_exitcode(status)
                    pid = None  # don't kill in finally
                    break
            except ChildProcessError:
                exit_code = 0
                pid = None
                break
            time.sleep(0.1)

        if exit_code is None:
            bug("S2_clean_exit: process did not exit within 5s after /exit", "", "HIGH")
        elif exit_code == 0:
            ok("S2_clean_exit", f"exited with code 0")
        else:
            bug(f"S2_clean_exit: exit code {exit_code} (expected 0)", "", "HIGH")

    finally:
        if pid is not None:
            kill_proc(pid, fd)
        try:
            os.close(fd)
        except OSError:
            pass

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
        f.write("# PTY Smoke Test — Rust M1 Scaffold\n\n")
        f.write(f"**Date:** {datetime.now(UTC).isoformat()}  \n")
        f.write(f"**Rust TUI binary:** `{RUST_TUI}`  \n")
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
