"""Plan artifact: export and sync task state as markdown.

Exports task state to `.autocode/plans/<session-id>.md` with
checkboxes and subagent status. Parses checkbox changes back to
update TaskStore status.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Regex: - [x] #<id>: <title> [<status>]
_CHECKBOX_RE = re.compile(
    r"^-\s+\[([x >])\]\s+#(\w+):\s+(.+?)(?:\s+\[(\w+)\])?"
    r"\s*$",
)


def export(
    session_id: str,
    task_store: Any,
    subagent_manager: Any | None = None,
    project_root: Path | str = ".",
) -> Path:
    """Export task state as a markdown plan artifact.

    Creates `.autocode/plans/<session-id>.md` with task checkboxes
    and subagent status.

    Returns the path to the written file.
    """
    project_root = Path(project_root)
    plans_dir = project_root / ".autocode" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    output_path = plans_dir / f"{session_id}.md"

    lines: list[str] = []
    lines.append(f"# Plan: {session_id[:8]}")
    lines.append(f"_Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}_\n")

    # Tasks section
    tasks = task_store.list_tasks()
    if tasks:
        lines.append("## Tasks\n")
        for t in tasks:
            if t.status == "completed":
                check = "x"
            elif t.status == "in_progress":
                check = ">"
            else:
                check = " "
            blocked = task_store.get_blocked_reason(t.id)
            suffix = f" [{blocked}]" if blocked else ""
            lines.append(f"- [{check}] #{t.id}: {t.title}{suffix}")
        lines.append("")

    # Decisions / notes section (placeholder)
    lines.append("## Decisions\n")
    lines.append("_No decisions recorded._\n")

    # Subagent status
    if subagent_manager:
        all_subs = subagent_manager.list_all()
        if all_subs:
            lines.append("## Subagents\n")
            for sa in all_subs:
                lines.append(
                    f"- [{sa['id']} {sa.get('type', '?')}] "
                    f"{sa['status']}: {sa.get('summary', '')[:80]}"
                )
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Plan artifact exported to %s", output_path)
    return output_path


def sync_from_markdown(
    session_id: str,
    task_store: Any,
    markdown_path: Path | str,
) -> list[str]:
    """Parse checkbox states from markdown and update TaskStore.

    Parses lines matching `- [x] #<id>: ...` and updates task status.
    Returns list of updated task IDs.
    """
    markdown_path = Path(markdown_path)
    if not markdown_path.exists():
        raise FileNotFoundError(f"Plan file not found: {markdown_path}")

    text = markdown_path.read_text(encoding="utf-8")
    updated: list[str] = []

    for line in text.splitlines():
        match = _CHECKBOX_RE.match(line.strip())
        if not match:
            continue

        check_char, task_id, _title, _status = match.groups()

        # Map checkbox to status
        if check_char == "x":
            new_status = "completed"
        elif check_char == ">":
            new_status = "in_progress"
        else:
            new_status = "pending"

        # Verify task exists
        task = task_store.get_task(task_id)
        if task is None:
            logger.debug("sync_from_markdown: ignoring unknown task #%s", task_id)
            continue

        if task.status != new_status:
            task_store.update_task(task_id, status=new_status)
            updated.append(task_id)
            logger.debug("sync_from_markdown: #%s -> %s", task_id, new_status)

    return updated
