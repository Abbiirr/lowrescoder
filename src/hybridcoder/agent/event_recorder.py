"""Training-grade event recorder for AgentLoop.

All public methods are fail-open: errors are logged as warnings
but never propagate to the caller.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from hybridcoder.session.episode_store import EpisodeStore

logger = logging.getLogger(__name__)


class EventRecorder:
    """Captures training-grade events during AgentLoop execution."""

    def __init__(self, episode_store: EpisodeStore) -> None:
        self._store = episode_store

    def on_turn_start(self, user_message: str) -> str | None:
        """Start a new episode for this turn. Returns episode_id or None on failure."""
        try:
            return self._store.start_episode(user_message)
        except Exception:
            logger.warning("EventRecorder.on_turn_start failed, continuing", exc_info=True)
            return None

    def on_model_request(
        self,
        episode_id: str,
        messages: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
        iteration: int,
    ) -> None:
        """Record a model request event with full messages and tool schemas."""
        try:
            messages_str = json.dumps(messages, default=str)
            schemas_str = json.dumps(tool_schemas, default=str)
            data = {
                "messages": self._store._externalize_value(messages_str),
                "tool_schemas": self._store._externalize_value(schemas_str),
                "iteration": iteration,
            }
            self._store.add_event(episode_id, "model_request", data)
        except Exception:
            logger.warning("EventRecorder.on_model_request failed, continuing", exc_info=True)

    def on_model_response(
        self,
        episode_id: str,
        response: Any,
        duration_ms: int,
        iteration: int,
    ) -> None:
        """Record a model response event."""
        try:
            content = getattr(response, "content", None) or ""
            reasoning = getattr(response, "reasoning", None) or ""
            tool_calls_raw = getattr(response, "tool_calls", [])
            finish_reason = getattr(response, "finish_reason", None)
            usage = getattr(response, "usage", None)

            tool_calls = [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in tool_calls_raw
            ]

            data: dict[str, Any] = {
                "content": self._store._externalize_value(content),
                "tool_calls": tool_calls,
                "finish_reason": finish_reason,
                "duration_ms": duration_ms,
                "iteration": iteration,
            }
            if reasoning:
                data["reasoning"] = self._store._externalize_value(reasoning)
            if usage:
                data["usage"] = usage if isinstance(usage, dict) else str(usage)
            self._store.add_event(episode_id, "model_response", data)
        except Exception:
            logger.warning("EventRecorder.on_model_response failed, continuing", exc_info=True)

    def on_tool_call(
        self,
        episode_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str,
    ) -> None:
        """Record a tool call event."""
        try:
            args_str = json.dumps(arguments, default=str)
            data = {
                "tool_name": tool_name,
                "arguments": self._store._externalize_value(args_str),
                "tool_call_id": tool_call_id,
            }
            self._store.add_event(episode_id, "tool_call", data)
        except Exception:
            logger.warning("EventRecorder.on_tool_call failed, continuing", exc_info=True)

    def on_tool_result(
        self,
        episode_id: str,
        tool_name: str,
        result: str,
        status: str,
        duration_ms: int,
    ) -> None:
        """Record a tool result event."""
        try:
            data = {
                "tool_name": tool_name,
                "result": self._store._externalize_value(result),
                "status": status,
                "duration_ms": duration_ms,
            }
            self._store.add_event(episode_id, "tool_result", data)
        except Exception:
            logger.warning("EventRecorder.on_tool_result failed, continuing", exc_info=True)

    def on_human_feedback(
        self,
        episode_id: str,
        feedback_type: str,
        detail: str,
    ) -> None:
        """Record a human feedback event (approval/denial/ask_user_response)."""
        try:
            data = {
                "feedback_type": feedback_type,
                "detail": detail,
            }
            self._store.add_event(episode_id, "human_feedback", data)
        except Exception:
            logger.warning("EventRecorder.on_human_feedback failed, continuing", exc_info=True)

    def on_human_edit(
        self,
        episode_id: str,
        draft_text: str,
        edited_text: str,
    ) -> None:
        """Record a human edit event for DPO-grade provenance."""
        try:
            data = {
                "draft_text": self._store._externalize_value(draft_text),
                "edited_text": self._store._externalize_value(edited_text),
                "edit_source": "user",
            }
            self._store.add_event(episode_id, "human_edit", data)
        except Exception:
            logger.warning("EventRecorder.on_human_edit failed, continuing", exc_info=True)

    def on_turn_end(
        self,
        episode_id: str,
        final_text: str,
        outcome: str,
        metrics: dict,
    ) -> None:
        """Record the final answer and close the episode."""
        try:
            # Emit final_answer event
            data = {
                "text": self._store._externalize_value(final_text),
                "token_count": max(1, len(final_text) // 4),
            }
            self._store.add_event(episode_id, "final_answer", data)
            # Close the episode
            self._store.end_episode(episode_id, outcome, metrics)
        except Exception:
            logger.warning("EventRecorder.on_turn_end failed, continuing", exc_info=True)
