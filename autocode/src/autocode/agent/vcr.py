"""VCR — record and replay LLM interactions for deterministic testing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class VCRCassette:
    """A recorded LLM interaction."""

    request_hash: str
    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    response: dict[str, Any]
    duration_ms: int = 0


class VCRRecorder:
    """Records LLM interactions to a JSONL file."""

    def __init__(self, cassette_path: Path) -> None:
        self._path = cassette_path
        self._recordings: list[VCRCassette] = []

    @staticmethod
    def hash_request(model: str, messages: list[dict], tools: list[dict]) -> str:
        """Create a deterministic hash of an LLM request."""
        key = json.dumps(
            {"model": model, "messages": messages, "tools": tools}, sort_keys=True
        )
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def record(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict],
        response: dict,
        duration_ms: int = 0,
    ) -> None:
        """Record a request/response pair."""
        cassette = VCRCassette(
            request_hash=self.hash_request(model, messages, tools),
            model=model,
            messages=messages,
            tools=tools,
            response=response,
            duration_ms=duration_ms,
        )
        self._recordings.append(cassette)

    def save(self) -> None:
        """Write all recordings to the cassette file."""
        with self._path.open("a") as f:
            for r in self._recordings:
                json.dump(
                    {
                        "request_hash": r.request_hash,
                        "model": r.model,
                        "messages": r.messages,
                        "tools": r.tools,
                        "response": r.response,
                        "duration_ms": r.duration_ms,
                    },
                    f,
                )
                f.write("\n")
        self._recordings.clear()

    @property
    def recording_count(self) -> int:
        return len(self._recordings)


class VCRPlayer:
    """Replays recorded LLM interactions from a JSONL cassette file."""

    def __init__(self, cassette_path: Path) -> None:
        self._path = cassette_path
        self._cassettes: dict[str, VCRCassette] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                self._cassettes[d["request_hash"]] = VCRCassette(**d)

    def lookup(
        self, model: str, messages: list[dict], tools: list[dict]
    ) -> VCRCassette | None:
        """Look up a recorded response for a request."""
        h = VCRRecorder.hash_request(model, messages, tools)
        return self._cassettes.get(h)

    @property
    def cassette_count(self) -> int:
        return len(self._cassettes)
