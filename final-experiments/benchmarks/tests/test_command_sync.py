"""Tests for marker-based command sync helpers."""

from __future__ import annotations

from benchmarks.adapters.command_sync import (
    build_marker_wrapped_command,
    new_command_marker,
    strip_marker_output,
)


def test_new_command_marker_is_unique() -> None:
    marker_a = new_command_marker()
    marker_b = new_command_marker()
    assert marker_a != marker_b
    assert marker_a
    assert marker_b


def test_build_marker_wrapped_command_includes_status_marker() -> None:
    marker = "abc123"
    wrapped = build_marker_wrapped_command("echo hello", marker)
    assert "__AUTOCODE_SYNC__:abc123:" in wrapped
    assert "__autocode_status=$?" in wrapped


def test_strip_marker_output_removes_marker_and_returns_status() -> None:
    output = "hello\nworld\n__AUTOCODE_SYNC__:abc123:7\n"
    cleaned, status = strip_marker_output(output, "abc123")
    assert cleaned == "hello\nworld"
    assert status == 7


def test_strip_marker_output_returns_none_when_missing() -> None:
    cleaned, status = strip_marker_output("plain output", "missing")
    assert cleaned == "plain output"
    assert status is None
