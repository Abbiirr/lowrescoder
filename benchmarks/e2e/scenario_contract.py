"""Scenario contract for E2E benchmarks.

Every E2E scenario must provide a ScenarioManifest that defines:
- Unique scenario ID
- Prompt and follow-ups for the agent
- Acceptance checks (deterministic commands)
- Scoring rubric
- Budget limits
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AcceptanceCheck:
    """A deterministic check to run against the generated project."""

    name: str
    command: str  # Shell command to run (e.g., "npm test")
    timeout_s: int = 120
    required: bool = True  # If True, failure → FAIL verdict
    expect_exit_code: int = 0  # Expected exit code
    expect_output: str | None = None  # Optional regex to match in stdout


@dataclass
class ScenarioManifest:
    """Complete definition of an E2E benchmark scenario."""

    scenario_id: str
    name: str
    description: str

    # Agent prompts
    prompt: str
    follow_ups: list[str] = field(default_factory=list)

    # What the agent should produce
    expected_files: list[str] = field(default_factory=list)
    expected_commands: list[str] = field(default_factory=list)

    # Acceptance checks
    acceptance_checks: list[AcceptanceCheck] = field(default_factory=list)

    # Scoring
    max_score: int = 100
    scoring_categories: dict[str, int] = field(default_factory=dict)

    # Budgets
    max_wall_time_s: int = 1800
    max_tool_calls: int = 100
    max_turns: int = 5

    # Pass criteria
    min_score: int = 30
    strict_min_score: int = 60

    # Metadata
    language: str = "javascript"
    tags: list[str] = field(default_factory=list)

    # Seed / setup
    seed_fixture: Path | None = None  # Path to seed project directory
    setup_commands: list[str] = field(default_factory=list)  # Commands after seeding
    required_artifacts: list[str] = field(default_factory=list)  # Files that must exist after run
    scoring_function: str | None = None  # Dotted path to custom scorer
