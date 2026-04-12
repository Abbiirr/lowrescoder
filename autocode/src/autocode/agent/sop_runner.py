"""SOPRunner — Deterministic pipeline executor.

Runs multi-step agent workflows (Standard Operating Procedures)
with gate conditions between steps.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SOPStatus(StrEnum):
    """SOP execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    GATE_FAILED = "gate_failed"
    ERROR = "error"


@dataclass
class SOPStep:
    """A single step in an SOP pipeline."""

    agent: str  # Agent ID
    action: str  # Prompt template
    input_from: str | None = None  # Previous step's output key
    output_type: str = "text"  # Expected output format
    gate: str | None = None  # Condition to proceed (e.g., "tests_pass")


@dataclass
class SOPResult:
    """Result of SOP execution."""

    status: SOPStatus = SOPStatus.COMPLETED
    step: SOPStep | None = None  # Step that caused failure
    outputs: dict[str, Any] = field(default_factory=dict)
    steps_completed: int = 0
    error: str = ""


@dataclass
class SOPPipeline:
    """A complete SOP pipeline definition."""

    name: str
    steps: list[SOPStep] = field(default_factory=list)
    description: str = ""

    @classmethod
    def bugfix(cls) -> SOPPipeline:
        """Pre-defined bugfix pipeline."""
        return cls(
            name="bugfix",
            description="Scout → Architect → Engineer → Verify",
            steps=[
                SOPStep(
                    agent="scout",
                    action="Find files related to: {task}",
                    output_type="relevant_files",
                ),
                SOPStep(
                    agent="architect",
                    action="Analyze bug and plan fix for: {task}",
                    input_from="relevant_files",
                    output_type="edit_plan",
                ),
                SOPStep(
                    agent="engineer",
                    action="Apply the fix according to the plan",
                    input_from="edit_plan",
                    output_type="code_changes",
                    gate="syntax_valid",
                ),
            ],
        )

    @classmethod
    def code_review(cls) -> SOPPipeline:
        """Pre-defined code review pipeline."""
        return cls(
            name="code_review",
            description="Scout → Reviewer",
            steps=[
                SOPStep(
                    agent="scout",
                    action="Find all files related to: {target}",
                    output_type="relevant_files",
                ),
                SOPStep(
                    agent="architect",
                    action="Review these files for: {criteria}",
                    input_from="relevant_files",
                    output_type="review_report",
                ),
            ],
        )


class SOPRunner:
    """Executes SOP pipelines step by step.

    Each step runs an agent with a prompt, optionally passing
    output from the previous step. Gate conditions are checked
    between steps.
    """

    def __init__(
        self,
        gate_checker: Callable[[str, Any], bool] | None = None,
    ) -> None:
        self._gate_checker = gate_checker or self._default_gate

    @staticmethod
    def _default_gate(gate_name: str, step_output: Any) -> bool:
        """Default gate: always passes."""
        return True

    def run(
        self,
        pipeline: SOPPipeline,
        context: dict[str, Any] | None = None,
        step_executor: Callable[[SOPStep, dict[str, Any]], Any] | None = None,
    ) -> SOPResult:
        """Execute an SOP pipeline.

        Args:
            pipeline: The pipeline to run.
            context: Initial context variables (task, target, etc.)
            step_executor: Function that executes a step and returns output.
                          If None, uses a placeholder executor.
        """
        outputs: dict[str, Any] = dict(context or {})
        executor = step_executor or self._placeholder_executor

        for i, step in enumerate(pipeline.steps):
            try:
                # Execute step
                output = executor(step, outputs)
                outputs[step.output_type] = output

                # Check gate
                if step.gate:
                    if not self._gate_checker(step.gate, output):
                        return SOPResult(
                            status=SOPStatus.GATE_FAILED,
                            step=step,
                            outputs=outputs,
                            steps_completed=i,
                            error=f"Gate '{step.gate}' failed at step {i + 1}",
                        )

            except Exception as e:
                return SOPResult(
                    status=SOPStatus.ERROR,
                    step=step,
                    outputs=outputs,
                    steps_completed=i,
                    error=str(e),
                )

        return SOPResult(
            status=SOPStatus.COMPLETED,
            outputs=outputs,
            steps_completed=len(pipeline.steps),
        )

    @staticmethod
    def _placeholder_executor(
        step: SOPStep, context: dict[str, Any],
    ) -> Any:
        """Placeholder: returns step description as output."""
        return f"[{step.agent}] {step.action}"
