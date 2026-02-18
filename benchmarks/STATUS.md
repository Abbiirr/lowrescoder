# Benchmark Gate Status — Phase 5 Readiness

> Updated: 2026-02-18

## Blocker Status

| ID | Lane | Status | Score | Artifact |
|----|------|--------|-------|----------|
| B6 | React Calculator (external project) | IN_PROGRESS | — | Generating via AgentLoop |
| B7 | SWE-bench Verified subset | NOT_STARTED | — | — |
| B8 | SWE-bench Bash-Only control | NOT_STARTED | — | — |
| B9 | Terminal-Bench subset | NOT_STARTED | — | — |
| B10 | Multi-SWE-bench multilingual | NOT_STARTED | — | — |
| B11 | BaxBench backend/security | NOT_STARTED | — | — |
| B12 | SWE-Lancer | NOT_STARTED | — | Access TBD |
| B13 | CodeClash | NOT_STARTED | — | Access TBD |
| B14 | LiveCodeBench | NOT_STARTED | — | — |

## Pass Criteria

- B6: score >= 60 (standard threshold, no override)
- B7-B14: TBD after calibration runs (R0)

## Directory Structure

```
benchmarks/
  STATUS.md              — This file
  B6-react-calculator/   — Generated React project (AUTOCODE_BENCH_TARGET_DIR)
  B7-swebench-verified/  — SWE-bench Verified subset results
  B8-swebench-bash/      — SWE-bench Bash-Only results
  B9-terminal-bench/     — Terminal-Bench results
  B10-multi-swebench/    — Multi-SWE-bench results
  B11-baxbench/          — BaxBench results
  B12-swe-lancer/        — SWE-Lancer results
  B13-codeclash/         — CodeClash results
  B14-livecodebench/     — LiveCodeBench results
```

## Workflow

1. AutoCode AgentLoop generates project from scratch in B6-react-calculator/
2. Benchmark scorer runs against the generated project
3. Score >= 60 required to close B6
4. B7-B14 follow same pattern: generate/run → score → store artifact
