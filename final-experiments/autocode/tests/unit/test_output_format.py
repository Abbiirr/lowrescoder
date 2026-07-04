"""Tests for ``--output-format json|text|stream-json`` (clean-room from puku-cli).

AutoCode's ``exec --json`` emits a *stream* of NDJSON events (puku's stream-json).
puku-cli also offers ``json`` (one consolidated result object) and ``text`` (plain
final message). ``collapse_ndjson_to_result`` folds the event stream into that
single result; the existing ``--json`` / stream-json path is untouched.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from autocode.backend.headless_schema import collapse_ndjson_to_result
from autocode.cli import app
from autocode.config import AutoCodeConfig

runner = CliRunner()

_STREAM = [
    '{"type":"thread_started","session_id":"S1","thread_id":"t1"}',
    '{"type":"turn_started","turn_id":"u1"}',
    '{"type":"item_started","item_id":"i1","kind":"tool_execution"}',
    '{"type":"item_completed","item_id":"i1","result":"ran tool"}',
    '{"type":"item_started","item_id":"i2","kind":"agent_message"}',
    '{"type":"item_delta","item_id":"i2","delta":"Hello "}',
    '{"type":"item_delta","item_id":"i2","delta":"world."}',
    '{"type":"item_completed","item_id":"i2","result":"Hello world."}',
    '{"type":"turn_completed","turn_id":"u1","usage":{"input_tokens":5,"output_tokens":2}}',
]


def test_collapse_extracts_agent_message_and_session() -> None:
    result = collapse_ndjson_to_result(_STREAM)
    assert result["type"] == "result"
    assert result["session_id"] == "S1"
    assert result["result"] == "Hello world."
    assert result["is_error"] is False
    assert result["num_tool_calls"] == 1
    assert result["usage"] == {"input_tokens": 5, "output_tokens": 2}


def test_collapse_uses_deltas_when_no_completed_result() -> None:
    stream = [
        '{"type":"thread_started","session_id":"S2"}',
        '{"type":"item_started","item_id":"a","kind":"agent_message"}',
        '{"type":"item_delta","item_id":"a","delta":"par"}',
        '{"type":"item_delta","item_id":"a","delta":"tial"}',
    ]
    assert collapse_ndjson_to_result(stream)["result"] == "partial"


def test_collapse_reports_error() -> None:
    stream = [
        '{"type":"thread_started","session_id":"S3"}',
        '{"type":"error","message":"boom","code":"x"}',
    ]
    result = collapse_ndjson_to_result(stream)
    assert result["is_error"] is True
    assert "boom" in result["result"]


def test_collapse_ignores_non_json_lines() -> None:
    stream = ["not json", "", '{"type":"thread_started","session_id":"S4"}']
    assert collapse_ndjson_to_result(stream)["session_id"] == "S4"


# --- CLI wiring -------------------------------------------------------------


def _run_exec_with_stream(args: list[str], stream: list[str]):
    captured: dict[str, object] = {}

    def make_runner(**kwargs: object) -> MagicMock:
        captured["out"] = kwargs.get("output")
        m = MagicMock()

        async def run(_prompt: str) -> None:
            out = captured["out"]
            for line in stream:
                out.write(line + "\n")  # type: ignore[union-attr]

        m.run = run
        return m

    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        with patch("autocode.backend.headless_runner.HeadlessRunner", side_effect=make_runner):
            return runner.invoke(app, args)


def test_exec_output_format_json_prints_single_object() -> None:
    result = _run_exec_with_stream(["exec", "hi", "--output-format", "json"], _STREAM)
    assert result.exit_code == 0, result.output
    obj = json.loads(result.stdout)
    assert obj["type"] == "result"
    assert obj["result"] == "Hello world."
    assert obj["session_id"] == "S1"


def test_exec_output_format_text_prints_plain_message() -> None:
    result = _run_exec_with_stream(["exec", "hi", "--output-format", "text"], _STREAM)
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "Hello world."


def test_exec_invalid_output_format_rejected() -> None:
    with patch("autocode.cli.load_config", return_value=AutoCodeConfig()):
        result = runner.invoke(app, ["exec", "hi", "--output-format", "bogus"])
    assert result.exit_code != 0
    assert "output-format" in result.output.lower() or "output format" in result.output.lower()
