"""Tests for structured logging system."""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from pathlib import Path

import pytest

from hybridcoder.config import LoggingConfig
from hybridcoder.core.logging import (
    JSONFormatter,
    log_debug_prompt,
    log_event,
    setup_logging,
)


class TestJSONFormatter:
    """Test JSONFormatter produces valid JSON with expected fields."""

    def test_basic_record_is_valid_json(self) -> None:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "hello world"
        assert "ts" in data

    def test_event_data_merged_into_output(self) -> None:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="my_event",
            args=(),
            exc_info=None,
        )
        record.event_data = {"session_id": "abc", "duration_ms": 42}  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert data["event"] == "my_event"
        assert data["session_id"] == "abc"
        assert data["duration_ms"] == 42

    def test_no_event_data_means_no_event_key(self) -> None:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="plain message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "event" not in data

    def test_ts_is_iso_format(self) -> None:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="ts test",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        # Should contain 'T' separator and timezone info
        assert "T" in data["ts"]


class TestSetupLogging:
    """Test setup_logging configures handlers correctly."""

    def setup_method(self) -> None:
        """Clean up root logger before each test."""
        root = logging.getLogger()
        root.handlers.clear()

    def test_creates_console_handler_on_stderr(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"), file_enabled=False)
        setup_logging(config)
        root = logging.getLogger()
        stream_handlers = [
            h for h in root.handlers if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) == 1
        assert stream_handlers[0].stream is sys.stderr

    def test_no_handler_writes_to_stdout(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"))
        setup_logging(config)
        root = logging.getLogger()
        for handler in root.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                assert handler.stream is not sys.stdout

    def test_creates_file_handler_when_enabled(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"))
        setup_logging(config)
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        assert (tmp_path / "logs" / "hybridcoder.jsonl").exists()

    def test_no_file_handler_when_disabled(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"), file_enabled=False)
        setup_logging(config)
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 0

    def test_file_rotation_config(self, tmp_path: Path) -> None:
        config = LoggingConfig(
            log_dir=str(tmp_path / "logs"),
            max_file_size_mb=20,
            max_files=3,
        )
        setup_logging(config)
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        assert file_handlers[0].maxBytes == 20 * 1024 * 1024
        assert file_handlers[0].backupCount == 3

    def test_verbose_sets_console_to_debug(self, tmp_path: Path) -> None:
        config = LoggingConfig(
            log_dir=str(tmp_path / "logs"),
            file_enabled=False,
            console_level="WARNING",
        )
        setup_logging(config, verbose=True)
        root = logging.getLogger()
        console = [
            h for h in root.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        assert console[0].level == logging.DEBUG

    def test_third_party_loggers_silenced(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"), file_enabled=False)
        setup_logging(config)
        for name in ("httpx", "httpcore", "openai", "ollama", "urllib3"):
            assert logging.getLogger(name).level >= logging.WARNING


class TestDebugPromptsLogger:
    """Test debug_prompts logger isolation."""

    def setup_method(self) -> None:
        root = logging.getLogger()
        root.handlers.clear()
        debug_logger = logging.getLogger("hybridcoder.debug_prompts")
        debug_logger.handlers.clear()

    def test_debug_prompts_logger_does_not_propagate(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"), debug_prompts=True)
        setup_logging(config)
        debug_logger = logging.getLogger("hybridcoder.debug_prompts")
        assert debug_logger.propagate is False

    def test_debug_prompts_file_created_when_enabled(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"), debug_prompts=True)
        setup_logging(config)
        debug_logger = logging.getLogger("hybridcoder.debug_prompts")
        assert len(debug_logger.handlers) == 1
        # Write something to create the file
        log_debug_prompt("sess1", [{"role": "user", "content": "hi"}], "response")
        assert (tmp_path / "logs" / "debug-prompts.jsonl").exists()

    def test_debug_prompts_no_handler_when_disabled(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"), debug_prompts=False)
        setup_logging(config)
        debug_logger = logging.getLogger("hybridcoder.debug_prompts")
        assert len(debug_logger.handlers) == 0


class TestLogEvent:
    """Test log_event attaches structured data."""

    def test_event_data_in_record(self, tmp_path: Path) -> None:
        config = LoggingConfig(log_dir=str(tmp_path / "logs"))
        setup_logging(config)
        test_logger = logging.getLogger("test.event")

        # Read back from the JSON log file
        log_event(
            test_logger,
            logging.INFO,
            "test_event",
            session_id="s1",
            duration_ms=100,
        )

        # Flush handlers
        for h in logging.getLogger().handlers:
            h.flush()

        log_file = tmp_path / "logs" / "hybridcoder.jsonl"
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        found = False
        for line in lines:
            data = json.loads(line)
            if data.get("event") == "test_event":
                assert data["session_id"] == "s1"
                assert data["duration_ms"] == 100
                found = True
                break
        assert found, "test_event not found in log file"
