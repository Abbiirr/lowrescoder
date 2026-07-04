"""Tests for VCR — record and replay LLM interactions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def cassette_path(tmp_path: Path) -> Path:
    return tmp_path / "test_cassette.jsonl"


@pytest.fixture
def sample_messages() -> list[dict]:
    return [{"role": "user", "content": "Hello, world!"}]


@pytest.fixture
def sample_tools() -> list[dict]:
    return [{"type": "function", "function": {"name": "read_file", "parameters": {}}}]


@pytest.fixture
def sample_response() -> dict:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": "Hi there!"}}
        ]
    }


# ── hash_request ──────────────────────────────────────────────────


def test_hash_request_deterministic(sample_messages, sample_tools):
    from autocode.agent.vcr import VCRRecorder

    h1 = VCRRecorder.hash_request("gpt-4", sample_messages, sample_tools)
    h2 = VCRRecorder.hash_request("gpt-4", sample_messages, sample_tools)
    assert h1 == h2
    assert isinstance(h1, str)
    assert len(h1) == 16  # truncated sha256


def test_hash_request_different_inputs(sample_messages, sample_tools):
    from autocode.agent.vcr import VCRRecorder

    h1 = VCRRecorder.hash_request("gpt-4", sample_messages, sample_tools)
    h2 = VCRRecorder.hash_request("gpt-3.5", sample_messages, sample_tools)
    h3 = VCRRecorder.hash_request(
        "gpt-4", [{"role": "user", "content": "different"}], sample_tools
    )
    assert h1 != h2
    assert h1 != h3
    assert h2 != h3


# ── record & save ─────────────────────────────────────────────────


def test_record_and_save(
    cassette_path, sample_messages, sample_tools, sample_response
):
    from autocode.agent.vcr import VCRRecorder

    recorder = VCRRecorder(cassette_path)
    recorder.record("gpt-4", sample_messages, sample_tools, sample_response, duration_ms=150)
    assert recorder.recording_count == 1

    recorder.save()

    # Verify JSONL format — one JSON object per line
    lines = cassette_path.read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["model"] == "gpt-4"
    assert data["messages"] == sample_messages
    assert data["tools"] == sample_tools
    assert data["response"] == sample_response
    assert data["duration_ms"] == 150
    assert "request_hash" in data


def test_recorder_clears_after_save(
    cassette_path, sample_messages, sample_tools, sample_response
):
    from autocode.agent.vcr import VCRRecorder

    recorder = VCRRecorder(cassette_path)
    recorder.record("gpt-4", sample_messages, sample_tools, sample_response)
    assert recorder.recording_count == 1

    recorder.save()
    assert recorder.recording_count == 0


# ── VCRPlayer ─────────────────────────────────────────────────────


def test_player_loads_cassettes(
    cassette_path, sample_messages, sample_tools, sample_response
):
    from autocode.agent.vcr import VCRPlayer, VCRRecorder

    # Save some cassettes first
    recorder = VCRRecorder(cassette_path)
    recorder.record("gpt-4", sample_messages, sample_tools, sample_response)
    recorder.record(
        "gpt-3.5",
        [{"role": "user", "content": "other"}],
        [],
        {"choices": []},
    )
    recorder.save()

    # Load via player
    player = VCRPlayer(cassette_path)
    assert player.cassette_count == 2


def test_player_lookup_hit(
    cassette_path, sample_messages, sample_tools, sample_response
):
    from autocode.agent.vcr import VCRPlayer, VCRRecorder

    recorder = VCRRecorder(cassette_path)
    recorder.record("gpt-4", sample_messages, sample_tools, sample_response, duration_ms=42)
    recorder.save()

    player = VCRPlayer(cassette_path)
    result = player.lookup("gpt-4", sample_messages, sample_tools)
    assert result is not None
    assert result.response == sample_response
    assert result.model == "gpt-4"
    assert result.duration_ms == 42


def test_player_lookup_miss(
    cassette_path, sample_messages, sample_tools, sample_response
):
    from autocode.agent.vcr import VCRPlayer, VCRRecorder

    recorder = VCRRecorder(cassette_path)
    recorder.record("gpt-4", sample_messages, sample_tools, sample_response)
    recorder.save()

    player = VCRPlayer(cassette_path)
    result = player.lookup("gpt-4", [{"role": "user", "content": "unknown"}], [])
    assert result is None


def test_player_empty_file(tmp_path):
    from autocode.agent.vcr import VCRPlayer

    nonexistent = tmp_path / "does_not_exist.jsonl"
    player = VCRPlayer(nonexistent)
    assert player.cassette_count == 0
