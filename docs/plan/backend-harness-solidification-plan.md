# Backend Harness Solidification Plan

Status: ACTIVE.

Last updated: 2026-05-06

## Purpose

This is the durable backend-first plan that supersedes the comms-only BHF/B0-B8 planning chain. It exists so a builder can start from docs without reconstructing the current priority from `AGENTS_CONVERSATION.MD`.

Current direction: make the backend harness and backend-facing surfaces solid before any TUI implementation work. `TUI_PLAN.md` is locked but parked until B6 closes or the user explicitly overrides.

## Source Inputs

- `AGENTS_CONVERSATION.MD` Entry 1950
- `next_remaining_plan.md`
- `next_remaining_todo.md`
- `docs/plan/ai-verification-harness-fixes-plan.md`
- `docs/plan/deferred/modular_migration_todo.md`
- `docs/features/backend_features.md`
- `docs/features/inventory.md`
- `TUI_PLAN.md`

## Standing Rules

### B0 — Backend-First Boundary

Backend Harness Solidification is the active priority. Do not start TUI implementation until B6 closes or the user explicitly overrides.

The active docs must keep this order visible:

```text
B1 audit/gap map
B2 deterministic verdict truthfulness
B3 scenario contract hardening
B4 structured artifacts and batch reporting
B5 infra classifier and retry validation
B6 backend feature surface coverage
TUI_PLAN.md TUI-0..TUI-5
```

### B8 — Deferred Roadmap Hygiene

Do not silently implement deferred backend items. If a deferred trigger fires, post a Concern first.

Deferred unless user redirects:

- Tier 2 Item/Turn/Thread
- Tier 2.2 broader transport suite beyond current local stdio/TCP shape
- Tier 2.3 turn/steer mid-flight protocol
- Tier 4.2 ephemeral fork
- Tier 4.3 sticky env per turn
- remote transport security/auth
- full reconnect/reattach semantics
- Web UI
- MCP server hosting
- vector retrieval
- multi-agent broker
- hard-abort cost limits
- tool-call execution memoization
- L3 broadening
- subagent permission enforcement
- scheduler fairness
- cross-session memory promotion
- full `/sandbox <mode>`

## Sequential Implementation Phases

### B1 — Current-State Audit And Gap Map

Goal: establish what is already implemented versus only documented.

Actions:

- Compare tracked files under `benchmarks/ai_verification/`, `benchmarks/tests/`, root `scripts/`, `evals/`, and backend unit tests against `docs/plan/ai-verification-harness-fixes-plan.md`.
- Verify whether hidden immutable tests, `must_not_change_files`, tool-family assertions, artifact reports, mixed infra classification, batch summaries, and current script behavior are actually implemented.
- Audit test isolation, documentation truthfulness, sandbox cleanup, and cross-language LSP regression risk.
- Store `autocode/docs/qa/test-results/<ts>-backend-harness-audit.md`.

Exit:

- A concrete bug/gap list exists and maps each gap to B2-B6 or B7.
- No TUI implementation starts while B1/B2 blockers remain.

### B2 — Deterministic Verdict Truthfulness

Goal: eliminate false PASS classes.

Actions:

- Add or verify deterministic tests for zero pytest collection, missing grading command, missing final grading, empty behavior when behavior is required, hidden-test failure, no-op pass, visible-test rewrite, and vacuous `no_regression_after_pass`.
- Ensure run summaries expose the failing assertion clearly.
- Preserve mixed infra signals instead of flattening them into ambiguous outcomes.

Primary files:

- `benchmarks/ai_verification/run_scenario.py`
- `benchmarks/ai_verification/artifact_grader.py`
- `benchmarks/ai_verification/turn_grader.py`
- `benchmarks/ai_verification/infra_classifier.py`
- `benchmarks/tests/test_ai_verification_substrate.py`
- `benchmarks/tests/test_hfix_structured_trace.py`

Exit:

- Focused RED->GREEN deterministic tests prove each false-PASS class fails correctly.

### B3 — Scenario Contract Hardening

Goal: make scenarios enforce intended behavior, not mutable visible-test coincidence.

Actions:

- Add hidden immutable post-agent tests to Python scenarios that seed visible tests.
- Add `must_not_change_files` for reference tests where appropriate.
- Convert literal `edit_file` requirements to semantic `file_write` family requirements unless the literal tool is the feature being tested.
- Tighten Redis, KVStore/multi-turn, ask-user, todo/config/slugify contracts so visible-test mutation cannot mask behavior.
- Replace brittle static/product assertions with explicit scenario requirements or proper browser/build checks where those scenarios remain in scope.

Exit:

- Seeded-test scenarios cannot PASS by rewriting the tests.
- Scenario lint flags seeded visible tests without hidden tests or explicit mutation policy.

### B4 — Structured Artifacts And Batch Reporting

Goal: make every run diagnosable from structured artifacts.

Actions:

- Always write `artifact_report.json`, `trajectory_report.json`, `turns.json`, `tool_calls.jsonl`, `grading_report.json`, and `run_summary.json` when a run starts, including failure paths.
- Persist detailed artifact assertion results, not just booleans.
- Keep changed-file manifests focused on relevant source/test/product files while ignoring generated bytecode/noise.
- Add or verify current-batch reporting through `--run-ids`, `--since-run-id`, or batch manifests.

Exit:

- A failed live run can be triaged from JSON artifacts without first reading free-form transcript.
- Fresh summaries no longer mix historical runs unless explicitly requested.

### B5 — Infra Classifier And Retry Validation

Goal: separate provider/gateway/setup failures from agent behavior failures.

Actions:

- Cover gateway unreachable, 429/rate-limit, 5xx, timeouts, LiteLLM/OpenRouter error events, missing imports/dependencies, no structured stream, sandbox/preflight failure, and mixed infra+agent signals.
- Preserve the supervised retry schedule for live runs:
  `5s, 30s, 1m, 2m, 3m, 4m, 5m, 6m, 7m, 8m, 9m, 10m, 20m, 30m, 1h, 2h, 3h, 4h, 5h, 6h, 7h, 8h, 9h, 10h`.
- Keep deterministic tests network-free.

Exit:

- Live verdicts classify as `PASS`, `FAIL`, `INFRA_FAIL`, or mixed infra+agent with explicit reason tags.
- Retry exhaustion produces an honest infra deferral.

### B6 — Backend Feature Surface Coverage Without TUI

Goal: prove backend surfaces required by future TUI binding without launching Rust TUI.

Actions:

- Add or verify deterministic/headless coverage for thinking-token streaming, tool events, task/todo/subagent projection, context assembly, memory bootstrap/list/read/write, PEV/Ralph/entropy seams, cost/cache telemetry, KAIROS tick dispatch, and stdio/TCP/headless transport equivalence.

Primary files:

- `autocode/src/autocode/backend/headless_runner.py`
- `autocode/src/autocode/backend/headless_schema.py`
- `autocode/src/autocode/backend/server.py`
- `autocode/src/autocode/backend/chat.py`
- `autocode/src/autocode/backend/transport.py`
- `autocode/src/autocode/backend/dispatcher.py`
- `autocode/src/autocode/agent/loop.py`
- `autocode/tests/unit/test_backend_server.py`
- `autocode/tests/unit/test_backend_dispatcher.py`
- `autocode/tests/unit/test_headless_runner.py`

Exit:

- Backend surfaces needed by TUI binding are verified without a TUI.
- Remaining frontend-only dependencies are logged before TUI work resumes.

## Parallel Cleanup Track

### B7 — Modular Backend Follow-Through

This can run in parallel with B2-B6 if a separate builder is available; otherwise it follows B6.

Open items from `docs/plan/deferred/modular_migration_todo.md`:

- Narrow `autocode.backend.chat.ChatHost` into a real public service surface instead of relying on `BackendServer` internals.
- Rename `autocode/rtui/src/backend/pty.rs` or restore a real PTY-backed spawn path; preserve backend stderr on the live user path.
- Remove dead `ChildGuard` / resize scaffolding if spawn-managed path remains stdio-based.
- Expand transport conformance beyond current session/command/status seed surface.
- Tighten or document the `RpcApplication` host-adapter protocol.
- Decide/document TCP single-client behavior.
- Warn or refuse non-loopback `serve --transport tcp --host ...` binds by default.
- Replace fire-and-forget TCP drain tasks with a back-pressure-safe writer strategy.
- Verify Textual and legacy UI entrypoints consume `autocode.app.commands` cleanly.

## Required Closeout Validation

Before claiming backend harness solidity:

```bash
uv run pytest benchmarks/tests -q
uv run pytest autocode/tests/unit -q
git diff --check
```

Also run the focused eval runner gate for `evals/cases` and any focused tests for touched modules. If the gateway is healthy, run one supervised canary batch with the long retry policy and classify live failures honestly.

Store a consolidated artifact at:

```text
autocode/docs/qa/test-results/<ts>-backend-harness-solidification.md
```
