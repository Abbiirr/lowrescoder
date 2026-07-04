# TASK-001: Core PIV Loop Implementation

## Status: OPEN

## Goal
Implement the `EnhancedPIVStrategy` — a Plan→Implement→Validate loop that outperforms
the baseline autocode strategy on bug-fix benchmark tasks.

This is the core of meta-autocode. Every other component builds on it.

## Background Reading (read these FIRST before writing any code)

1. **autocode's SOP runner** (existing foundation to extend):
   `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/sop_runner.py`
   → Study `SOPPipeline.bugfix()` and `SOPStep` — this is your base class pattern.

2. **autocode's strategy overlays** (hook point for meta-autocode):
   `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/strategy_overlays.py`
   → Understand `StrategyOverlay` dataclass — meta-autocode overlays plug in here.

3. **Codex CLI implementation** (what we're beating):
   `/home/bs01763/projects/ai/autocode-full/research-components/openai-codex/codex-cli/src/`
   → Study Codex's approach. Identify weaknesses to exploit.

4. **autocode agent loop** (integration target):
   `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/loop.py`
   → Understand `AgentLoop` to know how strategies hook in.

## What to Build

### File 1: `src/meta_autocode/__init__.py`
```python
"""meta-autocode: A coding agent harness that beats Codex."""
__version__ = "0.1.0"
```

### File 2: `src/meta_autocode/piv.py`

Implement `EnhancedPIVStrategy` with these phases:

**PLAN phase:**
- Read `task.md` (or equivalent task description file)
- Read all test files (`test_*.py`, `*_test.py`, `verify.sh`, `*.test.ts`)
- Read source files most likely to need changes (use file size + name heuristics)
- Output a structured plan: list of (file, change_description) tuples

**IMPLEMENT phase:**
- Execute plan: make targeted edits to each file
- Use `edit_file` for small changes, `write_file` for rewrites
- Track what was changed

**VALIDATE phase:**
- Run verify.sh if present, else run pytest/test suite
- Check exit code
- If FAIL: collect error output, go back to PLAN with error context (max 3 iterations)
- If PASS: done

**Key difference from baseline autocode:**
- Baseline: reactive (sees error → tries fix → sees error → tries fix)
- PIV: proactive (reads tests FIRST → plans what to change → changes it → verifies)

The PIV approach uses fewer tool calls because it understands the goal before acting.

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class PIVPlan:
    """A structured plan produced by the PLAN phase."""
    task_description: str
    files_to_read: list[str] = field(default_factory=list)
    changes_needed: list[dict[str, str]] = field(default_factory=list)  # [{file, description, reason}]
    test_files: list[str] = field(default_factory=list)
    verify_command: str = "./verify.sh"

@dataclass
class PIVResult:
    """Result of one PIV cycle."""
    phase: str  # "plan", "implement", "validate"
    success: bool
    tool_calls_used: int
    error_output: str = ""
    iterations: int = 1

class EnhancedPIVStrategy:
    """
    Plan → Implement → Validate loop.

    Harness-level control flow that enforces structured problem-solving.
    Beats Codex by reading tests BEFORE making changes (proactive vs reactive).
    """
    MAX_ITERATIONS = 3

    def describe(self) -> str:
        """Return the system prompt injection for this strategy."""
        return """
You are using the meta-autocode PIV strategy. Follow this EXACT sequence:

PHASE 1 — PLAN:
1. Read task.md (or the task description provided)
2. Read ALL test files first (test_*.py, verify.sh, *_test.py)
3. Read source files that the tests import
4. Think: what exactly needs to change to make the tests pass?
5. Output a plan: list each file and what change it needs

PHASE 2 — IMPLEMENT:
6. Make ONLY the changes from your plan
7. Do not read files you already read
8. Do not make speculative changes

PHASE 3 — VALIDATE:
9. Run verify.sh (or pytest if no verify.sh)
10. If tests pass: DONE
11. If tests fail: re-read the error, go back to PHASE 1 with the error context
12. Maximum 3 full PIV cycles

This structure beats Codex by eliminating exploratory tool calls.
Codex wastes calls on reactive trial-and-error. PIV plans first.
"""

    def get_overlay(self) -> dict[str, Any]:
        """Return strategy overlay parameters for autocode's StrategyOverlay system."""
        return {
            "max_edit_retries": 3,
            "max_build_retries": 3,
            "require_verifier_signal_before_retry": True,
            "stagnation_threshold": 2,
            "preferred_tools": ("read_file", "edit_file", "run_command"),
            "additional_prompt_guidance": self.describe(),
        }
```

### File 3: `src/meta_autocode/scorer.py`

Track performance vs Codex baseline.

```python
from dataclasses import dataclass, field
import json
from pathlib import Path

CODEX_BASELINE = {
    "functionality": 0.615,   # 61.5% from MindStudio benchmark
    "swe_bench_verified": 0.32,  # ~32% estimated Codex SWE-bench
}

@dataclass
class BenchmarkScore:
    task_id: str
    resolved: bool
    tool_calls: int
    wall_time_s: float
    piv_iterations: int = 1
    failure_type: str = ""

@dataclass
class SessionScores:
    scores: list[BenchmarkScore] = field(default_factory=list)

    @property
    def resolve_rate(self) -> float:
        if not self.scores:
            return 0.0
        return sum(1 for s in self.scores if s.resolved) / len(self.scores)

    @property
    def avg_tool_calls(self) -> float:
        resolved = [s for s in self.scores if s.resolved]
        if not resolved:
            return 0.0
        return sum(s.tool_calls for s in resolved) / len(resolved)

    def vs_codex(self) -> dict[str, float]:
        """Return comparison against Codex baseline."""
        return {
            "meta_autocode_rate": self.resolve_rate,
            "codex_baseline": CODEX_BASELINE["functionality"],
            "delta": self.resolve_rate - CODEX_BASELINE["functionality"],
            "beats_codex": self.resolve_rate > CODEX_BASELINE["functionality"],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "resolve_rate": self.resolve_rate,
            "avg_tool_calls": self.avg_tool_calls,
            "vs_codex": self.vs_codex(),
            "tasks": [vars(s) for s in self.scores],
        }, indent=2))
```

### File 4: `pyproject.toml`
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "meta-autocode"
version = "0.1.0"
description = "A coding agent harness that beats Codex on harness benchmarks"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.hatch.build.targets.wheel]
packages = ["src/meta_autocode"]
```

### File 5: `tests/test_piv.py`

```python
"""Tests for EnhancedPIVStrategy."""
import pytest
from meta_autocode.piv import EnhancedPIVStrategy, PIVPlan, PIVResult
from meta_autocode.scorer import SessionScores, BenchmarkScore, CODEX_BASELINE


def test_strategy_has_describe():
    s = EnhancedPIVStrategy()
    desc = s.describe()
    assert "PLAN" in desc
    assert "IMPLEMENT" in desc
    assert "VALIDATE" in desc
    assert len(desc) > 100  # non-trivial guidance


def test_strategy_overlay_has_required_keys():
    s = EnhancedPIVStrategy()
    overlay = s.get_overlay()
    assert "max_edit_retries" in overlay
    assert "additional_prompt_guidance" in overlay
    assert overlay["require_verifier_signal_before_retry"] is True


def test_piv_plan_structure():
    plan = PIVPlan(
        task_description="Fix wrong port in config.yaml",
        files_to_read=["config.yaml", "test_app.py"],
        changes_needed=[{"file": "config.yaml", "description": "Change port from 9090 to 8080", "reason": "test expects 8080"}],
        test_files=["test_app.py"],
        verify_command="./verify.sh",
    )
    assert plan.task_description
    assert len(plan.changes_needed) == 1
    assert plan.changes_needed[0]["file"] == "config.yaml"


def test_piv_result_tracks_phases():
    result = PIVResult(phase="validate", success=True, tool_calls_used=8)
    assert result.success
    assert result.tool_calls_used == 8
    assert result.iterations == 1


def test_scorer_resolve_rate():
    session = SessionScores()
    session.scores.append(BenchmarkScore("b27", resolved=True, tool_calls=8, wall_time_s=14.0))
    session.scores.append(BenchmarkScore("b24", resolved=True, tool_calls=15, wall_time_s=42.0))
    session.scores.append(BenchmarkScore("b20", resolved=False, tool_calls=0, wall_time_s=16.0, failure_type="INFRA_FAIL"))
    assert session.resolve_rate == pytest.approx(2/3)
    assert session.avg_tool_calls == pytest.approx(11.5)


def test_beats_codex_target():
    """A session with 6/6 resolved should beat Codex's 61.5%."""
    session = SessionScores()
    for i in range(6):
        session.scores.append(BenchmarkScore(f"task-{i}", resolved=True, tool_calls=10, wall_time_s=30.0))
    comparison = session.vs_codex()
    assert comparison["resolve_rate"] == 1.0
    assert comparison["beats_codex"] is True
    assert comparison["delta"] > 0


def test_codex_baseline_is_documented():
    assert CODEX_BASELINE["functionality"] == pytest.approx(0.615)
    assert CODEX_BASELINE["swe_bench_verified"] > 0


def test_max_iterations_is_three():
    assert EnhancedPIVStrategy.MAX_ITERATIONS == 3
```

## Verification Steps

After writing all files, run:
```bash
cd /home/bs01763/projects/ai/autocode-full/meta-autocode
pip install -e ".[dev]" 2>/dev/null || python -m pip install -e ".[dev]"
python -m pytest tests/test_piv.py -v
```

All 8 tests must pass.

## Definition of Done
- [ ] `pyproject.toml` exists and is valid
- [ ] `src/meta_autocode/__init__.py` exists
- [ ] `src/meta_autocode/piv.py` — `EnhancedPIVStrategy` class with `describe()` and `get_overlay()`
- [ ] `src/meta_autocode/scorer.py` — `SessionScores`, `BenchmarkScore`, `CODEX_BASELINE`
- [ ] `tests/test_piv.py` — 8 tests, all passing
- [ ] `python -m pytest tests/test_piv.py -v` exits 0

## Notes for autocode
- You are building meta-autocode, a harness designed to beat Codex (61.5% baseline)
- Study the codex CLI code in research-components/openai-codex/ to understand what to beat
- The PIV strategy is the key insight: plan before acting, validate after acting
- Keep it clean Python — no external dependencies beyond stdlib + pytest
- The task.md files you normally work on have verify.sh — meta-autocode's tests use pytest
