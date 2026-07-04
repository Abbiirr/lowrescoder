#!/usr/bin/env python3
"""Capture multiple mid-run TUI frames from a scripted PTY session.

Use this when a final-state snapshot is not enough, for example:

- planning surfaces that only appear during an active run
- restore/checkpoint overlays reached mid-flow
- benchmark-driven sessions where interesting chrome exists before completion

The script writes PNG + text frames under
``autocode/docs/qa/tui-frame-sequences/<stamp>/<name>/``.
"""

from __future__ import annotations

import argparse
import ast
import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios
import time
from datetime import UTC, datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUTOCODE_ROOT = _HERE.parents[1]
_REPO_ROOT = _AUTOCODE_ROOT.parent
_TUI_COMPARISON_DIR = _AUTOCODE_ROOT / "tests" / "tui-comparison"
_VHS_DIR = _AUTOCODE_ROOT / "tests" / "vhs"
for directory in (str(_TUI_COMPARISON_DIR), str(_VHS_DIR)):
    if directory not in sys.path:
        sys.path.insert(0, directory)
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from dsr_responder import DsrResponder  # type: ignore  # noqa: E402
from renderer import feed_ansi_to_screen, render_screen_to_png  # type: ignore  # noqa: E402
from scene_presets import get_scene_preset, scene_presets  # type: ignore  # noqa: E402


FRAME_ROOT = _AUTOCODE_ROOT / "docs" / "qa" / "tui-frame-sequences"


def resolve_tui_binary() -> Path:
    override = os.environ.get("AUTOCODE_TUI_BIN", "").strip()
    if override:
        return Path(override)
    return _AUTOCODE_ROOT / "rtui" / "target" / "release" / "autocode-tui"


def parse_steps_literal(raw: str) -> list[str | float]:
    value = ast.literal_eval(raw)
    if not isinstance(value, list):
        raise ValueError("steps must evaluate to a list")
    parsed: list[str | float] = []
    for item in value:
        if isinstance(item, str):
            parsed.append(item)
        elif isinstance(item, (int, float)):
            parsed.append(float(item))
        else:
            raise ValueError(f"unsupported step item: {item!r}")
    return parsed


def _winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _spawn(argv: list[str], *, rows: int, cols: int, env_extra: dict[str, str]) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    _winsize(master_fd, rows, cols)
    _winsize(slave_fd, rows, cols)
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
        os.execvpe(argv[0], argv, env)
        os._exit(127)
    os.close(slave_fd)
    return master_fd, pid


def _read_with_dsr(fd: int, *, quiet_s: float, maxwait_s: float, responder: DsrResponder) -> bytes:
    buf = bytearray()
    deadline = time.monotonic() + maxwait_s
    last = time.monotonic()
    saw_output = False
    while time.monotonic() < deadline:
        timeout = max(0.05, min(quiet_s, deadline - time.monotonic()))
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            if saw_output and time.monotonic() - last >= quiet_s:
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
        responder.process(chunk)
        buf += chunk
        saw_output = True
        last = time.monotonic()
    return bytes(buf)


def _save_frame(out_dir: Path, name: str, ansi: bytes, *, rows: int, cols: int) -> None:
    screen = feed_ansi_to_screen(ansi, columns=cols, lines=rows)
    png_path = out_dir / f"{name}.png"
    txt_path = out_dir / f"{name}.txt"
    render_screen_to_png(screen, png_path)
    txt_path.write_text("\n".join(screen.display) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture multiple mid-run TUI frames")
    parser.add_argument("--name", help="Logical name for the run")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--steps",
        help=r"Python literal list of steps, e.g. '[0.8, \"/sessions\\r\", 2.0]'",
    )
    group.add_argument(
        "--preset",
        help="Named preset from tests/tui-references/scene_presets.py",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List the named scene presets and exit",
    )
    parser.add_argument("--rows", type=int)
    parser.add_argument("--cols", type=int)
    parser.add_argument("--boot-budget", type=float)
    parser.add_argument("--drain-quiet", type=float)
    parser.add_argument("--drain-maxwait", type=float)
    parser.add_argument(
        "--backend",
        default=str(_AUTOCODE_ROOT / "tests" / "pty" / "mock_backend.py"),
        help="Backend command path for AUTOCODE_PYTHON_CMD",
    )
    parser.add_argument("--stamp", default="", help="Optional timestamp override")
    args = parser.parse_args(argv)

    if args.list_presets:
        for preset in scene_presets().values():
            print(
                f"{preset.scene_id:12} {preset.capture_mode:11} "
                f"{preset.label:18} {preset.note}"
            )
        return 0

    if not args.steps and not args.preset:
        parser.error("one of --steps or --preset is required unless --list-presets is used")

    preset = None
    if args.preset:
        try:
            preset = get_scene_preset(args.preset)
        except KeyError:
            parser.error(f"unknown preset: {args.preset}")
        if not preset.runnable:
            print(f"ERROR: preset `{preset.scene_id}` is blocked")
            print(preset.note)
            return 2

    if not args.name:
        if preset is not None:
            args.name = preset.scene_id
        else:
            parser.error("--name is required when using --steps")

    steps = parse_steps_literal(args.steps) if args.steps else list(preset.steps)
    rows = args.rows if args.rows is not None else (preset.rows if preset else 50)
    cols = args.cols if args.cols is not None else (preset.cols if preset else 160)
    boot_budget = (
        args.boot_budget if args.boot_budget is not None else (preset.boot_budget if preset else 4.0)
    )
    drain_quiet = (
        args.drain_quiet if args.drain_quiet is not None else (preset.drain_quiet if preset else 1.0)
    )
    drain_maxwait = (
        args.drain_maxwait
        if args.drain_maxwait is not None
        else (preset.drain_maxwait if preset else 4.0)
    )
    stamp = args.stamp or datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir = FRAME_ROOT / stamp / args.name
    out_dir.mkdir(parents=True, exist_ok=True)

    binary = resolve_tui_binary()
    if not binary.is_file():
        print(f"ERROR: TUI binary not found at {binary}")
        return 2

    env_extra = {"AUTOCODE_PYTHON_CMD": args.backend}
    if Path(args.backend).name == "mock_backend.py":
        env_extra["AUTOCODE_MOCK_SUPPRESS_STARTUP_WARNING"] = "1"
    fd, pid = _spawn([str(binary)], rows=rows, cols=cols, env_extra=env_extra)
    responder = DsrResponder(pty_fd=fd)
    captured = bytearray()
    frame_index = 0
    try:
        captured += _read_with_dsr(
            fd,
            quiet_s=1.0,
            maxwait_s=boot_budget,
            responder=responder,
        )
        _save_frame(out_dir, f"{frame_index:02d}-boot", bytes(captured), rows=rows, cols=cols)
        frame_index += 1

        for step in steps:
            if isinstance(step, float):
                time.sleep(step)
                captured += _read_with_dsr(
                    fd,
                    quiet_s=0.4,
                    maxwait_s=step + 1.0,
                    responder=responder,
                )
                _save_frame(
                    out_dir,
                    f"{frame_index:02d}-sleep",
                    bytes(captured),
                    rows=rows,
                    cols=cols,
                )
                frame_index += 1
            else:
                os.write(fd, step.encode("utf-8"))
                time.sleep(0.2)
                captured += _read_with_dsr(
                    fd,
                    quiet_s=0.4,
                    maxwait_s=2.0,
                    responder=responder,
                )
                _save_frame(
                    out_dir,
                    f"{frame_index:02d}-input",
                    bytes(captured),
                    rows=rows,
                    cols=cols,
                )
                frame_index += 1

        captured += _read_with_dsr(
            fd,
            quiet_s=drain_quiet,
            maxwait_s=drain_maxwait,
            responder=responder,
        )
        _save_frame(out_dir, f"{frame_index:02d}-final", bytes(captured), rows=rows, cols=cols)
    finally:
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.2)
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
