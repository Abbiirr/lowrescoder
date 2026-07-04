"""KAIROS proactive-mode substrate.

This module is intentionally inert unless ``AUTOCODE_FEATURE_KAIROS=true`` is
set and a caller explicitly starts a :class:`ProactiveLoop`.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
MAX_SLEEP_MULTIPLIER = 10
TelemetryEmit = Callable[[str, dict[str, Any]], None]


@dataclass(frozen=True)
class TickConfig:
    """Runtime configuration for KAIROS proactive ticks."""

    enabled: bool = False
    base_interval_sec: float = 30.0
    blocking_budget_sec: float = 15.0
    cache_ttl_sec: float = 300.0
    terminal_focus_aware: bool = True


def kairos_enabled_from_env(environ: Mapping[str, str] | None = None) -> bool:
    """Return whether KAIROS is enabled by environment flag."""
    values = os.environ if environ is None else environ
    return values.get("AUTOCODE_FEATURE_KAIROS", "").strip().lower() in TRUE_VALUES


def build_tick_message(*, now: datetime | None = None) -> str:
    """Build the synthetic wake-up message injected between user turns."""
    current = now or datetime.now().astimezone()
    return (
        f"<tick local_time=\"{current.isoformat(timespec='seconds')}\">\n"
        "You're awake. Look for useful work to do. "
        "If there is nothing useful to do, call Sleep.\n"
        "</tick>"
    )


def new_tick_id() -> str:
    """Return a trace id for one KAIROS tick."""
    return str(uuid.uuid4())


def build_tick_rpc_request(
    *,
    request_id: int,
    session_id: str | None,
    tick_id: str,
    message: str,
    read_only: bool,
) -> dict[str, Any]:
    """Build a backend JSON-RPC request for one KAIROS tick.

    AutoCode's ``kairos.tick`` backend route honors ``read_only`` by forcing a
    read-only agent mode for the tick turn. Other recipients must explicitly
    honor this field before treating it as enforcement.
    """
    params: dict[str, Any] = {
        "message": message,
        "session_id": session_id,
        "tick_id": tick_id,
        "read_only": read_only,
    }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "kairos.tick",
        "params": params,
    }


async def send_tick_rpc(
    *,
    host: str,
    port: int,
    session_id: str | None,
    tick_id: str,
    message: str,
    read_only: bool = True,
    request_id: int = 1,
) -> dict[str, Any]:
    """Send one KAIROS tick to an attached TCP JSON-RPC backend."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        request = build_tick_rpc_request(
            request_id=request_id,
            session_id=session_id,
            tick_id=tick_id,
            message=message,
            read_only=read_only,
        )
        writer.write((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
        await writer.drain()
        while True:
            line = await reader.readline()
            if not line:
                return {}
            decoded = json.loads(line.decode("utf-8"))
            if decoded.get("id") == request_id:
                return decoded.get("result", decoded)
    finally:
        writer.close()
        await writer.wait_closed()


def should_skip_for_cost_cap(
    *,
    cost_limit_usd: float | None,
    current_cost_usd: float,
) -> bool:
    """Return True when a daemon tick should be skipped due to cost cap."""
    return cost_limit_usd is not None and current_cost_usd >= cost_limit_usd


def detect_anti_narration(content: str | None, *, tool_calls: list[Any]) -> bool:
    """Return True when a tick response narrates instead of acting or sleeping."""
    return bool((content or "").strip()) and not tool_calls


def kairos_allows_tool(tool: Any, *, user_present: bool) -> bool:
    """KAIROS may not use approval-required tools while the user is absent."""
    return user_present or not bool(getattr(tool, "requires_approval", False))


def default_kairos_audit_log_path() -> Path:
    """Return the default local KAIROS audit log path."""
    return Path.home() / ".autocode" / "kairos_audit.jsonl"


class KairosAuditLog:
    """Append-only local blast-radius log for proactive actions."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_kairos_audit_log_path()

    def record_action(
        self,
        *,
        session_id: str,
        action: str,
        files_changed: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "session_id": session_id,
            "action": action,
            "files_changed": files_changed or [],
            "metadata": metadata or {},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    def read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            records.append(json.loads(line))
        return records


def format_kairos_pulse(records: list[dict[str, Any]], *, limit: int = 5) -> str:
    """Return a compact human-readable summary of recent KAIROS audit activity."""
    if not records:
        return "KAIROS pulse: no audit records yet."

    action_counts: dict[str, int] = {}
    session_ids: set[str] = set()
    changed_files: set[str] = set()
    for record in records:
        action = str(record.get("action") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        session_id = str(record.get("session_id") or "")
        if session_id:
            session_ids.add(session_id)
        for changed in record.get("files_changed") or []:
            if changed:
                changed_files.add(str(changed))

    lines = [
        "KAIROS pulse",
        f"- {len(records)} audit records across {len(session_ids)} sessions",
        f"- {len(changed_files)} unique files changed",
        "- Actions: "
        + ", ".join(
            f"{action}: {count}" for action, count in sorted(action_counts.items())
        ),
    ]

    recent = list(reversed(records[-max(0, limit) :]))
    if recent:
        lines.append("Recent activity:")
        for record in recent:
            metadata = record.get("metadata") or {}
            details = [
                str(record.get("action") or "unknown"),
                f"session={record.get('session_id') or '<none>'}",
            ]
            tick_id = metadata.get("tick_id")
            tool_name = metadata.get("tool_name")
            if tick_id:
                details.append(f"tick={tick_id}")
            if tool_name:
                details.append(f"tool={tool_name}")
            files_changed = record.get("files_changed") or []
            if files_changed:
                details.append(f"files={len(files_changed)}")
            lines.append("- " + " ".join(details))

    return "\n".join(lines)


class ProactiveLoop:
    """Inject periodic KAIROS ticks when enabled.

    The loop owns only scheduling and tick injection. Agent execution remains
    owned by the backend/agent loop that supplies ``inject_tick``.
    """

    def __init__(
        self,
        *,
        config: TickConfig | None = None,
        inject_tick: Callable[[str], Any] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        has_pending_user_input: Callable[[], bool] | None = None,
        telemetry_emit: TelemetryEmit | None = None,
    ) -> None:
        self.config = config or TickConfig()
        self._inject_tick_callback = inject_tick
        self._sleep = sleep
        self._has_pending_user_input = has_pending_user_input or (lambda: False)
        self._telemetry_emit = telemetry_emit
        self._terminal_focused = False
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._tick_in_flight = False
        self._queued_tick = False
        self._requested_sleep_sec: float | None = None
        self.last_sleep_reason: str | None = None

    def start(self) -> bool:
        """Start the background tick loop. Returns False when disabled."""
        if not self.config.enabled or self._task is not None:
            return False
        self._stopping.clear()
        self._task = asyncio.create_task(self._tick_loop())
        return True

    async def stop(self) -> None:
        """Stop the background tick loop."""
        self._stopping.set()
        task = self._task
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    def request_sleep(self, seconds: float, *, reason: str = "") -> float:
        """Request a delay before the next tick, capped at 10x cache TTL."""
        requested = max(0.0, float(seconds))
        capped = min(requested, self.config.cache_ttl_sec * MAX_SLEEP_MULTIPLIER)
        self._requested_sleep_sec = capped
        self.last_sleep_reason = reason or None
        self._emit(
            "kairos_sleep",
            {
                "requested_seconds": requested,
                "granted_seconds": capped,
                "reason": reason,
            },
        )
        return capped

    def consume_requested_sleep(self) -> float | None:
        """Return and clear the pending SleepTool delay."""
        requested = self._requested_sleep_sec
        self._requested_sleep_sec = None
        return requested

    def set_terminal_focused(self, focused: bool) -> None:
        """Record whether the interactive terminal currently has focus."""
        self._terminal_focused = focused

    def should_pause_for_user_input(self) -> bool:
        """Return True when ticks should pause to avoid interrupting typing."""
        return (
            self.config.terminal_focus_aware
            and self._terminal_focused
            and self._has_pending_user_input()
        )

    async def inject_once(self, *, now: datetime | None = None) -> bool:
        """Inject one tick unless paused or another tick is already in flight."""
        if self.should_pause_for_user_input():
            return False
        if self._tick_in_flight:
            self._queued_tick = True
            return False

        self._tick_in_flight = True
        self._queued_tick = False
        try:
            await self._inject_tick(now=now)
            self._emit("kairos_tick", {"coalesced": self._queued_tick})
            return True
        finally:
            self._tick_in_flight = False

    async def _tick_loop(self) -> None:
        while not self._stopping.is_set():
            await self.inject_once()
            delay = self.consume_requested_sleep()
            await self._sleep(delay if delay is not None else self.config.base_interval_sec)

    async def _inject_tick(self, *, now: datetime | None = None) -> None:
        if self._inject_tick_callback is None:
            return
        result = self._inject_tick_callback(build_tick_message(now=now))
        if inspect.isawaitable(result):
            await result

    def _emit(self, kind: str, data: dict[str, Any]) -> None:
        if self._telemetry_emit is not None:
            self._telemetry_emit(kind, data)
