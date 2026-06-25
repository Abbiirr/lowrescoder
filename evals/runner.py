"""Deterministic production eval-suite runner substrate."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from evals.judge import CriterionScore, LLMJudge


@dataclass(frozen=True, slots=True)
class EvalProvenance:
    source: str
    bug_id: str = ""
    recorded_at: str = ""


@dataclass(frozen=True, slots=True)
class EvalSetup:
    fixture_repo: str = ""
    initial_files: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvalExpectedOutcomes:
    must_have: list[str] = field(default_factory=list)
    must_not_have: list[str] = field(default_factory=list)
    judge_criteria: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class EvalConfig:
    model: str = "coding"
    max_turns: int = 3
    timeout_sec: int = 120
    temperature: float = 0.0
    seed: int = 0


@dataclass(frozen=True, slots=True)
class EvalBaseline:
    correctness_score: float = 1.0
    minimality_score: float = 1.0
    test_quality_score: float = 1.0
    cost_usd_p50: float = 0.0


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    name: str
    provenance: EvalProvenance
    setup: EvalSetup
    input: dict[str, str]
    expected_outcomes: EvalExpectedOutcomes
    config: EvalConfig
    baseline: EvalBaseline
    archived: bool = False

    @classmethod
    def load(cls, path: str | Path) -> EvalCase:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("Eval case YAML must be a mapping")
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> EvalCase:
        required = [
            "id",
            "name",
            "provenance",
            "setup",
            "input",
            "expected_outcomes",
            "config",
            "baseline",
        ]
        missing = [key for key in required if key not in raw]
        if missing:
            raise ValueError(f"Eval case missing required fields: {', '.join(missing)}")

        provenance_raw = _mapping(raw["provenance"], "provenance")
        setup_raw = _mapping(raw["setup"], "setup")
        input_raw = _mapping(raw["input"], "input")
        outcomes_raw = _mapping(raw["expected_outcomes"], "expected_outcomes")
        config_raw = _mapping(raw["config"], "config")
        baseline_raw = _mapping(raw["baseline"], "baseline")

        baseline = EvalBaseline(
            correctness_score=_score(baseline_raw.get("correctness_score", 1.0)),
            minimality_score=_score(baseline_raw.get("minimality_score", 1.0)),
            test_quality_score=_score(baseline_raw.get("test_quality_score", 1.0)),
            cost_usd_p50=max(0.0, float(baseline_raw.get("cost_usd_p50", 0.0))),
        )
        return cls(
            id=str(raw["id"]),
            name=str(raw["name"]),
            provenance=EvalProvenance(
                source=str(provenance_raw.get("source") or ""),
                bug_id=str(provenance_raw.get("bug_id") or ""),
                recorded_at=str(provenance_raw.get("recorded_at") or ""),
            ),
            setup=EvalSetup(
                fixture_repo=str(setup_raw.get("fixture_repo") or ""),
                initial_files={
                    str(path): str(content)
                    for path, content in _mapping(setup_raw.get("initial_files", {}), "initial_files").items()
                },
            ),
            input={"user_message": str(input_raw.get("user_message") or "")},
            expected_outcomes=EvalExpectedOutcomes(
                must_have=[str(item) for item in outcomes_raw.get("must_have", [])],
                must_not_have=[str(item) for item in outcomes_raw.get("must_not_have", [])],
                judge_criteria=[str(item) for item in outcomes_raw.get("judge_criteria", [])],
            ),
            config=EvalConfig(
                model=str(config_raw.get("model") or "coding"),
                max_turns=int(config_raw.get("max_turns", 3)),
                timeout_sec=int(config_raw.get("timeout_sec", 120)),
                temperature=float(config_raw.get("temperature", 0.0)),
                seed=int(config_raw.get("seed", 0)),
            ),
            baseline=baseline,
            archived=bool(raw.get("archived", False)),
        )

    @property
    def user_message(self) -> str:
        return self.input.get("user_message", "")


@dataclass(frozen=True, slots=True)
class EvalRunInput:
    telemetry_events: list[dict[str, Any]] = field(default_factory=list)
    diff: str = ""
    test_output: str = ""
    final_response: str = ""


@dataclass(frozen=True, slots=True)
class EvalResult:
    case_id: str
    passed: bool
    workdir: Path
    must_have_missing: list[str] = field(default_factory=list)
    must_not_have_present: list[str] = field(default_factory=list)
    judge_scores: dict[str, CriterionScore] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EvalAgentCommand:
    """Command used by isolated eval/CI runs to execute one AutoCode turn.

    The default auto-approves tools because eval cases run in temporary
    fixture workdirs. Non-eval callers should explicitly set
    ``auto_approve=False``.
    """

    executable: str = "autocode"
    args: tuple[str, ...] = ("exec",)
    json_output: bool = True
    auto_approve: bool = True
    test_command: tuple[str, ...] = ()
    env: dict[str, str] = field(default_factory=dict)

    def argv_for(self, prompt: str) -> list[str]:
        argv = [self.executable, *self.args, prompt]
        if self.json_output:
            argv.append("--json")
        if self.auto_approve:
            argv.append("--auto-approve")
        return argv


class EvalRunner:
    """Runs eval cases against deterministic artifacts or a future live harness."""

    def __init__(
        self,
        *,
        judge: LLMJudge | None = None,
        agent_command: EvalAgentCommand | None = None,
    ) -> None:
        self.judge = judge or LLMJudge()
        self.agent_command = agent_command or EvalAgentCommand()

    def setup_fixture(self, case: EvalCase) -> Path:
        workdir = Path(tempfile.mkdtemp(prefix=f"autocode-eval-{case.id}-"))
        if case.setup.fixture_repo:
            source = Path(case.setup.fixture_repo)
            if source.exists():
                shutil.copytree(source, workdir, dirs_exist_ok=True)
        for rel_path, content in case.setup.initial_files.items():
            target = workdir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return workdir

    async def run(
        self,
        case: EvalCase,
        run_input: EvalRunInput | None = None,
    ) -> EvalResult:
        run_input = run_input or EvalRunInput()
        workdir = self.setup_fixture(case)
        return await self.evaluate(case, run_input, workdir=workdir)

    async def run_live(self, case: EvalCase) -> EvalResult:
        """Run a case through the configured headless AutoCode command."""

        workdir = self.setup_fixture(case)
        before_dir = _snapshot_workdir(workdir)
        run_input = await self._execute_agent_command(case, workdir)
        try:
            diff = _capture_workdir_diff(before_dir, workdir)
        finally:
            shutil.rmtree(before_dir.parent, ignore_errors=True)
        test_output = await self._run_test_command(case, workdir)
        run_input = EvalRunInput(
            telemetry_events=run_input.telemetry_events,
            diff=diff,
            test_output="\n".join(
                part for part in (run_input.test_output, test_output) if part
            ),
            final_response=run_input.final_response,
        )
        return await self.evaluate(case, run_input, workdir=workdir)

    async def evaluate(
        self,
        case: EvalCase,
        run_input: EvalRunInput,
        *,
        workdir: Path,
    ) -> EvalResult:
        event_text = "\n".join(json.dumps(event, sort_keys=True) for event in run_input.telemetry_events)
        must_have_missing = [
            predicate
            for predicate in case.expected_outcomes.must_have
            if predicate not in event_text
        ]
        must_not_have_present = [
            predicate
            for predicate in case.expected_outcomes.must_not_have
            if predicate in event_text
        ]
        judge_scores: dict[str, CriterionScore] = {}
        if case.expected_outcomes.judge_criteria:
            judge_scores = await self.judge.score(
                case.expected_outcomes.judge_criteria,
                diff=run_input.diff,
                test_output=run_input.test_output,
                final_response=run_input.final_response,
            )
        passed = not must_have_missing and not must_not_have_present
        if judge_scores:
            passed = passed and _scores_within_baseline(case, judge_scores)
        return EvalResult(
            case_id=case.id,
            passed=passed,
            workdir=workdir,
            must_have_missing=must_have_missing,
            must_not_have_present=must_not_have_present,
            judge_scores=judge_scores,
        )

    async def _execute_agent_command(self, case: EvalCase, workdir: Path) -> EvalRunInput:
        argv = self.agent_command.argv_for(case.user_message)
        env = os.environ.copy()
        env.update(self.agent_command.env)
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(workdir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=max(1, case.config.timeout_sec),
            )
        except TimeoutError:
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            return EvalRunInput(
                telemetry_events=[{
                    "type": "error",
                    "kind": "error",
                    "message": f"eval command timed out after {case.config.timeout_sec}s",
                }],
                test_output=stderr,
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        events, final_response = _parse_ndjson_events(stdout)
        if process.returncode:
            events.append({
                "type": "error",
                "kind": "error",
                "message": f"eval command exited with code {process.returncode}",
            })
        return EvalRunInput(
            telemetry_events=events,
            test_output=stderr,
            final_response=final_response,
        )

    async def _run_test_command(self, case: EvalCase, workdir: Path) -> str:
        if not self.agent_command.test_command:
            return ""
        env = os.environ.copy()
        env.update(self.agent_command.env)
        process = await asyncio.create_subprocess_exec(
            *self.agent_command.test_command,
            cwd=str(workdir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=max(1, case.config.timeout_sec),
            )
        except TimeoutError:
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()
            timeout_msg = f"test command timed out after {case.config.timeout_sec}s"
            return "\n".join([
                timeout_msg,
                stdout_bytes.decode("utf-8", errors="replace"),
                stderr_bytes.decode("utf-8", errors="replace"),
            ]).strip()

        parts = [
            stdout_bytes.decode("utf-8", errors="replace"),
            stderr_bytes.decode("utf-8", errors="replace"),
        ]
        if process.returncode:
            parts.append(f"test command exited with code {process.returncode}")
        return "\n".join(part for part in parts if part).strip()


def load_cases(path: str | Path) -> list[EvalCase]:
    root = Path(path)
    paths = [root] if root.is_file() else sorted(root.glob("*.yaml"))
    return [EvalCase.load(item) for item in paths if item.name != "_schema.yaml"]


def select_stratified_sample(cases: Sequence[EvalCase], limit: int) -> list[EvalCase]:
    """Pick a deterministic source-stratified sample."""

    if limit <= 0 or len(cases) <= limit:
        return list(cases)
    buckets: dict[str, list[EvalCase]] = {}
    for case in cases:
        buckets.setdefault(case.provenance.source, []).append(case)
    selected: list[EvalCase] = []
    while len(selected) < limit:
        progressed = False
        for source in sorted(buckets):
            bucket = buckets[source]
            if bucket:
                selected.append(bucket.pop(0))
                progressed = True
                if len(selected) >= limit:
                    break
        if not progressed:
            break
    return selected


def _scores_within_baseline(
    case: EvalCase,
    scores: Mapping[str, CriterionScore],
    tolerance: float = 0.10,
) -> bool:
    baselines = {
        "correctness": case.baseline.correctness_score,
        "minimality": case.baseline.minimality_score,
        "test_quality": case.baseline.test_quality_score,
    }
    for criterion, score in scores.items():
        baseline = baselines.get(criterion)
        if baseline is None:
            continue
        if score.score < max(0.0, baseline - tolerance):
            return False
    return True


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Eval case field must be a mapping: {field_name}")
    return value


def _score(value: Any) -> float:
    score = float(value)
    if score < 0.0 or score > 1.0:
        raise ValueError(f"Score out of range: {score}")
    return score


def _snapshot_workdir(workdir: Path) -> Path:
    before_root = Path(tempfile.mkdtemp(prefix="autocode-eval-before-"))
    before_dir = before_root / "before"
    shutil.copytree(workdir, before_dir)
    return before_dir


def _capture_workdir_diff(before_dir: Path, workdir: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "--no-index", "--", str(before_dir), str(workdir)],
        capture_output=True,
        text=True,
        check=False,
    )
    return "\n".join(part for part in (result.stdout, result.stderr) if part).strip()


def _parse_ndjson_events(output: str) -> tuple[list[dict[str, Any]], str]:
    events: list[dict[str, Any]] = []
    response_chunks: list[str] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            events.append({
                "type": "error",
                "kind": "error",
                "message": "non-json output in eval command stdout",
            })
            continue
        if not isinstance(event, dict):
            continue
        event.setdefault("kind", event.get("type", ""))
        events.append(event)
        if event.get("type") == "item_delta":
            response_chunks.append(str(event.get("delta", "")))
    return events, "".join(response_chunks)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AutoCode eval cases.")
    parser.add_argument("--cases", default="evals/cases")
    parser.add_argument("--baseline-tolerance", type=float, default=0.10)
    parser.add_argument("--max-budget-usd", type=float, default=5.00)
    parser.add_argument("--stratified-sample", action="store_true")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--soft-gate", action="store_true")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    if args.stratified_sample:
        cases = select_stratified_sample(cases, args.sample_size)
    print(json.dumps({
        "case_count": len(cases),
        "baseline_tolerance": args.baseline_tolerance,
        "max_budget_usd": args.max_budget_usd,
        "soft_gate": args.soft_gate,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "EvalBaseline",
    "EvalAgentCommand",
    "EvalCase",
    "EvalConfig",
    "EvalExpectedOutcomes",
    "EvalProvenance",
    "EvalResult",
    "EvalRunInput",
    "EvalRunner",
    "EvalSetup",
    "load_cases",
    "select_stratified_sample",
]
