"""Training data exporter — generates SFT/DPO/Eval JSONL from episode store.

Stub implementation: full export logic deferred to a training sprint.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from autocode.core.blob_store import BlobStore
from autocode.session.episode_store import EpisodeStore

logger = logging.getLogger(__name__)


def _resolve(resolver, ref: object) -> str:
    """Resolve a blob ref or inline value. Falls back to str()."""
    if isinstance(ref, dict):
        return resolver(ref)
    return str(ref)


class TrainingExporter:
    """Generates SFT/DPO/Eval JSONL from episode store."""

    def __init__(self, episode_store: EpisodeStore, blob_store: BlobStore) -> None:
        self._episodes = episode_store
        self._blobs = blob_store

    def _resolve_ref(self, ref: dict) -> str:
        """Resolve a blob reference or inline value to its full string."""
        if "inline" in ref:
            return ref["inline"]
        sha = ref.get("blob_sha256")
        if sha:
            content = self._blobs.get(sha)
            return content if content is not None else ref.get("preview", "")
        return str(ref)

    def _parse_event_data(self, ev: dict) -> dict:
        """Parse event data from JSON string or return as-is."""
        data = ev["data"]
        if isinstance(data, str):
            return json.loads(data)
        return data

    def _extract_messages(self, data: dict) -> list[dict] | None:
        """Extract prompt messages from a model_request event."""
        msgs_ref = data.get("messages", {})
        raw = _resolve(self._resolve_ref, msgs_ref)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return [{"role": "user", "content": raw}]

    def export_sft(
        self,
        output_path: Path,
        session_ids: list[str] | None = None,
    ) -> int:
        """Export SFT training data.

        For each completed episode:
          1. Get model_request messages (resolve blobs)
          2. Get final_answer text as completion
          3. Write {"prompt": [...], "completion": [...]}

        Returns the number of examples written.
        """
        count = 0
        episodes = self._episodes.list_episodes()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for ep in episodes:
                if ep.get("outcome") not in ("text_response", "max_iterations"):
                    continue

                events = self._episodes.get_episode_events(ep["id"])
                prompt_messages = None
                final_text = None

                for ev in events:
                    data = self._parse_event_data(ev)
                    if ev["event_type"] == "model_request" and prompt_messages is None:
                        prompt_messages = self._extract_messages(data)
                    elif ev["event_type"] == "final_answer":
                        text_ref = data.get("text", {})
                        final_text = _resolve(self._resolve_ref, text_ref)

                if prompt_messages and final_text:
                    example = {
                        "prompt": prompt_messages,
                        "completion": [
                            {"role": "assistant", "content": final_text},
                        ],
                    }
                    f.write(json.dumps(example) + "\n")
                    count += 1

        logger.info("Exported %d SFT examples to %s", count, output_path)
        return count

    def export_dpo(
        self,
        output_path: Path,
        session_ids: list[str] | None = None,
    ) -> int:
        """Export DPO training data from episodes with human_edit events.

        For episodes with human_edit events:
          1. prompt = messages from first model_request
          2. rejected = human_edit.draft_text
          3. chosen = human_edit.edited_text
          4. Write {"prompt": [...], "chosen": [...], "rejected": [...]}

        Returns the number of examples written.
        """
        count = 0
        episodes = self._episodes.list_episodes()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for ep in episodes:
                events = self._episodes.get_episode_events(ep["id"])
                prompt_messages = None
                edits: list[tuple[str, str]] = []

                for ev in events:
                    data = self._parse_event_data(ev)
                    if ev["event_type"] == "model_request" and prompt_messages is None:
                        prompt_messages = self._extract_messages(data)
                    elif ev["event_type"] == "human_edit":
                        draft_ref = data.get("draft_text", {})
                        edited_ref = data.get("edited_text", {})
                        draft = _resolve(self._resolve_ref, draft_ref)
                        edited = _resolve(self._resolve_ref, edited_ref)
                        edits.append((draft, edited))

                if prompt_messages and edits:
                    for draft, edited in edits:
                        example = {
                            "prompt": prompt_messages,
                            "chosen": [
                                {"role": "assistant", "content": edited},
                            ],
                            "rejected": [
                                {"role": "assistant", "content": draft},
                            ],
                        }
                        f.write(json.dumps(example) + "\n")
                        count += 1

        logger.info("Exported %d DPO examples to %s", count, output_path)
        return count

    def export_eval(
        self,
        output_path: Path,
        session_ids: list[str] | None = None,
    ) -> int:
        """Export evaluation data — full event sequences + metrics.

        Returns the number of episodes written.
        """
        count = 0
        episodes = self._episodes.list_episodes()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for ep in episodes:
                events = self._episodes.get_episode_events(ep["id"])
                raw_metrics = ep.get("metrics", "{}")
                if isinstance(raw_metrics, str):
                    metrics = json.loads(raw_metrics)
                else:
                    metrics = raw_metrics
                record = {
                    "episode_id": ep["id"],
                    "session_id": ep["session_id"],
                    "outcome": ep.get("outcome"),
                    "metrics": metrics,
                    "events": [
                        {
                            "event_type": ev["event_type"],
                            "timestamp": ev["timestamp"],
                            "data": self._parse_event_data(ev),
                        }
                        for ev in events
                    ],
                }
                f.write(json.dumps(record) + "\n")
                count += 1

        logger.info("Exported %d eval episodes to %s", count, output_path)
        return count
