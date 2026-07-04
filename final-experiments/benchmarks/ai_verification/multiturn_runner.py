"""Multi-turn single-session runner for AI verification harness.

Creates ONE HeadlessRunner per scenario (= one agent session with full context
continuity). Calls runner.run() once per turn in the same asyncio event loop.
The prompter (harness) acts as a human: after each turn it checks grading and
sends a targeted follow-up if tests still fail.

Session continuity contract:
  - One HeadlessRunner instance for the whole scenario.
  - All turns share the same agent_loop, conversation history, and memory.
  - asyncio.wait_for() enforces a per-turn timeout so stuck LLM calls don't
    leave the artifact directory with only scenario.json.

Artifact guarantee:
  - Always writes agent_transcript.jsonl with all captured NDJSON.
  - On timeout or error writes INFRA_FAIL to grading_report.json and meta.json.
"""

from __future__ import annotations

import asyncio
import io
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from benchmarks.ai_verification.schema import ScenarioSpec

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_SANDBOX_CONFIG = """\
# Injected by AI-verification harness for benchmark runs
llm:
  # Explicit model prevents config.py from replacing 'tools' with 'coding'
  model: tools
shell:
  enabled: true
  timeout: 120
  max_timeout: 300
  allowed_commands:
    - go
    - cargo
    - npm
    - npx
    - node
    - pytest
    - uv
    - python
    - python3
    - pip
    - git
    - make
    - java
    - mvn
  blocked_commands:
    - rm -rf
    - sudo
git:
  auto_commit: false
edit:
  auto_commit: false
agent:
  tool_result_max_tokens: 2000
  # Disable planning enforcement so agent can act immediately without task overhead
  planning_enforcement: false
"""


@dataclass
class MultiturnRunResult:
    exit_code: int
    events: list
    tool_calls: int
    tokens_in: int
    tokens_out: int
    error: str
    turns: int
    grading_passed: bool
    turn_outputs: list[str] = field(default_factory=list)
    turn_summaries: list[dict] = field(default_factory=list)


def _inject_sandbox_config(sandbox: Path) -> None:
    (sandbox / ".autocode.yaml").write_text(_SANDBOX_CONFIG)


def _grading_env() -> dict[str, str]:
    """Build an env for grading subprocesses that includes the project venv on PATH."""
    env = os.environ.copy()
    venv_bin = Path(sys.executable).parent
    existing_path = env.get("PATH", "")
    env["PATH"] = f"{venv_bin}:{existing_path}"
    return env


def _run_grading(scenario: ScenarioSpec, sandbox: Path) -> tuple[bool, str]:
    from benchmarks.ai_verification.grade_run import _default_command
    from benchmarks.ai_verification.schema import Check

    check = scenario.grading.checks[0] if scenario.grading.checks else Check.RUN_TESTS
    override = scenario.grading.check_commands.get(check.value, "")
    cmd = override or _default_command(check, scenario)

    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=sandbox, capture_output=True, text=True, timeout=120,
            env=_grading_env(),
        )
        output = (proc.stdout + proc.stderr).strip()
        return proc.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT after 120s"
    except Exception as exc:
        return False, str(exc)


async def _run_all_turns(
    runner: object,
    scenario: ScenarioSpec,
    sandbox: Path,
    max_turns: int,
    timeout_per_turn: float,
    buf: io.StringIO,
) -> tuple[list[str], list[str], int, bool, list[dict]]:
    """Core multi-turn loop. Returns NDJSON, logs, turns used, final pass, and turn summaries."""
    all_lines: list[str] = []
    turn_outputs: list[str] = []
    turn_summaries: list[dict] = []
    prompt = scenario.task_spec.prompt
    prev_pos = 0
    prior_turn_passed = False
    scope_changed_after_pass = False

    try:
        for turn in range(1, max_turns + 1):
            try:
                await asyncio.wait_for(runner.run(prompt), timeout=timeout_per_turn)  # type: ignore[union-attr]
            except asyncio.TimeoutError:
                turn_outputs.append(f"[turn {turn}] TIMEOUT after {timeout_per_turn:.0f}s")
                turn_summaries.append({
                    "turn": turn,
                    "event_count": 0,
                    "grading_passed": False,
                    "error": f"TIMEOUT after {timeout_per_turn:.0f}s",
                })
                break
            except Exception as exc:
                turn_outputs.append(f"[turn {turn}] ERROR: {exc}")
                turn_summaries.append({
                    "turn": turn,
                    "event_count": 0,
                    "grading_passed": False,
                    "error": str(exc),
                })
                break

            # Collect only new NDJSON from this turn
            cur_pos = buf.tell()
            buf.seek(prev_pos)
            new_content = buf.read()
            prev_pos = cur_pos

            turn_lines = [line for line in new_content.splitlines() if line.strip()]
            all_lines.extend(turn_lines)
            turn_outputs.append(f"[turn {turn}] {len(turn_lines)} events, exit=0")

            passed, grading_output = _run_grading(scenario, sandbox)
            turn_outputs.append(f"[turn {turn}] grading={'PASS' if passed else 'FAIL'}")
            turn_summaries.append({
                "turn": turn,
                "event_count": len(turn_lines),
                "grading_passed": passed,
                "grading_output_tail": grading_output[-500:],
                "scope_changed_after_pass": scope_changed_after_pass,
            })

            scripted = scenario.task_spec.followup_prompts
            scripted_idx = turn - 1  # scripted[0] is the turn-2 prompt, etc.

            if turn < max_turns:
                if scripted_idx < len(scripted):
                    # Human-scripted follow-up: always deliver, even if already passing.
                    # This ensures the full scripted session plays out regardless of early pass.
                    prompt = scripted[scripted_idx]
                    scope_changed_after_pass = passed or prior_turn_passed
                elif passed:
                    # All scripted prompts delivered and tests pass — done
                    return all_lines, turn_outputs, turn, True, turn_summaries
                else:
                    prompt = (
                        f"Tests failed:\n```\n{grading_output[-1500:]}\n```\n"
                        f"Please fix the remaining issues."
                    )
                    scope_changed_after_pass = False
            elif passed:
                return all_lines, turn_outputs, turn, True, turn_summaries
            prior_turn_passed = passed
    finally:
        try:
            await runner._teardown_agent_resources()  # type: ignore[union-attr]
        except Exception:
            pass

    return all_lines, turn_outputs, max_turns, False, turn_summaries


def run_multiturn(
    scenario: ScenarioSpec,
    sandbox: Path,
    max_turns: int = 4,
) -> MultiturnRunResult:
    import os
    from autocode.config import load_config
    from autocode.backend.headless_runner import HeadlessRunner
    from benchmarks.ai_verification.ndjson_runner import build_run_result

    _inject_sandbox_config(sandbox)

    # Force a tool-capable model alias regardless of .env file overrides.
    # The .env at repo root sets OPENROUTER_MODEL=coding which _apply_openrouter_env
    # injects into every load_config call. Override it for benchmark runs.
    _saved_model = os.environ.get("OPENROUTER_MODEL")
    os.environ["OPENROUTER_MODEL"] = os.environ.get("AUTOCODE_BENCH_MODEL", "tools")
    try:
        config = load_config(project_root=sandbox)
    finally:
        if _saved_model is None:
            os.environ.pop("OPENROUTER_MODEL", None)
        else:
            os.environ["OPENROUTER_MODEL"] = _saved_model
    timeout_per_turn = float(max(90, scenario.duration_hint_minutes * 60 // max(1, max_turns)))

    buf = io.StringIO()
    runner = HeadlessRunner(
        config=config,
        project_root=sandbox,
        output=buf,
        auto_approve=True,
    )

    try:
        all_lines, turn_outputs, turns, passed, turn_summaries = asyncio.run(
            _run_all_turns(runner, scenario, sandbox, max_turns, timeout_per_turn, buf)
        )
    except Exception as exc:
        all_lines = []
        turn_outputs = [f"RUNNER EXCEPTION: {exc}"]
        turn_summaries = [{"turn": 0, "event_count": 0, "grading_passed": False, "error": str(exc)}]
        turns = 0
        passed = False

    result = build_run_result(all_lines, exit_code=0 if passed else 1, error="" if passed else turn_outputs[-1] if turn_outputs else "unknown error")

    return MultiturnRunResult(
        exit_code=result.exit_code,
        events=result.events,
        tool_calls=result.tool_calls,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        error=result.error,
        turns=turns,
        grading_passed=passed,
        turn_outputs=turn_outputs,
        turn_summaries=turn_summaries,
    )
