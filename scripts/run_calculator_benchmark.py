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

import argparse
import asyncio
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from autocode.agent.approval import ApprovalManager, ApprovalMode  # noqa: E402
from autocode.agent.loop import AgentLoop  # noqa: E402
from autocode.agent.tools import create_default_registry  # noqa: E402
from autocode.config import ShellConfig, load_config  # noqa: E402
from autocode.layer4.llm import create_provider  # noqa: E402
from autocode.session.store import SessionStore  # noqa: E402

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

BENCHMARK_VERSION = "1.1.0"
RUBRIC_VERSION = "2.0.0"
PROMPT_VERSION = "3.0.0"

DEFAULT_KEEP_LAST = 3


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

    provider = os.environ.get("AUTOCODE_LLM_PROVIDER") or os.environ.get("HYBRIDCODER_LLM_PROVIDER")
    if not provider:
        errors.append("AUTOCODE_LLM_PROVIDER is not set in .env")

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


def clean_old_sandboxes(keep_last: int = DEFAULT_KEEP_LAST) -> None:
    """Remove old bench_* directories, keeping the most recent `keep_last`."""
    sandboxes_dir = PROJECT_ROOT / "sandboxes"
    if not sandboxes_dir.exists():
        return
    bench_dirs = sorted(
        [c for c in sandboxes_dir.iterdir() if c.is_dir() and c.name.startswith("bench_")],
        key=lambda p: p.name,
        reverse=True,
    )
    to_remove = bench_dirs[keep_last:]
    for child in to_remove:
        try:
            SandboxProcessTracker(child).kill_all()
        except Exception:
            pass
        try:
            shutil.rmtree(child)
        except OSError:
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


class SandboxProcessTracker:
    """Track and kill processes spawned inside a benchmark sandbox."""

    def __init__(self, sandbox: Path) -> None:
        self._pid_file = sandbox / ".sandbox-pids.json"
        self._pids: list[int] = []

    def register(self, pid: int) -> None:
        self._pids.append(pid)
        self._save()

    def _save(self) -> None:
        self._pid_file.write_text(
            json.dumps({"pids": self._pids}), encoding="utf-8",
        )

    def kill_all(self) -> None:
        """Kill all tracked processes."""
        if self._pid_file.exists():
            try:
                data = json.loads(self._pid_file.read_text(encoding="utf-8"))
                pids = data.get("pids", [])
            except (json.JSONDecodeError, OSError):
                pids = []
        else:
            pids = self._pids

        for pid in pids:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True, check=False,
                    )
                else:
                    os.kill(pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass


_active_tracker: SandboxProcessTracker | None = None


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
            if _active_tracker:
                _active_tracker.register(proc.pid)
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


def validate_imports_vs_deps(project_root: Path) -> dict:
    """Scan JS/TS files for import/require and compare to package.json deps."""
    NODE_BUILTINS = {
        "path", "fs", "os", "url", "http", "https", "crypto", "util", "stream",
        "events", "buffer", "child_process", "assert", "querystring", "net",
        "tls", "zlib", "dns", "domain", "cluster", "readline", "repl", "vm",
        "string_decoder", "timers", "tty", "dgram", "v8", "perf_hooks",
        "worker_threads", "inspector", "async_hooks", "wasi", "trace_events",
        "node:path", "node:fs", "node:os", "node:url", "node:http",
        "node:https", "node:crypto", "node:util", "node:stream",
    }
    IMPLICIT_PACKAGES = {"react/jsx-runtime", "react-dom/client"}

    pkg_path = project_root / "package.json"
    if not pkg_path.exists():
        return {"valid": False, "declared": [], "imported": [], "missing": [], "unused": []}

    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"valid": False, "declared": [], "imported": [], "missing": [], "unused": []}

    declared = set()
    for dep_group in ("dependencies", "devDependencies", "peerDependencies"):
        declared.update(pkg.get(dep_group, {}).keys())

    src_dir = project_root / "src"
    if not src_dir.exists():
        return {
            "valid": True, "declared": sorted(declared),
            "imported": [], "missing": [], "unused": sorted(declared),
        }

    import_re = re.compile(
        r"""(?:import\s+.*?\s+from\s+['"]([^'"./][^'"]*?)['"]"""
        r"""|require\s*\(\s*['"]([^'"./][^'"]*?)['"]\s*\))""",
    )

    imported = set()
    for path in src_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in import_re.finditer(content):
            raw = m.group(1) or m.group(2)
            # Extract package name: @scope/pkg or just pkg
            if raw.startswith("@"):
                parts = raw.split("/")
                pkg_name = "/".join(parts[:2]) if len(parts) >= 2 else raw
            else:
                pkg_name = raw.split("/")[0]
            imported.add(pkg_name)

    # Filter out builtins and implicit packages
    imported = {
        p for p in imported
        if p not in NODE_BUILTINS and p not in IMPLICIT_PACKAGES
        and not p.startswith("node:")
    }

    missing = sorted(imported - declared)
    unused = sorted(declared - imported)

    return {
        "valid": len(missing) == 0,
        "declared": sorted(declared),
        "imported": sorted(imported),
        "missing": missing,
        "unused": unused,
    }


def run_security_checks(project_root: Path) -> dict:
    """Run security hygiene checks on the generated project."""
    result: dict = {
        "npm_audit": None,
        "secrets_detected": [],
        "typosquat_warnings": [],
    }

    # npm audit
    if (project_root / "node_modules").exists() and shutil.which("npm"):
        try:
            proc = _run_npm(["audit", "--json"], cwd=project_root, timeout=60)
            try:
                audit_data = json.loads(proc.stdout)
                result["npm_audit"] = {
                    "critical": audit_data.get("metadata", {}).get("vulnerabilities", {}).get("critical", 0),
                    "high": audit_data.get("metadata", {}).get("vulnerabilities", {}).get("high", 0),
                    "moderate": audit_data.get("metadata", {}).get("vulnerabilities", {}).get("moderate", 0),
                    "low": audit_data.get("metadata", {}).get("vulnerabilities", {}).get("low", 0),
                }
            except json.JSONDecodeError:
                result["npm_audit"] = {"error": "Could not parse npm audit output"}
        except (subprocess.TimeoutExpired, OSError):
            result["npm_audit"] = {"error": "npm audit failed or timed out"}

    # Secret detection
    secret_patterns = [
        (r'(?:api[_-]?key|secret|token|password)\s*[=:]\s*["\'][A-Za-z0-9+/=_-]{16,}["\']', "hardcoded_secret"),
        (r'sk-[A-Za-z0-9]{20,}', "openai_key"),
        (r'ghp_[A-Za-z0-9]{36}', "github_token"),
        (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "private_key"),
    ]
    seen_secrets: set[tuple[str, str]] = set()
    secrets: list[dict] = []

    # Scan all project files
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"node_modules", "dist", ".git", ".venv"} for part in path.parts):
            continue
        if path.stat().st_size > 1_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(project_root))
        for pattern, secret_type in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                key = (rel, secret_type)
                if key not in seen_secrets:
                    seen_secrets.add(key)
                    secrets.append({"file": rel, "type": secret_type})

    # Also check explicit root-level .env files
    for env_name in (".env", ".env.local", ".env.production"):
        env_path = project_root / env_name
        if env_path.exists():
            try:
                content = env_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern, secret_type in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    key = (env_name, secret_type)
                    if key not in seen_secrets:
                        seen_secrets.add(key)
                        secrets.append({"file": env_name, "type": secret_type})

    result["secrets_detected"] = secrets

    # Typosquat detection
    POPULAR_PACKAGES = {
        "react", "express", "lodash", "axios", "moment", "webpack",
        "typescript", "eslint", "prettier", "jest", "mocha", "chalk",
        "commander", "inquirer", "dotenv", "cors", "body-parser",
        "mongoose", "sequelize", "prisma", "next", "vue", "angular",
    }
    pkg_path = project_root / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            all_deps = set()
            for dep_group in ("dependencies", "devDependencies"):
                all_deps.update(pkg.get(dep_group, {}).keys())
            for dep in all_deps:
                for popular in POPULAR_PACKAGES:
                    if dep != popular and _levenshtein_distance(dep, popular) == 1:
                        result["typosquat_warnings"].append({
                            "package": dep, "similar_to": popular,
                        })
        except (json.JSONDecodeError, OSError):
            pass

    return result


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


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


def get_anti_patterns(project_root: Path) -> dict:
    """Get anti-pattern analysis for the project."""
    import types

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
    from benchmark.test_project_creation import _detect_anti_patterns, _project_text

    raw_text = _project_text(project_root)
    return _detect_anti_patterns(raw_text)


class BenchmarkVerdict:
    """Verdict constants for benchmark results."""

    PASS = "PASS"
    FAIL = "FAIL"
    INFRA_FAIL = "INFRA_FAIL"


def classify_result(
    scores: dict,
    npm_result: dict,
    agent_result: dict,
    min_score: int = 30,
) -> tuple[str, list[str]]:
    """Classify benchmark result as PASS, FAIL, or INFRA_FAIL."""
    reasons: list[str] = []

    # Check for API/infra errors in turns
    turns = agent_result.get("turns", [])
    api_errors = [t for t in turns if t.get("error")]
    if api_errors:
        reasons.append(f"API errors in {len(api_errors)} turn(s)")
        return BenchmarkVerdict.INFRA_FAIL, reasons

    total = scores.get("total", 0)
    if total < min_score:
        reasons.append(f"Score {total} < minimum {min_score}")

    build_result = npm_result.get("build") or {}
    if not build_result.get("success", False):
        reasons.append("npm build failed")

    if reasons:
        return BenchmarkVerdict.FAIL, reasons

    return BenchmarkVerdict.PASS, []


def analyze_trace(log_path: Path) -> dict:
    """Analyze a benchmark event log for quality metrics."""
    events = []
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return {"total_events": 0, "tool_calls": {"total": 0, "failures": 0}}

    tool_calls = [e for e in events if e.get("event") == "tool_call"]
    failures = [e for e in tool_calls if e.get("status") == "error"]

    # Count tool calls by name
    by_name: dict[str, int] = {}
    for tc in tool_calls:
        name = tc.get("name", "unknown")
        by_name[name] = by_name.get(name, 0) + 1

    # Find repeated failures (same tool, 3+)
    failure_names: dict[str, int] = {}
    for f in failures:
        name = f.get("name", "unknown")
        failure_names[name] = failure_names.get(name, 0) + 1
    repeated_failures = {k: v for k, v in failure_names.items() if v >= 3}

    # Duration
    durations = [e.get("elapsed_s", 0) for e in events if "elapsed_s" in e]
    total_duration = max(durations) if durations else 0

    # API errors
    api_errors = [e for e in events if e.get("event") == "api_error"]

    # Warnings
    warnings = []
    failure_rate = len(failures) / max(len(tool_calls), 1)
    if failure_rate > 0.30:
        warnings.append(f"High failure rate: {failure_rate:.0%}")
    if total_duration > 1800:
        warnings.append(f"Excessive duration: {total_duration:.0f}s")
    if len(tool_calls) < 5:
        warnings.append(f"Few tool calls: {len(tool_calls)}")

    return {
        "total_events": len(events),
        "duration_s": round(total_duration, 1),
        "tool_calls": {
            "total": len(tool_calls),
            "failures": len(failures),
            "by_name": by_name,
            "repeated_failures": repeated_failures,
        },
        "api_errors": len(api_errors),
        "warnings": warnings,
    }


# Budget constants
BUDGET_MAX_WALL_TIME_S = 1800
BUDGET_MAX_TOOL_CALLS = 100
BUDGET_MAX_TURNS = 5


def check_budgets(agent_result: dict, bench_log: object) -> dict:
    """Check if the benchmark stayed within budget limits."""
    wall_time = agent_result.get("total_duration_s", 0)
    tool_calls = agent_result.get("total_tool_calls", 0)
    turns = len(agent_result.get("turns", []))

    return {
        "wall_time": {
            "value": wall_time,
            "limit": BUDGET_MAX_WALL_TIME_S,
            "passed": wall_time <= BUDGET_MAX_WALL_TIME_S,
        },
        "tool_calls": {
            "value": tool_calls,
            "limit": BUDGET_MAX_TOOL_CALLS,
            "passed": tool_calls <= BUDGET_MAX_TOOL_CALLS,
        },
        "turns": {
            "value": turns,
            "limit": BUDGET_MAX_TURNS,
            "passed": turns <= BUDGET_MAX_TURNS,
        },
    }


# Strict mode constants
STRICT_MIN_SCORE = 60
STRICT_REQUIRE_BUILD = True


def classify_result_strict(
    scores: dict,
    npm_result: dict,
    agent_result: dict,
    anti_patterns: dict | None = None,
    budgets: dict | None = None,
) -> tuple[str, list[str]]:
    """Strict mode classification with higher thresholds."""
    reasons: list[str] = []

    # Check for API/infra errors first
    turns = agent_result.get("turns", [])
    api_errors = [t for t in turns if t.get("error")]
    if api_errors:
        reasons.append(f"API errors in {len(api_errors)} turn(s)")
        return BenchmarkVerdict.INFRA_FAIL, reasons

    total = scores.get("total", 0)
    if total < STRICT_MIN_SCORE:
        reasons.append(f"Score {total} < strict minimum {STRICT_MIN_SCORE}")

    build_result = npm_result.get("build") or {}
    if STRICT_REQUIRE_BUILD and not build_result.get("success", False):
        reasons.append("npm build failed (required in strict mode)")

    # Critical anti-patterns block in strict mode
    if anti_patterns and anti_patterns.get("critical"):
        for name, findings in anti_patterns["critical"].items():
            if findings:
                reasons.append(f"Critical anti-pattern: {name}")

    # Budget enforcement in strict mode
    if budgets:
        for budget_name, budget_data in budgets.items():
            if not budget_data.get("passed", True):
                reasons.append(
                    f"Budget exceeded: {budget_name} "
                    f"({budget_data['value']} > {budget_data['limit']})",
                )

    if reasons:
        return BenchmarkVerdict.FAIL, reasons

    return BenchmarkVerdict.PASS, []


# --- Phase F: Report & Storage ---


def generate_report(
    sandbox: Path,
    agent_result: dict,
    npm_result: dict,
    scores: dict[str, int],
    bench_log: BenchmarkLogger,
    verdict: str = "",
    verdict_reasons: list[str] | None = None,
    anti_patterns: dict | None = None,
    import_validation: dict | None = None,
    trace_analysis: dict | None = None,
    budgets: dict | None = None,
    security: dict | None = None,
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
**Benchmark Version:** {BENCHMARK_VERSION}
**Rubric Version:** {RUBRIC_VERSION}
**Prompt Version:** {PROMPT_VERSION}

## Verdict: {verdict or 'N/A'}

"""
    if verdict_reasons:
        report += "**Reasons:**\n"
        for r in verdict_reasons:
            report += f"- {r}\n"
        report += "\n"

    report += f"""## Score: {scores.get('total', 0)} / 100

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

"""

    # Anti-patterns section
    if anti_patterns:
        report += "## Anti-Pattern Detection\n\n"
        report += f"**Penalty:** {anti_patterns.get('penalty', 0)} points\n\n"
        if anti_patterns.get("critical"):
            report += "**Critical:**\n"
            for name, findings in anti_patterns["critical"].items():
                if findings:
                    report += f"- {name}: {findings} occurrence(s)\n"
        if anti_patterns.get("minor"):
            report += "**Minor:**\n"
            for name, findings in anti_patterns["minor"].items():
                if findings:
                    report += f"- {name}: {findings}\n"
        report += "\n"

    # Import validation section
    if import_validation:
        report += "## Import Validation\n\n"
        report += f"**Valid:** {import_validation.get('valid', False)}\n"
        if import_validation.get("missing"):
            report += f"**Missing deps:** {', '.join(import_validation['missing'])}\n"
        if import_validation.get("unused"):
            report += f"**Unused deps:** {', '.join(import_validation['unused'])}\n"
        report += "\n"

    # Budgets section
    if budgets:
        report += "## Budget Gates\n\n"
        report += "| Budget | Value | Limit | Status |\n"
        report += "|--------|-------|-------|--------|\n"
        for name, data in budgets.items():
            status = "PASS" if data["passed"] else "FAIL"
            report += f"| {name} | {data['value']} | {data['limit']} | {status} |\n"
        report += "\n"

    # Trace analysis section
    if trace_analysis:
        report += "## Trace Analysis\n\n"
        report += f"- Total events: {trace_analysis.get('total_events', 0)}\n"
        report += f"- Duration: {trace_analysis.get('duration_s', 0)}s\n"
        tc = trace_analysis.get("tool_calls", {})
        report += f"- Tool calls: {tc.get('total', 0)} (failures: {tc.get('failures', 0)})\n"
        report += f"- API errors: {trace_analysis.get('api_errors', 0)}\n"
        if trace_analysis.get("warnings"):
            report += "**Warnings:**\n"
            for w in trace_analysis["warnings"]:
                report += f"- {w}\n"
        report += "\n"

    # Security section
    if security:
        report += "## Security Hygiene\n\n"
        audit = security.get("npm_audit")
        if audit and "error" not in audit:
            report += f"**npm audit:** critical={audit.get('critical', 0)}, "
            report += f"high={audit.get('high', 0)}, "
            report += f"moderate={audit.get('moderate', 0)}, "
            report += f"low={audit.get('low', 0)}\n"
        secrets = security.get("secrets_detected", [])
        if secrets:
            report += f"**Secrets detected:** {len(secrets)}\n"
            for s in secrets:
                report += f"- {s['file']}: {s['type']}\n"
        typos = security.get("typosquat_warnings", [])
        if typos:
            report += f"**Typosquat warnings:** {len(typos)}\n"
            for t in typos:
                report += f"- {t['package']} (similar to {t['similar_to']})\n"
        report += "\n"

    report += f"""## Agent Execution

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
    ts: str | None = None,
    verdict: str = "",
    verdict_reasons: list[str] | None = None,
    anti_patterns: dict | None = None,
    import_validation: dict | None = None,
    trace_analysis: dict | None = None,
    budgets: dict | None = None,
    security: dict | None = None,
) -> tuple[str, Path]:
    """Save all result artifacts. Returns (ts, results_dir)."""
    if ts is None:
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
        "benchmark_version": BENCHMARK_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "prompt_version": PROMPT_VERSION,
        "timestamp": ts,
        "verdict": verdict,
        "verdict_reasons": verdict_reasons or [],
        "provider": agent_result.get("provider", "unknown"),
        "model": agent_result.get("model", "unknown"),
        "scores": scores,
        "agent": agent_result,
        "npm": npm_result,
        "event_count": len(bench_log.events),
        "anti_patterns": anti_patterns,
        "import_validation": import_validation,
        "trace_analysis": trace_analysis,
        "budgets": budgets,
        "security": security,
    }
    json_path.write_text(
        json.dumps(json_data, indent=2, default=str), encoding="utf-8",
    )
    print(f"JSON results saved: {json_path}", flush=True)

    return ts, results_dir


def verify_artifacts(
    sandbox: Path,
    results_dir: Path,
    ts: str,
    strict: bool = False,
) -> list[str]:
    """Verify that all expected benchmark artifacts exist."""
    expected = [
        (sandbox / ".hybridcoder-benchmark.json", "Benchmark JSON"),
        (sandbox / ".benchmark-events.jsonl", "Event log (sandbox)"),
        (results_dir / f"{ts}-e2e-react-calculator.md", "Markdown report"),
        (results_dir / f"{ts}-e2e-react-calculator.log", "Event log (results)"),
    ]

    errors = []
    for path, label in expected:
        if not path.exists():
            msg = f"Missing artifact: {label} ({path.name})"
            errors.append(msg)
            if strict:
                print(f"  ERROR: {msg}", flush=True)
            else:
                print(f"  WARNING: {msg}", flush=True)

    if not errors:
        print("  All artifacts present", flush=True)

    return errors


# --- Replay Mode ---


def replay_benchmark(sandbox: Path, score_only: bool = False) -> int:
    """Re-score an existing benchmark sandbox without running the agent."""
    json_path = sandbox / ".hybridcoder-benchmark.json"
    if not json_path.exists():
        print(f"ERROR: No benchmark JSON found at {json_path}", flush=True)
        return 1

    data = json.loads(json_path.read_text(encoding="utf-8"))
    original_ts = data.get("timestamp", "unknown")

    print("=" * 60)
    print(f"REPLAY MODE — Re-scoring sandbox: {sandbox.name}")
    print(f"Original timestamp: {original_ts}")
    print("=" * 60)

    project_root = find_project_root(sandbox)

    # npm validation (skip if score_only)
    if score_only:
        npm_result = data.get("npm", {"install": None, "build": None})
        print("\n[Replay] Skipping npm validation (--score-only)", flush=True)
    else:
        print("\n[Replay] Running npm validation...", flush=True)
        npm_result = run_npm_validation(project_root)

    # Re-score
    print("\n[Replay] Scoring project with current rubric...", flush=True)
    scores = score_project(project_root)
    print(f"  Total score: {scores.get('total', 0)} / 100")

    # Anti-patterns
    anti_patterns = get_anti_patterns(project_root)

    # Import validation
    import_val = validate_imports_vs_deps(project_root)

    # Trace analysis
    log_path = sandbox / ".benchmark-events.jsonl"
    trace = analyze_trace(log_path) if log_path.exists() else None

    # Classify
    agent_result = data.get("agent", {"turns": []})
    verdict, reasons = classify_result(scores, npm_result, agent_result)

    # Generate replay report
    bench_log = BenchmarkLogger(sandbox / ".replay-events.jsonl")
    bench_log.log("replay_start", original_ts=original_ts)

    report = generate_report(
        sandbox, agent_result, npm_result, scores, bench_log,
        verdict=verdict, verdict_reasons=reasons,
        anti_patterns=anti_patterns, import_validation=import_val,
        trace_analysis=trace,
    )

    # Add replay header
    replay_ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    report = f"<!-- REPLAY of {original_ts} at {replay_ts} -->\n\n" + report

    bench_log.log("replay_end", scores=scores, verdict=verdict)
    bench_log.close()

    # Save replay report
    results_dir = PROJECT_ROOT / "docs" / "qa" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    replay_path = results_dir / f"{original_ts}-replay-{replay_ts}-e2e-react-calculator.md"
    replay_path.write_text(report, encoding="utf-8")
    print(f"\nReplay report saved: {replay_path}", flush=True)

    print(f"\nREPLAY VERDICT: {verdict}")
    if reasons:
        for r in reasons:
            print(f"  - {r}")

    if verdict == BenchmarkVerdict.PASS:
        return 0
    elif verdict == BenchmarkVerdict.INFRA_FAIL:
        return 2
    return 1


# --- Multi-Run ---


async def run_single_benchmark(
    strict: bool = False,
    min_score: int = 30,
) -> dict:
    """Run a single benchmark iteration (Phases B-F).

    Returns a dict with all results from the run.
    Does NOT check prerequisites or clean old sandboxes.
    """
    sandbox = create_sandbox()
    print(f"  Sandbox: {sandbox}")

    global _active_tracker
    _active_tracker = SandboxProcessTracker(sandbox)

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

    # Detect actual project root
    project_root = find_project_root(sandbox)
    if project_root != sandbox:
        print(f"\n  NOTE: Project found in subdirectory: {project_root.name}/")

    # Phase D: npm Validation
    print("\n[Phase D] Running npm validation...")
    npm_result = run_npm_validation(project_root)

    # Import validation
    print("\n[Phase D.1] Validating imports vs deps...")
    import_val = validate_imports_vs_deps(project_root)
    if import_val.get("missing"):
        print(f"  WARNING: Missing deps: {', '.join(import_val['missing'])}")

    # Security checks
    print("\n[Phase D.2] Running security checks...")
    security = run_security_checks(project_root)

    # Phase E: Scoring
    print("\n[Phase E] Scoring project...")
    scores = score_project(project_root)
    print(f"  Total score: {scores.get('total', 0)} / 100")

    # Anti-patterns
    anti_patterns = get_anti_patterns(project_root)
    if anti_patterns.get("penalty", 0) < 0:
        print(f"  Anti-pattern penalty: {anti_patterns['penalty']}")

    # Trace analysis
    bench_log.log("benchmark_end", scores=scores)
    bench_log.close()
    trace = analyze_trace(bench_log.log_path)

    # Budget check
    budgets = check_budgets(agent_result, bench_log)

    # Classify verdict
    if strict:
        verdict, reasons = classify_result_strict(
            scores, npm_result, agent_result,
            anti_patterns=anti_patterns, budgets=budgets,
        )
    else:
        verdict, reasons = classify_result(scores, npm_result, agent_result, min_score=min_score)

    # Phase F: Report & Storage
    print("\n[Phase F] Saving results...")
    report = generate_report(
        sandbox, agent_result, npm_result, scores, bench_log,
        verdict=verdict, verdict_reasons=reasons,
        anti_patterns=anti_patterns, import_validation=import_val,
        trace_analysis=trace, budgets=budgets, security=security,
    )

    ts, results_dir = save_results(
        sandbox, report, bench_log, scores, agent_result, npm_result,
        verdict=verdict, verdict_reasons=reasons,
        anti_patterns=anti_patterns, import_validation=import_val,
        trace_analysis=trace, budgets=budgets, security=security,
    )

    # Verify artifacts
    artifact_errors = verify_artifacts(sandbox, results_dir, ts, strict=strict)

    # Summary
    print("\n" + "=" * 60)
    print(f"BENCHMARK {verdict} - Score: {scores.get('total', 0)} / 100")
    print(f"Sandbox: {sandbox}")
    if reasons:
        for r in reasons:
            print(f"  - {r}")
    print("=" * 60)

    return {
        "sandbox": str(sandbox),
        "scores": scores,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "npm_result": npm_result,
        "npm_build": (npm_result.get("build") or {}).get("success", False),
        "agent_result": agent_result,
        "anti_patterns": anti_patterns,
        "import_validation": import_val,
        "trace_analysis": trace,
        "budgets": budgets,
        "security": security,
        "artifact_errors": artifact_errors,
        "ts": ts,
    }


def aggregate_multi_run(
    results: list[dict],
    strict: bool = False,
    min_score: int = 30,
) -> dict:
    """Aggregate results from multiple benchmark runs.

    INFRA_FAIL runs are excluded from product statistics per Codex Entry 219.
    """
    product_runs = [r for r in results if r["verdict"] != BenchmarkVerdict.INFRA_FAIL]
    infra_fails = [r for r in results if r["verdict"] == BenchmarkVerdict.INFRA_FAIL]

    if not product_runs:
        return {
            "total_runs": len(results),
            "product_runs": 0,
            "infra_fails": len(infra_fails),
            "pass_rate": 0.0,
            "scores": {"min": 0, "max": 0, "median": 0, "mean": 0.0},
            "build_pass_rate": 0.0,
            "verdicts": [r["verdict"] for r in results],
        }

    product_scores = [r["scores"].get("total", 0) for r in product_runs]
    passes = [r for r in product_runs if r["verdict"] == BenchmarkVerdict.PASS]
    builds = [r for r in product_runs if r.get("npm_build", False)]

    return {
        "total_runs": len(results),
        "product_runs": len(product_runs),
        "infra_fails": len(infra_fails),
        "pass_rate": len(passes) / len(product_runs),
        "scores": {
            "min": min(product_scores),
            "max": max(product_scores),
            "median": statistics.median(product_scores),
            "mean": round(statistics.mean(product_scores), 1),
        },
        "build_pass_rate": len(builds) / len(product_runs),
        "verdicts": [r["verdict"] for r in results],
    }


async def run_multi(
    n_runs: int,
    strict: bool = False,
    min_score: int = 30,
) -> int:
    """Run the benchmark N times and aggregate results."""
    print(f"\n{'=' * 60}")
    print(f"MULTI-RUN MODE: {n_runs} runs")
    print(f"{'=' * 60}")

    results = []
    for i in range(n_runs):
        print(f"\n--- Run {i + 1}/{n_runs} ---")
        result = await run_single_benchmark(strict=strict, min_score=min_score)
        results.append(result)

    agg = aggregate_multi_run(results, strict=strict, min_score=min_score)

    print(f"\n{'=' * 60}")
    print("MULTI-RUN SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total runs: {agg['total_runs']}")
    print(f"  Product runs: {agg['product_runs']}")
    print(f"  INFRA_FAIL: {agg['infra_fails']}")
    print(f"  Pass rate: {agg['pass_rate']:.0%}")
    print(f"  Build pass rate: {agg['build_pass_rate']:.0%}")
    print(f"  Scores: min={agg['scores']['min']}, max={agg['scores']['max']}, "
          f"median={agg['scores']['median']}, mean={agg['scores']['mean']}")
    print(f"  Verdicts: {agg['verdicts']}")

    # Save multi-run summary
    results_dir = PROJECT_ROOT / "docs" / "qa" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    summary_path = results_dir / f"{ts}-multi-run-summary.json"
    summary_path.write_text(
        json.dumps(agg, indent=2, default=str), encoding="utf-8",
    )
    print(f"\nMulti-run summary saved: {summary_path}")

    # Return: 0 if all product runs passed, 2 if all infra-fail, 1 otherwise
    if agg["product_runs"] == 0:
        return 2
    if agg["pass_rate"] >= 1.0:
        return 0
    return 1


# --- Matrix Mode ---


async def run_matrix(matrix_path: Path) -> int:
    """Run benchmarks across multiple model/config combinations."""
    if not matrix_path.exists():
        print(f"ERROR: Matrix config not found: {matrix_path}", flush=True)
        return 1

    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    configs = matrix.get("configs", [])
    if not configs:
        print("ERROR: No configs in matrix file", flush=True)
        return 1

    print(f"\n{'=' * 60}")
    print(f"MATRIX MODE: {len(configs)} configurations")
    print(f"{'=' * 60}")

    all_results = []
    for i, config in enumerate(configs):
        name = config.get("name", f"config-{i}")
        print(f"\n--- Config {i + 1}/{len(configs)}: {name} ---")

        # Save original env
        saved_env = {}
        env_overrides = config.get("env", {})
        for key, value in env_overrides.items():
            saved_env[key] = os.environ.get(key)
            os.environ[key] = str(value)

        try:
            n_runs = config.get("runs", 1)
            min_score = config.get("min_score", 30)
            strict = config.get("strict", False)

            if n_runs > 1:
                results = []
                for j in range(n_runs):
                    r = await run_single_benchmark(strict=strict, min_score=min_score)
                    results.append(r)
                agg = aggregate_multi_run(results, strict=strict, min_score=min_score)
                all_results.append({"config": name, "aggregate": agg, "runs": results})
            else:
                result = await run_single_benchmark(strict=strict, min_score=min_score)
                all_results.append({"config": name, "runs": [result]})
        finally:
            # Restore env
            for key, orig in saved_env.items():
                if orig is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = orig

    # Save matrix results
    results_dir = PROJECT_ROOT / "docs" / "qa" / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    matrix_results_path = results_dir / f"{ts}-matrix-results.json"

    # Summarize for JSON (avoid serializing full run data)
    summary = []
    for entry in all_results:
        config_summary = {"config": entry["config"]}
        if "aggregate" in entry:
            config_summary["aggregate"] = entry["aggregate"]
        else:
            run = entry["runs"][0]
            config_summary["score"] = run["scores"].get("total", 0)
            config_summary["verdict"] = run["verdict"]
        summary.append(config_summary)

    matrix_results_path.write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8",
    )

    print(f"\n{'=' * 60}")
    print("MATRIX RESULTS")
    print(f"{'=' * 60}")
    print(f"| {'Config':<30} | {'Score':>5} | {'Verdict':<12} |")
    print(f"|{'-'*32}|{'-'*7}|{'-'*14}|")
    for entry in summary:
        score = entry.get("score", entry.get("aggregate", {}).get("scores", {}).get("median", "N/A"))
        verdict = entry.get("verdict", entry.get("aggregate", {}).get("verdicts", ["N/A"])[0])
        print(f"| {entry['config']:<30} | {score:>5} | {verdict:<12} |")

    print(f"\nMatrix results saved: {matrix_results_path}")

    return 0


# --- Flake Triage ---


async def run_with_flake_triage(
    strict: bool = False,
    min_score: int = 30,
) -> int:
    """Run benchmark with automatic flake triage.

    If first run passes, done. If it fails/infra-fails, rerun once.
    Classify as DETERMINISTIC_FAIL, FLAKY, or INFRA_FAIL.
    """
    print(f"\n{'=' * 60}")
    print("FLAKE TRIAGE MODE")
    print(f"{'=' * 60}")

    print("\n--- Run 1 ---")
    result1 = await run_single_benchmark(strict=strict, min_score=min_score)

    if result1["verdict"] == BenchmarkVerdict.PASS:
        print("\nFlake triage: PASS on first run — done.")
        return 0

    print(f"\nFirst run: {result1['verdict']} — rerunning for triage...")
    print("\n--- Run 2 (triage) ---")
    result2 = await run_single_benchmark(strict=strict, min_score=min_score)

    # Classify
    v1, v2 = result1["verdict"], result2["verdict"]
    if v1 == BenchmarkVerdict.INFRA_FAIL and v2 == BenchmarkVerdict.INFRA_FAIL:
        triage = "INFRA_FAIL"
        exit_code = 2
    elif v2 == BenchmarkVerdict.PASS:
        triage = "FLAKY"
        exit_code = 0  # Flaky counts as soft pass
    else:
        triage = "DETERMINISTIC_FAIL"
        exit_code = 1

    print(f"\n{'=' * 60}")
    print(f"FLAKE TRIAGE RESULT: {triage}")
    print(f"  Run 1: {v1} (score={result1['scores'].get('total', 0)})")
    print(f"  Run 2: {v2} (score={result2['scores'].get('total', 0)})")
    print(f"{'=' * 60}")

    return exit_code


# --- Argparse ---


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="HybridCoder E2E Benchmark: React Calculator",
    )

    # Modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--replay", type=Path, default=None,
        help="Replay/re-score an existing benchmark sandbox (path to sandbox dir)",
    )
    mode_group.add_argument(
        "--matrix", type=Path, default=None,
        help="Run matrix benchmark with config file (path to JSON)",
    )
    mode_group.add_argument(
        "--flake-triage", action="store_true", default=False,
        help="Run with automatic flake triage (rerun on failure)",
    )

    # Modifiers
    parser.add_argument(
        "--strict", action="store_true", default=False,
        help="Enable strict mode (higher thresholds, enforced budgets)",
    )
    parser.add_argument(
        "--runs", type=int, default=1,
        help="Number of benchmark runs (default: 1)",
    )
    parser.add_argument(
        "--min-score", type=int, default=30,
        help="Minimum acceptable score (default: 30)",
    )
    parser.add_argument(
        "--keep-last", type=int, default=DEFAULT_KEEP_LAST,
        help=f"Number of old sandboxes to keep (default: {DEFAULT_KEEP_LAST})",
    )
    parser.add_argument(
        "--score-only", action="store_true", default=False,
        help="In replay mode, skip npm validation and only re-score",
    )

    return parser


# --- Main ---


async def main(
    strict: bool = False,
    min_score: int = 30,
    keep_last: int = DEFAULT_KEEP_LAST,
    runs: int = 1,
) -> int:
    """Run the full E2E benchmark."""
    print("=" * 60)
    print("HybridCoder E2E Benchmark: React Calculator")
    print(f"Version: {BENCHMARK_VERSION}")
    print("=" * 60)

    # Phase A: Prerequisites (exits if .env is incomplete)
    print("\n[Phase A] Checking prerequisites...")
    check_prerequisites()
    print("  All required config found in .env")

    # Phase B: Setup
    print("\n[Phase B] Cleaning old sandboxes...")
    clean_old_sandboxes(keep_last=keep_last)
    print("  Old sandboxes cleaned (keeping last {})".format(keep_last))

    if runs > 1:
        return await run_multi(n_runs=runs, strict=strict, min_score=min_score)

    result = await run_single_benchmark(strict=strict, min_score=min_score)

    verdict = result["verdict"]
    if verdict == BenchmarkVerdict.PASS:
        return 0
    elif verdict == BenchmarkVerdict.INFRA_FAIL:
        return 2
    return 1


if __name__ == "__main__":
    args = build_arg_parser().parse_args()
    if args.replay:
        sys.exit(replay_benchmark(args.replay.resolve(), score_only=args.score_only))
    elif args.matrix:
        sys.exit(asyncio.run(run_matrix(args.matrix.resolve())))
    elif args.flake_triage:
        sys.exit(asyncio.run(run_with_flake_triage(
            strict=args.strict, min_score=args.min_score,
        )))
    else:
        sys.exit(asyncio.run(main(
            strict=args.strict,
            min_score=args.min_score,
            keep_last=args.keep_last,
            runs=args.runs,
        )))
