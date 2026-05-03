"""RED/GREEN tests for the Tier 4.4 NDJSON headless event schema.

Covers:
  - Well-formed NDJSON: every line includes protocol_version
  - item.kind outside the subset raises ValueError
  - usage block always present on turn_completed, even when all values are 0
  - error event structure
  - validate_event round-trips
  - generate_json_schemas produces valid output
"""

from __future__ import annotations

import json

import pytest

from autocode.backend.headless_schema import (
    PROTOCOL_VERSION,
    VALID_ITEM_KINDS,
    ErrorEvent,
    ItemCompletedEvent,
    ItemDeltaEvent,
    ItemStartedEvent,
    ThreadStartedEvent,
    TurnCompletedEvent,
    TurnStartedEvent,
    UsageBlock,
    validate_event,
    generate_json_schemas,
    write_schema_files,
)


class TestProtocolVersion:
    def test_every_event_carries_protocol_version(self):
        events = [
            ThreadStartedEvent(),
            TurnStartedEvent(),
            ItemStartedEvent(kind="agent_message"),
            ItemDeltaEvent(),
            ItemCompletedEvent(),
            TurnCompletedEvent(),
            ErrorEvent(message="boom"),
        ]
        for event in events:
            raw = json.loads(event.model_dump_json())
            assert raw["protocol_version"] == PROTOCOL_VERSION

    def test_protocol_version_value(self):
        assert PROTOCOL_VERSION == "0.2.0-harness"


class TestItemTypeConstraint:
    def test_valid_kinds_accepted(self):
        for kind in ("agent_message", "tool_execution", "plan_update", "approval"):
            event = ItemStartedEvent(kind=kind)
            assert event.kind == kind

    def test_reserved_kind_rejected(self):
        for kind in ("reasoning", "subagent_delegation", "diff"):
            with pytest.raises(ValueError, match="Invalid item.kind"):
                ItemStartedEvent(kind=kind)

    def test_arbitrary_kind_rejected(self):
        with pytest.raises(ValueError, match="Invalid item.kind"):
            ItemStartedEvent(kind="totally_made_up")

    def test_valid_item_kinds_set(self):
        assert VALID_ITEM_KINDS == {"agent_message", "tool_execution", "plan_update", "approval"}


class TestUsageBlock:
    def test_defaults_all_zero(self):
        usage = UsageBlock()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.total_tokens == 0
        assert usage.cached_input_tokens == 0
        assert usage.cache_creation_tokens == 0
        assert usage.reasoning_tokens == 0

    def test_usage_always_present_on_turn_completed(self):
        event = TurnCompletedEvent()
        raw = json.loads(event.model_dump_json())
        assert "usage" in raw
        usage = raw["usage"]
        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["total_tokens"] == 0
        assert usage["cached_input_tokens"] == 0
        assert usage["cache_creation_tokens"] == 0
        assert usage["reasoning_tokens"] == 0

    def test_usage_with_nonzero_values(self):
        usage = UsageBlock(
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        event = TurnCompletedEvent(usage=usage)
        raw = json.loads(event.model_dump_json())
        assert raw["usage"]["input_tokens"] == 100
        assert raw["usage"]["output_tokens"] == 50
        assert raw["usage"]["total_tokens"] == 150


class TestErrorEvent:
    def test_error_event_structure(self):
        event = ErrorEvent(message="something failed", code="E001")
        raw = json.loads(event.model_dump_json())
        assert raw["type"] == "error"
        assert raw["message"] == "something failed"
        assert raw["code"] == "E001"
        assert raw["protocol_version"] == PROTOCOL_VERSION

    def test_error_event_minimal(self):
        event = ErrorEvent(message="fail")
        raw = json.loads(event.model_dump_json())
        assert raw["type"] == "error"
        assert raw["message"] == "fail"
        assert raw["code"] is None


class TestEventTypes:
    def test_thread_started(self):
        event = ThreadStartedEvent(thread_id="t1", session_id="s1")
        raw = json.loads(event.model_dump_json())
        assert raw["type"] == "thread_started"
        assert raw["thread_id"] == "t1"

    def test_turn_started(self):
        event = TurnStartedEvent(turn_id="turn1", thread_id="t1", message="hi")
        raw = json.loads(event.model_dump_json())
        assert raw["type"] == "turn_started"
        assert raw["message"] == "hi"

    def test_item_delta(self):
        event = ItemDeltaEvent(item_id="i1", delta="hello ")
        raw = json.loads(event.model_dump_json())
        assert raw["type"] == "item_delta"
        assert raw["delta"] == "hello "

    def test_item_completed(self):
        event = ItemCompletedEvent(item_id="i1", result="done")
        raw = json.loads(event.model_dump_json())
        assert raw["type"] == "item_completed"
        assert raw["result"] == "done"


class TestValidateEvent:
    def test_roundtrip_thread_started(self):
        original = ThreadStartedEvent(thread_id="abc", session_id="xyz")
        raw = json.loads(original.model_dump_json())
        recovered = validate_event(raw)
        assert isinstance(recovered, ThreadStartedEvent)
        assert recovered.thread_id == "abc"

    def test_roundtrip_turn_completed(self):
        original = TurnCompletedEvent(turn_id="t1", usage=UsageBlock(input_tokens=10))
        raw = json.loads(original.model_dump_json())
        recovered = validate_event(raw)
        assert isinstance(recovered, TurnCompletedEvent)
        assert recovered.usage.input_tokens == 10

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown event type"):
            validate_event({"type": "unknown_event", "protocol_version": PROTOCOL_VERSION})

    def test_invalid_kind_in_raw_raises(self):
        raw = {
            "type": "item_started",
            "protocol_version": PROTOCOL_VERSION,
            "item_id": "i1",
            "turn_id": "t1",
            "kind": "invalid_kind",
        }
        with pytest.raises(ValueError, match="Invalid item.kind"):
            validate_event(raw)


class TestSchemaGeneration:
    def test_generate_json_schemas_keys(self):
        schemas = generate_json_schemas()
        expected_keys = {
            "thread_started", "turn_started", "item_started", "item_delta",
            "item_completed", "turn_completed", "error", "usage", "meta",
            "tool_call_started", "tool_call_completed", "tool_call_failed",
        }
        assert set(schemas.keys()) == expected_keys

    def test_meta_schema(self):
        schemas = generate_json_schemas()
        meta = schemas["meta"]
        assert meta["protocol_version"] == PROTOCOL_VERSION
        assert "thread_started" in meta["valid_event_types"]
        assert "agent_message" in meta["valid_item_kinds"]
        assert "reasoning" in meta["reserved_item_kinds"]

    def test_write_schema_files(self, tmp_path):
        written = write_schema_files(str(tmp_path / "out"))
        assert len(written) == 12
        for path in written:
            data = json.loads((tmp_path / "out" / path.split("/")[-1]).read_text())
            assert isinstance(data, dict)

    def test_schema_is_valid_json_schema(self):
        schemas = generate_json_schemas()
        for name, schema in schemas.items():
            if name == "meta":
                continue
            assert "properties" in schema or "title" in schema, f"{name} missing schema structure"


class TestExtraFieldsForbidden:
    def test_extra_fields_rejected(self):
        raw = {
            "type": "error",
            "protocol_version": PROTOCOL_VERSION,
            "message": "test",
            "unexpected_field": "oops",
        }
        with pytest.raises(Exception):
            validate_event(raw)
