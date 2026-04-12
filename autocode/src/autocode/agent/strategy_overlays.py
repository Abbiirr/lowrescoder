"""Task-family strategy overlays for Terminal-Bench / Harbor adapter.

PLAN.md Section 3.1-3.3: Strategy overlays that teach the Harbor path
to behave differently by task family, plus verifier-aware retry and
stronger stagnation detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TaskFamily(StrEnum):
    """Known task families for strategy overlay selection."""

    HTML_OUTPUT = "html_output"
    PYTHON_BUILD = "python_build"
    GENERAL = "general"


@dataclass
class StrategyOverlay:
    """Strategy parameters for a specific task family."""

    family: TaskFamily
    max_edit_retries: int = 4
    max_build_retries: int = 3
    require_verifier_signal_before_retry: bool = True
    stagnation_threshold: int = 3
    preferred_tools: tuple[str, ...] = ()
    avoid_tools: tuple[str, ...] = ()
    additional_prompt_guidance: str = ""


TASK_FAMILY_PATTERNS: dict[TaskFamily, list[str]] = {
    TaskFamily.HTML_OUTPUT: [
        "html",
        "filter",
        "extract",
        "parse",
        "css",
        "dom",
        "scrape",
        "strip",
    ],
    TaskFamily.PYTHON_BUILD: [
        "cython",
        "setup.py",
        "pyproject.toml",
        "build",
        "compile",
        "extension",
        "cffi",
        "wheel",
        "install",
    ],
}


OVERLAYS: dict[TaskFamily, StrategyOverlay] = {
    TaskFamily.HTML_OUTPUT: StrategyOverlay(
        family=TaskFamily.HTML_OUTPUT,
        max_edit_retries=3,
        max_build_retries=2,
        require_verifier_signal_before_retry=True,
        stagnation_threshold=3,
        preferred_tools=("read_file", "edit_file", "write_file"),
        avoid_tools=("bash",),
        additional_prompt_guidance=(
            "For HTML/output filtering tasks: read the source first, "
            "identify the exact content to filter, make a single targeted edit, "
            "then verify the output. Avoid wholesale rewrites."
        ),
    ),
    TaskFamily.PYTHON_BUILD: StrategyOverlay(
        family=TaskFamily.PYTHON_BUILD,
        max_edit_retries=4,
        max_build_retries=3,
        require_verifier_signal_before_retry=True,
        stagnation_threshold=3,
        preferred_tools=("bash", "read_file", "edit_file"),
        avoid_tools=(),
        additional_prompt_guidance=(
            "For Python/Cython build tasks: fix the build error first, "
            "then run the build again. Extract the exact error message "
            "before retrying. Do not re-run the build without changes."
        ),
    ),
    TaskFamily.GENERAL: StrategyOverlay(
        family=TaskFamily.GENERAL,
        max_edit_retries=4,
        max_build_retries=3,
        require_verifier_signal_before_retry=False,
        stagnation_threshold=4,
    ),
}


def classify_task(task_description: str) -> TaskFamily:
    """Classify a task into a task family based on description keywords.

    Args:
        task_description: The task title or description.

    Returns:
        The most likely TaskFamily.
    """
    desc_lower = task_description.lower()
    best_family = TaskFamily.GENERAL
    best_score = 0

    for family, patterns in TASK_FAMILY_PATTERNS.items():
        score = sum(1 for p in patterns if p in desc_lower)
        if score > best_score:
            best_score = score
            best_family = family

    return best_family


def get_overlay(task_description: str) -> StrategyOverlay:
    """Get the strategy overlay for a task.

    Args:
        task_description: The task title or description.

    Returns:
        The StrategyOverlay for the classified task family.
    """
    family = classify_task(task_description)
    return OVERLAYS[family]


@dataclass
class StagnationDetector:
    """Detect stagnation in build/install/test cycles.

    PLAN.md Section 3.3: Catch repeated build/install/test cycles
    with no meaningful progress.
    """

    max_identical_results: int = 3
    _result_hashes: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._result_hashes = []

    def check(self, tool_name: str, tool_result: str) -> str | None:
        """Check if the current result indicates stagnation.

        Args:
            tool_name: The tool that was just called.
            tool_result: The result of the tool call.

        Returns:
            A warning string if stagnation detected, None otherwise.
        """
        result_hash = f"{tool_name}:{hash(tool_result)}"
        self._result_hashes.append(result_hash)

        if len(self._result_hashes) < self.max_identical_results:
            return None

        recent = self._result_hashes[-self.max_identical_results :]
        if len(set(recent)) == 1:
            return (
                f"STAGNATION DETECTED: {tool_name} has produced identical "
                f"results {self.max_identical_results} times in a row. "
                "You must change your approach before retrying. "
                "Read the output carefully, identify the root cause, "
                "and try a different fix."
            )

        return None


def verifier_aware_retry_guidance(
    tool_name: str,
    tool_result: str,
    retry_count: int,
    max_retries: int,
) -> str | None:
    """Generate verifier-aware retry guidance.

    PLAN.md Section 3.2: Require the agent to extract failing
    output/verifier signal before repeating build or rewrite cycles.

    Args:
        tool_name: The tool that failed.
        tool_result: The result of the failed tool call.
        retry_count: Current retry attempt number.
        max_retries: Maximum allowed retries.

    Returns:
        Guidance string if retry is needed, None if no guidance needed.
    """
    if retry_count >= max_retries:
        return (
            f"MAX RETRIES ({max_retries}) reached for {tool_name}. "
            "Stop retrying and report the failure."
        )

    if retry_count > 0 and _has_error_signal(tool_result):
        return (
            f"Retry {retry_count}/{max_retries} for {tool_name}. "
            "Before retrying: (1) extract the exact error message, "
            "(2) identify the root cause, (3) make a targeted fix. "
            "Do NOT re-run without changes."
        )

    return None


def _has_error_signal(result: str) -> bool:
    """Check if a tool result contains error signals."""
    error_markers = ("error", "failed", "traceback", "exception", "fatal")
    result_lower = result.lower()
    return any(m in result_lower for m in error_markers)
