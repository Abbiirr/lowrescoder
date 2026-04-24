from __future__ import annotations

from pathlib import Path

from benchmarks.tui_benchmark_driver import (
    SurfaceState,
    SurfaceStateTracker,
    TURN_TIMEOUT_ENV,
    TuiConnectionMode,
    _build_tui_timing_payload,
    build_tui_backend_command,
    build_tui_chat_command,
    build_tui_runtime_env,
    build_tui_runner_context,
    resolve_tui_turn_timeout_s,
    write_tui_benchmark_config,
)


def test_surface_tracker_detects_ready_streaming_completed_cycle() -> None:
    tracker = SurfaceStateTracker()

    ready = tracker.observe(
        "tools openrouter suggest\n● ready\nDescribe a change, ask a question",
    )
    streaming = tracker.observe(
        "tools openrouter suggest\n● working\nThinking and tool activity will stream here.",
    )
    completed = tracker.observe(
        "tools openrouter suggest\n● ready\nReady for the next task.",
    )

    assert ready == SurfaceState.READY
    assert streaming == SurfaceState.STREAMING
    assert completed == SurfaceState.COMPLETED


def test_surface_tracker_detects_recovery_surface() -> None:
    tracker = SurfaceStateTracker()

    recovery = tracker.observe(
        "Backend not responding\nChoose a recovery action or edit the draft before retrying.\nRetry",
    )

    assert recovery == SurfaceState.RECOVERY


def test_build_tui_chat_command_uses_uv_project_and_altscreen() -> None:
    command = build_tui_chat_command(
        project_root=Path("/repo/root"),
        sandbox=Path("/tmp/task-sandbox"),
    )

    assert command[:2] == ["bash", "-lc"]
    assert "cd /tmp/task-sandbox" in command[2]
    assert "uv --project /repo/root run autocode --mode altscreen" in command[2]
    assert "exec" in command[2]


def test_build_tui_chat_command_can_attach_to_tcp_backend() -> None:
    command = build_tui_chat_command(
        project_root=Path("/repo/root"),
        sandbox=Path("/tmp/task-sandbox"),
        attach_addr="127.0.0.1:8765",
    )

    assert "--attach 127.0.0.1:8765" in command[2]


def test_build_tui_backend_command_launches_tcp_host() -> None:
    command = build_tui_backend_command(
        project_root=Path("/repo/root"),
        sandbox=Path("/tmp/task-sandbox"),
        host="127.0.0.1",
        port=8765,
    )

    assert command[:2] == ["bash", "-lc"]
    assert "cd /tmp/task-sandbox" in command[2]
    assert (
        "uv --project /repo/root run autocode serve --transport tcp "
        "--host 127.0.0.1 --port 8765"
    ) in command[2]


def test_build_tui_timing_payload_includes_timings_and_paths() -> None:
    payload = _build_tui_timing_payload(
        command=["bash", "-lc", "uv run autocode --mode altscreen"],
        final_state=SurfaceState.COMPLETED,
        elapsed_s=12.4,
        timings={
            "pty_launch_start_s": 0.0,
            "ready_detected_s": 1.2,
            "first_streaming_s": 3.4,
            "completed_detected_s": 12.1,
            "prompt_chars": 321,
        },
        state_trace=[
            {"state": "ready", "timestamp": 1.2},
            {"state": "streaming", "timestamp": 3.4},
            {"state": "completed", "timestamp": 12.1},
        ],
        raw_log_path="/tmp/tui.raw.log",
        screen_log_path="/tmp/tui.screen.log",
        live_screen_log_path="/tmp/tui.screen.live.log",
        backend_stdout_log_path="/tmp/backend.stdout.log",
        backend_stderr_log_path="/tmp/backend.stderr.log",
        backend_attach_addr="127.0.0.1:8765",
    )

    assert payload["final_state"] == "completed"
    assert payload["elapsed_s"] == 12.4
    assert payload["timings"]["ready_detected_s"] == 1.2
    assert payload["timings"]["prompt_chars"] == 321
    assert payload["raw_log_path"] == "/tmp/tui.raw.log"
    assert payload["screen_log_path"] == "/tmp/tui.screen.log"
    assert payload["live_screen_log_path"] == "/tmp/tui.screen.live.log"
    assert payload["backend_stdout_log_path"] == "/tmp/backend.stdout.log"
    assert payload["backend_stderr_log_path"] == "/tmp/backend.stderr.log"
    assert payload["backend_attach_addr"] == "127.0.0.1:8765"


def test_write_tui_benchmark_config_enables_autonomous_shell(tmp_path: Path) -> None:
    config_path = write_tui_benchmark_config(
        home_dir=tmp_path,
        provider="openrouter",
        model="tools",
        api_base="http://localhost:4000/v1",
    )

    config_text = config_path.read_text(encoding="utf-8")

    assert config_path == tmp_path / ".autocode" / "config.yaml"
    assert "approval_mode: autonomous" in config_text
    assert "enabled: true" in config_text
    assert "provider: openrouter" in config_text
    assert "model: tools" in config_text
    assert "api_base: http://localhost:4000/v1" in config_text
    assert "console_level: ERROR" in config_text


def test_build_tui_runtime_env_overrides_ambient_model_selection(tmp_path: Path) -> None:
    env = build_tui_runtime_env(
        base_env={
            "AUTOCODE_LLM_PROVIDER": "openrouter",
            "AUTOCODE_LLM_MODEL": "tools",
            "AUTOCODE_LLM_API_BASE": "http://localhost:4000/v1",
            "OPENROUTER_MODEL": "tools",
            "OLLAMA_HOST": "http://localhost:11435",
            "OLLAMA_MODEL": "qwen3:8b",
        },
        home_dir=tmp_path,
        provider="openrouter",
        model="swebench",
        api_base="http://localhost:4000/v1",
    )

    assert env["HOME"] == str(tmp_path)
    assert env["AUTOCODE_FORCE_L4"] == "1"
    assert env["AUTOCODE_LLM_PROVIDER"] == "openrouter"
    assert env["AUTOCODE_LLM_MODEL"] == "swebench"
    assert env["AUTOCODE_LLM_API_BASE"] == "http://localhost:4000/v1"
    assert env["OPENROUTER_MODEL"] == "swebench"
    assert "OLLAMA_HOST" not in env
    assert "OLLAMA_MODEL" not in env


def test_build_tui_runner_context_defaults_to_spawn_mode() -> None:
    context = build_tui_runner_context(
        project_root=Path("/repo/root"),
        provider="openrouter",
        model="swebench",
        api_base="http://localhost:4000/v1",
        build_prompt=lambda *args, **kwargs: "prompt",
        build_feedback_prompt=lambda *args, **kwargs: "feedback",
        run_grading_command=lambda *args, **kwargs: (0, ""),
        find_work_dir=lambda sandbox, task: sandbox,
    )

    assert context.connection_mode == TuiConnectionMode.SPAWN


def test_resolve_tui_turn_timeout_defaults_to_lane_budget() -> None:
    timeout_s = resolve_tui_turn_timeout_s(remaining_s=600.0)

    assert timeout_s == 600.0


def test_resolve_tui_turn_timeout_honors_positive_override(
    monkeypatch,
) -> None:
    monkeypatch.setenv(TURN_TIMEOUT_ENV, "180")

    timeout_s = resolve_tui_turn_timeout_s(remaining_s=600.0)

    assert timeout_s == 180.0


def test_resolve_tui_turn_timeout_ignores_invalid_override(
    monkeypatch,
) -> None:
    monkeypatch.setenv(TURN_TIMEOUT_ENV, "not-a-number")

    timeout_s = resolve_tui_turn_timeout_s(remaining_s=600.0)

    assert timeout_s == 600.0
