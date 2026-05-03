"""Scratch storage for large tool outputs."""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRATCH_THRESHOLD_BYTES = 5_000
HEADER_LINES_KEPT = 5
SUMMARY_MAX_CHARS = 300
SCRATCH_NEVER_FOR = {"todo_read", "ask_user", "memory_index_show"}
SCRATCH_ALWAYS_FOR = {"web_fetch", "git_log"}
SCRATCH_STUB_PREFIX = "[Tool output offloaded"


def scratch_disabled() -> bool:
    return os.environ.get("AUTOCODE_DISABLE_SCRATCH", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def is_scratch_stub(result: str) -> bool:
    return result.lstrip().startswith(SCRATCH_STUB_PREFIX)


@dataclass(slots=True)
class ScratchOffload:
    tool_name: str
    result_bytes: int
    path: str
    summary: str


class ScratchStore:
    """Persist large tool output and return a compact context stub."""

    def __init__(self, root: str | Path, *, thread_id: str) -> None:
        self.root = Path(root)
        self.thread_id = _safe_segment(thread_id)
        self.last_offload: ScratchOffload | None = None

    def offload_if_large(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: str,
        *,
        turn_id: str,
    ) -> str:
        self.last_offload = None
        if scratch_disabled() or tool_name in SCRATCH_NEVER_FOR:
            return result

        result_bytes = len(result.encode("utf-8", errors="replace"))
        if tool_name not in SCRATCH_ALWAYS_FOR and result_bytes < SCRATCH_THRESHOLD_BYTES:
            return result

        turn_dir = self.root / self.thread_id / _safe_segment(turn_id)
        turn_dir.mkdir(parents=True, exist_ok=True)
        output_path = turn_dir / f"{_next_sequence(turn_dir):03d}-{_safe_segment(tool_name)}.md"
        output_path.write_text(result, encoding="utf-8")

        summary = _compute_summary(tool_name, args, result)
        offload = ScratchOffload(
            tool_name=tool_name,
            result_bytes=result_bytes,
            path=str(output_path),
            summary=summary,
        )
        self._append_manifest(turn_dir, offload)
        self.last_offload = offload
        return _format_stub(offload, result)

    def cleanup_after_n_turns(self, *, current_turn_count: int, keep_n: int = 10) -> None:
        thread_dir = self.root / self.thread_id
        if not thread_dir.exists():
            return
        keep_names = {
            f"turn-{idx:03d}"
            for idx in range(max(0, current_turn_count - keep_n), current_turn_count)
        }
        for turn_dir in sorted(path for path in thread_dir.iterdir() if path.is_dir()):
            if turn_dir.name not in keep_names:
                shutil.rmtree(turn_dir, ignore_errors=True)

    def _append_manifest(self, turn_dir: Path, offload: ScratchOffload) -> None:
        manifest_path = turn_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                manifest = {"offloads": []}
        else:
            manifest = {"offloads": []}
        manifest.setdefault("offloads", []).append({
            "tool_name": offload.tool_name,
            "result_bytes": offload.result_bytes,
            "path": offload.path,
            "summary": offload.summary,
        })
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _compute_summary(tool_name: str, args: dict[str, Any], result: str) -> str:
    lines = [line for line in result.splitlines() if line.strip()]
    if tool_name == "list_files":
        directory = str(args.get("path") or args.get("directory") or ".")
        return _clip_summary(f"{len(lines)} entries in {directory}")
    if tool_name == "git_log":
        commit_count = sum(1 for line in lines if line.startswith("commit "))
        return _clip_summary(f"{commit_count or len(lines)} commits")
    if tool_name == "web_fetch":
        url = str(args.get("url") or args.get("uri") or "")
        prefix = f"{url}: " if url else ""
        return _clip_summary(f"{prefix}{len(result.encode('utf-8', errors='replace'))} bytes")
    if tool_name == "grep_content":
        pattern = str(args.get("pattern") or "")
        return _clip_summary(f"{len(lines)} matches for {pattern!r}")
    return _clip_summary(lines[0] if lines else "(empty output)")


def _clip_summary(summary: str) -> str:
    if len(summary) <= SUMMARY_MAX_CHARS:
        return summary
    return summary[: SUMMARY_MAX_CHARS - 3].rstrip() + "..."


def _format_stub(offload: ScratchOffload, result: str) -> str:
    preview = "\n".join(result.splitlines()[:HEADER_LINES_KEPT])
    return (
        f"{SCRATCH_STUB_PREFIX} — {offload.result_bytes} bytes saved to {offload.path}]\n\n"
        f"Summary: {offload.summary}\n\n"
        "First 5 lines:\n"
        "```\n"
        f"{preview}\n"
        "```\n"
        "Use read_file on the path above to see the full output."
    )


def _next_sequence(turn_dir: Path) -> int:
    existing = [
        int(match.group(1))
        for path in turn_dir.glob("*.md")
        if (match := re.match(r"^(\d+)-", path.name))
    ]
    return max(existing, default=0) + 1


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "unknown"
