"""Run artifact writers for AI verification harness.

Writes the new HFIX artifacts:
  - tool_calls.jsonl  (one structured record per tool execution)
  - turns.json
  - trajectory_report.json
  - run_summary.json

Privacy defaults: args/results are stored as shape + hash + byte count.
Full previews are opt-in via ``AUTOCODE_HARNESS_CAPTURE_TOOL_PREVIEWS=true``.

Secret scrubbing: before computing args_sha256 and result_sha256,
well-known sensitive keys are replaced with ``<redacted>`` to prevent
high-entropy token leakage. Matching is substring/case-insensitive:
any key containing substrings like api_key, token, secret, password,
authorization, gateway_url, litellm, openrouter, anthropic, openai,
credentials, auth_, access_key, private_key, refresh_token, access_token,
or bearer is scrubbed.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SECRET_KEY_SUBSTRINGS = (
    "api_key",
    "apikey",
    "api_secret",
    "apisecret",
    "token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "gateway_url",
    "litellm",
    "openrouter",
    "anthropic",
    "openai",
    "credentials",
    "auth_",
    "access_key",
    "private_key",
    "refresh_token",
    "access_token",
    "bearer",
)


def _scrub_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: "<redacted>" if _is_secret_key(k) else _scrub_secrets(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_secrets(item) for item in obj]
    return obj


def _is_secret_key(key: str) -> bool:
    lower = key.lower()
    for substr in _SECRET_KEY_SUBSTRINGS:
        if substr in lower:
            return True
    return False


def _compute_shape(value: Any, depth: int = 0, max_depth: int = 2) -> str:
    if depth >= max_depth:
        return type(value).__name__
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, list):
        return "list"
    return type(value).__name__


def _args_shape(args: dict[str, Any] | None) -> dict[str, str]:
    if not args:
        return {}
    return {k: _compute_shape(v) for k, v in args.items()}


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _sha256_hex_dict(data: dict | None) -> str:
    if not data:
        return ""
    scrubbed = _scrub_secrets(data)
    canonical = json.dumps(scrubbed, sort_keys=True, separators=(",", ":"))
    return _sha256_hex(canonical)


def _should_capture_previews() -> bool:
    return os.environ.get("AUTOCODE_HARNESS_CAPTURE_TOOL_PREVIEWS", "").lower() in {
        "1", "true", "yes", "on"
    }


def build_tool_call_record(
    *,
    event_type: str,
    thread_id: str,
    turn_id: str,
    item_id: str,
    tool_call_id: str,
    tool_name: str,
    tool_family: str,
    status: str,
    started_at: str,
    finished_at: str = "",
    duration_ms: int = 0,
    args: dict[str, Any] | None = None,
    result: Any = None,
    error_type: str | None = None,
    error_message: str = "",
) -> dict[str, Any]:
    result_bytes = len(str(result).encode("utf-8")) if result else 0
    capture_preview = _should_capture_previews()
    scrubbed_result = _scrub_secrets(result) if isinstance(result, (dict, list)) else result
    record: dict[str, Any] = {
        "protocol_version": "0.2.0-harness",
        "type": event_type,
        "thread_id": thread_id,
        "turn_id": turn_id,
        "item_id": item_id,
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "tool_family": tool_family,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
        "args_shape": _args_shape(args),
        "args_sha256": _sha256_hex_dict(args),
        "result_bytes": result_bytes,
        "result_sha256": _sha256_hex(str(scrubbed_result)) if scrubbed_result else "",
        "result_preview": str(result)[:200] if (capture_preview and result) else "",
        "error_type": error_type,
    }
    if error_message:
        record["error_message"] = error_message[:500]
    return record


def write_tool_calls_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    lines = [json.dumps(r, sort_keys=True) for r in records]
    path.write_text("\n".join(lines) + "\n" if lines else "")


def write_turns_json(turns: list[dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(turns, indent=2, default=str) + "\n")


def write_trajectory_report(report: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(report, indent=2, default=str) + "\n")


def write_run_summary(summary: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(summary, indent=2, default=str) + "\n")
