"""System prompts for the AutoCode agent."""

from __future__ import annotations

import json
from typing import Any

CACHE_BOUNDARY_MARKER = "# === DANGEROUS_uncachedSystemPromptSection_BELOW ==="

SYSTEM_PROMPT = (
    "You are AutoCode, an AI coding assistant running locally "
    "on the user's machine.\n\n"
    "You help with software development tasks: writing code, debugging, "
    "explaining code, refactoring, and answering questions about codebases.\n\n"
    "Key principles:\n"
    "- Be concise and direct\n"
    "- Show code changes as complete file contents or clear diffs\n"
    "- Explain your reasoning briefly\n"
    "- Use the available tools to read files, write files, search code, "
    "and run commands\n"
    "- Always read a file before modifying it\n"
    "- Prefer minimal changes over large rewrites\n"
    "- For conversational messages (greetings like 'hi'/'hello', questions "
    "about who you are, casual chat, or simple factual questions you can "
    "answer from general knowledge), reply directly in plain text. Do NOT "
    "call any tools. Tools are for work on the user's files or system.\n\n"
    "When using tools:\n"
    "- Use read_file to understand existing code before making changes\n"
    "- Use list_files and search_text to explore the codebase\n"
    "- Use edit_file to modify existing files, write_file for new files\n"
    "- Use run_command sparingly and only when needed (e.g., running tests)\n"
    "- When old tool output is cluttering context, use list_tool_results to "
    "inspect cached entries and clear_tool_result to prune stale results by "
    "id, tool, age, or all=true\n"
    "- Use ask_user ONLY for genuine questions: clarifications, choosing "
    "between approaches, or gathering requirements. Do NOT use ask_user to "
    "request permission to use a tool — the approval system handles "
    "permissions automatically. Just call the tool directly.\n"
    "- When the user specifies a target directory for writing code (e.g., "
    "'write all code inside sandboxes/test_123'), write files directly "
    "inside that directory — the write_file tool automatically creates "
    "parent directories. Do not ask the user whether to create the "
    "directory. Do not list files first. Just proceed with writing.\n\n"
    "When working on multi-step tasks, use create_task to break work into "
    "trackable steps. Task status should move pending -> in_progress -> completed: "
    "call update_task with status in_progress before the first concrete action "
    "on a task, then completed when done.\n"
    "If dependencies are required, use add_task_dependency explicitly. "
    "After task changes, use list_tasks so the user sees the current to-do board.\n\n"
    "Subagents:\n"
    "- Use spawn_subagent for self-contained tasks that don't need user interaction\n"
    "- Use 'explore' for codebase research producing verbose output\n"
    "- Use 'plan' when you need to research AND create tasks from findings\n"
    "- Use 'execute' only for independent subtasks with clear criteria\n"
    "- Do NOT delegate when user interaction or simple single-step work is needed\n"
    "- Background subagents cannot request approval — they auto-deny write/shell\n"
    "- Check subagent results with check_subagent\n"
)

VERIFY_BEFORE_USE_SECTION = """

## Memory and recall discipline

You may have access to memory from past sessions (loaded as MEMORY.md and
topic files). Treat ALL such memory as a HINT, not as ground truth. Codebases
change between sessions: dependencies are updated, files are renamed, decisions
are reversed.

Before acting on any remembered information:
1. If the memory is about a file's contents, structure, or behavior, re-read
   the file with read_file before relying on it.
2. If the memory is about a tool's availability or signature, check with
   tool_search before calling.
3. If the memory is about a project decision or convention, confirm it's
   still current via grep or by asking the user.

You DO NOT need to verify:
- Truly stable facts, such as programming language semantics or well-known
  library APIs.
- The user's stated preferences in the current session.

When you find that memory contradicts current reality, update memory to correct
it when a memory-writing tool is available. Do not leave stale information.
"""

STABLE_INSTRUCTIONS = SYSTEM_PROMPT + VERIFY_BEFORE_USE_SECTION


def build_static_prefix() -> str:
    """Return the cacheable static portion of the system prompt.

    This never changes across iterations or sessions, making it ideal
    for prompt-caching (e.g., Anthropic's cache_control).
    """
    return SYSTEM_PROMPT


def serialize_tool_defs_stable(tools: list[dict[str, Any]]) -> str:
    """Serialize tool definitions deterministically for prompt caching."""
    def _tool_name(tool: dict[str, Any]) -> str:
        function = tool.get("function")
        if isinstance(function, dict):
            return str(function.get("name", ""))
        return str(tool.get("name", ""))

    ordered = sorted(tools, key=_tool_name)
    return json.dumps(ordered, sort_keys=True, separators=(",", ":"))


def build_stable_prefix(
    *,
    tool_definitions_json: str = "",
    rules_text: str = "",
    skill_catalog_index: str = "",
) -> str:
    """Build the deterministic cacheable prompt prefix."""
    parts = [STABLE_INSTRUCTIONS]
    if tool_definitions_json:
        parts.append(f"\n\n## Tool Definitions\n{tool_definitions_json}")
    if rules_text:
        parts.append(f"\n\n## Repository Rules\n{rules_text}")
    if skill_catalog_index:
        parts.append(f"\n\n## Skill Catalog\n{skill_catalog_index}")
    return "".join(parts)


def build_dynamic_tail(
    *,
    cwd: str = "",
    git_status_summary: str = "",
    current_iso_date: str = "",
    current_todo_state: str = "",
    open_tasks_summary: str = "",
) -> str:
    """Build the uncached per-turn prompt tail."""
    lines = ["## Dynamic Runtime Context"]
    if cwd:
        lines.append(f"- Working directory: {cwd}")
    if git_status_summary:
        lines.append(f"- Git status: {git_status_summary}")
    if current_iso_date:
        lines.append(f"- Current date: {current_iso_date}")
    if current_todo_state:
        lines.append(f"\n## Current Todo State\n{current_todo_state}")
    if open_tasks_summary:
        lines.append(f"\n## Open Tasks\n{open_tasks_summary}")
    return "\n".join(lines) + "\n"


def assemble_system_prompt(*, stable: str, dynamic: str) -> str:
    """Join stable and dynamic prompt regions with an explicit cache boundary."""
    return f"{stable.rstrip()}\n\n{CACHE_BOUNDARY_MARKER}\n\n{dynamic.lstrip()}"


def build_dynamic_suffix(
    memory_content: str | None = None,
    *,
    shell_enabled: bool = False,
    approval_mode: str = "suggest",
    context: str | None = None,
    task_summary: str = "",
    subagent_status: str = "",
    plan_mode: bool = False,
    research_mode: bool = False,
    agent_mode: str | None = None,
    memory_context: str = "",
) -> str:
    """Build the dynamic portion of the system prompt.

    This changes every iteration (approval mode, memory, tasks, etc.)
    and is NOT cached for prompt-caching purposes.

    Args:
        memory_content: Project memory text to inject.
        shell_enabled: Whether shell execution is enabled.
        approval_mode: Current approval mode (read-only, suggest, auto, autonomous).
        context: Assembled context from Layer 2 (repo map, search results, rules).
        task_summary: Task board state.
        subagent_status: Running/completed subagent summaries.
        plan_mode: Backward-compatible planning flag.
        research_mode: Backward-compatible research flag.
        agent_mode: Explicit agent mode (normal, planning, research).
        memory_context: Learned patterns from MemoryStore.
    """
    parts: list[str] = []
    effective_mode = agent_mode or (
        "research" if research_mode else "planning" if plan_mode else "normal"
    )

    # Inject environment status so the LLM knows what's available
    env_lines = ["\n## Current Environment\n"]
    env_lines.append(f"- Approval mode: {approval_mode}\n")
    if approval_mode == "autonomous":
        env_lines.append(
            "- Non-interactive mode: do not ask the user questions. "
            "Avoid ask_user, make the best bounded decision with the available context, "
            "and fail clearly if preconditions such as shell access are unavailable.\n"
        )
    if shell_enabled:
        env_lines.append("- Shell execution: ENABLED (run_command is available)\n")
    else:
        env_lines.append(
            "- Shell execution: DISABLED — but you can still call run_command. "
            "The user will be prompted to enable shell access.\n"
        )
    if effective_mode == "planning":
        env_lines.append(
            "- Mode: PLANNING — tools that modify the filesystem or execute "
            "shell commands are blocked. Use /plan approve to switch to "
            "execution mode.\n"
        )
    elif effective_mode == "research":
        env_lines.append(
            "- Mode: RESEARCH — this is read-only codebase comprehension mode. "
            "Tools that modify the filesystem or execute shell commands are blocked. "
            "Use /research off to switch to execution mode.\n"
        )
        env_lines.append(
            "- End with a concise implementation handoff containing candidate files "
            "and symbols, the active working set, repo-local command hints, open "
            "questions, and a compact next-step note.\n"
        )
    parts.append("".join(env_lines))

    if memory_content:
        parts.append(f"\n## Project Memory\n{memory_content}\n")

    if context:
        parts.append(f"\n## Project Context\n{context}\n")

    if task_summary:
        parts.append(f"\n## Active Tasks\n{task_summary}\n")

    if subagent_status:
        parts.append(f"\n## Background Work\n{subagent_status}\n")

    if memory_context:
        parts.append(f"\n## Learned Patterns\n{memory_context}\n")

    return "".join(parts)


def build_system_prompt(
    memory_content: str | None = None,
    *,
    shell_enabled: bool = False,
    approval_mode: str = "suggest",
    context: str | None = None,
    task_summary: str = "",
    subagent_status: str = "",
    plan_mode: bool = False,
    research_mode: bool = False,
    agent_mode: str | None = None,
    memory_context: str = "",
) -> str:
    """Build the full system prompt (backward-compatible wrapper).

    Concatenates build_static_prefix() + build_dynamic_suffix().

    Args:
        memory_content: Project memory text to inject.
        shell_enabled: Whether shell execution is enabled.
        approval_mode: Current approval mode (read-only, suggest, auto, autonomous).
        context: Assembled context from Layer 2 (repo map, search results, rules).
        task_summary: Task board state.
        subagent_status: Running/completed subagent summaries.
        plan_mode: Backward-compatible planning flag.
        research_mode: Backward-compatible research flag.
        agent_mode: Explicit agent mode (normal, planning, research).
        memory_context: Learned patterns from MemoryStore.
    """
    stable = build_static_prefix()
    dynamic = build_dynamic_suffix(
        memory_content,
        shell_enabled=shell_enabled,
        approval_mode=approval_mode,
        context=context,
        task_summary=task_summary,
        subagent_status=subagent_status,
        plan_mode=plan_mode,
        research_mode=research_mode,
        agent_mode=agent_mode,
        memory_context=memory_context,
    )
    return assemble_system_prompt(stable=stable, dynamic=dynamic)
