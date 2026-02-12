#!/usr/bin/env python3
"""E2E Benchmark: Drive HybridCoder to create a React calculator app.

Runs AgentLoop programmatically with auto-approval, scores the output
using the 100-point rubric, and saves results to docs/qa/test-results/.

All config comes from .env — no hardcoded defaults. If .env is missing
required vars, the script exits immediately with a clear error.

Usage:
    uv run python scripts/run_calculator_benchmark.py
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hybridcoder.agent.approval import ApprovalManager, ApprovalMode  # noqa: E402
from hybridcoder.agent.loop import AgentLoop  # noqa: E402
from hybridcoder.agent.tools import create_default_registry  # noqa: E402
from hybridcoder.config import ShellConfig, load_config  # noqa: E402
from hybridcoder.layer4.llm import create_provider  # noqa: E402
from hybridcoder.session.store import SessionStore  # noqa: E402

# --- Constants ---

BENCHMARK_PROMPT = (
    "Create a React web app with a landing page and 4 calculator pages: "
    "regular calculator, scientific calculator, currency converter "
    "(using Frankfurter API), and unit converter (length, weight, temperature, "
    "volume, speed). Use Vite, React Router v6, Tailwind CSS, mathjs for "
    "scientific calculations, and big.js for decimal precision. Include proper "
    "error handling.\n\n"
    "UI REQUIREMENTS (very important — follow these closely):\n"
    "- Dark theme: use dark backgrounds (bg-gray-800, bg-gray-900, or bg-slate-800/900) "
    "with light text (text-white, text-gray-100). The entire app should feel dark and modern.\n"
    "- Calculator buttons: arrange in a clean 4-column CSS grid (grid grid-cols-4 gap-2). "
    "Number buttons should be neutral dark (bg-gray-700). Operator buttons (+, -, *, /) "
    "should use an accent color (bg-orange-500 or bg-indigo-500). The equals button should "
    "be a standout gradient or bright accent color.\n"
    "- Display area: show the current result in large text (text-4xl or text-5xl font-bold) "
    "and the expression history in smaller muted text above it (text-sm text-gray-400). "
    "The display should have a dark card background with rounded corners.\n"
    "- Navigation: include a sidebar (on desktop) or top tab bar with icons/labels "
    "to switch between calculator types. The active page should have a highlighted state "
    "(bg-indigo-600 or similar accent). Use React Router NavLink with activeClassName.\n"
    "- Cards and containers: use rounded-xl or rounded-2xl with shadow-lg for main panels.\n"
    "- Buttons: all buttons should have rounded-lg, hover: states (hover:bg-gray-600), "
    "and active: states (active:scale-95) for tactile feedback.\n"
    "- Converter pages: use styled dropdown selectors (select elements with dark bg, "
    "rounded borders, padding) for 'From' and 'To' units/currencies. Include a swap "
    "button between them. Show the conversion result prominently.\n"
    "- Typography: use font-mono for number displays, consistent text sizing hierarchy.\n"
    "- Spacing: consistent p-4/p-6 padding, gap-2/gap-3 between elements.\n"
    "- Responsive: the layout should work on mobile (stack sidebar below on small screens).\n\n"
    "IMPORTANT BUILD RULES:\n"
    "- Create all project files directly in the current working "
    "directory (.). Do NOT create a subdirectory — package.json, index.html, "
    "vite.config.js, and src/ should all be at the top level of the current "
    "directory. Use `npm init -y` to initialize, then install dependencies "
    "with `npm install`. Use `write_file` to create source files.\n"
    "- Config files (vite.config.js, postcss.config.js, tailwind.config.js) "
    "MUST use CommonJS syntax: `module.exports = { ... }`. Do NOT use "
    "`export default` — Node.js will fail with 'Unexpected token export'. "
    "This is critical for the build to succeed."
)

FOLLOW_UP_PROMPTS = [
    "Continue building the React calculator app. Focus on any pages or "
    "components that are not yet complete. Make sure all files are created "
    "and the project can be built with `npm run build`. "
    "Remember: all files go in the current directory (.), not a subdirectory.",
    "Finish any remaining work on the calculator app. Ensure package.json "
    "has all required dependencies and all page components are complete. "
    "All files must be in the current directory (.), not nested in a subfolder.",
]

MAX_ITERATIONS = 50
MAX_TOOL_TIMEOUT = 120  # Hard cap for any run_command during benchmark
NPM_TIMEOUT = 300
API_RETRY_COOLDOWN = 60  # Seconds to wait after a rate-limit error before retrying
MAX_API_RETRIES = 3  # Maximum number of retry attempts after API errors


# --- Helpers ---


def find_project_root(sandbox: Path) -> Path:
    """Find the actual React project root inside the sandbox.

    The LLM might create files directly in the sandbox (ideal) or inside a
    subdirectory like 'calculator-app/'. This function detects both cases
    by looking for package.json.
    """
    # Check sandbox root first
    if (sandbox / "package.json").exists():
        return sandbox

    # Check one level deep for a subdirectory with package.json
    for child in sandbox.iterdir():
        if child.is_dir() and (child / "package.json").exists():
            return child

    # Nothing found — return sandbox root anyway (scoring will just give 0)
    return sandbox


# --- Phase A: Prerequisites ---


def check_prerequisites() -> None:
    """Validate that .env has required config. Exit on failure."""
    errors: list[str] = []

    provider = os.environ.get("HYBRIDCODER_LLM_PROVIDER")
    if not provider:
        errors.append("HYBRIDCODER_LLM_PROVIDER is not set in .env")

    if provider == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            errors.append("OPENROUTER_API_KEY is not set in .env")
        if not os.environ.get("OPENROUTER_MODEL"):
            errors.append("OPENROUTER_MODEL is not set in .env")
    elif provider == "ollama":
        if not os.environ.get("OLLAMA_HOST"):
            errors.append("OLLAMA_HOST is not set in .env")
        if not os.environ.get("OLLAMA_MODEL"):
            errors.append("OLLAMA_MODEL is not set in .env")
    elif provider:
        errors.append(f"Unknown provider: {provider}")

    if errors:
        print("FATAL: Missing required configuration in .env:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    # Warnings (non-fatal)
    if not shutil.which("node"):
        print("WARNING: Node.js not found — npm validation will be skipped")
    if not shutil.which("npm"):
        print("WARNING: npm not found — npm validation will be skipped")


# --- Phase B: Setup ---


def clean_old_sandboxes() -> None:
    """Remove all previous bench_* directories inside sandboxes/."""
    sandboxes_dir = PROJECT_ROOT / "sandboxes"
    if not sandboxes_dir.exists():
        return
    for child in sandboxes_dir.iterdir():
        if child.is_dir() and child.name.startswith("bench_"):
            try:
                shutil.rmtree(child)
            except OSError:
                # On Windows, node_modules binaries may be locked — kill node first
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/IM", "node.exe"],
                        capture_output=True, check=False,
                    )
                    try:
                        shutil.rmtree(child)
                    except OSError as e:
                        print(f"  WARNING: Could not remove {child.name}: {e}")
                else:
                    print(f"  WARNING: Could not remove {child.name}")


def create_sandbox() -> Path:
    """Create a timestamped sandbox directory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    sandbox = PROJECT_ROOT / "sandboxes" / f"bench_{ts}"
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


class BenchmarkLogger:
    """Captures all events to a JSON Lines file."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._fh = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
        self.events: list[dict] = []
        self.tool_calls: list[dict] = []
        self.ask_user_questions: list[dict] = []
        self.text_chunks: list[str] = []
        self._start_time = time.monotonic()

    def log(self, event_type: str, **data: object) -> None:
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "elapsed_s": round(time.monotonic() - self._start_time, 2),
            "event": event_type,
            **data,
        }
        self.events.append(entry)
        self._fh.write(json.dumps(entry, default=str) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


# --- Robust run_command for Windows ---


def _benchmark_run_command(command: str, timeout: int = 30) -> str:
    """Run a shell command with hard timeout cap and process-tree kill on Windows.

    The default run_command handler can hang on Windows because killing a
    PowerShell parent doesn't terminate child processes (npm/node/vite).
    This version uses Popen + taskkill /T to clean up the whole tree.
    """
    import platform

    timeout = min(timeout, MAX_TOOL_TIMEOUT)

    try:
        if platform.system() == "Windows":
            proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                output = stdout
                if proc.returncode != 0:
                    output += f"\n[exit code {proc.returncode}]"
                    if stderr:
                        output += f"\nstderr: {stderr}"
                return output.strip() or "(no output)"
            except subprocess.TimeoutExpired:
                # Kill entire process tree on Windows
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                    check=False,
                )
                proc.kill()
                proc.wait()
                return f"Command timed out after {timeout}s"
        else:
            result = subprocess.run(
                command,
                shell=True,  # noqa: S602
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            output = result.stdout
            if result.returncode != 0:
                output += f"\n[exit code {result.returncode}]"
                if result.stderr:
                    output += f"\nstderr: {result.stderr}"
            return output.strip() or "(no output)"
    except Exception as e:
        return f"Error running command: {e}"


# --- Phase C: Agent Execution ---


async def run_agent(
    sandbox: Path,
    bench_log: BenchmarkLogger,
) -> dict:
    """Run the AgentLoop with the benchmark prompt."""
    # Load config from .env (load_config reads .env automatically)
    config = load_config(project_root=PROJECT_ROOT)

    # Override settings for benchmark mode
    config.shell.enabled = True
    config.shell.timeout = 120
    config.shell.max_timeout = 300
    config.shell.allow_network = True
    config.shell.allowed_commands = [
        "npm", "npx", "node", "git", "mkdir", "ls", "cat", "echo",
        "pytest", "python", "pip", "uv", "ruff", "mypy",
    ]
    config.tui.approval_mode = "auto"

    # Override MAX_ITERATIONS
    original_max = AgentLoop.MAX_ITERATIONS
    AgentLoop.MAX_ITERATIONS = MAX_ITERATIONS

    # Change CWD to sandbox so run_command operates inside the project
    original_cwd = os.getcwd()
    os.chdir(sandbox)

    try:
        provider = create_provider(config)
        registry = create_default_registry(project_root=str(sandbox))

        # Replace run_command with benchmark-safe handler (timeout cap + tree kill)
        run_cmd_tool = registry.get("run_command")
        if run_cmd_tool:
            run_cmd_tool.handler = _benchmark_run_command

        shell_config = ShellConfig(
            enabled=True,
            timeout=120,
            max_timeout=300,
            allow_network=True,
            allowed_commands=config.shell.allowed_commands,
            blocked_commands=["rm -rf /", "rm -rf ~", "sudo"],
        )
        approval_mgr = ApprovalManager(ApprovalMode.AUTO, shell_config)

        db_path = sandbox / ".benchmark-sessions.db"
        session_store = SessionStore(db_path)
        session_id = session_store.create_session(
            title="E2E Benchmark: React Calculator",
            model=config.llm.model,
            provider=config.llm.provider,
            project_dir=str(sandbox),
        )

        loop = AgentLoop(
            provider=provider,
            tool_registry=registry,
            approval_manager=approval_mgr,
            session_store=session_store,
            session_id=session_id,
        )

        # Callbacks
        tool_call_count = 0

        def on_chunk(text: str) -> None:
            bench_log.text_chunks.append(text)

        def on_thinking_chunk(text: str) -> None:
            bench_log.log("thinking", text=text[:200])

        def on_tool_call(name: str, status: str, result: str) -> None:
            nonlocal tool_call_count
            if status == "running":
                tool_call_count += 1
            bench_log.tool_calls.append({
                "name": name, "status": status, "result": result[:500],
            })
            bench_log.log(
                "tool_call", name=name, status=status, result_preview=result[:200],
            )
            if status in ("running", "completed"):
                print(f"  [{tool_call_count:3d}] {name}: {status}", flush=True)

        async def approval_callback(
            tool_name: str, arguments: dict,
        ) -> bool:
            bench_log.log("approval", tool_name=tool_name, approved=True)
            return True

        async def ask_user_callback(
            question: str, options: list[str], allow_text: bool,
        ) -> str:
            if options:
                answer = options[0]
            else:
                answer = "Proceed with your best judgment."
            bench_log.ask_user_questions.append({
                "question": question, "options": options, "answer": answer,
            })
            bench_log.log("ask_user", question=question[:200], answer=answer)
            print(f"  [ask_user] Q: {question[:80]} -> A: {answer}", flush=True)
            return answer

        # Helper to run a single turn with retry on API errors
        async def _run_turn(
            prompt: str, turn_num: int, tc_before: int,
        ) -> dict:
            nonlocal tool_call_count
            retries = 0
            while True:
                turn_start = time.monotonic()
                try:
                    bench_log.log(
                        "turn_start", turn=turn_num, prompt=prompt[:200],
                        retry=retries,
                    )
                    result = await loop.run(
                        prompt,
                        on_chunk=on_chunk,
                        on_thinking_chunk=on_thinking_chunk,
                        on_tool_call=on_tool_call,
                        approval_callback=approval_callback,
                        ask_user_callback=ask_user_callback,
                    )
                    turn_duration = time.monotonic() - turn_start
                    turn_data = {
                        "turn": turn_num,
                        "prompt": prompt,
                        "result_preview": result[:500],
                        "duration_s": round(turn_duration, 1),
                        "tool_calls": tool_call_count - tc_before,
                        "hit_max_iterations": "[Max iterations reached]" in result,
                        "api_retries": retries,
                        "error": None,
                    }
                    bench_log.log(
                        "turn_end", turn=turn_num,
                        duration_s=round(turn_duration, 1),
                    )
                    print(
                        f"  Turn {turn_num} complete: {round(turn_duration, 1)}s, "
                        f"{tool_call_count - tc_before} tool calls"
                        f"{f' ({retries} retries)' if retries else ''}",
                        flush=True,
                    )
                    return turn_data
                except Exception as e:
                    turn_duration = time.monotonic() - turn_start
                    error_msg = str(e)
                    bench_log.log(
                        "api_error", turn=turn_num, error=error_msg,
                        retry=retries, tool_calls_so_far=tool_call_count,
                    )

                    if retries >= MAX_API_RETRIES:
                        print(
                            f"\n  Turn {turn_num} FAILED after {retries} retries: "
                            f"{error_msg[:100]}",
                            flush=True,
                        )
                        return {
                            "turn": turn_num,
                            "prompt": prompt,
                            "result_preview": f"[API Error: {error_msg[:200]}]",
                            "duration_s": round(turn_duration, 1),
                            "tool_calls": tool_call_count - tc_before,
                            "hit_max_iterations": False,
                            "api_retries": retries,
                            "error": error_msg,
                        }

                    retries += 1
                    cooldown = API_RETRY_COOLDOWN * retries
                    print(
                        f"\n  API error on turn {turn_num}: {error_msg[:80]}"
                        f"\n  Waiting {cooldown}s before retry {retries}/{MAX_API_RETRIES}...",
                        flush=True,
                    )
                    await asyncio.sleep(cooldown)

                    # After cooldown, send a continuation prompt instead of
                    # repeating the original — the model's conversation history
                    # is preserved in the session, so it knows what it was doing.
                    prompt = (
                        "Continue where you left off. Check what files already "
                        "exist and finish building any missing pages or components. "
                        "All files go in the current directory (.)."
                    )
                    print(
                        f"\n--- Turn {turn_num} retry {retries}: "
                        f"Continuing after cooldown ---",
                        flush=True,
                    )

        # Run main prompt
        turns = []
        print("\n--- Turn 1: Initial prompt ---", flush=True)
        turn_data = await _run_turn(BENCHMARK_PROMPT, turn_num=1, tc_before=0)
        turns.append(turn_data)

        # Follow-up turns if max iterations was hit OR if the initial turn
        # errored but made some progress (tool calls > 0)
        all_prompts = FOLLOW_UP_PROMPTS + [
            "Almost done. Check which page components are still missing and "
            "create them. Make sure App.jsx imports match the actual files in "
            "src/pages/. All files in current directory (.).",
        ]
        for i, followup in enumerate(all_prompts):
            last = turns[-1]
            should_continue = (
                last["hit_max_iterations"]
                or (last.get("error") and last["tool_calls"] > 0)
            )
            if not should_continue:
                break

            turn_num = i + 2
            tc_before = tool_call_count

            print(f"\n--- Turn {turn_num}: Follow-up ---", flush=True)
            turn_data = await _run_turn(followup, turn_num=turn_num, tc_before=tc_before)
            turns.append(turn_data)

        session_store.close()

        return {
            "turns": turns,
            "total_tool_calls": tool_call_count,
            "total_ask_user": len(bench_log.ask_user_questions),
            "total_duration_s": round(sum(t["duration_s"] for t in turns), 1),
            "model": config.llm.model,
            "provider": config.llm.provider,
        }
    finally:
        os.chdir(original_cwd)
        AgentLoop.MAX_ITERATIONS = original_max


# --- Phase D: npm Validation ---


def _run_npm(args: list[str], cwd: Path, timeout: int = NPM_TIMEOUT) -> subprocess.CompletedProcess:
    """Run an npm command, handling Windows .cmd lookup."""
    # On Windows, npm is npm.cmd — shell=True is needed to resolve it
    use_shell = sys.platform == "win32"
    return subprocess.run(
        ["npm", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=use_shell,  # noqa: S603
    )


def run_npm_validation(sandbox: Path) -> dict:
    """Run npm install and npm run build in the sandbox."""
    results: dict = {"install": None, "build": None}

    if not (sandbox / "package.json").exists():
        results["install"] = {"success": False, "error": "No package.json found"}
        return results

    if not shutil.which("npm"):
        results["install"] = {"success": False, "error": "npm not found"}
        return results

    # npm install
    print("\n--- npm install ---", flush=True)
    try:
        proc = _run_npm(["install"], cwd=sandbox)
        results["install"] = {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-1000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-1000:] if proc.stderr else "",
        }
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        print(f"  npm install: {status}", flush=True)
    except subprocess.TimeoutExpired:
        results["install"] = {"success": False, "error": f"Timed out after {NPM_TIMEOUT}s"}
        print("  npm install: TIMEOUT", flush=True)
        return results
    except Exception as e:
        results["install"] = {"success": False, "error": str(e)}
        print(f"  npm install: ERROR - {e}", flush=True)
        return results

    if not results["install"]["success"]:
        return results

    # npm run build
    print("--- npm run build ---", flush=True)
    try:
        proc = _run_npm(["run", "build"], cwd=sandbox)
        results["build"] = {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-1000:] if proc.stdout else "",
            "stderr_tail": proc.stderr[-1000:] if proc.stderr else "",
        }
        status = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
        print(f"  npm run build: {status}", flush=True)
    except subprocess.TimeoutExpired:
        results["build"] = {"success": False, "error": f"Timed out after {NPM_TIMEOUT}s"}
        print("  npm run build: TIMEOUT", flush=True)
    except Exception as e:
        results["build"] = {"success": False, "error": str(e)}
        print(f"  npm run build: ERROR - {e}", flush=True)

    return results


# --- Phase E: Scoring ---


def score_project(sandbox: Path) -> dict[str, int]:
    """Score using the existing rubric."""
    import types

    # The test module uses @pytest.fixture, @pytest.mark.*, and pytest.skip at
    # module level. Provide a stub with those attributes so the import succeeds
    # outside a pytest session.
    if "pytest" not in sys.modules:
        stub = types.ModuleType("pytest")
        stub.fixture = lambda *a, **kw: (lambda f: f)  # type: ignore[attr-defined]
        stub.skip = lambda *a, **kw: None  # type: ignore[attr-defined]
        mark = types.SimpleNamespace(
            integration=lambda *a, **kw: (lambda f: f),
            benchmark=lambda *a, **kw: (lambda f: f),
        )
        stub.mark = mark  # type: ignore[attr-defined]
        sys.modules["pytest"] = stub

    sys.path.insert(0, str(PROJECT_ROOT / "tests"))
    from benchmark.test_project_creation import score_react_calculator_project

    return score_react_calculator_project(sandbox, run_build=False)


# --- Phase F: Report & Storage ---


def generate_report(
    sandbox: Path,
    agent_result: dict,
    npm_result: dict,
    scores: dict[str, int],
    bench_log: BenchmarkLogger,
) -> str:
    """Generate markdown report."""
    provider = agent_result.get("provider", "unknown")
    model = agent_result.get("model", "unknown")

    npm_install_ok = (npm_result.get("install") or {}).get("success", False)
    npm_build_ok = (npm_result.get("build") or {}).get("success", False)

    report = f"""# E2E Benchmark: React Calculator

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Provider:** {provider}
**Model:** {model}
**Sandbox:** `{sandbox.name}`

## Score: {scores.get('total', 0)} / 100

| Category | Score | Max |
|----------|-------|-----|
| Scaffold | {scores.get('scaffold', 0)} | 15 |
| Regular Calculator | {scores.get('regular', 0)} | 10 |
| Scientific Calculator | {scores.get('scientific', 0)} | 15 |
| Currency Converter | {scores.get('currency', 0)} | 15 |
| Unit Converter | {scores.get('unit', 0)} | 10 |
| Code Quality | {scores.get('quality', 0)} | 10 |
| UI Quality | {scores.get('ui', 0)} | 25 |

## npm Validation

| Step | Result |
|------|--------|
| npm install | {'PASS' if npm_install_ok else 'FAIL'} |
| npm run build | {'PASS' if npm_build_ok else 'FAIL / SKIPPED'} |

## Agent Execution

| Metric | Value |
|--------|-------|
| Total turns | {len(agent_result.get('turns', []))} |
| Total tool calls | {agent_result.get('total_tool_calls', 0)} |
| Total ask_user questions | {agent_result.get('total_ask_user', 0)} |
| Total duration | {agent_result.get('total_duration_s', 0)}s |

### Turn Details
"""
    for turn in agent_result.get("turns", []):
        report += f"""
**Turn {turn['turn']}** - {turn['duration_s']}s, {turn['tool_calls']} tool calls
- Hit max iterations: {turn['hit_max_iterations']}
- Result preview: `{turn['result_preview'][:200]}...`
"""

    report += f"""
## Event Log

- Total events: {len(bench_log.events)}
- Tool calls logged: {len(bench_log.tool_calls)}
- Ask-user questions: {len(bench_log.ask_user_questions)}
"""

    return report


def save_results(
    sandbox: Path,
    report: str,
    bench_log: BenchmarkLogger,
    scores: dict[str, int],
    agent_result: dict,
    npm_result: dict,
) -> None:
    """Save all result artifacts."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    results_dir = PROJECT_ROOT / "docs" / "qa" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Markdown report
    report_path = results_dir / f"{ts}-e2e-react-calculator.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport saved: {report_path}", flush=True)

    # Copy event log
    log_dest = results_dir / f"{ts}-e2e-react-calculator.log"
    shutil.copy2(bench_log.log_path, log_dest)
    print(f"Event log saved: {log_dest}", flush=True)

    # Machine-readable JSON in sandbox
    json_path = sandbox / ".hybridcoder-benchmark.json"
    json_data = {
        "timestamp": ts,
        "provider": agent_result.get("provider", "unknown"),
        "model": agent_result.get("model", "unknown"),
        "scores": scores,
        "agent": agent_result,
        "npm": npm_result,
        "event_count": len(bench_log.events),
    }
    json_path.write_text(
        json.dumps(json_data, indent=2, default=str), encoding="utf-8",
    )
    print(f"JSON results saved: {json_path}", flush=True)


# --- Main ---


async def main() -> int:
    """Run the full E2E benchmark."""
    print("=" * 60)
    print("HybridCoder E2E Benchmark: React Calculator")
    print("=" * 60)

    # Phase A: Prerequisites (exits if .env is incomplete)
    print("\n[Phase A] Checking prerequisites...")
    check_prerequisites()
    print("  All required config found in .env")

    # Phase B: Setup
    print("\n[Phase B] Cleaning old sandboxes...")
    clean_old_sandboxes()
    print("  Old sandboxes removed")
    print("[Phase B] Setting up sandbox...")
    sandbox = create_sandbox()
    print(f"  Sandbox: {sandbox}")

    bench_log = BenchmarkLogger(sandbox / ".benchmark-events.jsonl")
    bench_log.log("benchmark_start")

    # Phase C: Agent Execution
    print("\n[Phase C] Running agent loop...")
    try:
        agent_result = await run_agent(sandbox, bench_log)
    except Exception as e:
        print(f"\nERROR during agent execution: {e}")
        import traceback
        traceback.print_exc()
        bench_log.log("agent_error", error=str(e))
        agent_result = {
            "turns": [],
            "total_tool_calls": 0,
            "total_ask_user": 0,
            "total_duration_s": 0,
            "error": str(e),
            "provider": os.environ.get("HYBRIDCODER_LLM_PROVIDER", "unknown"),
            "model": "unknown",
        }

    # Detect actual project root (model may nest in a subdirectory)
    project_root = find_project_root(sandbox)
    if project_root != sandbox:
        print(f"\n  NOTE: Project found in subdirectory: {project_root.name}/")

    # Phase D: npm Validation
    print("\n[Phase D] Running npm validation...")
    npm_result = run_npm_validation(project_root)

    # Phase E: Scoring
    print("\n[Phase E] Scoring project...")
    scores = score_project(project_root)
    print(f"  Total score: {scores.get('total', 0)} / 100")
    for cat, val in scores.items():
        if cat != "total":
            print(f"    {cat}: {val}")

    # Phase F: Report & Storage
    print("\n[Phase F] Saving results...")
    report = generate_report(sandbox, agent_result, npm_result, scores, bench_log)
    bench_log.log("benchmark_end", scores=scores)
    bench_log.close()

    save_results(sandbox, report, bench_log, scores, agent_result, npm_result)

    # Summary
    print("\n" + "=" * 60)
    print(f"BENCHMARK COMPLETE - Score: {scores.get('total', 0)} / 100")
    print(f"Sandbox: {sandbox}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
