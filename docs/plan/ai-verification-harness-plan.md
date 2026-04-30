# AI-Driven Verification Harness Plan

Date: 2026-04-29  
Status: IN PROGRESS — Milestones 1–5 + 7 complete; 6 pending (needs operator input); 73 scenario files, 71 runnable, 100% canary pass rate; 67 E2E simulations PASS (94.4%); matrix fully covered (all 7 categories × 3 difficulties); 1252 dashboard runs

## Goal

Create a repeatable "agent as tester" layer for:

- backend feature coding
- frontend feature coding
- refactor/cleanup
- migration
- dirty-codebase rescue
- repo initialization from scratch
- long multi-step work with evolving requirements

## Architecture

### 1. Scenario Generator

- Uses Codex/Claude-style prompts to generate new tasks each run.
- Inputs: category, difficulty, target stack, duration, required artifacts.
- Output: frozen scenario JSON so each run is reproducible.

### 2. Sandbox Repo Builder

- Creates isolated repo under `sandboxes/ai-verification/<run_id>/`.
- Can initialize new repos or copy/mutate existing fixtures.
- Injects dirty code, failing tests, TODOs, partial migrations, bad abstractions, etc.

### 3. Agent Runner

- Runs target agent through existing adapter style:
  - autocode
  - codex
  - claude
- No TUI required initially.
- Captures stdout/stderr, transcript, wall time, exit status, diffs.

### 4. Verifier/Grader

- Deterministic checks first: tests, lint, typecheck, build, snapshot checks.
- AI review second: Codex/Claude reviews diff and behavior against task spec.
- Produces structured verdict: `PASS`, `FAIL`, `PARTIAL`, `INFRA_FAIL`.

### 5. Artifact Capture

- Store all prompts, generated repo seed, final diff, test logs, agent transcript, review verdict, timings.
- Canonical path: `autocode/docs/qa/test-results/ai-verification/<run_id>/`
- Summary index: `autocode/docs/qa/test-results/ai-verification/index.md`

## Scenario Categories

| Category | Description |
|---|---|
| `backend_feature` | Add API/service behavior with tests |
| `frontend_feature` | Build UI component or flow (no TUI dependency initially) |
| `refactor` | Preserve behavior while improving structure |
| `migration` | Move modules/API/schema with compatibility |
| `dirty_cleanup` | Fix broken tests, bad formatting, dead code, drifted docs |
| `repo_init` | Create a new small app/library from scratch |
| `long_horizon` | 5–10 step task with docs, tests, follow-up fixes |

## Execution Flow

```sh
uv run python benchmarks/ai_verification/generate_scenario.py \
  --category backend_feature \
  --difficulty medium \
  --seed random

uv run python benchmarks/ai_verification/run_scenario.py \
  --agent autocode \
  --scenario <scenario.json>

uv run python benchmarks/ai_verification/grade_run.py \
  --run-id <run_id>
```

## Safety Rules

- Every run uses an isolated sandbox.
- No commits by agents.
- Network off by default unless scenario explicitly allows it.
- Generated tests must be saved before agent execution.
- AI grader cannot override deterministic failures; it can only explain them.

## Milestones

1. [DONE] Define scenario schema + artifact layout — `benchmarks/ai_verification/schema.py`
2. [DONE] Add 49 hand-written canary scenarios across 5 stacks (Python, Go, Rust, TypeScript, Java) — `benchmarks/ai_verification/canary_scenarios/`
3. [DONE] Add deterministic runner/grader — `run_scenario.py`, `grade_run.py`, `sandbox_builder.py`, `validate_canaries.py`
4. [DONE] Add AI scenario generation with seed persistence — `generate_scenario.py` (LLM call + dry-run mode)
5. [DONE] AI review grading — `_run_ai_review` complete: gateway call, JSON parse, graceful degradation, review.md artifact
6. [ ] Run one canary per category with a real agent (`--agent autocode`)
7. [DONE] Dashboard with pass-rate trend tracking — `build_dashboard.py` → `dashboard.md` (406 runs, 100% pass rate)

## Fixtures

| Fixture | Stack | Category |
|---|---|---|
| `backend_health_endpoint` | Python/FastAPI | brownfield backend |
| `refactor_extract_function` | Python | brownfield refactor |
| `go_http_server` | Go/net/http | brownfield backend |
| `ts_todo_api` | TypeScript/Express | brownfield backend (failing tests) |
| `rust_string_utils` | Rust | brownfield library |
| `python_sqlite_migration` | Python/SQLAlchemy | brownfield migration |
| `python_flask_app` | Python/Flask | brownfield frontend |
| `python_multistep_service` | Python | brownfield long-horizon |
| `go_middleware_server` | Go | brownfield refactor + dirty_cleanup |
| `python_paginated_api` | Python/FastAPI | brownfield backend (hard) |
| `java_calculator` | Java/Maven | brownfield backend (skip: no mvn) |
| `python_async_api` | Python/FastAPI | brownfield backend (async job queue) |
| `rust_panic_service` | Rust | brownfield migration (panic→Result) |
| `rust_buggy_stats` | Rust | brownfield dirty_cleanup (4 bugs + dead code) |
| `go_items_handler` | Go | brownfield refactor (global vars → Server struct) |
| `go_buggy_kvstore` | Go | brownfield dirty_cleanup hard (nil map + missing lock) |
| `go_legacy_products` | Go | brownfield migration + backend hard (monolithic Handler → ServeMux) |
| `rust_boxed_errors` | Rust | brownfield migration hard (Box<dyn Error> → AppError enum) |
| `python_monolith_api` | Python/FastAPI | brownfield refactor hard (monolith → APIRouter modules) |
| `python_blog_app` | Python/Flask | brownfield frontend (blog with admin, tags, export) |
| `rust_number_utils` | Rust | brownfield long_horizon easy (abs → parity → clamp) |
| `python_path_migration` | Python | brownfield migration easy (os.path → pathlib.Path) |
| (greenfield fresh) | Python/Go/Rust | repo_init (scenarios 08, 17, 21, 25, 29, 38) |

## Canary Validation Results (2026-04-29, Iteration 9)

**39/39 runnable scenarios PASS** (2 skipped: TypeScript=no npm, Java=no mvn)  
41 total scenarios across 7 categories × 3 difficulties (easy/medium/hard) and 5 stacks.  
Full coverage: no gaps in the 7×3 category×difficulty matrix.

QA artifacts:
- `autocode/docs/qa/test-results/20260429-115100-ai-verification-harness-milestone-1-3.md`
- `autocode/docs/qa/test-results/20260429-122800-ai-verification-harness-milestone-5-7.md`
- `autocode/docs/qa/test-results/20260429-123500-ai-verification-harness-iteration-3.md`
- `autocode/docs/qa/test-results/20260429-125000-ai-verification-harness-iteration-4.md`
- `autocode/docs/qa/test-results/20260429-133000-ai-verification-harness-iteration-5.md`
- `autocode/docs/qa/test-results/20260429-143000-ai-verification-harness-iteration-6.md`
- `autocode/docs/qa/test-results/20260429-153000-ai-verification-harness-iteration-7.md`
- `autocode/docs/qa/test-results/20260429-163500-ai-verification-harness-iteration-9.md`
- `autocode/docs/qa/test-results/20260429-173500-ai-verification-harness-iteration-10.md`
- `autocode/docs/qa/test-results/20260430-183500-ai-verification-harness-iteration-11.md`

Run index: `autocode/docs/qa/test-results/ai-verification/index.md`
Dashboard: `autocode/docs/qa/test-results/ai-verification/dashboard.md` (351 runs, 100% pass rate)
