# TASK: Build meta-autocode PIV Strategy (Phase 1)

## Mission
You are building `meta-autocode` — a coding agent harness designed to **beat Codex** (OpenAI) on standard harness benchmarks.

Codex scores **61.5%** on harness functionality benchmarks (MindStudio 2025 data).
Your job: implement the core PIV (Plan-Implement-Validate) loop that will push meta-autocode past that baseline.

## What to Build

Implement the following Python files so all pytest tests pass:

### 1. `src/meta_autocode/__init__.py`
```python
"""meta-autocode: A coding agent harness that beats Codex."""
__version__ = "0.1.0"
```

### 2. `src/meta_autocode/piv.py`

Implement these dataclasses and class:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class PIVPlan:
    task_description: str
    files_to_read: list[str] = field(default_factory=list)
    changes_needed: list[dict[str, str]] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    verify_command: str = "./verify.sh"

@dataclass
class PIVResult:
    phase: str   # "plan", "implement", or "validate"
    success: bool
    tool_calls_used: int
    error_output: str = ""
    iterations: int = 1

class EnhancedPIVStrategy:
    MAX_ITERATIONS = 3

    def describe(self) -> str:
        # Return a multi-line string (>100 chars) describing the PIV loop.
        # Must contain the words "PLAN", "IMPLEMENT", and "VALIDATE".
        ...

    def get_overlay(self) -> dict[str, Any]:
        # Return a dict with at least these keys:
        #   "max_edit_retries": int
        #   "additional_prompt_guidance": str  (non-empty)
        #   "require_verifier_signal_before_retry": True
        ...
```

### 3. `src/meta_autocode/scorer.py`

```python
from dataclasses import dataclass, field
import json
from pathlib import Path

CODEX_BASELINE = {
    "functionality": 0.615,   # 61.5% from MindStudio harness benchmark 2025
    "swe_bench_verified": 0.32,
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
        # proportion of scores where resolved=True
        # MUST return 0.0 for empty sessions (guard against ZeroDivisionError)
        ...

    @property
    def avg_tool_calls(self) -> float:
        # average tool_calls across resolved tasks ONLY (not unresolved)
        # MUST return 0.0 if there are no resolved scores
        ...

    def vs_codex(self) -> dict[str, float]:
        # return dict with keys:
        #   "meta_autocode_rate": float
        #   "codex_baseline": float
        #   "delta": float
        #   "beats_codex": float (0.0 or 1.0 — comparable to float, NOT a bool)
        ...

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({
            "resolve_rate": self.resolve_rate,
            "avg_tool_calls": self.avg_tool_calls,
            "vs_codex": self.vs_codex(),
            "tasks": [vars(s) for s in self.scores],
        }, indent=2))
```

## Verification

Run: `python -m pytest tests/test_piv.py -v`

All 9 tests must pass. The tests are in `tests/test_piv.py` — read them to understand exactly what each method must return.

## Key context
- Read `tests/test_piv.py` FIRST — the tests define exactly what you need to implement
- No external dependencies — stdlib + pytest only
- Codex baseline is 61.5%. Every line of meta-autocode is a step toward beating it.
- Study `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/sop_runner.py` for patterns
- Study `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/strategy_overlays.py` for the overlay interface
