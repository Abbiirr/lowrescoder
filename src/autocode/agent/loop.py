"""Agent loop: LLM <-> tool execution cycle."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from autocode.agent.approval import ApprovalManager
from autocode.agent.context import ContextEngine
from autocode.agent.event_recorder import EventRecorder
from autocode.agent.prompts import build_system_prompt
from autocode.agent.tools import ToolRegistry
from autocode.core.logging import log_debug_prompt, log_event
from autocode.layer4.llm import LLMResponse, ToolCall
from autocode.session.store import SessionStore
from autocode.session.task_store import TaskStore

logger = logging.getLogger(__name__)


class AgentMode(Enum):
    """Execution mode for the agent loop."""
    NORMAL = "normal"
    PLANNING = "planning"


class AgentLoop:
    """Runs the LLM <-> tool execution cycle up to MAX_ITERATIONS."""

    MAX_ITERATIONS = 10

    def __init__(
        self,
        provider: Any,
        tool_registry: ToolRegistry,
        approval_manager: ApprovalManager,
        session_store: SessionStore,
        session_id: str,
        memory_content: str | None = None,
        context_engine: ContextEngine | None = None,
        task_store: TaskStore | None = None,
        event_recorder: EventRecorder | None = None,
        subagent_manager: Any | None = None,
        memory_context: str = "",
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.approval_manager = approval_manager
        self.session_store = session_store
        self.session_id = session_id
        self._memory_content = memory_content
        self._context_engine = context_engine
        self._task_store = task_store
        self._event_recorder = event_recorder
        self._subagent_manager = subagent_manager
        self._memory_context = memory_context
        self._current_episode_id: str | None = None
        self._cancelled = False
        self._mode: AgentMode = AgentMode.NORMAL

    def set_mode(self, mode: AgentMode) -> None:
        """Set the agent execution mode (normal or planning)."""
        self._mode = mode
        logger.info("Agent mode set to %s", mode.value)

    def get_mode(self) -> AgentMode:
        """Get the current agent execution mode."""
        return self._mode

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current runtime state."""
        task_summary = ""
        if self._task_store:
            task_summary = self._task_store.summary()
        subagent_status = ""
        if self._subagent_manager and hasattr(self._subagent_manager, "get_status_summary"):
            subagent_status = self._subagent_manager.get_status_summary()
        return build_system_prompt(
            self._memory_content,
            shell_enabled=self.approval_manager.shell_config.enabled,
            approval_mode=self.approval_manager.mode.value,
            task_summary=task_summary,
            subagent_status=subagent_status,
            plan_mode=self._mode == AgentMode.PLANNING,
            memory_context=self._memory_context,
        )

    def cancel(self) -> None:
        """Cancel the current run."""
        self._cancelled = True

    async def run(
        self,
        user_message: str,
        *,
        on_chunk: Callable[[str], None] | None = None,
        on_thinking_chunk: Callable[[str], None] | None = None,
        on_tool_call: Callable[[str, str, str], None] | None = None,
        approval_callback: Callable[[str, dict[str, Any]], Awaitable[bool]] | None = None,
        ask_user_callback: Callable[[str, list[str], bool], Awaitable[str]] | None = None,
        injected_context: str = "",
    ) -> str:
        """Run the agent loop for a user message.

        Args:
            user_message: The user's input text.
            on_chunk: Called with text chunks as they stream.
            on_thinking_chunk: Called with thinking/reasoning chunks.
            on_tool_call: Called with (tool_name, status, result) for display.
            approval_callback: Async callable for user approval. Returns bool.
            ask_user_callback: Async callable when the LLM invokes ask_user.
                Receives (question, options, allow_text), returns user's answer.

        Returns:
            The final assistant text response.
        """
        self._cancelled = False
        _run_start = time.monotonic()
        logger.debug("AgentLoop.run start: %s", user_message[:80])

        # Store user message
        self.session_store.add_message(self.session_id, "user", user_message)

        # Training-grade episode tracking
        if self._event_recorder:
            self._current_episode_id = self._event_recorder.on_turn_start(user_message)
        _episode_id = self._current_episode_id

        # Build messages from session history (rebuild prompt for current state)
        tool_schemas = self.tool_registry.get_schemas_openai_format()
        if self._context_engine:
            task_summary = self._task_store.summary() if self._task_store else ""
            messages = await self._context_engine.build_messages(
                self.session_id,
                self._build_system_prompt(),
                tool_schemas,
                task_summary=task_summary,
            )
        else:
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": self._build_system_prompt()},
            ]
            for msg in self.session_store.get_messages(self.session_id):
                if msg.role in ("user", "assistant", "system", "tool"):
                    messages.append({"role": msg.role, "content": msg.content})
        if injected_context:
            messages.insert(1, {"role": "system", "content": injected_context})
        logger.debug("Loaded %d tool schemas, %d messages", len(tool_schemas), len(messages))
        log_event(
            logger, logging.INFO, "agent_loop_start",
            session_id=self.session_id,
            user_message_length=len(user_message),
            message_count=len(messages),
            tool_count=len(tool_schemas),
        )

        for _iteration in range(self.MAX_ITERATIONS):
            if self._cancelled:
                logger.debug("Cancelled at iteration %d", _iteration)
                if self._event_recorder and _episode_id:
                    self._event_recorder.on_turn_end(_episode_id, "[Cancelled]", "cancelled", {})
                return "[Cancelled]"

            # Call LLM with tools
            logger.debug("Iteration %d: calling generate_with_tools", _iteration)
            log_event(
                logger, logging.INFO, "llm_request",
                session_id=self.session_id,
                iteration=_iteration,
                provider=getattr(self.provider, "model", "unknown"),
            )
            if self._event_recorder and _episode_id:
                self._event_recorder.on_model_request(
                    _episode_id, messages, tool_schemas, _iteration,
                )
            _llm_start = time.monotonic()
            response: LLMResponse = await self.provider.generate_with_tools(
                messages, tool_schemas,
                on_chunk=on_chunk,
                on_thinking_chunk=on_thinking_chunk,
            )
            _llm_ms = int((time.monotonic() - _llm_start) * 1000)
            logger.debug(
                "LLM response: content=%s, tool_calls=%d, reasoning=%s",
                bool(response.content), len(response.tool_calls), bool(response.reasoning),
            )
            log_event(
                logger, logging.INFO, "llm_response",
                session_id=self.session_id,
                iteration=_iteration,
                duration_ms=_llm_ms,
                content_length=len(response.content or ""),
                tool_calls_count=len(response.tool_calls),
                finish_reason=response.finish_reason,
            )
            if self._event_recorder and _episode_id:
                self._event_recorder.on_model_response(
                    _episode_id, response, _llm_ms, _iteration,
                )
            else:
                log_debug_prompt(self.session_id, messages, response)

            # If text-only response (no tool calls), we're done
            if not response.tool_calls:
                text = response.content or ""
                self.session_store.add_message(self.session_id, "assistant", text)
                logger.debug("Text-only response, returning (%d chars)", len(text))
                _total_ms = int((time.monotonic() - _run_start) * 1000)
                log_event(
                    logger, logging.INFO, "agent_loop_end",
                    session_id=self.session_id,
                    iterations=_iteration + 1,
                    total_duration_ms=_total_ms,
                    outcome="text_response",
                )
                if self._event_recorder and _episode_id:
                    self._event_recorder.on_turn_end(
                        _episode_id, text, "text_response",
                        {"iterations": _iteration + 1, "total_duration_ms": _total_ms},
                    )
                return text

            # Process tool calls
            # First, add assistant message with tool calls to history
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                }
                for tc in response.tool_calls
            ]
            messages.append(assistant_msg)

            msg_id = self.session_store.add_message(
                self.session_id, "assistant", response.content or "(tool calls)"
            )

            for tc in response.tool_calls:
                result = await self._execute_tool_call(
                    tc, msg_id,
                    on_tool_call=on_tool_call,
                    approval_callback=approval_callback,
                    ask_user_callback=ask_user_callback,
                )
                # Add tool result to messages for the next iteration
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        # Max iterations reached — get final text response without tools
        log_event(
            logger, logging.WARNING, "agent_loop_max_iterations",
            session_id=self.session_id,
            iterations=self.MAX_ITERATIONS,
        )
        final_text = response.content or "[Max iterations reached]"
        self.session_store.add_message(self.session_id, "assistant", final_text)
        _total_ms = int((time.monotonic() - _run_start) * 1000)
        log_event(
            logger, logging.INFO, "agent_loop_end",
            session_id=self.session_id,
            iterations=self.MAX_ITERATIONS,
            total_duration_ms=_total_ms,
            outcome="max_iterations",
        )
        if self._event_recorder and _episode_id:
            self._event_recorder.on_turn_end(
                _episode_id, final_text, "max_iterations",
                {"iterations": self.MAX_ITERATIONS, "total_duration_ms": _total_ms},
            )
        return final_text

    async def _handle_ask_user(
        self,
        tc: ToolCall,
        msg_id: int,
        *,
        on_tool_call: Callable[[str, str, str], None] | None = None,
        callback: Callable[[str, list[str], bool], Awaitable[str]] | None = None,
    ) -> str:
        """Handle the ask_user tool call via interactive callback."""
        question = tc.arguments.get("question", "")
        options = tc.arguments.get("options", [])
        allow_text = tc.arguments.get("allow_text", False)
        logger.debug("ask_user: q=%s, opts=%s, text=%s", question[:50], options, allow_text)

        if on_tool_call:
            on_tool_call(tc.name, "waiting", question)

        if callback is None:
            result = "ask_user requires an interactive UI (no callback provided)."
            if on_tool_call:
                on_tool_call(tc.name, "error", result)
            return result

        # Record tool call
        tc_row_id = self.session_store.add_tool_call(
            session_id=self.session_id,
            message_id=msg_id,
            tool_call_id=tc.id,
            tool_name=tc.name,
            arguments=tc.arguments,
            status="waiting",
        )

        try:
            response = await callback(question, options, allow_text)
            response_str = str(response) if response else "(no response from user)"
            self.session_store.update_tool_call(
                tc_row_id, result=response_str, status="completed", duration_ms=0,
            )
            self.session_store.add_message(
                self.session_id, "tool", f"[ask_user] User answered: {response_str}",
            )
            if self._event_recorder and self._current_episode_id:
                self._event_recorder.on_human_feedback(
                    self._current_episode_id, "ask_user_response", response_str,
                )
            if on_tool_call:
                on_tool_call(tc.name, "completed", response_str)
            return f"User responded: {response_str}"
        except Exception as e:
            error = f"Error in ask_user: {e}"
            self.session_store.update_tool_call(
                tc_row_id, result=error, status="error", duration_ms=0,
            )
            if on_tool_call:
                on_tool_call(tc.name, "error", error)
            return error

    async def _execute_tool_call(
        self,
        tc: ToolCall,
        msg_id: int,
        *,
        on_tool_call: Callable[[str, str, str], None] | None = None,
        approval_callback: Callable[[str, dict[str, Any]], Awaitable[bool]] | None = None,
        ask_user_callback: Callable[[str, list[str], bool], Awaitable[str]] | None = None,
    ) -> str:
        """Execute a single tool call with approval checking."""
        # Special handling for ask_user — route to interactive callback
        if tc.name == "ask_user":
            logger.debug("Routing to ask_user handler")
            return await self._handle_ask_user(
                tc, msg_id, on_tool_call=on_tool_call, callback=ask_user_callback,
            )

        logger.debug("Executing tool: %s(%s)", tc.name, list(tc.arguments.keys()))
        if self._event_recorder and self._current_episode_id:
            self._event_recorder.on_tool_call(
                self._current_episode_id, tc.name, tc.arguments, tc.id,
            )
        log_event(
            logger, logging.INFO, "tool_call_start",
            session_id=self.session_id,
            tool_name=tc.name,
            argument_keys=list(tc.arguments.keys()),
        )
        tool = self.tool_registry.get(tc.name)
        if tool is None:
            error = f"Unknown tool: {tc.name}"
            if on_tool_call:
                on_tool_call(tc.name, "error", error)
            return error

        # Plan mode: block tools with mutates_fs or executes_shell
        if self._mode == AgentMode.PLANNING:
            if tool and (tool.mutates_fs or tool.executes_shell):
                reason = (
                    f"Blocked in plan mode: {tc.name} modifies filesystem or "
                    "executes shell. Use /plan approve to switch to execution mode."
                )
                log_event(
                    logger, logging.INFO, "tool_blocked_plan_mode",
                    session_id=self.session_id, tool_name=tc.name,
                )
                if on_tool_call:
                    on_tool_call(tc.name, "blocked", reason)
                return reason

        # Check if blocked
        blocked, reason = self.approval_manager.is_blocked(tc.name, tc.arguments)
        if blocked:
            log_event(
                logger, logging.WARNING, "tool_blocked",
                session_id=self.session_id, tool_name=tc.name, reason=reason,
            )
            if on_tool_call:
                on_tool_call(tc.name, "blocked", reason)
            return f"Blocked: {reason}"

        # Check if write is blocked in read-only mode
        if self.approval_manager.is_write_blocked(tc.name):
            reason = "Write operations are not allowed in read-only mode."
            if on_tool_call:
                on_tool_call(tc.name, "blocked", reason)
            return f"Blocked: {reason}"

        # Check if shell needs enabling (soft block — user can approve)
        shell_needs_enabling = (
            tc.name == "run_command"
            and self.approval_manager.is_shell_disabled()
        )

        # Check approval (merged with shell-enable prompt)
        if self.approval_manager.needs_approval(tool) or shell_needs_enabling:
            if approval_callback:
                approved = await approval_callback(tc.name, tc.arguments)
                if not approved:
                    log_event(
                        logger, logging.WARNING, "tool_denied",
                        session_id=self.session_id, tool_name=tc.name,
                    )
                    if self._event_recorder and self._current_episode_id:
                        self._event_recorder.on_human_feedback(
                            self._current_episode_id, "denial", tc.name,
                        )
                    if on_tool_call:
                        on_tool_call(tc.name, "denied", "User denied")
                    return "Tool call denied by user."
                if self._event_recorder and self._current_episode_id:
                    self._event_recorder.on_human_feedback(
                        self._current_episode_id, "approval", tc.name,
                    )
                # Enable shell if user approved a shell command
                if shell_needs_enabling:
                    self.approval_manager.enable_shell()
            else:
                # No callback, deny by default for safety
                if on_tool_call:
                    on_tool_call(tc.name, "denied", "No approval callback")
                return "Tool call requires approval but no callback provided."

        # Record tool call
        tc_row_id = self.session_store.add_tool_call(
            session_id=self.session_id,
            message_id=msg_id,
            tool_call_id=tc.id,
            tool_name=tc.name,
            arguments=tc.arguments,
            status="running",
        )

        if on_tool_call:
            on_tool_call(tc.name, "running", "")

        # Execute
        start = time.monotonic()
        try:
            result = tool.handler(**tc.arguments)
            task_tools = {"create_task", "update_task", "add_task_dependency", "list_tasks"}
            if self._context_engine and tc.name not in task_tools:
                result = self._context_engine.truncate_tool_result(result)
            duration_ms = int((time.monotonic() - start) * 1000)
            self.session_store.update_tool_call(
                tc_row_id, result=result, status="completed", duration_ms=duration_ms,
            )
            log_event(
                logger, logging.INFO, "tool_call_end",
                session_id=self.session_id, tool_name=tc.name,
                duration_ms=duration_ms, status="completed",
            )
            if self._event_recorder and self._current_episode_id:
                self._event_recorder.on_tool_result(
                    self._current_episode_id, tc.name, result, "completed", duration_ms,
                )
            if on_tool_call:
                on_tool_call(tc.name, "completed", result)

            # Also persist tool result as a message for session history
            self.session_store.add_message(
                self.session_id, "tool", f"[{tc.name}] {result[:500]}"
            )
            return result
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            error = f"Error: {e}"
            self.session_store.update_tool_call(
                tc_row_id, result=error, status="error", duration_ms=duration_ms,
            )
            log_event(
                logger, logging.WARNING, "tool_call_end",
                session_id=self.session_id, tool_name=tc.name,
                duration_ms=duration_ms, status="error",
            )
            if self._event_recorder and self._current_episode_id:
                self._event_recorder.on_tool_result(
                    self._current_episode_id, tc.name, error, "error", duration_ms,
                )
            if on_tool_call:
                on_tool_call(tc.name, "error", error)
            return error
