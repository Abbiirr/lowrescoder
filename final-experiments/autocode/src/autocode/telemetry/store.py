"""Append-only local telemetry store."""

from __future__ import annotations

import json
import os
import queue
import shutil
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autocode.telemetry.events import TELEMETRY_EVENT_KINDS, TelemetryEvent

QueuedEvent = tuple[float | datetime, str | None, str | None, str | None, str, dict[str, Any]]


def telemetry_root() -> Path:
    return Path.home() / ".autocode" / "telemetry"


def telemetry_disabled() -> bool:
    return os.environ.get("AUTOCODE_TELEMETRY_DISABLED", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def purge_telemetry(root: Path | None = None) -> None:
    target = root or telemetry_root()
    if target.exists():
        shutil.rmtree(target)


class TelemetryStore:
    """Non-blocking JSONL telemetry writer.

    ``emit`` only enqueues. The background writer owns disk I/O so telemetry
    cannot slow the agent loop under normal operation.
    """

    _STOP = object()

    def __init__(
        self,
        root: Path | None = None,
        max_queue: int = 10_000,
        autostart: bool = True,
    ) -> None:
        self.root = root or telemetry_root()
        self._queue: queue.Queue[QueuedEvent | object] = queue.Queue(maxsize=max_queue)
        self._thread: threading.Thread | None = None
        self._closed = False
        self._disabled = telemetry_disabled()
        self.dropped_count = 0
        if autostart and not self._disabled:
            self.start()

    def start(self) -> None:
        if self._thread is not None:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._thread.start()

    def emit(
        self,
        kind: str,
        *,
        session_id: str | None = None,
        thread_id: str | None = None,
        turn_id: str | None = None,
        data: dict[str, Any] | None = None,
        ts: datetime | None = None,
    ) -> bool:
        if self._closed or self._disabled:
            return False
        if kind not in TELEMETRY_EVENT_KINDS:
            raise ValueError(f"unknown telemetry event kind: {kind}")

        event = (
            ts if ts is not None else time.time(),
            session_id,
            thread_id,
            turn_id,
            kind,
            data or {},
        )
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self.dropped_count += 1
            return False
        return True

    def shutdown(self, timeout: float = 2.0) -> None:
        if self._closed:
            return
        self._closed = True
        if self._thread is None:
            self._drain_sync()
            return
        self._queue.put(self._STOP)
        self._thread.join(timeout=timeout)

    def _drain_sync(self) -> None:
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                return
            if isinstance(item, tuple):
                self._write_event(item)

    def _writer_loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is self._STOP:
                self._drain_sync()
                return
            if isinstance(item, tuple):
                self._write_event(item)

    def _write_event(self, queued: QueuedEvent) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        ts, session_id, thread_id, turn_id, kind, data = queued
        event = TelemetryEvent(
            ts=_format_ts(ts),
            session_id=session_id,
            thread_id=thread_id,
            turn_id=turn_id,
            kind=kind,
            data=data,
        )
        day = event.ts[:10]
        path = self.root / f"events-{day}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), separators=(",", ":")) + "\n")


def _format_ts(value: float | datetime) -> str:
    if isinstance(value, float):
        value = datetime.fromtimestamp(value, UTC)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    else:
        value = value.astimezone(UTC)
    return value.isoformat().replace("+00:00", "Z")
