"""Base types and protocol for agent adapters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class BenchmarkTask:
    """A single benchmark task to solve."""

    task_id: str
    description: str
    repo: str = ""
    difficulty: str = ""
    language: str = ""
    category: str = ""
    setup_commands: list[str] = field(default_factory=list)
    grading_command: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BenchmarkTask:
        known = {
            "task_id", "description", "repo", "difficulty",
            "language", "category", "setup_commands", "grading_command",
        }
        kwargs = {k: v for k, v in d.items() if k in known}
        extra = {k: v for k, v in d.items() if k not in known}
        return cls(**kwargs, extra=extra)


@dataclass
class BudgetProfile:
    """Resource budget for a benchmark run."""

    wall_time_s: int = 600
    token_cap: int = 50_000
    max_tool_calls: int = 100

    @property
    def profile_id(self) -> str:
        return f"wt{self.wall_time_s}_tc{self.token_cap}_mc{self.max_tool_calls}"


@dataclass
class AgentResult:
    """Result from a single task solved by an agent."""

    task_id: str
    resolved: bool
    score: float = 0.0
    wall_time_s: float = 0.0
    tool_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    error: str = ""
    output: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AgentAdapter(Protocol):
    """Interface for agent adapters."""

    @property
    def name(self) -> str:
        """Agent name (e.g. 'autocode', 'codex', 'claude-code')."""
        ...

    @property
    def version(self) -> str:
        """Agent/tool version string."""
        ...

    @property
    def provider_mode(self) -> str:
        """Cost mode: 'local_free', 'subscription', or 'paid_metered'."""
        ...

    @property
    def model(self) -> str:
        """Model identifier used by this agent."""
        ...

    async def solve_task(
        self,
        task: BenchmarkTask,
        sandbox: Path,
        budget: BudgetProfile,
    ) -> AgentResult:
        """Run the agent on a single task in the given sandbox directory."""
        ...


def compute_manifest_hash(manifest_path: Path) -> str:
    """Compute SHA-256 hash of a manifest file for reproducibility."""
    content = manifest_path.read_bytes()
    return f"sha256:{hashlib.sha256(content).hexdigest()[:16]}"


def load_manifest(manifest_path: Path) -> tuple[dict[str, Any], list[BenchmarkTask]]:
    """Load a benchmark manifest JSON and return (meta, tasks)."""
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)
    meta = data.get("_meta", {})
    tasks = [BenchmarkTask.from_dict(t) for t in data.get("tasks", [])]
    return meta, tasks
