"""Self-contained calibration tasks for harness validation.

Each task is a tiny, network-free unit with a *known* gold solution and a *known* wrong
solution, plus a real ``grading_command``. They are the ground-truth fixtures the harness
calibration runs against:

* a correct grader passes the gold solution (and a real agent's correct fix),
* a correct grader fails an empty (noop) sandbox,
* a correct grader fails a plausible-but-wrong solution.

The same task set is consumed by:
* ``benchmarks/tests/test_harness_calibration.py`` — deterministic oracle invariants, and
* ``benchmarks/calibrate_harness.py`` — the live runner that also drives puku-cli.

Tasks deliberately start from a *failing* state (``initial_files``) so that a NoopOracle
leaves the grade failing — proving the grader is not trivially passing everything.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from benchmarks.adapters.base import BenchmarkTask


@dataclass
class CalibrationTask:
    task_id: str
    description: str
    grading_command: str
    # State written into the sandbox before any agent/oracle runs (the failing baseline).
    initial_files: dict[str, str] = field(default_factory=dict)
    # GoldenOracle writes these (a correct solution) → grading must PASS.
    gold_files: dict[str, str] = field(default_factory=dict)
    # WrongOracle writes these (a plausible-but-wrong solution) → grading must FAIL.
    wrong_files: dict[str, str] = field(default_factory=dict)
    category: str = "calibration"

    def to_benchmark_task(self) -> BenchmarkTask:
        return BenchmarkTask(
            task_id=self.task_id,
            description=self.description,
            grading_command=self.grading_command,
            category=self.category,
            extra={
                "gold_files": self.gold_files,
                "wrong_files": self.wrong_files,
            },
        )

    def make_sandbox(self, root: Path | None = None) -> Path:
        """Create a fresh sandbox seeded with the failing baseline ``initial_files``."""
        base = root or Path(tempfile.mkdtemp(prefix=f"calib_{self.task_id}_"))
        base.mkdir(parents=True, exist_ok=True)
        for rel, content in self.initial_files.items():
            target = base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return base


CALIBRATION_TASKS: list[CalibrationTask] = [
    # 1) Greenfield file creation — simplest end-to-end signal.
    CalibrationTask(
        task_id="calib-greenfield-hello",
        description=(
            "Create a file named hello.txt in the current directory containing exactly "
            "the text: hello world"
        ),
        grading_command='test "$(cat hello.txt 2>/dev/null)" = "hello world"',
        initial_files={},  # nothing yet → noop leaves it failing (file absent)
        gold_files={"hello.txt": "hello world"},
        wrong_files={"hello.txt": "goodbye world"},
        category="repo_init",
    ),
    # 2) Bug fix with a real test — the false-positive / false-negative workhorse.
    #    Baseline subtracts; gold adds; wrong is off-by-one. The pytest catches all three.
    CalibrationTask(
        task_id="calib-bugfix-add",
        description=(
            "The function add() in calc.py is wrong: it must return the sum of its two "
            "arguments. Fix calc.py so that the tests in test_calc.py pass. Do not modify "
            "the test file."
        ),
        grading_command="python -m pytest test_calc.py -q",
        initial_files={
            "calc.py": "def add(a, b):\n    return a - b\n",
            "test_calc.py": (
                "from calc import add\n\n\n"
                "def test_add_positive():\n"
                "    assert add(2, 3) == 5\n\n\n"
                "def test_add_zero():\n"
                "    assert add(0, 0) == 0\n\n\n"
                "def test_add_large():\n"
                "    assert add(10, 5) == 15\n"
            ),
        },
        gold_files={"calc.py": "def add(a, b):\n    return a + b\n"},
        wrong_files={"calc.py": "def add(a, b):\n    return a + b + 1\n"},
        category="bugfix",
    ),
    # 3) Refactor preserving behavior — a tougher false-positive probe. The wrong variant
    #    passes the "happy path" but breaks an edge case the test exercises.
    CalibrationTask(
        task_id="calib-bugfix-clamp",
        description=(
            "clamp(x, lo, hi) in util.py must return x bounded to the inclusive range "
            "[lo, hi]. It is currently wrong. Fix util.py so test_util.py passes. Do not "
            "modify the test file."
        ),
        grading_command="python -m pytest test_util.py -q",
        initial_files={
            "util.py": "def clamp(x, lo, hi):\n    return x\n",
            "test_util.py": (
                "from util import clamp\n\n\n"
                "def test_within():\n"
                "    assert clamp(5, 0, 10) == 5\n\n\n"
                "def test_below():\n"
                "    assert clamp(-3, 0, 10) == 0\n\n\n"
                "def test_above():\n"
                "    assert clamp(99, 0, 10) == 10\n"
            ),
        },
        gold_files={
            "util.py": "def clamp(x, lo, hi):\n    return max(lo, min(x, hi))\n",
        },
        # Wrong: clamps the low side only — passes test_within + test_below, fails test_above.
        wrong_files={
            "util.py": "def clamp(x, lo, hi):\n    return max(lo, x)\n",
        },
        category="bugfix",
    ),
]


def get_task(task_id: str) -> CalibrationTask:
    for t in CALIBRATION_TASKS:
        if t.task_id == task_id:
            return t
    raise KeyError(task_id)
