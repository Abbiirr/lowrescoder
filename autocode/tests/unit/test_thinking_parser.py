"""Streaming parser tests for provider-emitted <think> tags."""

from __future__ import annotations

from autocode.layer4.thinking_parser import StreamingThinkTagParser


def test_tag_split_across_chunks() -> None:
    """Split open/close tags must not leak partial tag text to content."""
    parser = StreamingThinkTagParser()

    content, thinking = parser.feed("answer prefix <thi")
    assert content == "answer prefix "
    assert thinking == ""

    content, thinking = parser.feed("nk>hidden reason</thi")
    assert content == ""
    assert thinking == "hidden reason"

    content, thinking = parser.feed("nk> final answer")
    assert content == " final answer"
    assert thinking == ""

    content, thinking = parser.finish()
    assert content == ""
    assert thinking == ""


def test_multiple_think_blocks_route_text_to_correct_channels() -> None:
    parser = StreamingThinkTagParser()

    content, thinking = parser.feed("a<think>b</think>c<think>d</think>e")

    assert content == "ace"
    assert thinking == "bd"


def test_unclosed_tag_flushes_remaining_thinking_on_finish() -> None:
    parser = StreamingThinkTagParser()

    content, thinking = parser.feed("before <think>reasoning</thi")
    assert content == "before "
    assert thinking == "reasoning"

    content, thinking = parser.finish()
    assert content == ""
    assert thinking == "</thi"
