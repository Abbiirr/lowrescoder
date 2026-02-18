"""Regression guard for the Phase 5 roadmap lock policy document."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_phase5_roadmap_lock_checklist_exists() -> None:
    path = _repo_root() / "docs/plan/phase5-roadmap-lock-checklist.md"
    assert path.exists(), "Roadmap lock checklist must exist."


def test_phase5_roadmap_lock_checklist_has_required_sections() -> None:
    path = _repo_root() / "docs/plan/phase5-roadmap-lock-checklist.md"
    content = path.read_text(encoding="utf-8")

    required_markers = [
        "## 1. Purpose",
        "## 2. Lock States",
        "## 3. Evidence Packs (Mandatory)",
        "## 4. Stage-Specific Non-Regression Gates",
        "## 5. Comms Resolution Rule",
        "## 6. Ownership and Execution",
        "## 7. Current Open Blockers",
        "Do not archive roadmap threads until:",
        "Current state: `PROVISIONAL_LOCKED`.",
    ]

    for marker in required_markers:
        assert marker in content, f"Missing required marker in lock checklist: {marker}"
