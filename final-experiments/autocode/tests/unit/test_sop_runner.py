"""Tests for SOPRunner — deterministic pipeline executor."""

from __future__ import annotations

from typing import Any

from autocode.agent.sop_runner import SOPPipeline, SOPRunner, SOPStatus, SOPStep


def test_sop_pipeline_bugfix() -> None:
    """Bugfix pipeline has 3 steps."""
    pipeline = SOPPipeline.bugfix()
    assert pipeline.name == "bugfix"
    assert len(pipeline.steps) == 3
    assert pipeline.steps[0].agent == "scout"
    assert pipeline.steps[1].agent == "architect"
    assert pipeline.steps[2].agent == "engineer"


def test_sop_pipeline_code_review() -> None:
    """Code review pipeline has 2 steps."""
    pipeline = SOPPipeline.code_review()
    assert len(pipeline.steps) == 2


def test_sop_runner_completes() -> None:
    """SOPRunner completes a simple pipeline."""
    pipeline = SOPPipeline(
        name="test",
        steps=[
            SOPStep(agent="a", action="do thing", output_type="result"),
        ],
    )
    runner = SOPRunner()
    result = runner.run(pipeline)

    assert result.status == SOPStatus.COMPLETED
    assert result.steps_completed == 1
    assert "result" in result.outputs


def test_sop_runner_passes_context() -> None:
    """SOPRunner passes initial context to steps."""
    outputs_seen: list[dict[str, Any]] = []

    def executor(step: SOPStep, ctx: dict[str, Any]) -> str:
        outputs_seen.append(dict(ctx))
        return f"output from {step.agent}"

    pipeline = SOPPipeline(
        name="test",
        steps=[
            SOPStep(agent="scout", action="find {task}", output_type="files"),
            SOPStep(agent="arch", action="plan", input_from="files", output_type="plan"),
        ],
    )
    runner = SOPRunner()
    result = runner.run(pipeline, context={"task": "fix bug"}, step_executor=executor)

    assert result.status == SOPStatus.COMPLETED
    assert result.steps_completed == 2
    assert "task" in outputs_seen[0]
    assert "files" in outputs_seen[1]  # output from step 1 available to step 2


def test_sop_runner_gate_failure() -> None:
    """SOPRunner stops on gate failure."""
    def strict_gate(gate_name: str, output: Any) -> bool:
        return gate_name != "must_fail"

    pipeline = SOPPipeline(
        name="test",
        steps=[
            SOPStep(agent="a", action="do", output_type="r1"),
            SOPStep(agent="b", action="do", output_type="r2", gate="must_fail"),
        ],
    )
    runner = SOPRunner(gate_checker=strict_gate)
    result = runner.run(pipeline)

    assert result.status == SOPStatus.GATE_FAILED
    assert result.steps_completed == 1
    assert "must_fail" in result.error


def test_sop_runner_error_handling() -> None:
    """SOPRunner catches step execution errors."""
    def failing_executor(step: SOPStep, ctx: dict[str, Any]) -> str:
        raise RuntimeError("step crashed")

    pipeline = SOPPipeline(
        name="test",
        steps=[SOPStep(agent="a", action="crash", output_type="r")],
    )
    runner = SOPRunner()
    result = runner.run(pipeline, step_executor=failing_executor)

    assert result.status == SOPStatus.ERROR
    assert "step crashed" in result.error
