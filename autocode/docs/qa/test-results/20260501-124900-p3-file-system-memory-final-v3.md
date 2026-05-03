# P3 File-System Memory — Final Verification Artifact (v3)

> **Phase:** P3 — Tier 3 File-System Memory (Tier 3.1 + 3.2)
> **Date:** 2026-05-01
> **Status:** Builder-complete after retained-sandbox `grade_run` parity fix; requesting review
> **Supersedes:** `20260501-121100-p3-file-system-memory-final-v2.md`

## Erratum Since v2

Codex Entry 1728 found one remaining harness parity issue: `run_scenario.py` used a repo-root `PYTHONPATH` for sandbox grading, but standalone `grade_run.py` did not. When a sandbox was retained and `grade_run --run-id` re-executed the module-form check, it failed with `ModuleNotFoundError: No module named 'benchmarks.ai_verification'`.

## Fix

- Added `benchmarks/ai_verification/grading_env.py` with shared `grading_env()`.
- Updated `run_scenario.py` and `grade_run.py` to use the same grading subprocess environment.
- Added `test_compaction_path_a_standalone_grade_run_reexecutes_check` to keep a sandbox alive, run standalone `grade()`, and assert the re-executed check passes with the Path A PASS marker and no module-resolution error.

## Verification Evidence

| Check | Result |
|---|---|
| `uv run python -m benchmarks.ai_verification.run_scenario --scenario benchmarks/ai_verification/scenarios/compaction-path-a.yaml --validate-fixture --keep-sandbox` | PASS, run ID `20260501-124656-da0bd691` |
| `uv run python -m benchmarks.ai_verification.grade_run --run-id 20260501-124656-da0bd691 --no-ai-review` | PASS, `check_results[0].passed == true` |
| `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` | `29 passed` |
| `uv run pytest autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py -q` | `17 passed` |
| `uv run ruff check benchmarks/ai_verification/grading_env.py benchmarks/ai_verification/run_scenario.py benchmarks/ai_verification/grade_run.py benchmarks/ai_verification/schema.py benchmarks/ai_verification/scenario_yaml.py benchmarks/tests/test_ai_verification_substrate.py autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py` | All checks passed |

## Standalone Regrade Output

```text
Verdict: PASS
  [PASS] snapshot: 'uv run python -m benchmarks.ai_verification.checks.check_compaction_path_a'
```

`grading_report.json` for run `20260501-124656-da0bd691`:

```json
{
  "verdict": "PASS",
  "check_results": [
    {
      "check": "snapshot",
      "passed": true,
      "command": "uv run python -m benchmarks.ai_verification.checks.check_compaction_path_a",
      "output": "PASS: Path A compaction deterministic proof succeeded\n",
      "exit_code": 0
    }
  ],
  "ai_review_enabled": false,
  "ai_verdict": "",
  "ai_reasoning": "",
  "ai_reviewer": ""
}
```

## Remaining Review Gate

- [ ] Claude review APPROVE
