"""Request dispatch for backend-host RPC methods.

This isolates JSON-RPC method-to-handler routing from ``BackendServer`` so the
host object does not have to own the dispatch table itself.
"""

from __future__ import annotations

from typing import Any

from autocode.backend import schema as rpc_schema


async def dispatch_request(
    host: Any,
    method: str,
    params: dict[str, Any],
    request_id: int,
) -> None:
    """Dispatch one RPC request to the appropriate backend-host handler."""
    if method == "chat":
        message = params.get("message", "")
        session_id = params.get("session_id")
        host._agent_task = host._loop_create_task(host.handle_chat(message, session_id, request_id))
    elif method == "cancel":
        await host.handle_cancel(request_id)
    elif method == "command":
        cmd = params.get("cmd", "")
        await host.handle_command(cmd, request_id)
    elif method == rpc_schema.METHOD_COMMAND_LIST:
        await host.handle_command_list(request_id)
    elif method == rpc_schema.METHOD_SESSION_NEW:
        title = params.get("title", "")
        await host.handle_session_new(title, request_id)
    elif method == rpc_schema.METHOD_SESSION_LIST:
        await host.handle_session_list(request_id)
    elif method == rpc_schema.METHOD_MODEL_LIST:
        await host.handle_model_list(request_id)
    elif method == rpc_schema.METHOD_PROVIDER_LIST:
        await host.handle_provider_list(request_id)
    elif method == rpc_schema.METHOD_SESSION_RESUME:
        session_id = params.get("session_id", "")
        await host.handle_session_resume(session_id, request_id)
    elif method == rpc_schema.METHOD_TASK_LIST:
        await host.handle_task_list(request_id)
    elif method == rpc_schema.METHOD_SUBAGENT_LIST:
        await host.handle_subagent_list(request_id)
    elif method == rpc_schema.METHOD_SUBAGENT_CANCEL:
        subagent_id = params.get("subagent_id", "")
        await host.handle_subagent_cancel(subagent_id, request_id)
    elif method == rpc_schema.METHOD_PLAN_STATUS:
        await host.handle_plan_status(request_id)
    elif method == rpc_schema.METHOD_PLAN_SET:
        mode = params.get("mode", "normal")
        await host.handle_plan_set(mode, request_id)
    elif method == rpc_schema.METHOD_CONFIG_GET:
        await host.handle_config_get(request_id)
    elif method == rpc_schema.METHOD_CONFIG_SET:
        key = params.get("key", "")
        value = params.get("value", "")
        await host.handle_config_set(key, value, request_id)
    elif method == rpc_schema.METHOD_MEMORY_LIST:
        await host.handle_memory_list(request_id)
    elif method == rpc_schema.METHOD_CHECKPOINT_LIST:
        await host.handle_checkpoint_list(request_id)
    elif method == rpc_schema.METHOD_CHECKPOINT_RESTORE:
        checkpoint_id = params.get("checkpoint_id", "")
        await host.handle_checkpoint_restore(checkpoint_id, request_id)
    elif method == rpc_schema.METHOD_PLAN_EXPORT:
        await host.handle_plan_export(request_id)
    elif method == rpc_schema.METHOD_PLAN_SYNC:
        path = params.get("path", "")
        await host.handle_plan_sync(path, request_id)
    elif method == rpc_schema.METHOD_STEER:
        message = params.get("message", "")
        await host.handle_steer(message, request_id)
    elif method == rpc_schema.METHOD_SESSION_FORK:
        await host.handle_session_fork(request_id)
    elif method == rpc_schema.METHOD_SHUTDOWN:
        await host.handle_shutdown(request_id)
    elif request_id:
        host.emit_response(request_id, {"error": f"Unknown method: {method}"})
