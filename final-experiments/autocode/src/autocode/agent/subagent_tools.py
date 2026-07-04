"""Subagent management tools for the agent (spawn, check, cancel, list)."""

from __future__ import annotations

import logging

from autocode.agent.subagent import SubagentManager
from autocode.agent.tools import ToolDefinition, ToolRegistry
from autocode.agent.worktree import build_merge_back_plan, create_worktree
from autocode.core.logging import log_event

logger = logging.getLogger(__name__)


def _make_spawn_handler(manager: SubagentManager):
    def handler(
        subagent_type: str = "explore",
        task: str = "",
        context: str = "",
        use_worktree: bool = False,
        **_kwargs,
    ) -> str:
        if not task:
            return "Error: task is required to spawn a subagent."
        worktree_note = ""
        if use_worktree:
            repo_root = getattr(manager, "project_root", None)
            if repo_root is None:
                return "Error: manager has no project_root for worktree isolation."
            info = create_worktree(repo_root)
            plan = build_merge_back_plan(info)
            context = (
                f"{context}\n\n[Worktree]\nPath: {info.path}\nBranch: {info.branch}\n"
                f"Merge-back: {' '.join(plan.diff_command)}\n{plan.instructions}"
            ).strip()
            worktree_note = f" in worktree {info.path}"
        try:
            subagent_id = manager.spawn(subagent_type, task, context)
        except (RuntimeError, ValueError) as e:
            return f"Error: {e}"
        log_event(
            logger, logging.INFO, "subagent_spawned",
            subagent_id=subagent_id, subagent_type=subagent_type,
            task=task[:100],
        )
        return (
            f"Spawned {subagent_type} subagent '{subagent_id}'{worktree_note}. "
            f"Use check_subagent(subagent_id='{subagent_id}') to get results."
        )
    return handler


def _make_check_handler(manager: SubagentManager):
    def handler(subagent_id: str = "", **_kwargs) -> str:
        if not subagent_id:
            return "Error: subagent_id is required."
        status = manager.get_status(subagent_id)
        if status["status"] == "not_found":
            return f"Error: subagent '{subagent_id}' not found."
        if status["status"] == "running":
            return f"Subagent '{subagent_id}' is still running."
        result = manager.get_result(subagent_id)
        if result is None:
            return f"Subagent '{subagent_id}': {status['status']}"
        lines = [
            f"Subagent '{subagent_id}' ({result.subagent_type}): {result.status}",
            f"Iterations: {result.iterations_used}, Duration: {result.duration_ms}ms",
        ]
        if result.files_touched:
            lines.append(f"Files touched: {', '.join(result.files_touched)}")
        lines.append(f"Summary:\n{result.summary}")
        return "\n".join(lines)
    return handler


def _make_cancel_handler(manager: SubagentManager):
    def handler(subagent_id: str = "", **_kwargs) -> str:
        if not subagent_id:
            return "Error: subagent_id is required."
        cancelled = manager.cancel(subagent_id)
        if cancelled:
            log_event(
                logger, logging.INFO, "subagent_cancelled",
                subagent_id=subagent_id,
            )
            return f"Cancelled subagent '{subagent_id}'."
        return f"Subagent '{subagent_id}' is not running or not found."
    return handler


def _make_list_handler(manager: SubagentManager):
    def handler(**_kwargs) -> str:
        items = manager.list_all()
        if not items:
            return "No subagents (active or completed)."
        lines = [f"Subagents ({len(items)}):"]
        for item in items:
            status = item["status"]
            sid = item["id"]
            summary = item.get("summary", "")
            sa_type = item.get("type", "")
            if status == "running":
                lines.append(f"  [{sid}] running")
            else:
                lines.append(f"  [{sid}] {sa_type} — {status}: {summary}")
        return "\n".join(lines)
    return handler


def register_subagent_tools(
    registry: ToolRegistry,
    manager: SubagentManager,
) -> None:
    """Register spawn, check, cancel, list subagent tools."""
    registry.register(ToolDefinition(
        name="spawn_subagent",
        description=(
            "Spawn a background subagent for parallel work. "
            "Types: explore (read-only), plan (research + tasks), "
            "execute (full tools, no approval). "
            "Returns subagent_id for check_subagent."
        ),
        parameters={
            "type": "object",
            "properties": {
                "subagent_type": {
                    "type": "string",
                    "enum": ["explore", "plan", "execute"],
                    "description": "Subagent capability tier",
                },
                "task": {
                    "type": "string",
                    "description": "Task description for the subagent",
                },
                "context": {
                    "type": "string",
                    "description": "Optional extra context",
                },
                "use_worktree": {
                    "type": "boolean",
                    "description": "Run subagent in an isolated git worktree",
                },
            },
            "required": ["subagent_type", "task"],
        },
        handler=_make_spawn_handler(manager),
    ))

    registry.register(ToolDefinition(
        name="check_subagent",
        description="Check the status/result of a spawned subagent.",
        parameters={
            "type": "object",
            "properties": {
                "subagent_id": {
                    "type": "string",
                    "description": "ID returned by spawn_subagent",
                },
            },
            "required": ["subagent_id"],
        },
        handler=_make_check_handler(manager),
    ))

    registry.register(ToolDefinition(
        name="cancel_subagent",
        description="Cancel a running subagent.",
        parameters={
            "type": "object",
            "properties": {
                "subagent_id": {
                    "type": "string",
                    "description": "ID of the subagent to cancel",
                },
            },
            "required": ["subagent_id"],
        },
        handler=_make_cancel_handler(manager),
    ))

    registry.register(ToolDefinition(
        name="list_subagents",
        description="List all subagents (active and completed).",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
        handler=_make_list_handler(manager),
    ))
