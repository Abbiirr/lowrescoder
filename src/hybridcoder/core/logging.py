"""Structured logging for HybridCoder.

Provides JSON Lines file output and human-readable console output.
Console writes to stderr only — stdout is reserved for JSON-RPC.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hybridcoder.config import LoggingConfig

# Isolated logger for full LLM prompt/response dumps (opt-in only)
_DEBUG_PROMPTS_LOGGER_NAME = "hybridcoder.debug_prompts"


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects (JSON Lines)."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge structured event_data from log_event() calls
        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict):
            entry["event"] = entry["message"]
            entry.update(event_data)
        return json.dumps(entry, default=str)


def setup_logging(config: LoggingConfig, *, verbose: bool = False) -> None:
    """Configure logging with console (stderr) and file (JSON Lines) handlers.

    Args:
        config: LoggingConfig with level, file path, rotation settings.
        verbose: If True, set console to DEBUG regardless of config.
    """
    root = logging.getLogger()

    # Avoid duplicate handlers on repeated calls
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    # --- Console handler (stderr only — never stdout) ---
    console_level = logging.DEBUG if verbose else getattr(logging, config.console_level)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(console_handler)

    # --- File handler (JSON Lines with rotation) ---
    if config.file_enabled:
        log_dir = Path(config.log_dir).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "hybridcoder.jsonl"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=config.max_file_size_mb * 1024 * 1024,
            backupCount=config.max_files,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, config.file_level))
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)

    # --- Debug prompts handler (isolated logger, opt-in) ---
    debug_logger = logging.getLogger(_DEBUG_PROMPTS_LOGGER_NAME)
    debug_logger.handlers.clear()
    debug_logger.propagate = False  # Never bubble up to root
    if config.debug_prompts and config.file_enabled:
        log_dir = Path(config.log_dir).expanduser()
        prompts_file = log_dir / "debug-prompts.jsonl"
        prompts_handler = logging.handlers.RotatingFileHandler(
            prompts_file,
            maxBytes=config.max_file_size_mb * 1024 * 1024,
            backupCount=config.max_files,
            encoding="utf-8",
        )
        prompts_handler.setLevel(logging.DEBUG)
        prompts_handler.setFormatter(JSONFormatter())
        debug_logger.addHandler(prompts_handler)

    # --- Silence noisy third-party loggers ---
    for name in ("httpx", "httpcore", "openai", "ollama", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **kwargs: Any,
) -> None:
    """Log a structured event with key-value data.

    The JSONFormatter merges kwargs into the JSON output.
    Console formatter shows just the event name as the message.
    """
    logger.log(level, event, extra={"event_data": kwargs})


def log_debug_prompt(
    session_id: str,
    messages: list[dict[str, Any]],
    response: Any,
) -> None:
    """Write full LLM prompt+response to the debug-prompts log.

    Only produces output when debug_prompts is enabled (the logger
    has no handlers otherwise).
    """
    debug_logger = logging.getLogger(_DEBUG_PROMPTS_LOGGER_NAME)
    if not debug_logger.handlers:
        return
    debug_logger.debug(
        "llm_exchange",
        extra={
            "event_data": {
                "session_id": session_id,
                "messages": messages,
                "response": str(response),
            }
        },
    )
