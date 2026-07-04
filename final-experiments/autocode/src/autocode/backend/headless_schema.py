"""Tier 4.4-compatible NDJSON event schema for headless --json mode.

Every event carries ``protocol_version: "0.2.0-harness"``.
The ``type`` discriminator selects the event shape.
``item.kind`` is constrained to the C6.G5 forward-compatible subset.
Structured tool events (``tool_call_started/completed/failed``) provide
first-class tool-execution evidence for the AI verification harness.
"""

from __future__ import annotations

import json
import sys
from enum import Enum
from typing import Any, Literal, TextIO

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_VERSION = "0.2.0-harness"


class ItemType(str, Enum):
    AGENT_MESSAGE = "agent_message"
    TOOL_EXECUTION = "tool_execution"
    PLAN_UPDATE = "plan_update"
    APPROVAL = "approval"


RESERVED_ITEM_KINDS = frozenset({"reasoning", "subagent_delegation", "diff"})
VALID_ITEM_KINDS = frozenset(e.value for e in ItemType)


class UsageBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0
    cache_creation_tokens: int = 0
    reasoning_tokens: int = 0


class _EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    protocol_version: str = PROTOCOL_VERSION
    type: str


class ThreadStartedEvent(_EventBase):
    type: Literal["thread_started"] = "thread_started"
    thread_id: str = ""
    session_id: str = ""


class TurnStartedEvent(_EventBase):
    type: Literal["turn_started"] = "turn_started"
    turn_id: str = ""
    thread_id: str = ""
    message: str = ""


class ItemStartedEvent(_EventBase):
    type: Literal["item_started"] = "item_started"
    item_id: str = ""
    turn_id: str = ""
    kind: str

    def model_post_init(self, __context: Any) -> None:
        if self.kind not in VALID_ITEM_KINDS:
            msg = (
                f"Invalid item.kind: {self.kind!r}. "
                f"Must be one of {sorted(VALID_ITEM_KINDS)}. "
                f"Reserved for future: {sorted(RESERVED_ITEM_KINDS)}."
            )
            raise ValueError(msg)


class ItemDeltaEvent(_EventBase):
    type: Literal["item_delta"] = "item_delta"
    item_id: str = ""
    delta: str = ""


class ItemCompletedEvent(_EventBase):
    type: Literal["item_completed"] = "item_completed"
    item_id: str = ""
    result: str | None = None


class TurnCompletedEvent(_EventBase):
    type: Literal["turn_completed"] = "turn_completed"
    turn_id: str = ""
    thread_id: str = ""
    usage: UsageBlock = Field(default_factory=UsageBlock)


class ErrorEvent(_EventBase):
    type: Literal["error"] = "error"
    message: str = ""
    code: str | None = None


TOOL_FAMILY_MAP: dict[str, str] = {
    "read_file": "file_read",
    "list_files": "file_read",
    "glob_files": "file_read",
    "write_file": "file_write",
    "edit_file": "file_write",
    "apply_patch": "file_write",
    "multi_edit": "file_write",
    "search_text": "search",
    "grep_content": "search",
    "search_code": "search",
    "semantic_search": "search",
    "find_definition": "lsp",
    "find_references": "lsp",
    "get_type_info": "lsp",
    "list_symbols": "lsp",
    "run_command": "shell",
    "git_status": "git",
    "git_diff": "git",
    "git_log": "git",
    "todo_read": "planning",
    "todo_write": "planning",
    "create_task": "planning",
    "update_task": "planning",
    "list_tasks": "planning",
    "spawn_subagent": "subagent",
    "check_subagent": "subagent",
    "cancel_subagent": "subagent",
    "list_subagents": "subagent",
    "ask_user": "user_interaction",
    "list_tool_results": "cache",
    "clear_tool_result": "cache",
    "clear_tool_results": "cache",
}


def tool_family(tool_name: str) -> str:
    return TOOL_FAMILY_MAP.get(tool_name, "unknown")


class ArgsShape(BaseModel):
    model_config = ConfigDict(extra="allow")

    args_shape: dict[str, str] = {}
    args_sha256: str = ""
    result_bytes: int = 0
    result_sha256: str = ""
    result_preview: str = ""


class ToolCallStartedEvent(_EventBase):
    type: Literal["tool_call_started"] = "tool_call_started"
    thread_id: str = ""
    turn_id: str = ""
    item_id: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    tool_family: str = ""
    started_at: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.tool_name:
            raise ValueError("tool_call_started requires non-empty tool_name")
        if not self.tool_call_id:
            raise ValueError("tool_call_started requires non-empty tool_call_id")
        if not self.started_at:
            raise ValueError("tool_call_started requires non-empty started_at")


class ToolCallCompletedEvent(_EventBase):
    type: Literal["tool_call_completed"] = "tool_call_completed"
    thread_id: str = ""
    turn_id: str = ""
    item_id: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    tool_family: str = ""
    status: Literal["success", "error"] = "success"
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    args_shape: dict[str, str] = {}
    args_sha256: str = ""
    result_bytes: int = 0
    result_sha256: str = ""
    result_preview: str = ""
    error_type: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.tool_name:
            raise ValueError("tool_call_completed requires non-empty tool_name")
        if not self.tool_call_id:
            raise ValueError("tool_call_completed requires non-empty tool_call_id")
        if not self.started_at:
            raise ValueError("tool_call_completed requires non-empty started_at")
        if not self.finished_at:
            raise ValueError("tool_call_completed requires non-empty finished_at")


class ToolCallFailedEvent(_EventBase):
    type: Literal["tool_call_failed"] = "tool_call_failed"
    thread_id: str = ""
    turn_id: str = ""
    item_id: str = ""
    tool_call_id: str = ""
    tool_name: str = ""
    tool_family: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    error_type: str = ""
    error_message: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.tool_name:
            raise ValueError("tool_call_failed requires non-empty tool_name")
        if not self.tool_call_id:
            raise ValueError("tool_call_failed requires non-empty tool_call_id")
        if not self.started_at:
            raise ValueError("tool_call_failed requires non-empty started_at")
        if not self.finished_at:
            raise ValueError("tool_call_failed requires non-empty finished_at")


EventType = (
    ThreadStartedEvent
    | TurnStartedEvent
    | ItemStartedEvent
    | ItemDeltaEvent
    | ItemCompletedEvent
    | TurnCompletedEvent
    | ErrorEvent
    | ToolCallStartedEvent
    | ToolCallCompletedEvent
    | ToolCallFailedEvent
)

_EVENT_UNION_MAP: dict[str, type[EventType]] = {
    "thread_started": ThreadStartedEvent,
    "turn_started": TurnStartedEvent,
    "item_started": ItemStartedEvent,
    "item_delta": ItemDeltaEvent,
    "item_completed": ItemCompletedEvent,
    "turn_completed": TurnCompletedEvent,
    "error": ErrorEvent,
    "tool_call_started": ToolCallStartedEvent,
    "tool_call_completed": ToolCallCompletedEvent,
    "tool_call_failed": ToolCallFailedEvent,
}


def validate_event(raw: dict[str, Any]) -> EventType:
    t = raw.get("type")
    if t not in _EVENT_UNION_MAP:
        raise ValueError(f"Unknown event type: {t!r}")
    model_cls = _EVENT_UNION_MAP[t]
    return model_cls.model_validate(raw)


def emit_event(event: EventType, *, fp: TextIO | None = None) -> None:
    line = event.model_dump_json() + "\n"
    target = fp or sys.stdout
    target.write(line)
    target.flush()


def collapse_ndjson_to_result(lines: list[str]) -> dict[str, Any]:
    """Fold a stream of NDJSON events into a single ``result`` object.

    This is the clean-room counterpart of puku-cli's ``--output-format json``: the
    same headless run that streams events (stream-json) is summarized into one
    consolidated object with the final agent message, session id, tool-call count,
    usage, and error state. Invalid / blank lines are skipped.
    """
    session_id = ""
    is_error = False
    error_message = ""
    usage: dict[str, Any] = {}
    kinds: dict[str, str] = {}
    texts: dict[str, str] = {}
    order: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(ev, dict):
            continue
        etype = ev.get("type")
        if etype == "thread_started":
            session_id = ev.get("session_id") or session_id
        elif etype == "item_started":
            iid = str(ev.get("item_id", ""))
            kinds[iid] = str(ev.get("kind", ""))
            if iid not in order:
                order.append(iid)
        elif etype == "item_delta":
            iid = str(ev.get("item_id", ""))
            texts[iid] = texts.get(iid, "") + str(ev.get("delta") or "")
            if iid not in order:
                order.append(iid)
        elif etype == "item_completed":
            iid = str(ev.get("item_id", ""))
            if ev.get("result") is not None:
                texts[iid] = str(ev.get("result"))
            if iid not in order:
                order.append(iid)
        elif etype == "turn_completed":
            if isinstance(ev.get("usage"), dict):
                usage = ev["usage"]
        elif etype == "error":
            is_error = True
            error_message = str(ev.get("message") or "")

    agent_text = "".join(texts.get(i, "") for i in order if kinds.get(i) == "agent_message")
    num_tool_calls = sum(1 for i in order if kinds.get(i) == "tool_execution")
    return {
        "type": "result",
        "session_id": session_id,
        "is_error": is_error,
        "result": error_message if is_error else agent_text,
        "num_tool_calls": num_tool_calls,
        "usage": usage,
        "protocol_version": PROTOCOL_VERSION,
    }


def build_usage_from_stats(session_stats: Any) -> UsageBlock:
    usage = UsageBlock()
    if session_stats is None:
        return usage
    tracker = getattr(session_stats, "token_tracker", None)
    if tracker is None:
        return usage
    tokens = tracker.total
    usage.input_tokens = tokens.prompt_tokens
    usage.output_tokens = tokens.completion_tokens
    usage.total_tokens = tokens.prompt_tokens + tokens.completion_tokens
    for field_name in ("cached_input_tokens", "cache_creation_tokens", "reasoning_tokens"):
        val = getattr(tokens, field_name, 0)
        if isinstance(val, int):
            setattr(usage, field_name, val)
    return usage


SCHEMA_METHODS: dict[str, type[BaseModel]] = {
    "thread_started": ThreadStartedEvent,
    "turn_started": TurnStartedEvent,
    "item_started": ItemStartedEvent,
    "item_delta": ItemDeltaEvent,
    "item_completed": ItemCompletedEvent,
    "turn_completed": TurnCompletedEvent,
    "error": ErrorEvent,
    "tool_call_started": ToolCallStartedEvent,
    "tool_call_completed": ToolCallCompletedEvent,
    "tool_call_failed": ToolCallFailedEvent,
    "usage": UsageBlock,
}


def generate_json_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for name, model_cls in SCHEMA_METHODS.items():
        schemas[name] = model_cls.model_json_schema()
    meta: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "valid_event_types": sorted(_EVENT_UNION_MAP.keys()),
        "valid_item_kinds": sorted(VALID_ITEM_KINDS),
        "reserved_item_kinds": sorted(RESERVED_ITEM_KINDS),
    }
    schemas["meta"] = meta
    return schemas


def write_schema_files(out_dir: str) -> list[str]:
    from pathlib import Path

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    schemas = generate_json_schemas()
    written: list[str] = []
    for name, schema_dict in schemas.items():
        file_path = out_path / f"{name}.schema.json"
        file_path.write_text(json.dumps(schema_dict, indent=2) + "\n")
        written.append(str(file_path))
    return written
