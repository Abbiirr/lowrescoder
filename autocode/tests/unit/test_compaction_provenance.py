"""Stable TUI v1 Slice 5 — tests for compaction provenance (Milestone D minimal).

Additive-only: existing CompactionResult fields are preserved and default
behavior is unchanged. The new `provenance` field labels each included
message so file- or tool-sourced text cannot silently pose as user
instruction after summarization.
"""

from __future__ import annotations

import pytest

from autocode.agent.remote_compaction import (
    COMPACTION_SYSTEM_PROMPT,
    CompactionResult,
    Provenance,
    classify_message_provenance,
    format_messages_for_compaction,
)


def test_compaction_result_has_provenance_field_default_empty() -> None:
    result = CompactionResult(
        summary="x",
        original_token_count=10,
        summary_token_count=5,
        messages_compacted=3,
    )
    assert result.provenance == {}


def test_compaction_result_provenance_roundtrip_dict() -> None:
    result = CompactionResult(
        summary="",
        original_token_count=0,
        summary_token_count=0,
        messages_compacted=0,
        provenance={"msg-0": Provenance.USER, "msg-1": Provenance.TOOL_OUTPUT},
    )
    assert result.provenance["msg-0"] == Provenance.USER
    assert result.provenance["msg-1"] == Provenance.TOOL_OUTPUT


def test_provenance_enum_members() -> None:
    assert Provenance.USER == "user"
    assert Provenance.TOOL_OUTPUT == "tool"
    assert Provenance.FILE_CONTENT == "file"
    assert Provenance.ASSISTANT == "assistant"
    assert Provenance.SYSTEM == "system"
    assert Provenance.UNKNOWN == "unknown"


def test_classify_user_message_is_user() -> None:
    msg = {"role": "user", "content": "please do a thing"}
    assert classify_message_provenance(msg) == Provenance.USER


def test_classify_assistant_message_is_assistant() -> None:
    msg = {"role": "assistant", "content": "ok"}
    assert classify_message_provenance(msg) == Provenance.ASSISTANT


def test_classify_tool_role_is_tool() -> None:
    msg = {"role": "tool", "content": "exit 0"}
    assert classify_message_provenance(msg) == Provenance.TOOL_OUTPUT


def test_classify_system_message_is_system() -> None:
    msg = {"role": "system", "content": "You are..."}
    assert classify_message_provenance(msg) == Provenance.SYSTEM


def test_classify_tool_result_content_structure_is_tool() -> None:
    # OpenAI tool-call result shape: {"role": "tool", "tool_call_id": ..., "content": ...}
    msg = {"role": "tool", "tool_call_id": "abc", "content": "ok"}
    assert classify_message_provenance(msg) == Provenance.TOOL_OUTPUT


def test_classify_file_hint_user_content_still_user() -> None:
    # Even if user mentions a file path, the role stays user — provenance
    # labels the ORIGIN not the topic.
    msg = {"role": "user", "content": "please look at /etc/passwd"}
    assert classify_message_provenance(msg) == Provenance.USER


def test_classify_unknown_role_falls_back_to_unknown() -> None:
    msg = {"role": "weird", "content": "x"}
    assert classify_message_provenance(msg) == Provenance.UNKNOWN


def test_format_messages_labels_each_line_with_origin() -> None:
    messages = [
        {"role": "user", "content": "prompt"},
        {"role": "tool", "content": "tool output"},
        {"role": "assistant", "content": "reply"},
    ]
    formatted = format_messages_for_compaction(messages, include_provenance=True)
    # Each line starts with a provenance-labeled role
    assert "[origin: user]" in formatted
    assert "[origin: tool]" in formatted
    assert "[origin: assistant]" in formatted


def test_format_messages_default_preserves_legacy_behavior() -> None:
    messages = [
        {"role": "user", "content": "prompt"},
        {"role": "tool", "content": "tool output"},
    ]
    # Default (no include_provenance kwarg) should match pre-Slice-5 format.
    formatted = format_messages_for_compaction(messages)
    assert "[origin:" not in formatted
    assert "[user]" in formatted or "user" in formatted.lower()


def test_system_prompt_mentions_provenance_when_requested() -> None:
    # The compaction system prompt should include guidance about provenance
    # so file- or tool-sourced text can't become instruction text silently.
    assert "provenance" in COMPACTION_SYSTEM_PROMPT.lower() or (
        "origin" in COMPACTION_SYSTEM_PROMPT.lower()
    )


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("user", Provenance.USER),
        ("assistant", Provenance.ASSISTANT),
        ("tool", Provenance.TOOL_OUTPUT),
        ("system", Provenance.SYSTEM),
        ("", Provenance.UNKNOWN),
    ],
)
def test_classify_message_provenance_table(role: str, expected: Provenance) -> None:
    assert classify_message_provenance({"role": role, "content": "x"}) == expected
