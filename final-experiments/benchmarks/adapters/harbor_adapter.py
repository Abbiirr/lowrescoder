"""Harbor/Terminal-Bench v2.0 adapter for AutoCode.

External Agent adapter with full harness engineering:
- write_file / read_file tools (bypass shell quoting)
- Forced planning step before execution
- Pre-completion verification
- Error-resilient LLM loop (errors don't burn turns)
- Tool-pair-safe context compaction
- Anti-hallucination prompt guidance
- Doom-loop detection with strategy nudge

Usage:
    harbor run -d terminal-bench@2.0 \
        --agent-import-path benchmarks.adapters.harbor_adapter:AutoCodeHarborAgent \
        -m "terminal_bench" --env-file .env -l 1 -y
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from autocode.agent.strategy_overlays import (
    StagnationDetector,
    classify_task,
    get_overlay,
    verifier_aware_retry_guidance,
)

logger = logging.getLogger(__name__)

# Tools exposed to the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a bash command in the task environment. "
                "Use for running scripts, installing packages, compiling, "
                "testing, and any shell operation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write content to a file. Use this instead of echo/cat/heredoc "
                "for creating or overwriting files. Handles all quoting safely."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path to write",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full file content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file. Safer than cat for large files "
                "(auto-truncates to 10KB)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute file path to read",
                    },
                },
                "required": ["path"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are AutoCode, an autonomous terminal agent solving a Terminal-Bench task.\n\n"
    "AVAILABLE TOOLS (use ONLY these — no others exist):\n"
    "- run_command: execute any bash command\n"
    "- write_file: create/overwrite a file with exact content (use this for code files)\n"
    "- read_file: read a file's contents\n\n"
    "RULES:\n"
    "1. PLAN first — list your steps before executing\n"
    "2. Execute ONE step at a time, check output, then proceed\n"
    "3. Use write_file for creating/editing code — NOT echo/cat/heredoc\n"
    "4. If something fails, analyze WHY and try a DIFFERENT approach\n"
    "5. Do NOT ask questions — decide and act autonomously\n"
    "6. If you've tried the same approach 3+ times, STOP and try something completely different\n"
    "7. Read existing files with read_file before modifying them\n"
    "8. Before finishing, VERIFY your work by running the test/verification command\n\n"
    "CRITICAL: There is NO apply_patch, NO edit_file tool. "
    "To modify a file: read_file → modify in your response → write_file with full new content.\n"
)


class AutoCodeHarborAgent(BaseAgent):
    """External Agent for Terminal-Bench v2.0 via Harbor."""

    SUPPORTS_ATIF: bool = False

    @staticmethod
    def name() -> str:
        return "autocode"

    def version(self) -> str | None:
        return "0.3.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        """Pre-task setup."""
        await environment.exec(command="which python3 || which python || true")

    async def _exec_write_file(
        self,
        environment: BaseEnvironment,
        path: str,
        content: str,
    ) -> str:
        """Write file content via base64 to bypass all shell quoting."""
        b64 = base64.b64encode(content.encode()).decode()
        cmd = (
            f'python3 -c "'
            f"import base64, pathlib, os; "
            f"p = pathlib.Path('{path}'); "
            f"p.parent.mkdir(parents=True, exist_ok=True); "
            f"p.write_text(base64.b64decode('{b64}').decode()); "
            f"print(f'Wrote {{len(p.read_text())}} chars to {path}')"
            f'"'
        )
        result = await environment.exec(command=cmd, timeout_sec=10)
        output = result.stdout or ""
        if result.return_code != 0:
            output += (
                f"\n[stderr] {result.stderr or ''}\n[exit code {result.return_code}]"
            )
        return output or f"Wrote to {path}"

    async def _exec_read_file(
        self,
        environment: BaseEnvironment,
        path: str,
    ) -> str:
        """Read file content with binary detection and truncation."""
        result = await environment.exec(
            command=f"cat '{path}' 2>&1",
            timeout_sec=10,
        )
        output = result.stdout or ""
        if result.return_code != 0:
            return f"Error reading {path}: {result.stderr or output}"
        if not output:
            return "(empty file)"
        # Binary detection: if >20% non-printable chars, summarize instead
        sample = output[:2000]
        non_printable = sum(
            1 for c in sample if not c.isprintable() and c not in "\n\r\t"
        )
        if len(sample) > 0 and non_printable / len(sample) > 0.2:
            return (
                f"Binary file ({len(output)} bytes). "
                f"Use run_command with hexdump/xxd/file to inspect."
            )
        if len(output) > 10000:
            output = output[:5000] + "\n...(truncated)...\n" + output[-2000:]
        return output

    async def _exec_command(
        self,
        environment: BaseEnvironment,
        command: str,
    ) -> str:
        """Execute a shell command with output truncation."""
        result = await environment.exec(command=command, timeout_sec=120)
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.return_code != 0:
            output += f"\n[exit code {result.return_code}]"
        if len(output) > 10000:
            output = output[:5000] + "\n...(truncated)...\n" + output[-2000:]
        return output or "(no output)"

    def _compact_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Tool-pair-safe context compaction.

        Preserves system + user prompt, summarizes trimmed middle,
        keeps recent messages with tool_call/response pairs intact.
        """
        total_chars = sum(len(json.dumps(m)) for m in messages)
        if total_chars < 80000:
            return messages

        # Keep system + user prompt
        kept = messages[:2]

        # Summarize trimmed middle
        trimmed = messages[2:-15]
        if trimmed:
            tool_summaries = []
            for m in trimmed:
                if m.get("role") == "tool":
                    content = m.get("content", "")[:80]
                    tool_summaries.append(content)
                elif m.get("role") == "assistant" and m.get("tool_calls"):
                    for tc in m["tool_calls"]:
                        fn = tc.get("function", {})
                        tool_summaries.append(
                            f"{fn.get('name', '?')}({str(fn.get('arguments', ''))[:60]})"
                        )
            summary = "Previous actions: " + "; ".join(tool_summaries[-20:])
            kept.append({"role": "user", "content": summary[:2000]})

        # Keep last 15 messages, ensuring tool pairs are intact
        recent = messages[-15:]
        # Collect valid tool_call IDs in recent messages
        tc_ids = set()
        for m in recent:
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    tc_ids.add(tc.get("id", ""))
        # Remove orphaned tool responses
        recent = [
            m
            for m in recent
            if m.get("role") != "tool" or m.get("tool_call_id", "") in tc_ids
        ]
        kept.extend(recent)
        return kept

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        """Run the agent loop with full harness engineering."""
        start = time.monotonic()
        model = self.model_name or os.environ.get(
            "AUTOCODE_TBENCH_MODEL", "terminal_bench"
        )
        max_iterations = int(os.environ.get("AUTOCODE_TBENCH_MAX_ITER", "50"))
        gateway_base = os.environ.get(
            "AUTOCODE_LLM_API_BASE", "http://localhost:4000/v1"
        )
        api_key = os.environ.get(
            "OPENROUTER_API_KEY",
            os.environ.get("LITELLM_MASTER_KEY", ""),
        )

        # --- Phase 1: Environment Bootstrap ---
        env_result = await environment.exec(
            command=(
                "echo '=== PWD ===' && pwd && "
                "echo '=== FILES ===' && ls -la && "
                "echo '=== SYSTEM ===' && uname -a && "
                "echo '=== TOOLS ===' && "
                "which python3 python gcc g++ make cmake pip npm node 2>/dev/null || true && "
                "echo '=== TESTS ===' && "
                "ls tests/ test_*.py *test*.sh verify.sh 2>/dev/null || true && "
                "echo '=== TEST CONTENT ===' && "
                "head -30 tests/test_outputs.py test_*.py verify.sh 2>/dev/null || true"
            ),
            timeout_sec=15,
        )
        bootstrap = (env_result.stdout or "")[:3000]

        # --- Strategy overlay for this task ---
        overlay = get_overlay(instruction)
        family = classify_task(instruction)
        stagnation = StagnationDetector(
            max_identical_results=overlay.stagnation_threshold,
        )
        self.logger.info(
            "Task family: %s, overlay: max_edit=%d max_build=%d verify=%s",
            family.value,
            overlay.max_edit_retries,
            overlay.max_build_retries,
            overlay.require_verifier_signal_before_retry,
        )

        family_guidance = ""
        if overlay.additional_prompt_guidance:
            family_guidance = (
                f"\n\nTASK-FAMILY GUIDANCE ({family.value}):\n"
                f"{overlay.additional_prompt_guidance}"
            )

        # --- Phase 2: Build messages with planning prompt ---
        task_prompt = (
            f"## Task\n{instruction}\n\n"
            f"## Environment\n```\n{bootstrap}\n```\n\n"
            f"STEP 1: Create a numbered plan of exactly what you need to do.\n"
            f"STEP 2: Execute each step using tools.\n"
            f"STEP 3: Verify by running tests/verification."
            f"{family_guidance}"
        )

        import httpx

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task_prompt},
        ]

        total_input_tokens = 0
        total_output_tokens = 0
        no_tool_count = 0
        error_count = 0
        edit_counts: dict[str, int] = {}
        productive_turns = 0

        llm_turns = 0

        while llm_turns < max_iterations:
            iteration = llm_turns
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    resp = await client.post(
                        f"{gateway_base}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "tools": TOOLS,
                            "stream": False,
                            "max_tokens": 4096,
                            "temperature": 0.3,
                        },
                    )
                    data = resp.json()

                # --- Fix 3: Error handling — don't burn turns ---
                if "error" in data:
                    error_count += 1
                    self.logger.warning(
                        "LLM error %d: %s", error_count, str(data["error"])[:200]
                    )
                    if error_count > 10:
                        self.logger.error("Too many LLM errors, stopping")
                        break
                    # If provider rejects due to malformed history, sanitize
                    err_msg = str(data.get("error", {}).get("message", ""))
                    if "invalid JSON" in err_msg or "tool_calls" in err_msg:
                        messages = self._compact_messages(messages)
                    import asyncio

                    await asyncio.sleep(3)
                    # Inject recovery context so model doesn't lose its thread
                    if messages and messages[-1].get("role") in ("tool", "assistant"):
                        last_action = ""
                        for m in reversed(messages[-5:]):
                            if m.get("tool_calls"):
                                fn = m["tool_calls"][0].get("function", {})
                                last_action = (
                                    f"{fn.get('name', '?')}"
                                    f"({str(fn.get('arguments', ''))[:80]})"
                                )
                                break
                        if last_action:
                            messages.append(
                                {
                                    "role": "user",
                                    "content": (
                                        "An LLM provider error occurred. "
                                        "Continue working on the task. "
                                        f"Your last action was: {last_action}"
                                    ),
                                }
                            )
                    continue  # Don't count as a productive turn

                choice = data.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content") or ""
                tool_calls = msg.get("tool_calls") or []

                # Only successful model responses consume the turn budget.
                llm_turns += 1

                # Track tokens
                usage = data.get("usage", {})
                total_input_tokens += usage.get("prompt_tokens", 0)
                total_output_tokens += usage.get("completion_tokens", 0)

                if tool_calls:
                    no_tool_count = 0
                    productive_turns += 1

                    # Sanitize tool_call arguments to valid JSON
                    clean_msg = dict(msg)
                    if "tool_calls" in clean_msg:
                        clean_tcs = []
                        for raw_tc in clean_msg["tool_calls"]:
                            tc_copy = dict(raw_tc)
                            fn = dict(tc_copy.get("function", {}))
                            args = fn.get("arguments", "{}")
                            if isinstance(args, str):
                                try:
                                    json.loads(args)
                                except (json.JSONDecodeError, TypeError):
                                    fn["arguments"] = json.dumps({"command": args})
                            tc_copy["function"] = fn
                            clean_tcs.append(tc_copy)
                        clean_msg["tool_calls"] = clean_tcs
                    messages.append(clean_msg)

                    # Execute each tool call
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        tc_id = tc.get("id", f"tc_{iteration}")
                        fn_name = fn.get("name", "run_command")
                        args_raw = fn.get("arguments", "{}")

                        # Parse arguments
                        if isinstance(args_raw, str):
                            try:
                                args = json.loads(args_raw)
                            except json.JSONDecodeError:
                                args = {"command": args_raw}
                        else:
                            args = args_raw

                        # Dispatch tool
                        if fn_name == "write_file":
                            path = args.get("path", "/tmp/unknown")
                            file_content = args.get("content", "")
                            self.logger.info(
                                "Turn %d: write_file %s (%d chars)",
                                iteration + 1,
                                path,
                                len(file_content),
                            )
                            output = await self._exec_write_file(
                                environment,
                                path,
                                file_content,
                            )
                            edit_counts[path] = edit_counts.get(path, 0) + 1

                        elif fn_name == "read_file":
                            path = args.get("path", "")
                            self.logger.info(
                                "Turn %d: read_file %s", iteration + 1, path
                            )
                            output = await self._exec_read_file(environment, path)

                        elif fn_name == "run_command":
                            cmd = args.get("command", str(args))
                            self.logger.info("Turn %d: %s", iteration + 1, cmd[:120])
                            output = await self._exec_command(environment, cmd)

                            # Track file edits from shell commands
                            for pattern in ["sed ", "cat >", "tee ", "> "]:
                                if pattern in cmd:
                                    for p in cmd.split():
                                        if "/" in p and not p.startswith("-"):
                                            edit_counts[p] = edit_counts.get(p, 0) + 1
                                            break
                                    break
                        else:
                            # Unknown tool (e.g., apply_patch hallucination)
                            output = (
                                f"ERROR: Tool '{fn_name}' does not exist. "
                                f"Available tools: run_command, write_file, read_file. "
                                f"Use write_file to create/edit files."
                            )
                            self.logger.warning("Hallucinated tool: %s", fn_name)

                        # Doom-loop detection with escalating response
                        # Use overlay thresholds per task family
                        edit_threshold = overlay.max_edit_retries
                        doom_files = [
                            f for f, c in edit_counts.items() if c >= edit_threshold
                        ]
                        if doom_files:
                            worst = max(doom_files, key=lambda f: edit_counts[f])
                            count = edit_counts[worst]
                            if count >= edit_threshold + 2:
                                output += (
                                    f"\n\n[DOOM LOOP CRITICAL: {worst} edited "
                                    f"{count} times with no progress. STOP editing "
                                    f"this file. Instead:\n"
                                    f"1. Re-read the task instructions\n"
                                    f"2. List 3 fundamentally DIFFERENT approaches\n"
                                    f"3. Pick the one you haven't tried\n"
                                    f"4. Only then proceed with a new strategy]"
                                )
                            else:
                                output += (
                                    f"\n\n[DOOM LOOP WARNING: {worst} edited "
                                    f"{count} times. Try a different approach.]"
                                )

                        # Stagnation detection (identical results)
                        stag_warning = stagnation.check(fn_name, output)
                        if stag_warning:
                            output += f"\n\n[{stag_warning}]"

                        # Verifier-aware retry guidance
                        if overlay.require_verifier_signal_before_retry:
                            retry_count = edit_counts.get(
                                args.get("path", ""),
                                0,
                            )
                            vguidance = verifier_aware_retry_guidance(
                                fn_name,
                                output,
                                retry_count,
                                overlay.max_build_retries,
                            )
                            if vguidance:
                                output += f"\n\n[{vguidance}]"

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc_id,
                                "content": output,
                            }
                        )

                elif content:
                    messages.append({"role": "assistant", "content": content})
                    no_tool_count += 1

                    # --- Fix 2: Raised threshold + nudge ---
                    if no_tool_count >= 5:
                        break

                    # Check for completion signals — strict matching to
                    # avoid false triggers on "once we're done..." etc.
                    import re as _re

                    content_lower = content.lower().strip()
                    _completion_re = _re.compile(
                        r"\b(?:task\s+(?:is\s+)?complete[d]?"
                        r"|i\s+have\s+(?:completed|finished)"
                        r"|all\s+(?:steps|checks)\s+(?:pass|complete)"
                        r"|completed\s+successfully"
                        r"|work\s+is\s+(?:done|complete)"
                        r"|everything\s+(?:is\s+)?(?:done|working|passing))\b"
                    )
                    if _completion_re.search(content_lower):
                        # --- Fix 6: Pre-completion verification ---
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Before finishing, VERIFY your work: "
                                    "run the test/verification command "
                                    "to confirm everything passes. "
                                    "Look for test_outputs.py, verify.sh, or test.sh "
                                    "in the environment."
                                ),
                            }
                        )
                        no_tool_count = 0  # Reset — give agent a chance to verify
                    elif no_tool_count >= 3:
                        # Nudge after 3 text-only responses
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "You must use tools to make progress. "
                                    "Execute a command or write a file NOW."
                                ),
                            }
                        )
                else:
                    # Empty response
                    no_tool_count += 1
                    if no_tool_count >= 5:
                        break

                # --- Fix 5: Tool-pair-safe context compaction ---
                messages = self._compact_messages(messages)

            except Exception as e:
                error_count += 1
                self.logger.warning("Turn %d error: %s", iteration + 1, str(e)[:200])
                if error_count > 10:
                    break
                import asyncio

                await asyncio.sleep(3)
                continue  # Don't count as productive turn

        # Populate context
        elapsed = time.monotonic() - start
        context.n_input_tokens = total_input_tokens
        context.n_output_tokens = total_output_tokens
        context.cost_usd = 0.0

        self.logger.info(
            "Completed: %d productive turns, %d errors, %.1fs, %d/%d tokens",
            productive_turns,
            error_count,
            elapsed,
            total_input_tokens,
            total_output_tokens,
        )
