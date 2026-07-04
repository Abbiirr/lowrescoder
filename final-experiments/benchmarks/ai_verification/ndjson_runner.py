"""NDJSON runner for AI verification harness.

Spawns ``autocode exec "<prompt>" --json --auto-approve`` against a sandbox,
captures NDJSON stdout, and parses events via ``headless_schema.validate_event()``.

Returns a ``RunResult`` with structured event list, tool call count, and
token usage extracted from the NDJSON stream.

Uses ``AUTOCODE_UNDER_TEST`` env var or falls back to ``python -m autocode``
from the repo root to ensure the checked-out code is exercised.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from benchmarks.ai_verification.schema import ScenarioSpec

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class RunResult:
    exit_code: int
    events: list
    tool_calls: int
    tokens_in: int
    tokens_out: int
    error: str


def _autocode_cmd() -> list[str]:
    executable = os.environ.get("AUTOCODE_UNDER_TEST", "")
    if executable:
        return [executable]
    # Use uv to run from the repo venv regardless of caller cwd
    return ["uv", "--project", str(_REPO_ROOT), "run", "autocode"]


def parse_ndjson_stream(lines: list[str]) -> list:
    from autocode.backend.headless_schema import validate_event

    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
            event = validate_event(raw)
            events.append(event)
        except (json.JSONDecodeError, ValueError):
            continue
    return events


def build_run_result(raw_lines: list[str], exit_code: int, error: str = "") -> RunResult:
    events = parse_ndjson_stream(raw_lines)

    typed_call_ids = set()
    legacy_item_ids = set()
    tokens_in = 0
    tokens_out = 0

    for event in events:
        event_type = getattr(event, "type", "")
        if event_type in ("tool_call_completed", "tool_call_failed"):
            call_id = getattr(event, "tool_call_id", "")
            if call_id:
                typed_call_ids.add(call_id)
            else:
                typed_call_ids.add(f"_typed_{getattr(event, 'tool_name', '')}_{getattr(event, 'started_at', '')}")
        if hasattr(event, "kind") and getattr(event, "kind", None) == "tool_execution":
            item_id = getattr(event, "item_id", "")
            if item_id:
                legacy_item_ids.add(item_id)
        if hasattr(event, "usage"):
            usage = event.usage
            tokens_in += usage.input_tokens
            tokens_out += usage.output_tokens

    typed_item_ids_from_typed = set()
    for event in events:
        if getattr(event, "type", "") in ("tool_call_completed", "tool_call_failed"):
            iid = getattr(event, "item_id", "")
            if iid:
                typed_item_ids_from_typed.add(iid)

    legacy_only = legacy_item_ids - typed_item_ids_from_typed
    legacy_no_id = sum(
        1 for event in events
        if hasattr(event, "kind") and getattr(event, "kind", None) == "tool_execution"
        and not getattr(event, "item_id", "")
    )
    tool_calls = len(typed_call_ids) + len(legacy_only) + legacy_no_id

    return RunResult(
        exit_code=exit_code,
        events=events,
        tool_calls=tool_calls,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        error=error,
    )


def run_autocode_ndjson(
    scenario: ScenarioSpec,
    sandbox: Path,
    timeout: int | None = None,
) -> RunResult:
    prompt = scenario.task_spec.prompt
    timeout = timeout or scenario.duration_hint_minutes * 60

    env = {**os.environ, "AUTOCODE_SANDBOX": str(sandbox)}
    cmd = _autocode_cmd() + ["exec", prompt, "--json", "--auto-approve"]

    try:
        proc = subprocess.run(
            cmd,
            cwd=sandbox,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        raw_lines = proc.stdout.splitlines()
        error = proc.stderr[-500:] if proc.returncode != 0 else ""
        return build_run_result(raw_lines, exit_code=proc.returncode, error=error)
    except subprocess.TimeoutExpired:
        return RunResult(
            exit_code=1,
            events=[],
            tool_calls=0,
            tokens_in=0,
            tokens_out=0,
            error="agent timed out",
        )
    except FileNotFoundError:
        return RunResult(
            exit_code=1,
            events=[],
            tool_calls=0,
            tokens_in=0,
            tokens_out=0,
            error=f"autocode executable not found: {cmd[0]}",
        )
