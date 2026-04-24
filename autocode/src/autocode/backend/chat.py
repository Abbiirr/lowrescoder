"""Host-independent backend chat execution helpers.

This module owns the substantive chat-turn execution path so ``BackendServer``
can stay focused on host coordination and transport concerns.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from pathlib import Path
from typing import Any, Protocol

from autocode.agent.loop import AgentLoop
from autocode.backend import schema as rpc_schema
from autocode.backend import services as backend_services
from autocode.core.logging import log_event, setup_session_logging

logger = logging.getLogger(__name__)

_CHAT_HEARTBEAT_INTERVAL_S = 15.0


class ChatHost(Protocol):
    """Host surface required by the backend chat service."""

    config: Any
    project_root: Path
    session_store: Any
    session_id: str
    _session_log_dir: Path
    _session_titled: bool
    _session_stats: Any | None
    _session_approved_tools: set[str]
    _approval_manager: Any | None
    _context_assembler: Any
    _l3_provider: Any
    _task_store: Any | None
    _subagent_manager: Any | None
    _edit_count: int

    def emit_notification(self, method: str, params: dict[str, Any]) -> None: ...

    async def emit_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]: ...

    def _emit_cost_update(self) -> None: ...

    async def _teardown_agent_resources(self) -> None: ...

    def _ensure_agent_loop(self) -> AgentLoop: ...

    def _expand_file_mentions(self, message: str) -> str: ...

    def _select_chat_layer(self, message: str) -> tuple[int, str, bool]: ...


def on_chunk(host: ChatHost, text: str) -> None:
    """Stream token callback -> notification on_token."""
    host.emit_notification("on_token", {"text": text})


def on_thinking_chunk(host: ChatHost, text: str) -> None:
    """Thinking token callback -> notification on_thinking."""
    host.emit_notification("on_thinking", {"text": text})


def emit_warning(host: ChatHost, message: str) -> None:
    """Visible non-fatal warning notification for the frontend."""
    host.emit_notification(rpc_schema.METHOD_ON_WARNING, {"message": message})


def emit_task_state(host: ChatHost) -> None:
    """Emit the canonical task/subagent projection notification."""
    payload = backend_services.build_task_state_payload(
        task_store=host._task_store,
        subagent_manager=host._subagent_manager,
    )
    host.emit_notification(rpc_schema.METHOD_ON_TASK_STATE, payload)


def on_tool_call(host: ChatHost, tool_name: str, status: str, result: str = "") -> None:
    """Tool call status callback -> notification on_tool_call."""
    host.emit_notification(
        "on_tool_call",
        {
            "name": tool_name,
            "status": status,
            "result": result,
        },
    )
    if status in ("completed", "success") and tool_name in ("write_file", "edit_file"):
        host._edit_count += 1

    task_tools = {"create_task", "update_task", "add_task_dependency", "list_tasks"}
    if tool_name in task_tools and status in ("completed", "success"):
        emit_task_state(host)


async def approval_callback(host: ChatHost, tool_name: str, arguments: dict[str, Any]) -> bool:
    """Approval callback -> request on_tool_request, waits for frontend response."""
    if tool_name in host._session_approved_tools:
        on_tool_call(host, tool_name, "pending", "(auto-approved)")
        if tool_name == "run_command" and host._approval_manager:
            host._approval_manager.enable_shell()
        return True

    args_str = json.dumps(arguments, indent=2)
    try:
        result = await host.emit_request(
            rpc_schema.METHOD_ON_TOOL_REQUEST,
            {
                "tool": tool_name,
                "args": args_str,
            },
        )
    except asyncio.CancelledError:
        return False

    approved = result.get("approved", False)
    session_approve = result.get("session_approve", False)

    if approved and session_approve:
        host._session_approved_tools.add(tool_name)

    if approved and tool_name == "run_command" and host._approval_manager:
        host._approval_manager.enable_shell()

    return bool(approved)


async def ask_user_callback(
    host: ChatHost,
    question: str,
    options: list[str],
    allow_text: bool,
) -> str:
    """Ask-user callback -> request on_ask_user, waits for frontend response."""
    try:
        result = await host.emit_request(
            rpc_schema.METHOD_ON_ASK_USER,
            {
                "question": question,
                "options": options,
                "allow_text": allow_text,
            },
        )
    except asyncio.CancelledError:
        return options[0] if options else ""

    return result.get("answer", "")


def _emit_chat_ack(host: ChatHost, request_id: int) -> None:
    host.emit_notification(
        rpc_schema.METHOD_ON_CHAT_ACK,
        {
            "request_id": request_id,
            "session_id": host.session_id,
        },
    )


def _done_params(host: ChatHost, layer_used: int, *, cancelled: bool = False) -> dict[str, Any]:
    params: dict[str, Any] = {"layer_used": layer_used}
    if cancelled:
        params["cancelled"] = True
    if host._session_stats:
        tokens = host._session_stats.token_tracker.total
        params["tokens_in"] = tokens.prompt_tokens
        params["tokens_out"] = tokens.completion_tokens
        params["session_summary"] = host._session_stats.summary()
    else:
        params["tokens_in"] = 0
        params["tokens_out"] = 0
    return params


async def run_chat_turn(
    host: ChatHost,
    *,
    message: str,
    session_id: str | None,
    request_id: int,
) -> None:
    """Run one backend chat turn without transport-specific concerns."""
    log_event(
        logger,
        logging.INFO,
        "backend_chat_received",
        request_id=request_id,
        session_id=session_id or host.session_id,
        message_chars=len(message),
    )

    layer_used = 4

    if session_id and session_id != host.session_id:
        await host._teardown_agent_resources()
        host.session_id = session_id
        host._session_log_dir = setup_session_logging(
            host.config.logging,
            host.session_id,
        )
        host._session_approved_tools.clear()

    _emit_chat_ack(host, request_id)
    log_event(
        logger,
        logging.INFO,
        "backend_chat_ack",
        request_id=request_id,
        session_id=host.session_id,
    )

    heartbeat_stop = asyncio.Event()

    async def _chat_heartbeat() -> None:
        while True:
            try:
                await asyncio.wait_for(
                    heartbeat_stop.wait(),
                    timeout=_CHAT_HEARTBEAT_INTERVAL_S,
                )
                return
            except TimeoutError:
                _emit_chat_ack(host, request_id)
                log_event(
                    logger,
                    logging.DEBUG,
                    "backend_chat_heartbeat",
                    request_id=request_id,
                    session_id=host.session_id,
                )

    heartbeat_task = asyncio.create_task(_chat_heartbeat())

    try:
        if not host._session_titled:
            title = message[:60] + ("..." if len(message) > 60 else "")
            host.session_store.update_session(host.session_id, title=title)
            host._session_titled = True

        message = host._expand_file_mentions(message)

        layer_used, request_type_name, force_l4 = host._select_chat_layer(message)
        log_event(
            logger,
            logging.INFO,
            "backend_chat_route_selected",
            request_id=request_id,
            session_id=host.session_id,
            force_l4=force_l4,
            request_type=request_type_name,
            selected_layer=layer_used,
            has_l2_context=bool(host._context_assembler),
            has_l3_provider=bool(host._l3_provider),
        )

        if layer_used == 1:
            try:
                from autocode.layer1.queries import DeterministicQueryHandler

                handler = DeterministicQueryHandler(project_root=host.project_root)
                response = handler.handle(message)
                host.emit_notification("on_token", {"text": response.content})
                host.emit_notification(
                    "on_done",
                    {
                        **_done_params(host, 1),
                        "layer_used": 1,
                    },
                )
                return
            except ImportError:
                layer_used = 4

        log_event(
            logger,
            logging.INFO,
            "backend_chat_agent_loop_init_start",
            request_id=request_id,
            session_id=host.session_id,
        )
        try:
            agent_loop = host._ensure_agent_loop()
            agent_loop.session_id = host.session_id
        except Exception as exc:  # noqa: BLE001 - surface as frontend error
            logger.exception("Error initializing agent loop: %s", exc)
            host.emit_notification("on_error", {"message": str(exc)})
            host.emit_notification("on_done", _done_params(host, layer_used))
            return
        log_event(
            logger,
            logging.INFO,
            "backend_chat_agent_loop_init_done",
            request_id=request_id,
            session_id=host.session_id,
        )

        if layer_used == 2:
            try:
                from autocode.agent.tools import _code_index_cache
                from autocode.layer2.rules import RulesLoader
                from autocode.layer2.search import HybridSearch

                if _code_index_cache is None:
                    layer_used = 4
                else:
                    search = HybridSearch(_code_index_cache)
                    top_k = host.config.layer2.search_top_k
                    results = search.search(message, top_k=top_k)
                    rules_loader = RulesLoader()
                    rules_text = rules_loader.load(host.project_root)
                    assembled = host._context_assembler.assemble(
                        message,
                        rules=rules_text,
                        search_results=results,
                    )
                    log_event(
                        logger,
                        logging.INFO,
                        "backend_chat_layer2_start",
                        request_id=request_id,
                        session_id=host.session_id,
                    )
                    await agent_loop.run(
                        message,
                        on_chunk=lambda text: on_chunk(host, text),
                        on_thinking_chunk=lambda text: on_thinking_chunk(host, text),
                        on_retry_notice=lambda text: emit_warning(host, text),
                        on_tool_call=lambda tool_name, status, result="": on_tool_call(
                            host, tool_name, status, result
                        ),
                        approval_callback=lambda tool_name, arguments: approval_callback(
                            host, tool_name, arguments
                        ),
                        ask_user_callback=lambda question, options, allow_text: ask_user_callback(
                            host, question, options, allow_text
                        ),
                        injected_context=assembled,
                    )
                    host._emit_cost_update()
                    host.emit_notification(
                        "on_done",
                        {
                            **_done_params(host, 2),
                            "layer_used": 2,
                        },
                    )
                    return
            except ImportError:
                layer_used = 4
            except Exception as exc:  # noqa: BLE001 - deliberate fallback to layer 4
                log_event(
                    logger,
                    logging.WARNING,
                    "backend_chat_layer2_fallback",
                    request_id=request_id,
                    session_id=host.session_id,
                    error=str(exc),
                )
                layer_used = 4

        if layer_used == 3:
            try:
                log_event(
                    logger,
                    logging.INFO,
                    "backend_chat_layer3_start",
                    request_id=request_id,
                    session_id=host.session_id,
                )
                result_text = await host._l3_provider.generate(message)
                host.session_store.add_message(host.session_id, "user", message)
                host.session_store.add_message(host.session_id, "assistant", result_text)
                host.emit_notification("on_token", {"text": result_text})
                host.emit_notification(
                    "on_done",
                    {
                        **_done_params(host, 3),
                        "layer_used": 3,
                    },
                )
                return
            except Exception as exc:  # noqa: BLE001 - deliberate fallback to layer 4
                log_event(
                    logger,
                    logging.WARNING,
                    "backend_chat_layer3_fallback",
                    request_id=request_id,
                    session_id=host.session_id,
                    error=str(exc),
                )
                layer_used = 4

        try:
            log_event(
                logger,
                logging.INFO,
                "backend_chat_layer4_start",
                request_id=request_id,
                session_id=host.session_id,
            )
            await agent_loop.run(
                message,
                on_chunk=lambda text: on_chunk(host, text),
                on_thinking_chunk=lambda text: on_thinking_chunk(host, text),
                on_retry_notice=lambda text: emit_warning(host, text),
                on_tool_call=lambda tool_name, status, result="": on_tool_call(
                    host, tool_name, status, result
                ),
                approval_callback=lambda tool_name, arguments: approval_callback(
                    host, tool_name, arguments
                ),
                ask_user_callback=lambda question, options, allow_text: ask_user_callback(
                    host, question, options, allow_text
                ),
            )
        except asyncio.CancelledError:
            host._emit_cost_update()
            host.emit_notification("on_done", _done_params(host, layer_used, cancelled=True))
            return
        except Exception as exc:  # noqa: BLE001 - surface as frontend error
            logger.exception("Error in handle_chat: %s", exc)
            host.emit_notification("on_error", {"message": str(exc)})

        host._emit_cost_update()
        host.emit_notification("on_done", _done_params(host, layer_used))
    finally:
        heartbeat_stop.set()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
