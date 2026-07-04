"""Standalone runner for Terminal-Bench tasks via AutoCode's full agent stack.

Called by harbor_adapter.py via subprocess. Runs inside our uv/Python 3.11 env
with full access to AgentLoop, Orchestrator, middleware, and tool registry.

Usage:
    uv run python benchmarks/adapters/harbor_runner.py \
        --instruction "task text" \
        --exec-socket /path/to/socket \
        --model tools
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "autocode" / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "benchmarks"))


async def run_task(
    instruction: str,
    exec_cmd_prefix: str,
    model: str,
    max_iterations: int = 30,
) -> dict:
    """Run a Terminal-Bench task through AutoCode's full agent stack."""
    from autocode.agent.approval import ApprovalManager, ApprovalMode
    from autocode.agent.factory import create_orchestrator
    from autocode.agent.tools import ToolDefinition, create_default_registry
    from autocode.config import load_config
    from autocode.layer4.llm import create_provider
    from autocode.session.store import SessionStore
    from benchmarks.adapters.command_sync import (
        build_marker_wrapped_command,
        new_command_marker,
        strip_marker_output,
    )

    start = time.monotonic()

    # Configure for autonomous terminal work
    config = load_config(project_root=PROJECT_ROOT)
    config.llm.model = model
    config.llm.provider = os.environ.get("AUTOCODE_LLM_PROVIDER", "openrouter")
    gateway_base = os.environ.get("AUTOCODE_LLM_API_BASE", "")
    if gateway_base:
        config.llm.api_base = gateway_base
    config.shell.enabled = True
    config.shell.timeout = 120
    config.shell.max_timeout = 300
    config.shell.allow_network = True
    config.tui.approval_mode = "auto"
    config.llm.temperature = 0.3

    provider = create_provider(config)
    registry = create_default_registry(project_root="/tmp/tbench-workspace")

    # Replace run_command handler to execute via docker exec
    def _handle_run_command(command: str, timeout: int = 120) -> str:
        """Execute command inside the Terminal-Bench container."""
        try:
            marker = new_command_marker()
            wrapped = build_marker_wrapped_command(command, marker)
            full_cmd = f"{exec_cmd_prefix} {json.dumps(wrapped)}"
            result = subprocess.run(
                full_cmd, shell=True, capture_output=True, text=True,
                timeout=timeout,
            )
            stdout, marker_status = strip_marker_output(result.stdout or "", marker)
            stderr, _stderr_status = strip_marker_output(result.stderr or "", marker)
            return_code = marker_status if marker_status is not None else result.returncode
            output = ""
            if stdout:
                output += stdout
            if stderr:
                output += f"\n[stderr]\n{stderr}"
            if marker_status is None:
                output += "\n[sync marker missing]"
            if return_code != 0:
                output += f"\n[exit code {return_code}]"
            # Truncate
            if len(output) > 10000:
                output = output[:5000] + "\n...(truncated)...\n" + output[-2000:]
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return f"[timeout after {timeout}s]"
        except Exception as e:
            return f"Error: {e}"

    # Override run_command in registry
    run_cmd_tool = registry.get("run_command")
    if run_cmd_tool:
        registry.register(ToolDefinition(
            name="run_command",
            description=(
                "Execute a bash command in the task environment. "
                "Use this to run any terminal command."
            ),
            parameters=run_cmd_tool.parameters,
            handler=lambda command="", timeout=120, **kw: _handle_run_command(
                command, int(timeout),
            ),
            requires_approval=False,
            executes_shell=True,
        ))

    # Create session
    session_store = SessionStore(":memory:")
    session_id = session_store.create_session(
        title="tbench-task",
        model=model,
        provider=config.llm.provider,
        project_dir="/tmp/tbench-workspace",
    )

    approval_manager = ApprovalManager(
        mode=ApprovalMode.AUTO,
        shell_config=config.shell,
    )

    # Bootstrap: gather environment info
    env_info = _handle_run_command(
        "pwd && ls -la && uname -a && which python3 python gcc make 2>/dev/null || true",
        timeout=10,
    )

    # Build the task prompt with bootstrap
    task_prompt = (
        f"You are solving a Terminal-Bench task autonomously. "
        f"Use run_command to execute bash commands. "
        f"Do NOT ask questions — work autonomously until the task is complete.\n\n"
        f"## Task\n{instruction}\n\n"
        f"## Environment\n```\n{env_info[:2000]}\n```\n\n"
        f"Read the task carefully, make a plan, then execute step by step. "
        f"Verify your work before finishing."
    )

    # Create orchestrator with full middleware stack
    orchestrator, session_stats = create_orchestrator(
        provider=provider,
        tool_registry=registry,
        approval_manager=approval_manager,
        session_store=session_store,
        session_id=session_id,
        memory_content=None,
        context_length=config.llm.context_length,
        compaction_threshold=config.agent.compaction_threshold,
    )

    # Set max iterations
    from autocode.agent.loop import AgentLoop
    original_max = AgentLoop.MAX_ITERATIONS
    AgentLoop.MAX_ITERATIONS = max_iterations

    try:
        # Run the agent
        response = await orchestrator.run(task_prompt)
        elapsed = time.monotonic() - start

        result = {
            "success": True,
            "response": str(response)[:1000] if response else "",
            "elapsed_s": elapsed,
            "turns": (
                session_stats.token_tracker.total_calls
                if session_stats.token_tracker else 0
            ),
            "input_tokens": (
                session_stats.token_tracker.total_input
                if session_stats.token_tracker else 0
            ),
            "output_tokens": (
                session_stats.token_tracker.total_output
                if session_stats.token_tracker else 0
            ),
        }
    except Exception as e:
        result = {
            "success": False,
            "error": str(e)[:500],
            "elapsed_s": time.monotonic() - start,
        }
    finally:
        AgentLoop.MAX_ITERATIONS = original_max

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instruction", required=True)
    parser.add_argument(
        "--exec-prefix",
        required=True,
        help="Command prefix for executing in container (e.g., 'docker exec CONTAINER bash -c')",
    )
    parser.add_argument("--model", default="tools")
    parser.add_argument("--max-iterations", type=int, default=30)
    args = parser.parse_args()

    result = asyncio.run(run_task(
        instruction=args.instruction,
        exec_cmd_prefix=args.exec_prefix,
        model=args.model,
        max_iterations=args.max_iterations,
    ))

    print(json.dumps(result))


if __name__ == "__main__":
    main()
