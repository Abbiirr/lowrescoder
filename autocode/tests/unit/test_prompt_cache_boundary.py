"""Prompt-cache boundary and provider cache-control tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_assemble_system_prompt_keeps_dynamic_values_below_boundary() -> None:
    from autocode.agent.prompts import (
        CACHE_BOUNDARY_MARKER,
        assemble_system_prompt,
        build_dynamic_tail,
        build_stable_prefix,
    )

    stable = build_stable_prefix(
        tool_definitions_json='[{"name":"read_file"}]',
        rules_text="Always test.",
        skill_catalog_index="pytest: testing skill",
    )
    dynamic = build_dynamic_tail(
        cwd="/tmp/project",
        git_status_summary="dirty: app.py",
        current_iso_date="2026-04-30",
        current_todo_state="- [ ] task",
        open_tasks_summary="task-1",
    )
    prompt = assemble_system_prompt(stable=stable, dynamic=dynamic)

    above, below = prompt.split(CACHE_BOUNDARY_MARKER, maxsplit=1)
    assert "read_file" in above
    assert "Always test." in above
    assert "/tmp/project" not in above
    assert "2026-04-30" not in above
    assert "dirty: app.py" not in above
    assert "/tmp/project" in below
    assert "2026-04-30" in below


def test_stable_instructions_include_verify_before_use_discipline() -> None:
    from autocode.agent.prompts import STABLE_INSTRUCTIONS

    assert "Treat ALL such memory as a HINT" in STABLE_INSTRUCTIONS
    assert "re-read" in STABLE_INSTRUCTIONS
    assert "read_file" in STABLE_INSTRUCTIONS
    assert "tool_search" in STABLE_INSTRUCTIONS


def test_serialize_tool_defs_stable_is_deterministic() -> None:
    from autocode.agent.prompts import serialize_tool_defs_stable

    tools = [
        {"function": {"name": "write_file", "parameters": {"b": 2, "a": 1}}},
        {"function": {"name": "read_file", "parameters": {"path": {"type": "string"}}}},
    ]

    first = serialize_tool_defs_stable(tools)
    second = serialize_tool_defs_stable(list(reversed(tools)))

    assert first == second
    assert first.index("read_file") < first.index("write_file")
    assert " " not in first


def test_inject_cache_breakpoint_only_marks_stable_system_block() -> None:
    from autocode.agent.prompts import CACHE_BOUNDARY_MARKER
    from autocode.layer4.llm import _inject_cache_breakpoint

    messages = [
        {
            "role": "system",
            "content": f"stable tools\n\n{CACHE_BOUNDARY_MARKER}\n\ndynamic cwd",
        },
        {"role": "user", "content": "hello"},
    ]

    injected = _inject_cache_breakpoint(messages)

    system = injected[0]
    assert system["role"] == "system"
    assert system["content"][0]["text"] == "stable tools"
    assert system["content"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert "cache_control" not in system["content"][1]
    assert injected[1] == {"role": "user", "content": "hello"}


def test_inject_cache_breakpoint_enforces_four_block_limit() -> None:
    from autocode.layer4.llm import _enforce_cache_control_limit

    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": str(i), "cache_control": {"type": "ephemeral"}}
                for i in range(5)
            ],
        }
    ]

    with pytest.raises(ValueError, match="cache_control"):
        _enforce_cache_control_limit(messages)


def test_provider_support_detection_for_explicit_cache() -> None:
    from autocode.layer4.llm import _supports_explicit_cache

    assert _supports_explicit_cache("anthropic", "claude-3-5-sonnet")
    assert _supports_explicit_cache("openrouter", "anthropic/claude-3.7-sonnet")
    assert _supports_explicit_cache("openrouter", "google/gemini-2.5-pro")
    assert not _supports_explicit_cache("openrouter", "openai/gpt-4.1")
    assert not _supports_explicit_cache("ollama", "llama3.2")


def test_cache_extra_headers_only_for_openrouter_anthropic() -> None:
    from autocode.layer4.llm import _cache_extra_headers

    assert _cache_extra_headers("openrouter", "anthropic/claude-3.7-sonnet") == {
        "anthropic-beta": "prompt-caching-2024-07-31",
    }
    assert _cache_extra_headers("openrouter", "google/gemini-2.5-pro") == {}
    assert _cache_extra_headers("anthropic", "claude-3-5-sonnet") == {}


def test_cache_control_rejection_detection_and_strip() -> None:
    from autocode.layer4.llm import _cache_control_rejected, _strip_cache_control

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "stable",
                    "cache_control": {"type": "ephemeral"},
                }
            ],
        }
    ]

    assert _cache_control_rejected(RuntimeError("provider rejected cache_control"))
    stripped = _strip_cache_control(messages)
    assert "cache_control" not in stripped[0]["content"][0]


def test_ollama_message_fix_treats_cache_control_blocks_as_text_noop() -> None:
    from autocode.layer4.llm import _fix_ollama_messages

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": "stable",
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": "dynamic"},
            ],
        }
    ]

    fixed = _fix_ollama_messages(messages)

    assert fixed == [{"role": "system", "content": "stable\ndynamic"}]


def test_capture_cache_usage_reads_creation_and_reasoning_tokens() -> None:
    from autocode.layer4.llm import _capture_cache_usage

    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=2_000,
            completion_tokens=100,
            prompt_tokens_details=SimpleNamespace(
                cached_tokens=1_250,
                cache_creation_tokens=750,
            ),
            completion_tokens_details=SimpleNamespace(reasoning_tokens=64),
        )
    )

    assert _capture_cache_usage(response) == {
        "prompt_tokens": 2_000,
        "completion_tokens": 100,
        "cached_input_tokens": 1_250,
        "cache_creation_tokens": 750,
        "reasoning_tokens": 64,
    }


@pytest.mark.parametrize(
    ("fixture_name", "expected_cached", "expected_created"),
    [
        ("cache_creation_response.json", 0, 1_500),
        ("cache_read_response.json", 1_500, 0),
    ],
)
def test_cache_usage_cassette_fixtures(
    fixture_name: str,
    expected_cached: int,
    expected_created: int,
) -> None:
    from autocode.layer4.llm import _capture_cache_usage

    fixture_path = (
        Path(__file__).parents[1]
        / "fixtures"
        / "cassettes"
        / fixture_name
    )
    raw = json.loads(fixture_path.read_text())
    response = SimpleNamespace(usage=raw["usage"])

    usage = _capture_cache_usage(response)

    assert usage["cached_input_tokens"] == expected_cached
    assert usage["cache_creation_tokens"] == expected_created
