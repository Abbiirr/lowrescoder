"""Rust-TUI benchmark driver for AutoCode.

This module launches ``autocode --mode altscreen`` inside a PTY, feeds a
benchmark prompt, watches the rendered Rust TUI surface for state transitions,
and returns enough evidence for the benchmark harness to keep grading,
resumability, artifact capture, and timing diagnostics in one place.
"""

from __future__ import annotations

import asyncio
import errno
import fcntl
import json
import os
import pty
import re
import select
import shlex
import signal
import socket
import struct
import subprocess
import termios
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

import pyte

from benchmarks.adapters.base import AgentResult, BenchmarkTask, BudgetProfile

COLS = 160
ROWS = 50
STARTUP_TIMEOUT_S = 20.0
QUIET_WINDOW_S = 1.0
POLL_INTERVAL_S = 0.2
GRADING_TIMEOUT_S = 120
STATE_WINDOW_CHARS = 12_000
TURN_TIMEOUT_ENV = "AUTOCODE_TUI_BENCHMARK_TURN_TIMEOUT_S"
ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
KITTY_CSI_U_RE = re.compile(rb"\x1b\[[?>=<0-9;:]*u")


class SurfaceState(str, Enum):
    UNKNOWN = "unknown"
    READY = "ready"
    STREAMING = "streaming"
    COMPLETED = "completed"
    RECOVERY = "recovery"


class TuiConnectionMode(str, Enum):
    SPAWN = "spawn"
    ATTACH = "attach"


@dataclass(frozen=True)
class TuiTurnResult:
    final_state: SurfaceState
    states: list[dict[str, str | float]]
    raw_log_path: str
    screen_log_path: str
    live_screen_log_path: str
    timing_log_path: str
    backend_stdout_log_path: str | None
    backend_stderr_log_path: str | None
    backend_attach_addr: str | None
    timings: dict[str, float | int | str | None]
    elapsed_s: float
    started_monotonic_s: float


@dataclass(frozen=True)
class TuiRunnerContext:
    project_root: Path
    provider: str
    model: str
    api_base: str
    connection_mode: TuiConnectionMode
    build_prompt: Callable[..., str]
    build_feedback_prompt: Callable[..., str]
    run_grading_command: Callable[..., tuple[int, str]]
    find_work_dir: Callable[[Path, BenchmarkTask], Path]


def _strip_ansi(raw: bytes) -> str:
    cleaned = KITTY_CSI_U_RE.sub(b"", raw)
    text = ANSI_RE.sub("", cleaned.decode("utf-8", errors="replace"))
    return text.replace("\r", "\n")


def _render_terminal_screen(screen: pyte.Screen) -> str:
    return "\n".join(line.rstrip() for line in screen.display)


def _latest_session_log_path(log_root: Path) -> Path | None:
    if not log_root.is_dir():
        return None
    candidates = [
        path for path in log_root.rglob("autocode.jsonl")
        if path.parent != log_root
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _session_log_indicates_turn_complete(log_path: Path | None) -> bool:
    if log_path is None or not log_path.is_file():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return '"event": "agent_loop_end"' in text or '"message": "agent_loop_end"' in text


def _last_marker_index(text: str, markers: tuple[str, ...]) -> int:
    lowered = text.lower()
    best = -1
    for marker in markers:
        if marker != marker.lower():
            idx = text.rfind(marker)
        else:
            idx = lowered.rfind(marker)
        if idx > best:
            best = idx
    return best


class SurfaceStateTracker:
    """Translate the visible Rust-TUI surface into benchmark-facing states."""

    _READY_MARKERS = (
        "● ready",
        "ready for the next task",
        "describe a change, ask a question",
    )
    _STREAMING_MARKERS = (
        "● working",
        "thinking and tool activity will stream here",
        "draft stays live while validation streams",
        "validation streams",
    )
    _RECOVERY_MARKERS = (
        "choose a recovery action",
        "retrying.",
        "backend not responding",
        "recovery",
    )

    def __init__(self) -> None:
        self._seen_streaming = False
        self._last = SurfaceState.UNKNOWN

    def observe(self, text: str) -> SurfaceState:
        window = text[-STATE_WINDOW_CHARS:]
        ready_idx = _last_marker_index(window, self._READY_MARKERS)
        streaming_idx = _last_marker_index(window, self._STREAMING_MARKERS)
        recovery_idx = _last_marker_index(window, self._RECOVERY_MARKERS)

        current = SurfaceState.UNKNOWN
        latest_idx = max(ready_idx, streaming_idx, recovery_idx)
        if latest_idx >= 0:
            if recovery_idx == latest_idx:
                current = SurfaceState.RECOVERY
            elif streaming_idx == latest_idx:
                current = SurfaceState.STREAMING
            elif ready_idx == latest_idx:
                current = SurfaceState.READY

        if current == SurfaceState.STREAMING:
            self._seen_streaming = True
            self._last = SurfaceState.STREAMING
            return SurfaceState.STREAMING

        if current == SurfaceState.RECOVERY:
            self._last = SurfaceState.RECOVERY
            return SurfaceState.RECOVERY

        if current == SurfaceState.READY and self._seen_streaming:
            self._seen_streaming = False
            self._last = SurfaceState.COMPLETED
            return SurfaceState.COMPLETED

        if current == SurfaceState.READY:
            self._last = SurfaceState.READY
            return SurfaceState.READY

        return self._last if self._last == SurfaceState.RECOVERY else SurfaceState.UNKNOWN


def build_tui_chat_command(
    project_root: Path,
    sandbox: Path,
    *,
    attach_addr: str | None = None,
) -> list[str]:
    command = (
        f"cd {shlex.quote(str(sandbox))} && "
        f"exec uv --project {shlex.quote(str(project_root))} "
        "run autocode --mode altscreen"
    )
    if attach_addr:
        command += f" --attach {shlex.quote(attach_addr)}"
    return ["bash", "-lc", command]


def build_tui_backend_command(
    project_root: Path,
    sandbox: Path,
    *,
    host: str,
    port: int,
) -> list[str]:
    command = (
        f"cd {shlex.quote(str(sandbox))} && "
        f"exec uv --project {shlex.quote(str(project_root))} "
        "run autocode serve --transport tcp "
        f"--host {shlex.quote(host)} --port {port}"
    )
    return ["bash", "-lc", command]


def write_tui_benchmark_config(
    *,
    home_dir: Path,
    provider: str,
    model: str,
    api_base: str,
) -> Path:
    config_dir = home_dir / ".autocode"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "llm:",
                f"  provider: {provider}",
                f"  model: {model}",
                f"  api_base: {api_base}",
                "shell:",
                "  enabled: true",
                "  timeout: 120",
                "  max_timeout: 300",
                "  allow_network: true",
                "logging:",
                "  console_level: ERROR",
                "tui:",
                "  approval_mode: autonomous",
                f"  session_db_path: {home_dir / '.autocode' / 'sessions.db'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def build_tui_runtime_env(
    *,
    base_env: dict[str, str],
    home_dir: Path,
    provider: str,
    model: str,
    api_base: str,
) -> dict[str, str]:
    """Build an isolated runtime env for benchmark-owned TUI sessions.

    The Rust frontend launches ``autocode serve``, whose config loader gives
    environment variables precedence over the sandbox-local ``config.yaml``.
    Export the benchmark's provider/model/api-base explicitly and remove
    provider-specific model/base overrides from the surrounding shell so the
    session cannot drift onto a user-default model like ``tools``.
    """
    env = dict(base_env)
    env.update(
        {
            "HOME": str(home_dir),
            "TERM": "xterm-256color",
            "COLUMNS": str(COLS),
            "LINES": str(ROWS),
            "BENCHMARK_NO_RETRY": "1",
            "AUTOCODE_FORCE_L4": "1",
            "AUTOCODE_STALE_REQUEST_TIMEOUT_SECS": "180",
            "AUTOCODE_LLM_PROVIDER": provider,
            "AUTOCODE_LLM_MODEL": model,
            "AUTOCODE_LLM_API_BASE": api_base,
        }
    )
    for key in (
        "AUTOCODE_MODEL",
        "HYBRIDCODER_LLM_PROVIDER",
        "HYBRIDCODER_LLM_MODEL",
        "HYBRIDCODER_LLM_API_BASE",
        "OPENROUTER_MODEL",
        "OLLAMA_MODEL",
        "OLLAMA_HOST",
    ):
        env.pop(key, None)
    if provider == "openrouter":
        env["OPENROUTER_MODEL"] = model
    elif provider == "ollama":
        env["OLLAMA_MODEL"] = model
        env["OLLAMA_HOST"] = api_base
    return env


def _set_winsize(fd: int, rows: int, cols: int) -> None:
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def _allocate_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _spawn_pty(argv: list[str], cwd: Path, env: dict[str, str]) -> tuple[int, int]:
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
        os.chdir(cwd)
        os.execvpe(argv[0], argv, env)
        raise SystemExit(1)
    os.close(slave_fd)
    return master_fd, pid


def _spawn_process(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> tuple[subprocess.Popen[str], object, object]:
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    return proc, stdout_handle, stderr_handle


def _kill_pty(pid: int, fd: int) -> None:
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


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    for terminate_first in (True, False):
        try:
            if terminate_first:
                proc.terminate()
            else:
                proc.kill()
            proc.wait(timeout=2)
            return
        except subprocess.TimeoutExpired:
            continue
        except OSError:
            return


def _wait_for_tcp_listener(
    host: str,
    port: int,
    *,
    timeout_s: float,
    proc: subprocess.Popen[str] | None = None,
) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            return False
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _read_available(fd: int, timeout_s: float) -> bytes:
    chunks = bytearray()
    rlist, _, _ = select.select([fd], [], [], timeout_s)
    if not rlist:
        return bytes(chunks)
    while True:
        try:
            chunk = os.read(fd, 8192)
        except OSError as exc:
            if exc.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not chunk:
            break
        chunks.extend(chunk)
        rlist, _, _ = select.select([fd], [], [], 0)
        if not rlist:
            break
    return bytes(chunks)


def _send_prompt(fd: int, prompt: str) -> None:
    payload = prompt.replace("\r\n", "\n").replace("\r", "\n")
    bracketed = b"\x1b[200~" + payload.encode("utf-8") + b"\x1b[201~"
    os.write(fd, bracketed)
    time.sleep(0.2)
    os.write(fd, b"\r")


def _append_state(
    state_trace: list[dict[str, str | float]],
    state: SurfaceState,
) -> None:
    if state_trace and state_trace[-1]["state"] == state.value:
        return
    state_trace.append(
        {
            "state": state.value,
            "timestamp": round(time.monotonic(), 3),
        }
    )


def _mark_timing_once(
    timings: dict[str, float | int | str | None],
    key: str,
    *,
    start: float,
) -> None:
    if timings.get(key) is not None:
        return
    timings[key] = round(time.monotonic() - start, 3)


def _build_tui_timing_payload(
    *,
    command: list[str],
    final_state: SurfaceState,
    elapsed_s: float,
    timings: dict[str, float | int | str | None],
    state_trace: list[dict[str, str | float]],
    raw_log_path: str,
    screen_log_path: str,
    live_screen_log_path: str,
    backend_stdout_log_path: str | None = None,
    backend_stderr_log_path: str | None = None,
    backend_attach_addr: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "command": command,
        "final_state": final_state.value,
        "elapsed_s": elapsed_s,
        "timings": timings,
        "state_trace": state_trace,
        "raw_log_path": raw_log_path,
        "screen_log_path": screen_log_path,
        "live_screen_log_path": live_screen_log_path,
    }
    if backend_stdout_log_path is not None:
        payload["backend_stdout_log_path"] = backend_stdout_log_path
    if backend_stderr_log_path is not None:
        payload["backend_stderr_log_path"] = backend_stderr_log_path
    if backend_attach_addr is not None:
        payload["backend_attach_addr"] = backend_attach_addr
    return payload


def resolve_tui_turn_timeout_s(*, remaining_s: float) -> float:
    """Resolve the per-turn timeout for benchmark-owned TUI runs.

    By default the driver inherits the lane wall-time budget, which is useful
    for full sweeps but impractical for live canaries when the provider route is
    retrying. A narrow env override lets the canary terminate into a stored
    benchmark artifact instead of hanging for many hours.
    """
    default_timeout_s = min(remaining_s, STARTUP_TIMEOUT_S + max(60.0, remaining_s))
    raw_override = os.environ.get(TURN_TIMEOUT_ENV, "").strip()
    if not raw_override:
        return default_timeout_s
    try:
        override_s = float(raw_override)
    except ValueError:
        return default_timeout_s
    if override_s <= 0:
        return default_timeout_s
    return min(remaining_s, override_s)


def _run_tui_turn(
    *,
    command: list[str],
    sandbox: Path,
    env: dict[str, str],
    prompt: str,
    artifact_dir: Path,
    timeout_s: float,
    backend_command: list[str] | None = None,
    backend_attach_addr: str | None = None,
    backend_host: str | None = None,
    backend_port: int | None = None,
) -> TuiTurnResult:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    raw_log_path = artifact_dir / "tui.raw.log"
    screen_log_path = artifact_dir / "tui.screen.log"
    live_screen_log_path = artifact_dir / "tui.screen.live.log"
    timing_log_path = artifact_dir / "tui.timing.json"
    backend_stdout_log_path = artifact_dir / "backend.stdout.log"
    backend_stderr_log_path = artifact_dir / "backend.stderr.log"

    start = time.monotonic()
    tracker = SurfaceStateTracker()
    state_trace: list[dict[str, str | float]] = []
    raw_bytes = bytearray()
    screen_text = ""
    screen = pyte.Screen(COLS, ROWS)
    screen_stream = pyte.ByteStream(screen)
    prompt_sent = False
    final_state = SurfaceState.UNKNOWN
    last_live_flush = 0.0
    session_log_path: Path | None = None
    fd: int | None = None
    pid: int | None = None
    backend_proc: subprocess.Popen[str] | None = None
    backend_stdout_handle = None
    backend_stderr_handle = None
    timings: dict[str, float | int | str | None] = {
        "pty_launch_start_s": 0.0,
        "pty_spawned_s": None,
        "ready_detected_s": None,
        "prompt_injection_start_s": None,
        "prompt_injection_end_s": None,
        "first_streaming_s": None,
        "completed_detected_s": None,
        "recovery_detected_s": None,
        "backend_spawned_s": None,
        "backend_ready_s": None,
        "backend_start_error": None,
        "prompt_chars": len(prompt),
        "raw_bytes_captured": 0,
        "screen_chars_captured": 0,
    }

    try:
        if backend_command is not None:
            if backend_host is None or backend_port is None:
                raise ValueError("backend host/port required when backend_command is provided")
            backend_proc, backend_stdout_handle, backend_stderr_handle = _spawn_process(
                backend_command,
                cwd=sandbox,
                env=env,
                stdout_path=backend_stdout_log_path,
                stderr_path=backend_stderr_log_path,
            )
            timings["backend_spawned_s"] = round(time.monotonic() - start, 3)
            if _wait_for_tcp_listener(
                backend_host,
                backend_port,
                timeout_s=min(15.0, timeout_s),
                proc=backend_proc,
            ):
                timings["backend_ready_s"] = round(time.monotonic() - start, 3)
            else:
                final_state = SurfaceState.UNKNOWN
                timings["backend_start_error"] = (
                    f"backend tcp host {backend_host}:{backend_port} did not become ready"
                )

        if timings["backend_start_error"] is None:
            fd, pid = _spawn_pty(command, sandbox, env)
            timings["pty_spawned_s"] = round(time.monotonic() - start, 3)

            while time.monotonic() - start < timeout_s:
                chunk = _read_available(fd, POLL_INTERVAL_S)
                if chunk:
                    raw_bytes.extend(chunk)
                    screen_stream.feed(KITTY_CSI_U_RE.sub(b"", chunk))
                    screen_text = _render_terminal_screen(screen)
                    now = time.monotonic()
                    if now - last_live_flush >= 0.25:
                        live_screen_log_path.write_text(screen_text, encoding="utf-8")
                        last_live_flush = now
                    current = tracker.observe(screen_text)
                    if current != SurfaceState.UNKNOWN:
                        _append_state(state_trace, current)
                    if current == SurfaceState.READY:
                        _mark_timing_once(timings, "ready_detected_s", start=start)
                    if current == SurfaceState.STREAMING:
                        _mark_timing_once(timings, "first_streaming_s", start=start)
                    if not prompt_sent and current == SurfaceState.READY:
                        _mark_timing_once(
                            timings, "prompt_injection_start_s", start=start,
                        )
                        _send_prompt(fd, prompt)
                        _mark_timing_once(
                            timings, "prompt_injection_end_s", start=start,
                        )
                        prompt_sent = True
                    elif prompt_sent and current in {
                        SurfaceState.COMPLETED,
                        SurfaceState.RECOVERY,
                    }:
                        final_state = current
                        marker = (
                            "completed_detected_s"
                            if current == SurfaceState.COMPLETED
                            else "recovery_detected_s"
                        )
                        _mark_timing_once(timings, marker, start=start)
                        break
                    elif (
                        prompt_sent
                        and current != SurfaceState.RECOVERY
                    ):
                        if session_log_path is None:
                            session_log_path = _latest_session_log_path(sandbox / "logs")
                        if _session_log_indicates_turn_complete(session_log_path):
                            final_state = SurfaceState.COMPLETED
                            _mark_timing_once(
                                timings,
                                "completed_detected_s",
                                start=start,
                            )
                            break
                elif prompt_sent and state_trace:
                    current = tracker.observe(screen_text)
                    if current in {SurfaceState.COMPLETED, SurfaceState.RECOVERY}:
                        final_state = current
                        marker = (
                            "completed_detected_s"
                            if current == SurfaceState.COMPLETED
                            else "recovery_detected_s"
                        )
                        _mark_timing_once(timings, marker, start=start)
                        break
                    if current != SurfaceState.RECOVERY:
                        if session_log_path is None:
                            session_log_path = _latest_session_log_path(sandbox / "logs")
                        if _session_log_indicates_turn_complete(session_log_path):
                            final_state = SurfaceState.COMPLETED
                            _mark_timing_once(
                                timings,
                                "completed_detected_s",
                                start=start,
                            )
                            break
            else:
                final_state = SurfaceState.UNKNOWN

            if prompt_sent and final_state == SurfaceState.UNKNOWN:
                current = tracker.observe(screen_text)
                if current in {SurfaceState.COMPLETED, SurfaceState.RECOVERY}:
                    final_state = current
                    marker = (
                        "completed_detected_s"
                        if current == SurfaceState.COMPLETED
                        else "recovery_detected_s"
                    )
                    _mark_timing_once(timings, marker, start=start)
            if not prompt_sent and final_state == SurfaceState.UNKNOWN:
                current = tracker.observe(screen_text)
                if current == SurfaceState.READY:
                    final_state = SurfaceState.READY
    finally:
        timings["raw_bytes_captured"] = len(raw_bytes)
        timings["screen_chars_captured"] = len(screen_text)
        raw_log_path.write_bytes(bytes(raw_bytes))
        screen_log_path.write_text(screen_text, encoding="utf-8")
        live_screen_log_path.write_text(screen_text, encoding="utf-8")
        elapsed_s = round(time.monotonic() - start, 1)
        timing_payload = _build_tui_timing_payload(
            command=command,
            final_state=final_state,
            elapsed_s=elapsed_s,
            timings=timings,
            state_trace=state_trace,
            raw_log_path=str(raw_log_path),
            screen_log_path=str(screen_log_path),
            live_screen_log_path=str(live_screen_log_path),
            backend_stdout_log_path=(
                str(backend_stdout_log_path) if backend_command is not None else None
            ),
            backend_stderr_log_path=(
                str(backend_stderr_log_path) if backend_command is not None else None
            ),
            backend_attach_addr=backend_attach_addr,
        )
        timing_log_path.write_text(
            json.dumps(timing_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        if pid is not None and fd is not None:
            _kill_pty(pid, fd)
        if backend_proc is not None:
            _terminate_process(backend_proc)
        if backend_stdout_handle is not None:
            backend_stdout_handle.close()
        if backend_stderr_handle is not None:
            backend_stderr_handle.close()

    return TuiTurnResult(
        final_state=final_state,
        states=state_trace,
        raw_log_path=str(raw_log_path),
        screen_log_path=str(screen_log_path),
        live_screen_log_path=str(live_screen_log_path),
        timing_log_path=str(timing_log_path),
        backend_stdout_log_path=(
            str(backend_stdout_log_path) if backend_command is not None else None
        ),
        backend_stderr_log_path=(
            str(backend_stderr_log_path) if backend_command is not None else None
        ),
        backend_attach_addr=backend_attach_addr,
        timings=timings,
        elapsed_s=elapsed_s,
        started_monotonic_s=start,
    )


class AutoCodeTuiBenchmarkRunner:
    """Drive benchmark tasks through the real Rust TUI in a PTY."""

    def __init__(self, context: TuiRunnerContext) -> None:
        self._context = context

    async def run_task(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        return await asyncio.to_thread(self._run_task_sync, task, sandbox, budget)

    def _run_task_sync(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        start = time.monotonic()
        work_dir = self._context.find_work_dir(sandbox, task)
        task_md_path = sandbox / "task.md"
        task_md = ""
        if task_md_path.is_file():
            task_md = task_md_path.read_text(encoding="utf-8", errors="replace")[:3000]

        initial_test_output = ""
        if task.grading_command:
            try:
                _init_rc, raw_output = self._context.run_grading_command(
                    sandbox,
                    task.grading_command,
                    container_name=task.extra.get("_container_name"),
                    timeout=int(GRADING_TIMEOUT_S),
                )
                initial_test_output = raw_output[-1500:] if len(raw_output) > 1500 else raw_output
            except Exception:
                initial_test_output = ""

        prompt = self._context.build_prompt(
            task,
            initial_test_output=initial_test_output,
            task_md=task_md,
            work_dir_str=str(work_dir),
        )
        grade_attempts: list[dict[str, object]] = []
        output = ""
        error = ""
        resolved = False

        for attempt in range(1, 4):
            remaining = budget.wall_time_s - (time.monotonic() - start)
            if remaining <= 0:
                error = f"Timeout after {budget.wall_time_s}s"
                break

            attempt_dir = sandbox / ".benchmark-tui" / f"attempt-{attempt}"
            home_dir = attempt_dir / "home"
            config_path = write_tui_benchmark_config(
                home_dir=home_dir,
                provider=self._context.provider,
                model=self._context.model,
                api_base=self._context.api_base,
            )
            env = build_tui_runtime_env(
                base_env=os.environ.copy(),
                home_dir=home_dir,
                provider=self._context.provider,
                model=self._context.model,
                api_base=self._context.api_base,
            )
            attach_addr = None
            backend_command = None
            backend_host = None
            backend_port = None
            if self._context.connection_mode == TuiConnectionMode.ATTACH:
                backend_host = "127.0.0.1"
                backend_port = _allocate_tcp_port()
                attach_addr = f"{backend_host}:{backend_port}"
                backend_command = build_tui_backend_command(
                    self._context.project_root,
                    sandbox,
                    host=backend_host,
                    port=backend_port,
                )
            command = build_tui_chat_command(
                self._context.project_root,
                sandbox,
                attach_addr=attach_addr,
            )
            turn = _run_tui_turn(
                command=command,
                sandbox=sandbox,
                env=env,
                prompt=prompt,
                artifact_dir=attempt_dir,
                timeout_s=resolve_tui_turn_timeout_s(remaining_s=remaining),
                backend_command=backend_command,
                backend_attach_addr=attach_addr,
                backend_host=backend_host,
                backend_port=backend_port,
            )

            grading_output = ""
            grading_path = attempt_dir / "grading_output.txt"
            attempt_timings = dict(turn.timings)
            if task.grading_command and turn.final_state == SurfaceState.COMPLETED:
                attempt_timings["grading_handoff_s"] = round(
                    time.monotonic() - turn.started_monotonic_s, 3,
                )
                returncode, grading_output = self._context.run_grading_command(
                    sandbox,
                    task.grading_command,
                    container_name=task.extra.get("_container_name"),
                    timeout=int(GRADING_TIMEOUT_S),
                )
                grading_path.write_text(grading_output, encoding="utf-8")
                resolved = returncode == 0
            else:
                returncode = None
                grading_path.write_text(grading_output, encoding="utf-8")

            grade_attempts.append(
                {
                    "attempt": attempt,
                    "resolved": resolved,
                    "returncode": returncode,
                    "tui_final_state": turn.final_state.value,
                    "tui_state_trace": turn.states,
                    "tui_raw_log_path": turn.raw_log_path,
                    "tui_screen_log_path": turn.screen_log_path,
                    "tui_live_screen_log_path": turn.live_screen_log_path,
                    "tui_timing_log_path": turn.timing_log_path,
                    "tui_backend_stdout_log_path": turn.backend_stdout_log_path,
                    "tui_backend_stderr_log_path": turn.backend_stderr_log_path,
                    "tui_backend_attach_addr": turn.backend_attach_addr,
                    "tui_timings": attempt_timings,
                    "tui_config_path": str(config_path),
                    "grading_output_path": str(grading_path),
                    "elapsed_s": turn.elapsed_s,
                }
            )

            if resolved:
                output = grading_output[-2000:] if grading_output else ""
                break

            if turn.final_state == SurfaceState.RECOVERY:
                error = "Rust TUI entered recovery state during benchmark turn."
                output = "Recovery state detected in Rust TUI."
                break

            if turn.final_state not in {SurfaceState.COMPLETED, SurfaceState.READY}:
                error = "Rust TUI did not reach a completed state before timeout."
                output = "Turn ended without a completed ready-state transition."
                break

            if not task.grading_command:
                output = "Rust TUI turn completed without harness grading command."
                break

            prompt = self._context.build_feedback_prompt(
                grading_output,
                task.grading_command,
                changed_files=[],
                test_files_changed=False,
                stagnation_count=0,
                consecutive_zero_diffs=0,
                docker_grading=bool(task.extra.get("_container_name")),
                test_patch=task.extra.get("test_patch", ""),
                grading_signature_repeated=False,
                prev_grading_signatures=[],
                protected_violation_files=[],
            )
            output = grading_output[-2000:] if grading_output else output

        elapsed = round(time.monotonic() - start, 1)
        failure_type = "RESOLVED" if resolved else "WRONG_FIX"
        if error:
            failure_type = "INFRA_FAIL"
        elif grade_attempts and any(
            attempt["tui_final_state"] == SurfaceState.RECOVERY.value
            for attempt in grade_attempts
        ):
            failure_type = "INFRA_FAIL"

        artifacts = {
            "grade_attempts": grade_attempts,
            "failure_type": failure_type,
            "runner_mode": "tui",
            "connection_mode": self._context.connection_mode.value,
            "timing_instrumentation": "permanent",
        }

        return AgentResult(
            task_id=task.task_id,
            resolved=resolved,
            wall_time_s=elapsed,
            error=error,
            output=output[:2000],
            artifacts=artifacts,
        )


def build_tui_runner_context(
    *,
    project_root: Path,
    provider: str,
    model: str,
    api_base: str,
    build_prompt: Callable[..., str],
    build_feedback_prompt: Callable[..., str],
    run_grading_command: Callable[..., tuple[int, str]],
    find_work_dir: Callable[[Path, BenchmarkTask], Path],
    connection_mode: TuiConnectionMode = TuiConnectionMode.SPAWN,
) -> TuiRunnerContext:
    return TuiRunnerContext(
        project_root=project_root,
        provider=provider,
        model=model,
        api_base=api_base,
        connection_mode=connection_mode,
        build_prompt=build_prompt,
        build_feedback_prompt=build_feedback_prompt,
        run_grading_command=run_grading_command,
        find_work_dir=find_work_dir,
    )
