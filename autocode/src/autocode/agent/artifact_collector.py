"""Artifact collection for the AutoCode harness.

Collects evidence during agent execution:
- commands.log: shell commands with timestamps and exit codes
- diff.patch: unified diff of all changes
- verify.json: structured verification results
- risk.md: auto-generated risk summary
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CommandLogEntry:
    """A single command execution record."""

    timestamp: float
    command: str
    exit_code: int
    duration_ms: int
    tool_name: str = ""


class ArtifactCollector:
    """Manages artifact collection for a session."""

    def __init__(self, session_id: str, project_root: Path | None = None) -> None:
        self._session_id = session_id
        self._project_root = project_root or Path.cwd()
        self._artifact_dir = self._project_root / ".autocode" / "artifacts" / session_id
        self._commands: list[CommandLogEntry] = []
        self._files_changed: set[str] = []
        self._tool_calls: int = 0

    @property
    def artifact_dir(self) -> Path:
        return self._artifact_dir

    def ensure_dir(self) -> None:
        self._artifact_dir.mkdir(parents=True, exist_ok=True)

    def log_command(
        self,
        command: str,
        exit_code: int,
        duration_ms: int = 0,
        tool_name: str = "",
    ) -> None:
        """Log a command execution."""
        self._commands.append(
            CommandLogEntry(
                timestamp=time.time(),
                command=command,
                exit_code=exit_code,
                duration_ms=duration_ms,
                tool_name=tool_name,
            )
        )
        self._tool_calls += 1

    def log_file_change(self, path: str) -> None:
        """Record that a file was modified."""
        if isinstance(self._files_changed, set):
            self._files_changed.add(path)
        else:
            self._files_changed = {path}

    def save_commands_log(self) -> Path:
        """Write commands.log to artifact directory."""
        self.ensure_dir()
        path = self._artifact_dir / "commands.log"
        lines = []
        for entry in self._commands:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry.timestamp))
            status = "OK" if entry.exit_code == 0 else f"FAIL({entry.exit_code})"
            lines.append(f"[{ts}] [{status}] [{entry.duration_ms}ms] {entry.command}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def save_diff_patch(self) -> Path | None:
        """Capture git diff and save as diff.patch."""
        self.ensure_dir()
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self._project_root,
                timeout=10,
            )
            if result.stdout.strip():
                path = self._artifact_dir / "diff.patch"
                path.write_text(result.stdout, encoding="utf-8")
                return path
        except (subprocess.SubprocessError, OSError):
            pass
        return None

    def save_verify_json(self, data: dict[str, Any]) -> Path:
        """Save verify.json to artifact directory."""
        self.ensure_dir()
        path = self._artifact_dir / "verify.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def generate_risk_summary(
        self,
        verify_passed: bool | None = None,
    ) -> str:
        """Generate a deterministic risk summary."""
        # Count changes
        diff_stats = self._get_diff_stats()
        files_changed = diff_stats.get("files", 0)
        lines_added = diff_stats.get("added", 0)
        lines_removed = diff_stats.get("removed", 0)

        # Assess risk level
        risk_level = "LOW"
        risk_notes = []

        if files_changed > 10:
            risk_level = "HIGH"
            risk_notes.append(f"Large change: {files_changed} files modified")
        elif files_changed > 5:
            risk_level = "MEDIUM"

        if lines_added + lines_removed > 500:
            risk_level = "HIGH"
            risk_notes.append(f"Large diff: +{lines_added}/-{lines_removed} lines")

        # Check for risky patterns
        failed_cmds = sum(1 for c in self._commands if c.exit_code != 0)
        if failed_cmds > 5:
            risk_level = "HIGH" if risk_level != "HIGH" else risk_level
            risk_notes.append(f"{failed_cmds} commands failed during execution")

        if verify_passed is False:
            risk_level = "HIGH"
            risk_notes.append("Verification did not pass")

        verdict = "GO" if risk_level != "HIGH" and verify_passed is not False else "NO-GO"

        summary = (
            f"## Risk Summary\n"
            f"- Files changed: {files_changed}\n"
            f"- Lines added/removed: +{lines_added}/-{lines_removed}\n"
            f"- Commands executed: {len(self._commands)}\n"
            f"- Failed commands: {failed_cmds}\n"
            f"- Tests: "
            f"{'passed' if verify_passed else 'failed' if verify_passed is False else 'not run'}\n"
            f"- Risk level: {risk_level}\n"
            f"- Reversible: {'yes' if files_changed <= 10 else 'review needed'}\n"
            f"\n## Verdict: {verdict}\n"
        )
        if risk_notes:
            summary += "\n## Notes\n" + "\n".join(f"- {n}" for n in risk_notes) + "\n"

        return summary

    def save_risk_summary(self, verify_passed: bool | None = None) -> Path:
        """Generate and save risk.md."""
        self.ensure_dir()
        summary = self.generate_risk_summary(verify_passed)
        path = self._artifact_dir / "risk.md"
        path.write_text(summary, encoding="utf-8")
        return path

    def _get_diff_stats(self) -> dict[str, int]:
        """Get diff statistics from git."""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self._project_root,
                timeout=10,
            )
            lines = result.stdout.strip().split("\n")
            if not lines:
                return {"files": 0, "added": 0, "removed": 0}
            # Parse last line: " N files changed, X insertions(+), Y deletions(-)"
            last = lines[-1]
            files = added = removed = 0
            for part in last.split(","):
                part = part.strip()
                if "file" in part:
                    files = int(part.split()[0])
                elif "insertion" in part:
                    added = int(part.split()[0])
                elif "deletion" in part:
                    removed = int(part.split()[0])
            return {"files": files, "added": added, "removed": removed}
        except (subprocess.SubprocessError, OSError, ValueError):
            return {"files": 0, "added": 0, "removed": 0}


# --- Artifact-First Resumability (PLAN.md Section 0.5) ---
# Structured handoff packets for reliable resume


@dataclass
class HandoffPacket:
    """A durable handoff packet for session resume."""

    session_id: str
    created_at: float
    summary: str
    checkpoint_id: str
    last_tool: str
    files_in_scope: list[str]


@dataclass
class CompactSummary:
    """Compact summary for memory-constrained resume."""

    session_id: str
    summary: str
    checkpoint_ids: list[str]
    last_turn_tool: str


@dataclass
class CheckpointManifest:
    """Manifest of available checkpoints."""

    session_id: str
    checkpoints: list[str]
    created_at: float


@dataclass
class ResumePacket:
    """Complete resume packet combining all artifacts."""

    handoff: HandoffPacket
    compact_summary: CompactSummary
    manifest: CheckpointManifest
    files_in_scope: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "handoff": {
                "session_id": self.handoff.session_id,
                "created_at": self.handoff.created_at,
                "summary": self.handoff.summary,
                "checkpoint_id": self.handoff.checkpoint_id,
                "last_tool": self.handoff.last_tool,
                "files_in_scope": self.handoff.files_in_scope,
            },
            "compact_summary": {
                "session_id": self.compact_summary.session_id,
                "summary": self.compact_summary.summary,
                "checkpoint_ids": self.compact_summary.checkpoint_ids,
                "last_turn_tool": self.compact_summary.last_turn_tool,
            },
            "manifest": {
                "session_id": self.manifest.session_id,
                "checkpoints": self.manifest.checkpoints,
                "created_at": self.manifest.created_at,
            },
            "files_in_scope": self.files_in_scope,
        }
