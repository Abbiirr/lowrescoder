# AI Verification Harness Fixes Plan

Date: 2026-05-03
Owner: Codex as current builder unless user redirects
Scope: AI verification harness quality, observability, and coverage
Status: Builder-complete. Deterministic tests green (39 substrate, 343 benchmark, 2244 unit). Default long supervised retry policy is implemented for transient `INFRA_FAIL`. Live `ask-user-scripted` and fresh multi-turn canaries remain gateway-deferred/queued. Awaiting Claude review APPROVE or User acceptance of residual gateway-deferred risk.

## Purpose

This plan fixes the harness weaknesses found during the multi-turn quality run recorded in:

- `autocode/docs/qa/test-results/20260501-194445-ai-verification-multiturn-harness-quality.md`
- `AGENTS_CONVERSATION.MD` Entries 1741 and 1742

The goal is not to make every model pass every scenario. The goal is to make every harness verdict explainable, reproducible, and tied to structured evidence about final behavior and tool trajectory.

## Current Weaknesses

1. Tool calls are visible but not first-class.
   - `meta.json.tool_calls` gives only an aggregate count.
   - `agent_transcript.jsonl` records tool names mostly inside free-form `item_completed.result` strings such as `edit_file: completed`.
   - Tool coverage is inferred by brittle parsing.

2. Scenario tool intent is not enforced.
   - Prompts say "use search_text" or "use git_diff", but grading mostly checks final tests.
   - A scenario can pass without proving it exercised the feature it is supposed to cover.

3. Multi-turn grading is not structured enough.
   - Per-turn grading is printed to stdout but not stored as a dedicated structured artifact.
   - To audit regressions, readers reconstruct state from transcript and logs.

4. No-op and weak PASS cases are possible.
   - Refactor scenarios may pass if the seed already passes and the agent does nothing.
   - Some categories need diff, structural, or forbidden-file-change predicates in addition to tests.

5. Coverage gaps remain for `docs/features/inventory.md`.
   - `semantic_search` was not proven by the large-codebase run, which used `search_text`.
   - No clear real-agent canaries exist for `spawn_subagent`.
   - No clear real-agent canaries exist for interactive `ask_user` in headless multi-turn mode.

6. Provider latency can contaminate harness results.
   - Runs take several minutes even for small scenarios.
   - Empty turns, 429s, and blocking HTTP reads need to be separated from model failure.

## Research Grounding

Primary-source patterns:

- OpenTelemetry GenAI semantic conventions model tool execution as a first-class operation named `execute_tool`, with `gen_ai.tool.name` required and tool call id, type, arguments, and result as structured attributes. Args/results are sensitive and should be opt-in or redacted. Source: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- Vertex AI agent evaluation separates final response evaluation from trajectory evaluation and defines exact, in-order, and any-order trajectory matching over tool-call sequences. Source: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-agents
- LangSmith recommends breaking evaluation into final response, trajectory, and single-step evaluation; its complex-agent example explicitly records tool-call trajectory. Sources: https://docs.langchain.com/langsmith/evaluate-complex-agent and https://docs.langchain.com/langsmith/evaluation-concepts
- MLflow GenAI supports multi-turn conversation evaluation and tool-call correctness scoring, including exact/fuzzy and ordered/unordered checks. Sources: https://mlflow.org/docs/latest/genai/eval-monitor/running-evaluation/multi-turn/ and https://mlflow.org/docs/latest/api_reference/python_api/mlflow.genai.html
- Phoenix/Arize treats traces as the substrate for debugging model calls, retrieval, tool use, custom logic, and eval scoring. Source: https://arize.com/docs/phoenix
- OpenAI Evals frames evals as system-level tests and supports advanced tool-using systems through completion functions. Source: https://github.com/openai/evals

Design conclusion: AutoCode should keep deterministic final grading, but add structured trajectory grading and run diagnostics. Do not rely on free-form transcript text for feature coverage.

## Design Principles

1. Final correctness and trajectory correctness are separate gates.
2. Tool execution evidence must be structured, queryable, and privacy-safe.
3. Scenario requirements must be machine-checkable.
4. Multi-turn sessions must expose per-turn state, not only final state.
5. Harness infrastructure failures must be distinct from agent failures.
6. Existing artifacts remain readable; new artifacts add evidence without deleting old files.

## Builder Execution Contract

This is the builder-facing contract for HFIX. Do not start P3b until these gates close unless the user redirects.

**Primary implementation files:**

| Area | Existing owner file(s) | Expected changes |
|---|---|---|
| Scenario schema | `benchmarks/ai_verification/schema.py`, `benchmarks/ai_verification/scenario_yaml.py` | Add typed trajectory/artifact/turn assertion dataclasses and YAML/JSON loading. |
| NDJSON parsing | `benchmarks/ai_verification/ndjson_runner.py`, `autocode/src/autocode/backend/headless_schema.py` | Parse/validate structured tool events while keeping old `item_*` compatibility. |
| Real run orchestration | `benchmarks/ai_verification/run_scenario.py` | Compose verdicts from infra, deterministic checks, artifact assertions, trajectory assertions, turn assertions; write new artifacts. |
| Multi-turn orchestration | `benchmarks/ai_verification/multiturn_runner.py` | Capture per-turn grading, tool histogram, timing, and regression state. |
| New graders | `benchmarks/ai_verification/trajectory_grader.py`, `benchmarks/ai_verification/artifact_grader.py` | Add deterministic graders for tool trajectory and patch/file assertions. |
| New artifact helpers | `benchmarks/ai_verification/run_artifacts.py` or equivalent | Centralize writing `tool_calls.jsonl`, `turns.json`, `trajectory_report.json`, `run_summary.json`. |
| Summary/reporting | `benchmarks/ai_verification/summarize_runs.py` | Scan run dirs and report verdict counts, infra reasons, tool coverage, assertion failures, slowest runs. |
| Tests | `benchmarks/tests/test_ai_verification_substrate.py` plus focused new files if needed | Add RED-first tests for each HFIX phase and preserve current substrate behavior. |
| Docs | `benchmarks/ai_verification/HARNESS_RUNNER_INSTRUCTIONS.md`, `benchmarks/ai_verification/MULTITURN_GUIDE.md`, `docs/features/inventory.md` | Document the new artifact contract, assertion schema, and feature-coverage expectations. |

**Non-goals for this pass:**

- Do not change agent product behavior outside the harness unless the harness cannot observe an existing event.
- Do not require broad real-agent sweeps to close HFIX; one fresh representative multi-turn run is required, broad sweeps remain provider/gateway dependent.
- Do not remove old artifacts or break old scenarios. New typed assertions are additive and opt-in until migration is explicit.

**Stop conditions:**

- If a deterministic scenario can PASS when its grading command did not execute, stop and fix verdict composition before adding more canaries.
- If tool coverage depends on free-form transcript text after HFIX-1, stop and fix structured event extraction.
- If provider latency/429/empty turns contaminate verdicts, classify as `INFRA_FAIL` and do not count the run as a model/agent failure.
- Supervised live runs retry transient `INFRA_FAIL` by default with the long infra-recovery schedule `5s,30s,1m,2m,3m,4m,5m,6m,7m,8m,9m,10m,20m,30m,1h,2h,3h,4h,5h,6h,7h,8h,9h,10h`; at a 600s attempt timeout this gives more than 57 hours of recovery window before final infra deferral.

## Proposed Artifact Set

Keep the existing per-run files:

- `scenario.json`
- `repo_seed/`
- `agent_transcript.jsonl`
- `diff.patch`
- `test_log.txt`
- `grading_report.json`
- `meta.json`

Add:

- `turns.json` - per-turn prompt, grading, timing, tool histogram, token counts
- `tool_calls.jsonl` - one structured record per tool execution
- `trajectory_report.json` - trajectory assertion results
- `run_summary.json` - compact human/machine summary

## Structured Tool Event Contract

Add new structured NDJSON events while keeping existing `item_started` and `item_completed` events for compatibility.

New events:

- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`

Minimal event shape:

```json
{
  "protocol_version": "0.2.0-harness",
  "type": "tool_call_completed",
  "thread_id": "thread-id",
  "turn_id": "turn-id",
  "item_id": "item-17",
  "tool_call_id": "call-id",
  "tool_name": "search_text",
  "tool_family": "search",
  "status": "success",
  "started_at": "2026-05-01T00:00:00Z",
  "finished_at": "2026-05-01T00:00:01Z",
  "duration_ms": 1000,
  "args_shape": {
    "pattern": "str",
    "path": "str"
  },
  "args_sha256": "redacted-hash",
  "result_bytes": 2048,
  "result_sha256": "redacted-hash",
  "result_preview": "",
  "error_type": null
}
```

Privacy defaults:

- Store argument shape and hash by default, not full arguments.
- Store result byte count and hash by default, not full result.
- Allow opt-in previews with `AUTOCODE_HARNESS_CAPTURE_TOOL_PREVIEWS=true`.
- Never capture full result for tools marked sensitive.

Tool family mapping:

| Family | Tools |
|---|---|
| file_read | `read_file`, `list_files`, `glob_files` |
| file_write | `write_file`, `edit_file`, `apply_patch`, `multi_edit` |
| search | `search_text`, `grep_content`, `search_code`, `semantic_search` |
| lsp | `find_definition`, `find_references`, `get_type_info`, `list_symbols`, `lsp_*` |
| shell | `run_command` |
| git | `git_status`, `git_diff`, `git_log` |
| planning | `todo_read`, `todo_write`, `create_task`, `update_task`, `list_tasks` |
| subagent | `spawn_subagent`, `check_subagent`, `cancel_subagent`, `list_subagents` |
| user_interaction | `ask_user` |
| cache | `list_tool_results`, `clear_tool_result`, `clear_tool_results` |

## Typed Scenario Assertions

Extend scenario schema with typed assertions. Keep legacy `expected_outcomes` for compatibility.

```json
{
  "trajectory_assertions": {
    "must_use_tools": ["search_text", "run_command"],
    "must_not_use_tools": ["write_file"],
    "must_use_tool_families": ["search", "shell"],
    "exact_tools": [],
    "in_order_tools": ["git_status", "git_diff", "run_command"],
    "any_order_tools": ["read_file", "edit_file"],
    "min_tool_calls": 2,
    "max_tool_calls": 80,
    "max_failed_tool_calls": 3
  },
  "artifact_assertions": {
    "must_change_files": ["config.py"],
    "must_not_change_files": ["test_pipeline.py"],
    "require_non_empty_diff": true,
    "forbid_noop_pass": true,
    "must_remove_text": ["NotImplementedError"],
    "must_contain_text": {
      "config.py": ["DEFAULT_NORMALIZE = True"]
    }
  },
  "turn_assertions": {
    "min_turns": 3,
    "max_turns": 4,
    "no_regression_after_pass": true,
    "require_final_turn_grading": true
  }
}
```

Trajectory matching modes:

- exact: predicted tool sequence equals reference sequence
- in-order: predicted sequence contains reference tools in order, allowing extra calls
- any-order: predicted sequence contains all required tools regardless of order
- family: predicted sequence contains at least one tool in each required family

## Per-Turn Artifact

Write `turns.json` for every real-agent run:

```json
[
  {
    "turn": 1,
    "prompt_kind": "initial",
    "prompt_sha256": "hash",
    "grading": "FAIL",
    "check_results": [
      {"check": "run_tests", "passed": false}
    ],
    "tool_histogram": {"read_file": 2, "edit_file": 1},
    "changed_files": ["store.py"],
    "tokens_in": 12345,
    "tokens_out": 678,
    "wall_time_s": 91.2,
    "empty_turn": false,
    "infra_signals": []
  }
]
```

This makes multi-turn regressions first-class. Example: the git-dirty run passed on turn 1 and final-failed after follow-ups. The harness should show that as a structured regression, not just stdout.

## Run Summary Artifact

Write `run_summary.json`:

```json
{
  "run_id": "20260501-...",
  "scenario_id": "canary-py-git-dirty-001",
  "verdict": "FAIL",
  "turn_count": 4,
  "tool_histogram": {"git_status": 1, "git_diff": 2, "edit_file": 18},
  "required_tools_satisfied": true,
  "trajectory_satisfied": false,
  "artifact_assertions_satisfied": false,
  "deterministic_checks_satisfied": false,
  "artifact_complete": true,
  "changed_files": ["math_utils.py"],
  "infra_fail_reason": ""
}
```

## Grading Composition

Final verdict should compose these layers:

1. Infrastructure health
2. Deterministic command checks
3. Artifact assertions
4. Trajectory assertions
5. Turn assertions
6. Optional AI review

Suggested verdict logic:

- `INFRA_FAIL`: sandbox setup failed, agent timeout with no usable transcript, grading command could not execute, provider produced empty turns due gateway/rate limit.
- `FAIL`: deterministic checks fail and no partial objective progress is proven.
- `PARTIAL`: some checks or typed assertions pass but final completion is missing.
- `PASS`: deterministic checks pass and all required typed assertions pass.

Top-level PASS must never be based only on an inverted fixture expectation or a missing command. Existing invariant from the compaction false-positive remains mandatory: check execution must be proven.

## Required Canaries

Add dedicated scenarios:

1. `semantic-search-required.yaml`
   - Large enough repo to justify semantic search.
   - `trajectory_assertions.must_use_tools: ["semantic_search"]`.
   - Grading fails if only `search_text` is used.

2. `spawn-subagent-required.yaml`
   - Long-horizon task with independent subtasks.
   - `must_use_tools: ["spawn_subagent", "check_subagent"]`.
   - Verifies subagent output is integrated into final patch.

3. `ask-user-scripted.yaml`
   - Ambiguous requirement.
   - Headless runner provides scripted response through `ask_user_callback`.
   - Requires `ask_user` and verifies selected branch.

4. `refactor-noop-guard.yaml`
   - Seed tests pass.
   - Requires non-empty diff and structural predicate.
   - Prevents false PASS when agent does nothing.

5. `multi-turn-regression.yaml`
   - Designed to pass after turn 1.
   - Later follow-up asks for an extension that can break prior behavior.
   - Requires `no_regression_after_pass: true`.

6. `tool-trajectory-git.yaml`
   - Requires `git_status` then `git_diff` before edit.
   - Verifies in-order trajectory matching.

## Builder TODO and Phase Gates

Each phase below is an implementation slice with tests, verification criteria, and an exit gate. Use RED-first tests where the change is behavioral.

### HFIX-0: Baseline and file map

Goal: prove the starting harness state and pin exact implementation ownership.

TODO:

- [ ] Run `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` and record the starting count/result in the HFIX artifact.
- [ ] Read `schema.py`, `scenario_yaml.py`, `ndjson_runner.py`, `multiturn_runner.py`, and `run_scenario.py`; note any file-ownership changes in the artifact.
- [ ] Pick whether new tests stay in `test_ai_verification_substrate.py` or split into focused files under `benchmarks/tests/`.
- [ ] Confirm P3b files are untouched in this pass.

Verification criteria:

- Existing substrate tests pass before HFIX code changes.
- The artifact records current known gaps: free-form tool parsing, no per-turn JSON, no typed assertions, weak no-op guard.

Exit gate:

- Baseline command result captured.
- Exact implementation files listed.
- No runtime product behavior changed.

### HFIX-1: Structured trace contract

Goal: make tool execution first-class evidence, not transcript text.

TODO:

- [ ] Extend `autocode/src/autocode/backend/headless_schema.py` with `tool_call_started`, `tool_call_completed`, and `tool_call_failed` event models or equivalent typed fields that validate with `validate_event()`.
- [ ] Emit structured tool events from `autocode/src/autocode/backend/headless_runner.py` around tool execution.
- [ ] Update `benchmarks/ai_verification/ndjson_runner.py::build_run_result()` to count typed tool events, while preserving old `item_started(kind="tool_execution")` compatibility.
- [ ] Add a `tool_calls.jsonl` writer in `run_scenario.py` or a shared artifact helper.
- [ ] Keep args/results privacy-safe by default: shape + hash + byte count; preview only behind `AUTOCODE_HARNESS_CAPTURE_TOOL_PREVIEWS=true`.

Tests:

- [ ] Unit: `validate_event()` accepts all three structured tool events.
- [ ] Unit: malformed tool events are rejected with a clear error.
- [ ] Unit: `build_run_result()` counts typed tool events.
- [ ] Unit: `build_run_result()` still counts legacy `item_started(kind="tool_execution")`.
- [ ] Unit: `tool_calls.jsonl` is emitted for both PASS and FAIL runs.

Verification criteria:

- Tool coverage can be computed from `tool_name`, not from `item_completed.result` string prefixes.
- `tool_calls.jsonl` contains one record per completed/failed tool execution with status and duration.
- No sensitive full arguments/results are captured unless the env var is set.

Exit gate:

- Existing substrate tests plus new trace-contract tests pass.
- A fixture or simulated run produces valid `agent_transcript.jsonl` and `tool_calls.jsonl`.

### HFIX-2: Typed scenario assertions and graders

Goal: make scenario intent machine-checkable.

TODO:

- [ ] Extend `ScenarioSpec` with `trajectory_assertions`, `artifact_assertions`, and `turn_assertions`; add dataclasses or typed dictionaries in `schema.py`.
- [ ] Extend `scenario_yaml.py` and JSON loading so assertions round-trip from YAML and JSON.
- [ ] Implement `benchmarks/ai_verification/trajectory_grader.py`.
- [ ] Implement `benchmarks/ai_verification/artifact_grader.py`.
- [ ] Include assertion result objects in `grading_report.json` without breaking existing report readers.
- [ ] Compose assertion failures into the final verdict: explicit required-tool or required-diff failure is `FAIL`, not `PASS`.

Tests:

- [ ] YAML loader preserves all new assertion blocks.
- [ ] JSON loader preserves all new assertion blocks.
- [ ] Trajectory exact, in-order, any-order, family, forbidden-tool, min/max tool-call tests.
- [ ] Artifact non-empty diff, required changed file, forbidden changed file, must-contain, must-remove tests.
- [ ] Verdict-composition test: deterministic checks pass but `must_use_tools` fails -> `FAIL`.
- [ ] Verdict-composition test: deterministic checks pass but `require_non_empty_diff` fails -> `FAIL`.

Verification criteria:

- The harness can prove a scenario exercised the intended feature.
- A scenario cannot PASS if its explicit typed assertions fail.
- Legacy scenarios without typed assertions still run unchanged.

Exit gate:

- All typed-grader tests pass.
- `grading_report.json` shows deterministic, trajectory, artifact, and turn assertion sections.

### HFIX-3: Per-turn and per-run artifacts

Goal: make multi-turn progression auditable without stdout reconstruction.

TODO:

- [ ] Extend `MultiturnRunResult` or a helper object to carry per-turn rows.
- [ ] Capture per-turn prompt kind, event count, grading result, check summary, tool histogram, changed files, wall time, empty-turn flag, and infra signals.
- [ ] Write `turns.json`.
- [ ] Write `trajectory_report.json`.
- [ ] Write `run_summary.json`.
- [ ] Add `infra_fail_reason` to `meta.json` and `run_summary.json`.

Tests:

- [ ] Simulated three-turn run writes three `turns.json` rows.
- [ ] Pass-then-regress simulated run records early PASS and final FAIL.
- [ ] Tool histogram in `run_summary.json` matches typed tool events.
- [ ] Changed files in `run_summary.json` match `diff.patch`.
- [ ] `grading_report.json` verdict references the relevant assertion/check evidence.

Verification criteria:

- A reader can answer "what failed on which turn?" from `turns.json` and `run_summary.json`.
- Multi-turn stdout is no longer the only source of per-turn grading state.

Exit gate:

- Per-turn/run artifact tests pass.
- A local simulated or fixture run writes all new artifacts.

### HFIX-4: Infrastructure classification

Goal: separate harness/provider failure from agent failure.

TODO:

- [ ] Detect empty turn: no tool events, no assistant message, and zero usage.
- [ ] Detect likely rate limit/provider failure from 429/rate-limit strings and blocked HTTP/read timeout signals.
- [ ] Detect per-turn timeout and whole-scenario timeout separately.
- [x] Add a subprocess-isolated per-task worker boundary for benchmark lane tasks so non-cooperative adapter cancellation and spawned child processes cannot stall the parent lane indefinitely.
- [x] Prefer structured `failure_evidence.transient_class` retry classification over broad error-substring matching, with legacy keyword fallback only when no structured class is present.
- [x] Make supervised scenario runs retry transient `INFRA_FAIL` by default with the long infra-recovery schedule and parent `retry_report.json` artifact.
- [ ] Classify sandbox setup/grading command execution failures as `INFRA_FAIL`.
- [ ] Ensure deterministic test failures still classify as `FAIL` or `PARTIAL`.

Tests:

- [ ] Empty-turn fixture -> `INFRA_FAIL`.
- [ ] 429/rate-limit fixture -> `INFRA_FAIL`.
- [ ] Sandbox build failure -> `INFRA_FAIL`.
- [x] Per-task worker timeout kills the worker process group, including a child process that ignores `SIGTERM`.
- [x] Cancellation-suppressing adapter path returns a structured `INFRA_FAIL` instead of hanging the lane.
- [x] Structured transient classes trigger one retry; structured non-transient classes override broad legacy keywords and do not retry.
- [x] Supervised retry schedule and retry-until-PASS behavior are covered by tests; default schedule plus a 600s attempt timeout exceeds 57 hours total recovery window.
- [ ] Grading command missing target file/module -> `INFRA_FAIL` or explicit check-execution failure, never `PASS`.
- [ ] Real assertion failure with executed tests -> `FAIL`, not `INFRA_FAIL`.

Verification criteria:

- Infra issues cannot lower model quality scores.
- Agent failures cannot hide behind infra classification.

Exit gate:

- Infra-classification tests pass.
- `meta.json`, `run_summary.json`, and `grading_report.json` agree on infra status.

### HFIX-5: Required canaries and feature inventory coverage

Goal: close the known feature-surface gaps with typed scenarios.

TODO:

- [ ] Add `semantic-search-required.yaml` with `must_use_tools: ["semantic_search"]`.
- [ ] Add `spawn-subagent-required.yaml` with `must_use_tools: ["spawn_subagent", "check_subagent"]` or the current exact tool names.
- [ ] Add `ask-user-scripted.yaml` with a scripted headless `ask_user` response path.
- [ ] Add `refactor-noop-guard.yaml` with `require_non_empty_diff: true`.
- [ ] Add `multi-turn-regression.yaml` with `no_regression_after_pass: true`.
- [ ] Add `tool-trajectory-git.yaml` with in-order `git_status -> git_diff`.
- [ ] Update `docs/features/inventory.md` so each canary maps to the feature it proves.

Tests:

- [ ] Fixture validation for each canary.
- [ ] Deterministic grader tests for each canary's typed assertions.
- [ ] If live provider is stable: one real-agent run for a lightweight required-tool canary.
- [ ] If live provider is unstable: store the blocker as `INFRA_FAIL` evidence and do not count it as model failure.

Verification criteria:

- `semantic_search`, `spawn_subagent`, and `ask_user` no longer rely on manual interpretation for coverage.
- The no-op refactor scenario fails if the agent makes no patch.

Exit gate:

- All required canaries load and validate.
- At least one fresh run artifact demonstrates typed assertion enforcement.
- `docs/features/inventory.md` has no stale claim that these features are covered only by prose.

### HFIX-6: Summary command, docs, and closeout verification

Goal: make the fixed workflow usable across hundreds of run directories.

TODO:

- [x] Add `benchmarks/ai_verification/summarize_runs.py`.
- [x] Summary output includes verdict counts, infra fail reasons, required-tool coverage, assertion failures, missing artifacts, and slowest runs.
- [x] Surface malformed NDJSON predicates as explicit grader warnings so scenario YAML typos do not look like ordinary missing evidence.
- [x] Harden `multi-turn-regression.yaml` so the original `test_get_set` and `test_delete` checks must remain present after agents are allowed to edit tests.
- [x] Update `HARNESS_RUNNER_INSTRUCTIONS.md` with the new artifacts and assertion contract.
- [x] Update `MULTITURN_GUIDE.md` with per-turn artifact interpretation and regression semantics.
- [ ] Store the closeout artifact at `autocode/docs/qa/test-results/<ts>-hfix-ai-verification-harness.md`.
- [ ] Post review request in comms with test results, representative run IDs, and known residual risk.

Tests:

- [x] Summary command handles old runs without new artifacts.
- [x] Summary command flags missing `turns.json`, `tool_calls.jsonl`, `trajectory_report.json`, or `run_summary.json` for new-format runs.
- [x] Summary command reports tool coverage matrix from typed events.
- [x] Summary command reports structured assertion failures from trajectory, turn, and artifact reports.
- [x] Malformed `cache_hit_ratio>=` predicates fail gracefully and report a `WARN: malformed predicate ...` warning.
- [x] Docs mention all new artifacts and verdict composition.

Verification criteria:

- Running the summary over a mixed old/new sample does not crash.
- New-format runs show typed tool coverage and assertion failure detail.
- Documentation is enough for a future agent to run, inspect, and interpret HFIX artifacts.

Exit gate:

- `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` passes.
- Any new focused HFIX tests pass.
- `git diff --check` passes.
- A fresh multi-turn run writes `tool_calls.jsonl`, `turns.json`, `trajectory_report.json`, `run_summary.json`, `grading_report.json`, and `meta.json`.
- Claude reviews and APPROVEs, or User explicitly accepts remaining risk.

## Verification Matrix

| Gate | Required command/evidence | Pass criterion |
|---|---|---|
| Baseline substrate | `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` | Existing tests pass before and after HFIX. |
| Trace contract | Focused schema/parser tests | Typed tool events validate; legacy events still count. |
| Typed assertions | Focused trajectory/artifact grader tests | Required-tool and required-diff failures force `FAIL`. |
| Per-turn artifacts | Simulated multi-turn test | `turns.json` has one row per turn and records pass/regress state. |
| Infra classification | Synthetic empty-turn/429/timeout/sandbox tests | `INFRA_FAIL` only for infra; deterministic failures remain `FAIL`/`PARTIAL`. |
| Benchmark timeout boundary | Focused benchmark-runner subprocess worker tests | Parent lane returns `INFRA_FAIL` on task timeout and kills worker process groups. |
| Canaries | Fixture validation plus at least one fresh run | Required feature canaries load, grade, and produce evidence. |
| Summary/docs | Summary command test plus doc diff | Old/new run dirs handled; docs describe artifact contract. |
| Hygiene | `git diff --check` | No whitespace errors. |

## Final HFIX Exit Gate

HFIX closes only when all of these are true:

- [x] All HFIX test gates above pass — 39 substrate, 343 benchmark, 2244 unit GREEN
- [~] A fresh multi-turn run produces the new artifacts — gateway-deferred; next live attempt should use the default long supervised retry policy
- [x] `grading_report.json` verdicts trace to structured check/tool/turn evidence
- [x] No-op refactor PASS is blocked
- [x] Explicit required-tool failure cannot PASS
- [x] Missing grading command/module/file cannot PASS
- [~] `semantic_search`, `spawn_subagent`, and `ask_user` have canaries or an explicit documented unsupported marker with User acceptance — canaries exist; live enforcement gateway-deferred
- [x] `docs/features/inventory.md`, `HARNESS_RUNNER_INSTRUCTIONS.md`, and `MULTITURN_GUIDE.md` are updated
- [x] Closeout artifact is stored under `autocode/docs/qa/test-results/` — `20260503-105128-hfix-ai-verification-harness.md`
- [ ] Claude posts APPROVE, or User explicitly accepts a listed residual risk

## Compatibility

- Old artifacts remain readable.
- New fields are optional for old scenarios.
- New typed assertions are opt-in at first.
- After the new canaries are green, require typed assertions for any new scenario.

## Resolved Decisions

1. Protocol version: bumped to `0.2.0-harness` for structured tool events.
2. Args/results capture policy: hash/shape only by default, preview opt-in via `AUTOCODE_HARNESS_CAPTURE_TOOL_PREVIEWS=true`.
3. Typed assertions: mandatory for new scenarios; legacy scenarios migrate gradually.
4. Failed typed trajectory assertions: downgrade to FAIL (not PARTIAL) when scenario explicitly requires the tool/trajectory.

## Success Criteria

The harness is considered fixed when:

- Tool coverage can be computed from structured events without parsing free-form result strings.
- Each feature-workflow scenario can assert required tools or tool families.
- Per-turn grading is stored in `turns.json`.
- `run_summary.json` answers what happened in one read.
- No-op refactor PASS is blocked.
- `semantic_search`, `spawn_subagent`, and `ask_user` each have dedicated canaries or an explicit unsupported marker.
- Infrastructure failures are distinguishable from agent failures.
