"""Host-independent backend application services.

These helpers own backend application behavior that should stay testable
without JSON-RPC framing or a terminal frontend. ``BackendServer`` remains
the stdio JSON-RPC host and delegates into this module for non-transport
operations.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from autocode.agent.loop import AgentMode
from autocode.app import commands as app_commands
from autocode.config import AutoCodeConfig
from autocode.core.logging import setup_session_logging
from autocode.session.task_store import TaskStore

if TYPE_CHECKING:
    from autocode.app.commands import AppContext, CommandRouter
    from autocode.session.store import SessionStore


class BackendServiceError(ValueError):
    """Raised when an application-service operation cannot be completed."""


@dataclass(slots=True)
class SessionTransition:
    """State that the host must apply after a session transition."""

    session_id: str
    title: str
    session_log_dir: Path
    session_titled: bool


@dataclass(slots=True)
class CommandExecutionResult:
    """Result of a slash-command execution."""

    payload: dict[str, Any]
    status_changed: bool


@dataclass(slots=True)
class PlanModeUpdate:
    """Updated persisted plan-mode state."""

    agent_mode: AgentMode
    plan_mode_enabled: bool
    changed: bool


@dataclass(slots=True)
class ConfigUpdate:
    """Updated backend configuration."""

    config: AutoCodeConfig


async def create_session_transition(
    *,
    title: str,
    config: AutoCodeConfig,
    project_root: Path,
    session_store: SessionStore,
    teardown_agent_resources: Callable[[], Awaitable[None]],
) -> SessionTransition:
    """Create a new session after tearing down current runtime resources."""

    await teardown_agent_resources()
    resolved_title = title or "New session"
    session_id = session_store.create_session(
        title=resolved_title,
        model=config.llm.model,
        provider=config.llm.provider,
        project_dir=str(project_root),
    )
    session_log_dir = setup_session_logging(config.logging, session_id)
    return SessionTransition(
        session_id=session_id,
        title=resolved_title,
        session_log_dir=session_log_dir,
        session_titled=bool(title),
    )


async def resume_session_transition(
    *,
    session_id: str,
    config: AutoCodeConfig,
    session_store: SessionStore,
    teardown_agent_resources: Callable[[], Awaitable[None]],
) -> SessionTransition:
    """Resolve a session prefix and return the resulting session transition."""

    normalized_id = session_id.strip()
    if not normalized_id:
        raise BackendServiceError("Session ID is required")

    sessions = session_store.list_sessions()
    matches = [session for session in sessions if session.id.startswith(normalized_id)]

    if not matches:
        raise BackendServiceError(f"Session not found: {normalized_id}")

    if len(matches) > 1:
        sample = ", ".join(session.id[:8] for session in matches[:5])
        raise BackendServiceError(
            f"Ambiguous session prefix '{normalized_id}'. Matches: {sample}"
        )

    match = matches[0]
    await teardown_agent_resources()
    return SessionTransition(
        session_id=match.id,
        title=match.title,
        session_log_dir=setup_session_logging(config.logging, match.id),
        session_titled=True,
    )


def build_command_list_payload(command_router: CommandRouter) -> dict[str, Any]:
    """Return the backend-owned slash command catalog."""

    commands = [
        {
            "name": cmd.name,
            "aliases": list(cmd.aliases),
            "description": cmd.description,
        }
        for cmd in command_router.get_all()
    ]
    return {"commands": commands}


async def execute_command(
    *,
    cmd: str,
    command_router: CommandRouter,
    app_context: AppContext,
    config: AutoCodeConfig,
) -> CommandExecutionResult:
    """Execute a slash command without transport concerns."""

    before = (
        config.llm.model,
        config.llm.provider,
        config.tui.approval_mode,
    )
    payload: dict[str, Any] = {"ok": True}

    stripped = cmd.strip()
    if stripped == "/compact":
        messages = app_context.session_store.get_messages(app_context.session_id)
        kept_messages = 4
        if len(messages) > kept_messages:
            summary_parts = [f"{m.role}: {m.content[:100]}" for m in messages[:-kept_messages]]
            summary = "Summary of previous conversation:\n" + "\n".join(summary_parts)
            payload.update(
                {
                    "compacted": True,
                    "messages_compacted": len(messages) - kept_messages,
                    "summary_tokens": max(1, len(summary) // 4),
                }
            )

    dispatched = command_router.dispatch(cmd)
    if dispatched is None:
        app_context.add_system_message(f"Unknown command: {cmd}")
        return CommandExecutionResult(payload=payload, status_changed=False)

    slash_cmd, args = dispatched
    await slash_cmd.handler(app_context, args)

    after = (
        config.llm.model,
        config.llm.provider,
        config.tui.approval_mode,
    )
    return CommandExecutionResult(payload=payload, status_changed=before != after)


def build_session_list_payload(session_store: SessionStore, *, limit: int = 20) -> dict[str, Any]:
    """Return a session list payload."""

    sessions = session_store.list_sessions()
    return {
        "sessions": [
            {
                "id": session.id,
                "title": session.title,
                "model": session.model,
                "provider": session.provider,
            }
            for session in sessions[:limit]
        ]
    }


def build_provider_list_payload(config: AutoCodeConfig) -> dict[str, Any]:
    """Return supported providers and the current selection."""

    return {
        "providers": list(app_commands._SUPPORTED_PROVIDERS),
        "current": config.llm.provider,
    }


def build_model_list_payload(config: AutoCodeConfig) -> dict[str, Any]:
    """Return models for the currently selected provider."""

    try:
        models = app_commands._list_models(config.llm.provider, config.llm.api_base)
    except Exception as exc:  # noqa: BLE001 - service returns structured backend error
        raise BackendServiceError(f"model.list failed: {exc}") from exc
    return {"models": models, "current": config.llm.model}


def ensure_task_store(
    task_store: TaskStore | None,
    *,
    session_store: SessionStore,
    session_id: str,
) -> TaskStore:
    """Return a task store for the active session."""

    if task_store is not None:
        return task_store
    return TaskStore(session_store.get_connection(), session_id)


def build_task_list_payload(task_store: TaskStore) -> dict[str, Any]:
    """Return the serialized task list for the current session."""

    tasks = task_store.list_tasks()
    return {"tasks": [task.model_dump(mode="json") for task in tasks]}


def build_task_state_payload(
    *,
    task_store: TaskStore | None,
    subagent_manager: Any | None,
) -> dict[str, Any]:
    """Return the canonical task/subagent projection payload."""

    tasks: list[dict[str, Any]] = []
    if task_store is not None:
        tasks = [task.model_dump(mode="json") for task in task_store.list_tasks()]

    subagents: list[dict[str, Any]] = []
    if subagent_manager is not None:
        subagents = subagent_manager.list_all()

    return {"tasks": tasks, "subagents": subagents}


def build_subagent_list_payload(subagent_manager: Any | None) -> dict[str, Any]:
    """Return the list of active and completed subagents."""

    if subagent_manager is None:
        return {"subagents": []}
    return {"subagents": subagent_manager.list_all()}


def cancel_subagent(subagent_manager: Any | None, subagent_id: str) -> dict[str, Any]:
    """Cancel a subagent if one exists."""

    if subagent_manager is None:
        return {"success": False}
    return {"success": subagent_manager.cancel(subagent_id)}


def build_plan_status_payload(agent_loop: Any | None, agent_mode: AgentMode) -> dict[str, Any]:
    """Return the current persisted plan mode."""

    if agent_loop is not None:
        mode = agent_loop.get_mode().value
    else:
        mode = agent_mode.value
    return {"mode": mode}


def update_plan_mode(
    *,
    mode: str,
    current_mode: AgentMode,
    agent_loop: Any | None,
) -> PlanModeUpdate:
    """Validate and update persisted plan mode state."""

    try:
        agent_mode = AgentMode(mode)
    except ValueError as exc:
        raise BackendServiceError(
            f"Invalid mode '{mode}'. Use 'normal', 'planning', or 'research'."
        ) from exc

    if agent_loop is not None:
        agent_loop.set_mode(agent_mode)

    return PlanModeUpdate(
        agent_mode=agent_mode,
        plan_mode_enabled=agent_mode == AgentMode.PLANNING,
        changed=current_mode != agent_mode,
    )


def build_config_payload(config: AutoCodeConfig) -> dict[str, Any]:
    """Return the serialized backend configuration."""

    return config.model_dump()


def update_config(
    *,
    config: AutoCodeConfig,
    key: str,
    value: str,
) -> ConfigUpdate:
    """Validate and update one config value."""

    parts = key.split(".")
    if len(parts) != 2:  # noqa: PLR2004
        raise BackendServiceError("Key must be section.field")

    section, field = parts
    data = config.model_dump()
    if section not in data:
        raise BackendServiceError(f"Unknown section: {section}")
    if field not in data[section]:
        raise BackendServiceError(f"Unknown field: {section}.{field}")

    data[section][field] = value
    return ConfigUpdate(config=AutoCodeConfig.model_validate(data))


def build_memory_list_payload(memory_store: Any | None) -> dict[str, Any]:
    """Return the memory list for the current project."""

    if memory_store is None:
        return {"memories": []}
    return {"memories": memory_store.get_memories()}


def build_checkpoint_list_payload(checkpoint_store: Any | None) -> dict[str, Any]:
    """Return serialized checkpoints for the active session."""

    if checkpoint_store is None:
        return {"checkpoints": []}
    checkpoints = checkpoint_store.list_checkpoints()
    return {"checkpoints": [checkpoint.model_dump(mode="json") for checkpoint in checkpoints]}


def restore_checkpoint(
    *,
    checkpoint_store: Any | None,
    task_store: TaskStore | None,
    session_store: SessionStore,
    checkpoint_id: str,
) -> dict[str, Any]:
    """Restore a checkpoint for the current session."""

    if checkpoint_store is None or task_store is None:
        raise BackendServiceError("No checkpoint or task store")

    try:
        result = checkpoint_store.restore_checkpoint(
            checkpoint_id,
            task_store,
            session_store,
        )
    except Exception as exc:  # noqa: BLE001 - backend needs structured failure
        raise BackendServiceError(str(exc)) from exc
    return {"ok": True, **result}


def export_plan_artifact(
    *,
    session_id: str,
    task_store: TaskStore | None,
    subagent_manager: Any | None,
    project_root: Path,
) -> dict[str, Any]:
    """Export the current plan artifact."""

    if task_store is None:
        raise BackendServiceError("No task store")

    try:
        from autocode.agent.plan_artifact import export

        path = export(session_id, task_store, subagent_manager, project_root)
    except Exception as exc:  # noqa: BLE001 - backend needs structured failure
        raise BackendServiceError(str(exc)) from exc
    return {"path": str(path)}


def sync_plan_artifact(
    *,
    session_id: str,
    task_store: TaskStore | None,
    path: str,
) -> dict[str, Any]:
    """Sync task state from a markdown plan artifact."""

    if task_store is None:
        raise BackendServiceError("No task store")

    try:
        from autocode.agent.plan_artifact import sync_from_markdown

        updated = sync_from_markdown(session_id, task_store, path)
    except Exception as exc:  # noqa: BLE001 - backend needs structured failure
        raise BackendServiceError(str(exc)) from exc
    return {"updated": updated}


def inject_steer(
    *,
    message: str,
    agent_task: Any | None,
    agent_loop: Any | None,
    session_store: SessionStore,
    session_id: str,
) -> dict[str, Any]:
    """Inject a steer message into the active session."""

    if not message.strip():
        return {"error": "Steer message is empty"}

    if agent_task is None or agent_task.done():
        return {"error": "No active run to steer", "active": False}

    if agent_loop is not None:
        agent_loop.cancel()

    session_store.add_message(session_id, "user", f"[steer] {message}")
    return {"ok": True, "injected": True}


def fork_session(
    *,
    session_store: SessionStore,
    source_session_id: str,
    config: AutoCodeConfig,
    project_root: Path,
) -> dict[str, Any]:
    """Create a forked copy of the current session."""

    new_id = session_store.create_session(
        title=f"Fork of {source_session_id[:8]}",
        model=config.llm.model,
        provider=config.llm.provider,
        project_dir=str(project_root),
    )

    for message in session_store.get_messages(source_session_id):
        session_store.add_message(new_id, message.role, message.content)

    return {"new_session_id": new_id}
