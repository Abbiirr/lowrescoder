# Archived Thread: Benchmark Harness Remediation

### Entry 659
**Date:** 2026-03-10
Agent: Codex | Role: Reviewer/Architect | Layer: 4 | Context: Implementing approved harness-first benchmark remediation plan | Intent: Apply run_id-scoped isolation, provider-gated health checks, explicit failure evidence, and validation coverage
Directed to: Claude, User

**Type: Pre-task Intent**

Plan:
- Implement `run_id`-scoped progress/lock handling and unique Docker container naming in the benchmark runner and Docker helpers.
- Move pre-task health checks behind the adapter boundary so only Ollama-backed AutoCode runs probe Ollama.
- Extend task artifacts/failure typing with explicit timeout source, grading-launch evidence, and Docker state evidence; update infra counting accordingly.
- Update the benchmark wrapper to propagate a single sweep `run_id` and add the approved `tb-002-fix-git` deterministic hint.
- Add unit coverage for collisions, preflight behavior, classification/evidence capture, and revised prompt guidance; store test results artifact after validation.

Priority: High
Tools Used: Read, Analysis

---

### Entry 660
**Date:** 2026-03-10
Agent: Codex | Role: Reviewer/Architect | Layer: 4 | Context: Completed harness-first benchmark remediation implementation | Intent: Record delivered changes, verification artifacts, and resolve the pre-task thread
Replying to: User
Directed to: Claude, User

**Type: Task Completion**

Completed:
- Added `run_id`-scoped progress, lock, and run-contract handling in `scripts/benchmark_runner.py`, and required `--run-id` for `--resume`.
- Scoped Docker container names to `run_id` and captured Docker inspect state for benchmark failure evidence in `scripts/docker_helpers.py`.
- Moved provider preflight checks behind the adapter boundary by adding `pre_task_healthcheck()` to the adapter protocol and implementing Ollama-only checks in `scripts/adapters/autocode_adapter.py`.
- Extended benchmark artifacts with `failure_type` and `failure_evidence`, and updated infra-fail counting to key off explicit classification instead of generic `error` truthiness.
- Strengthened prompt steering with first-pass source candidates, zero-diff recovery guidance, repeated-failure warnings, and bookkeeping-file filtering.
- Updated the benchmark wrapper to propagate a single sweep `BENCHMARK_RUN_ID` and added the approved safe-recovery hint to `scripts/e2e/external/fixtures/b9/tb-002-fix-git/task.md`.

Verification:
- `docs/qa/test-results/20260310-065404-benchmark-harness-remediation-ruff-rerun3.md`
- `docs/qa/test-results/20260310-065408-benchmark-harness-remediation-rerun3.md`

Notes:
- Validation covered focused Ruff and unit pytest runs for the touched harness code.
- Benchmark reruns were not executed as part of this implementation pass.

Status: RESOLVED — Harness-first benchmark remediation plan implemented and verified with focused unit and lint artifacts.

Priority: High
Tools Used: ApplyPatch, Ruff, Pytest
