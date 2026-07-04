"""Grader for AI verification runs.

Usage:
  uv run python benchmarks/ai_verification/grade_run.py --run-id <run_id>
  uv run python benchmarks/ai_verification/grade_run.py --run-id <run_id> --no-ai-review
  uv run python benchmarks/ai_verification/grade_run.py --run-id <run_id> --base <path>

Reads scenario.json + diff.patch + test_log.txt from the run artifact dir,
runs deterministic checks (if sandbox is still present), and writes grading_report.json.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from benchmarks.ai_verification.grading_env import grading_env
from benchmarks.ai_verification.schema import (
    Check,
    CheckResult,
    GradingReport,
    ScenarioSpec,
    Verdict,
    artifact_dir,
    sandbox_dir,
)


def grade(run_id: str, base: Path | None = None, ai_review: bool = True) -> GradingReport:
    arts = artifact_dir(run_id, base)
    scenario = ScenarioSpec.load(arts / "scenario.json")
    sandbox = sandbox_dir(run_id)

    check_results: list[CheckResult] = []

    for check in scenario.grading.checks:
        cmd = scenario.grading.check_commands.get(check.value, "")
        if not cmd:
            cmd = _default_command(check, scenario)

        if sandbox.exists():
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=sandbox,
                capture_output=True,
                text=True,
                timeout=120,
                env=grading_env(),
            )
            passed = result.returncode == 0
            output = result.stdout + result.stderr
        else:
            # sandbox gone — read cached test_log.txt if present
            log_path = arts / "test_log.txt"
            if log_path.exists():
                output = log_path.read_text()
                passed, output = _cached_test_log_passed(output)
            else:
                output = "sandbox not present and no cached test_log.txt"
                passed = False

        check_results.append(
            CheckResult(
                check=check,
                passed=passed,
                command=cmd,
                output=output,
                exit_code=0 if passed else 1,
            )
        )

    deterministic_all_passed = all(r.passed for r in check_results)

    if deterministic_all_passed and scenario.grading.ai_review_enabled and ai_review:
        ai_verdict, ai_reasoning = _run_ai_review(arts, scenario)
    else:
        ai_verdict = ""
        ai_reasoning = ""

    if not check_results:
        verdict = Verdict.INFRA_FAIL
    elif deterministic_all_passed:
        if ai_verdict and ai_verdict not in (Verdict.PASS.value, Verdict.PARTIAL.value, ""):
            verdict = Verdict.PARTIAL
        else:
            verdict = Verdict.PASS
    elif any(r.passed for r in check_results):
        verdict = Verdict.PARTIAL
    else:
        verdict = Verdict.FAIL

    report = GradingReport(
        verdict=verdict,
        check_results=check_results,
        ai_review_enabled=scenario.grading.ai_review_enabled and ai_review,
        ai_verdict=ai_verdict,
        ai_reasoning=ai_reasoning,
        ai_reviewer=scenario.grading.reviewer if ai_verdict else "",
    )

    report.save(arts / "grading_report.json")
    print(f"Verdict: {verdict.value}")
    for r in check_results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.check.value}: {r.command!r}")
    if ai_verdict:
        print(f"  [AI]  {ai_verdict}: {ai_reasoning[:80]}...")
    return report


def _default_command(check: Check, scenario: ScenarioSpec) -> str:
    lang = scenario.target_stack.language
    defaults: dict[tuple[str, str], str] = {
        ("python", Check.RUN_TESTS.value): "uv run pytest tests/ -q",
        ("python", Check.LINT.value): "uv run ruff check src/ tests/",
        ("python", Check.TYPECHECK.value): "uv run mypy src/",
        ("typescript", Check.RUN_TESTS.value): "npm test -- --ci",
        ("typescript", Check.LINT.value): "npx eslint src/",
        ("typescript", Check.TYPECHECK.value): "npx tsc --noEmit",
        ("javascript", Check.RUN_TESTS.value): "npm test -- --ci",
        ("go", Check.RUN_TESTS.value): "go test ./...",
        ("go", Check.LINT.value): "go vet ./...",
        ("go", Check.BUILD.value): "go build ./...",
        ("rust", Check.RUN_TESTS.value): "cargo test --quiet",
        ("rust", Check.LINT.value): "cargo clippy -- -D warnings",
        ("rust", Check.BUILD.value): "cargo build",
        ("java", Check.RUN_TESTS.value): "mvn test -q",
        ("java", Check.BUILD.value): "mvn package -q -DskipTests",
    }
    default = defaults.get((lang, check.value))
    if default:
        return default
    return (
        "printf 'HARNESS_CLASSIFICATION: missing_grading_command: "
        f"no default for {lang}/{check.value}\\n'; exit 1"
    )


def _cached_test_log_passed(output: str) -> tuple[bool, str]:
    stripped = output.strip()
    if not stripped:
        return False, "HARNESS_CLASSIFICATION: empty_grading_output\n"

    lower = output.lower()
    if "collected 0 items" in lower or "no tests ran" in lower:
        return False, output.rstrip() + "\nHARNESS_CLASSIFICATION: zero_tests_collected\n"

    if "failed" in lower or "error" in lower:
        return False, output

    has_pytest_pass = bool(re.search(r"\b\d+\s+passed\b", lower))
    has_generic_pass = bool(re.search(r"\b(pass|passed|ok)\b", lower))
    if has_pytest_pass or has_generic_pass:
        return True, output

    return False, output.rstrip() + "\nHARNESS_CLASSIFICATION: no_passing_grading_signal\n"


def _run_ai_review(arts: Path, scenario: ScenarioSpec) -> tuple[str, str]:
    """Call the LLM gateway to review the agent's diff against task success criteria.

    Returns (ai_verdict_str, ai_reasoning). On any failure returns ("", reason).
    The review prompt and raw response are always saved to review.md.
    """
    import os
    import urllib.request

    diff_path = arts / "diff.patch"
    test_log_path = arts / "test_log.txt"
    diff_text = diff_path.read_text() if diff_path.exists() else "(no diff)"
    test_log = test_log_path.read_text()[:2000] if test_log_path.exists() else "(no test log)"
    criteria = "\n".join(f"- {c}" for c in scenario.task_spec.success_criteria)
    artifacts_summary = "\n".join(f"- {a}" for a in scenario.task_spec.required_artifacts)

    review_prompt = (
        f"You are reviewing an AI coding agent's work. Be concise and objective.\n\n"
        f"TASK TITLE: {scenario.title}\n"
        f"CATEGORY: {scenario.category.value}  DIFFICULTY: {scenario.difficulty.value}\n\n"
        f"TASK PROMPT (shown to agent):\n{scenario.task_spec.prompt[:1500]}\n\n"
        f"REQUIRED ARTIFACTS:\n{artifacts_summary}\n\n"
        f"SUCCESS CRITERIA:\n{criteria}\n\n"
        f"DIFF (agent's changes):\n{diff_text[:3000]}\n\n"
        f"TEST LOG (deterministic check output):\n{test_log}\n\n"
        f"Evaluate whether the agent satisfied all required artifacts and success criteria.\n"
        f"Return ONLY a JSON object — no markdown fences, no prose before or after:\n"
        f'  {{"verdict": "PASS"|"FAIL"|"PARTIAL", "reasoning": "1-2 sentences"}}'
    )

    review_path = arts / "review.md"

    api_key = (
        os.environ.get("LITELLM_API_KEY")
        or os.environ.get("LITELLM_MASTER_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or ""
    )
    gateway = os.environ.get("LITELLM_GATEWAY_URL", "http://localhost:4000")

    review_path.write_text(
        f"# AI Review\n\n## Prompt\n\n```\n{review_prompt}\n```\n\n## Response\n\n(pending)\n"
    )

    if not api_key:
        review_path.write_text(
            f"# AI Review\n\n## Prompt\n\n```\n{review_prompt}\n```\n\n"
            "## Response\n\n**SKIPPED** — no API key found (set LITELLM_API_KEY or OPENROUTER_API_KEY)\n"
        )
        return "", "no API key"

    try:
        payload = json.dumps({
            "model": "coding",
            "messages": [{"role": "user", "content": review_prompt}],
            "temperature": 0.2,
            "max_tokens": 300,
        }).encode()
        req = urllib.request.Request(
            f"{gateway}/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read())
        content = raw["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        review_path.write_text(
            f"# AI Review\n\n## Prompt\n\n```\n{review_prompt}\n```\n\n"
            f"## Response\n\n**ERROR**: {exc}\n"
        )
        return "", f"gateway error: {exc}"

    # Parse the JSON verdict
    try:
        # Strip markdown fences if model ignored the instruction
        cleaned = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(cleaned)
        ai_verdict = result.get("verdict", "").upper()
        ai_reasoning = result.get("reasoning", "")
        if ai_verdict not in ("PASS", "FAIL", "PARTIAL"):
            raise ValueError(f"unexpected verdict: {ai_verdict!r}")
    except (json.JSONDecodeError, ValueError) as exc:
        review_path.write_text(
            f"# AI Review\n\n## Prompt\n\n```\n{review_prompt}\n```\n\n"
            f"## Raw Response\n\n{content}\n\n## Parse Error\n\n{exc}\n"
        )
        return "", f"parse error: {exc}"

    review_path.write_text(
        f"# AI Review\n\n## Prompt\n\n```\n{review_prompt}\n```\n\n"
        f"## Verdict\n\n**{ai_verdict}**\n\n{ai_reasoning}\n"
    )
    return ai_verdict, ai_reasoning


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade an AI verification run")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base", type=Path, default=None)
    parser.add_argument("--no-ai-review", action="store_true")
    args = parser.parse_args()
    grade(args.run_id, base=args.base, ai_review=not args.no_ai_review)


if __name__ == "__main__":
    main()
