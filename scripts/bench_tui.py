#!/usr/bin/env python3
"""TUI benchmark harness.

Requires the TUI to emit BENCH sentinel strings when HYBRIDCODER_BENCH=1 is set.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import select
import subprocess
import sys
import time
import pty
from dataclasses import dataclass
from typing import Optional

READY_SENTINEL = b"BENCH:READY"
PONG_SENTINEL = b"BENCH:PONG"
EXIT_SENTINEL = b"BENCH:EXIT"


@dataclass
class BenchResult:
    supported: bool
    startup_ms: Optional[float] = None
    ping_ms: Optional[float] = None
    error: Optional[str] = None


def _read_until(fd: int, sentinel: bytes, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    buf = b""
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        ready, _, _ = select.select([fd], [], [], remaining)
        if fd not in ready:
            continue
        try:
            data = os.read(fd, 4096)
        except OSError:
            return False
        if not data:
            return False
        buf += data
        if sentinel in buf:
            return True
    return False


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=1.0)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _run_version(cmd: list[str]) -> float:
    start = time.monotonic()
    subprocess.run(cmd + ["--version"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.monotonic()
    return (end - start) * 1000.0


def run_tui_bench(cmd: list[str], timeout_ready: float, timeout_ping: float) -> BenchResult:
    env = os.environ.copy()
    env["HYBRIDCODER_BENCH"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
        )
    except Exception as exc:
        os.close(master_fd)
        os.close(slave_fd)
        return BenchResult(supported=False, error=f"spawn failed: {exc}")

    os.close(slave_fd)

    start = time.monotonic()
    ready = _read_until(master_fd, READY_SENTINEL, timeout_ready)
    if not ready:
        _terminate(proc)
        os.close(master_fd)
        return BenchResult(supported=False, error="READY sentinel not seen")

    ready_ms = (time.monotonic() - start) * 1000.0

    try:
        os.write(master_fd, b":bench-ping\n")
    except OSError:
        _terminate(proc)
        os.close(master_fd)
        return BenchResult(supported=False, error="failed to write bench ping")

    ping_start = time.monotonic()
    pong = _read_until(master_fd, PONG_SENTINEL, timeout_ping)
    ping_ms = (time.monotonic() - ping_start) * 1000.0 if pong else None

    # Attempt graceful exit
    try:
        os.write(master_fd, b":exit\n")
        _read_until(master_fd, EXIT_SENTINEL, 0.5)
    except OSError:
        pass

    _terminate(proc)
    os.close(master_fd)

    if not pong:
        return BenchResult(supported=False, startup_ms=ready_ms, error="PONG sentinel not seen")

    return BenchResult(supported=True, startup_ms=ready_ms, ping_ms=ping_ms)


def main() -> int:
    parser = argparse.ArgumentParser(description="HybridCoder TUI benchmark")
    parser.add_argument("--cmd", default="hybridcoder", help="Command to run")
    parser.add_argument("--args", default="chat", help="Arguments for the command")
    parser.add_argument("--timeout-ready", type=float, default=3.0)
    parser.add_argument("--timeout-ping", type=float, default=1.0)
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument("--strict", action="store_true", help="Nonzero exit if unsupported")
    args = parser.parse_args()

    cmd = [args.cmd] + shlex.split(args.args)

    version_ms = _run_version([args.cmd])
    bench = run_tui_bench(cmd, args.timeout_ready, args.timeout_ping)

    payload = {
        "version_ms": round(version_ms, 2),
        "tui_supported": bench.supported,
        "startup_ms": round(bench.startup_ms, 2) if bench.startup_ms is not None else None,
        "ping_ms": round(bench.ping_ms, 2) if bench.ping_ms is not None else None,
        "error": bench.error,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("TUI benchmark")
        print(f"- version_ms: {payload['version_ms']}")
        print(f"- tui_supported: {payload['tui_supported']}")
        print(f"- startup_ms: {payload['startup_ms']}")
        print(f"- ping_ms: {payload['ping_ms']}")
        if payload["error"]:
            print(f"- error: {payload['error']}")

    if args.strict and not bench.supported:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
