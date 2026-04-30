"""Tier 4.4-compatible NDJSON event schema for headless --json mode.

Every event carries ``protocol_version: "0.1.0-c6g5-subset"``.
The ``type`` discriminator selects the event shape.
``item.kind`` is constrained to the C6.G5 forward-compatible subset.
"""

from __future__ import annotations

import json
import sys
from enum import Enum
from typing import Any, Literal, TextIO

from pydantic import BaseModel, ConfigDict, Field


PROTOCOL_VERSION = "0.1.0-c6g5-subset"


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


EventType = (
    ThreadStartedEvent
    | TurnStartedEvent
    | ItemStartedEvent
    | ItemDeltaEvent
    | ItemCompletedEvent
    | TurnCompletedEvent
    | ErrorEvent
)

_EVENT_UNION_MAP: dict[str, type[EventType]] = {
    "thread_started": ThreadStartedEvent,
    "turn_started": TurnStartedEvent,
    "item_started": ItemStartedEvent,
    "item_delta": ItemDeltaEvent,
    "item_completed": ItemCompletedEvent,
    "turn_completed": TurnCompletedEvent,
    "error": ErrorEvent,
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
