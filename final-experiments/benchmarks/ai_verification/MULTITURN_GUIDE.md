# Multi-Turn Testing Guide

This guide covers multi-turn scenario design and execution for the AI verification harness.

## What Multi-Turn Testing Adds

Single-prompt testing checks that an agent can respond to one instruction. Multi-turn testing
goes further:

**Session continuity.** The agent must maintain context across turns — remembering what it
built in turn 1, recognizing its own code in turn 2, and building on it correctly in turn 3.
This exercises the conversation context window and the agent's ability to reason about its
own prior work.

**Human-like interaction.** Real coding sessions are never single-shot. A developer sends an
initial prompt, sees what the agent produces, runs tests, and sends follow-up corrections or
extensions. Multi-turn scenarios simulate this realistic back-and-forth. The follow-up prompts
act as a human partner who checks the work and asks for more.

**Turn-by-turn validation.** Each turn in a scenario has a clear progression goal. Turn 1
establishes the foundation; turn 2 checks correctness and adds a harder feature; turn 3 is
a final audit. This structure lets the grader distinguish between agents that get everything
right on the first try vs. agents that need coaching to complete the task.

**Staged difficulty.** Multi-turn scenarios start with a tractable first problem and escalate.
This makes it possible to give partial credit and to understand *where* an agent gets stuck
rather than just whether it passes or fails a monolithic task.

## The 7 Category Patterns

Each scenario category uses a consistent follow-up pattern. The `{test_cmd}` placeholder is
resolved from `grading.check_commands.run_tests` or the language default.

### `repo_init` — Greenfield implementation
Turn 1 (initial): Implement specific stubs.\
Turn 2: "Run `{test_cmd}` and show me which tests are passing and which are still failing.
Fix any failures — pay attention to edge cases like empty input, boundary values, and error
conditions."\
Turn 3: "Final check: run `{test_cmd}` one more time. All tests must be green. If anything
is still failing, trace through the failing assertion and fix it now."

### `dirty_cleanup` — Bug fixing
Turn 1 (initial): Fix the described bug(s).\
Turn 2: "Run `{test_cmd}` to check the current state. Walk me through what bugs you found and
fixed. If any tests are still failing, show me the errors and fix them."\
Turn 3: "Final verification: run `{test_cmd}` and confirm a completely clean build. Every test
must pass — if any are still red, fix them now."

### `refactor` — Code quality improvement
Turn 1 (initial): Refactor as described.\
Turn 2: "Run `{test_cmd}` to confirm no regressions from your refactor. Also review the code
you changed — any remaining duplication, long functions, or unclear names to clean up?"\
Turn 3: "Final pass: run `{test_cmd}` and confirm everything is green. Give me a one-line
summary of what changed."

### `backend_feature` — Feature addition with validation
Turn 1 (initial): Implement the feature.\
Turn 2: "Good. Now add input validation and error handling to the feature you just implemented.
What should happen with invalid, missing, or malformed inputs? Update the implementation and
tests to cover those cases."\
Turn 3: "Run `{test_cmd}` to verify everything including your new error handling. Fix any
failures and confirm the feature is complete."

### `migration` — API or library upgrade
Turn 1 (initial): Migrate to the new API.\
Turn 2: "Run `{test_cmd}` to verify the migration is correct. Make sure existing behavior is
preserved and the migration handles edge cases safely."\
Turn 3: "Final verification: run `{test_cmd}` and confirm all tests pass. Is this migration
safe to run on real data without data loss or breaking existing clients?"

### `long_horizon` — Multi-step build (4 turns)
Turn 1 (initial): Implement the first major component.\
Turn 2: "Good progress. Run `{test_cmd}` to see where we stand. Continue with the remaining
steps, prioritizing the parts the tests depend on most."\
Turn 3: (scenario-specific intermediate step)\
Turn 4: "Final push: run `{test_cmd}` and fix any remaining failures. Make sure the full
implementation is complete and all tests pass."

### `frontend_feature` — UI feature with edge cases
Turn 1 (initial): Implement the UI feature.\
Turn 2: "Good. Now handle edge cases: what does the UI show when data is empty, loading, or
an error occurs? Add those states and tests."\
Turn 3: "Run `{test_cmd}` to verify the complete implementation. Fix any failures and confirm
all UI states work correctly."

## How to Write a New Multi-Turn Scenario

Use this checklist when creating a new scenario JSON:

- [ ] Pick a unique `scenario_id` (kebab-case, e.g. `"601-python-mt-my-feature"`)
- [ ] Set `schema_version: "1.1"`
- [ ] Set `category` to one of the 7 valid values
- [ ] Write a `repo_seed.files` with **complete, real code** — no placeholder comments like
  `// TODO` or `# implement me`. Use actual stubs: `raise NotImplementedError`, `unimplemented!()`,
  `panic!("not implemented")`, or empty function bodies that compile.
- [ ] Include tests in the repo_seed that drive the scenario grading
- [ ] Write `task_spec.prompt` as the first human turn — specific and actionable
- [ ] Write `task_spec.followup_prompts` with 2–3 turns that:
  - Turn N-1: verify current state, push for harder requirement
  - Turn N (final): explicit "all tests must pass" gate
- [ ] Reference the actual test command in follow-up prompts (backtick-quoted)
- [ ] Set `grading.check_commands.run_tests` to the concrete test command
- [ ] Verify the JSON is valid: `python3 -c "import json; json.load(open('path'))"`
- [ ] Confirm the seed **fails** grading before the agent acts (for dirty_cleanup/repo_init)
- [ ] Confirm a capable agent can complete the scenario in the allotted `duration_hint_minutes`

## How to Run a Specific Scenario

```sh
# Module form (required — file form breaks imports)
PYTHONPATH=. uv run python -m benchmarks.ai_verification.run_scenario \
  --scenario benchmarks/ai_verification/canary_scenarios/<file>.json \
  --agent autocode
```

Examples:
```sh
# Run the LRU cache scenario
PYTHONPATH=. uv run python -m benchmarks.ai_verification.run_scenario \
  --scenario benchmarks/ai_verification/canary_scenarios/501_python_mt_lru_cache.json \
  --agent autocode

# Run the Go circuit breaker (hard)
PYTHONPATH=. uv run python -m benchmarks.ai_verification.run_scenario \
  --scenario benchmarks/ai_verification/canary_scenarios/514_go_mt_circuit_breaker.json \
  --agent autocode
```

The `multiturn_runner.py` is used internally — it delivers each `followup_prompts` entry to
the agent sequentially within a single session.

## Interpreting Results for Multi-Turn Runs

| Verdict | Meaning |
|---|---|
| `PASS` | All grading checks exited 0 after the final turn. The agent completed the full scenario. |
| `PARTIAL` | Some grading checks passed but not all. The agent made progress but didn't finish. For multi-turn scenarios, this often means the first turns worked but the final edge cases didn't land. |
| `FAIL` | All grading checks failed. The agent either produced broken code or did not make meaningful progress across turns. |
| `INFRA_FAIL` | The harness itself failed (timeout, gateway error, sandbox setup failure). Not the agent's fault. Re-run the scenario. |

For multi-turn scenarios specifically:
- A `PARTIAL` on a `repo_init` scenario often means the agent got the core functionality in
  turn 1 but failed on edge cases introduced in turn 2 or 3.
- A `FAIL` on `dirty_cleanup` often means the agent didn't identify all bugs or introduced
  regressions when fixing one.
- A `PASS` on a `long_horizon` scenario is a strong signal — it means the agent maintained
  context across 4 turns and delivered a complete, working implementation.

To inspect which specific test assertions failed, read `test_log.txt` in the run artifact
directory: `autocode/docs/qa/test-results/ai-verification/<run_id>/test_log.txt`.

## Per-Turn Artifacts and Regression Semantics

Every HFIX-format multi-turn run should be explainable from structured artifacts, not from
stdout alone:

- `turns.json` records one row per delivered turn, including the turn number, grading state,
  event/tool counts, changed files, timing, token counts, and any infra signals available for
  that turn.
- `turn_report.json` records turn-level assertion results such as `min_turns`,
  `max_turns`, `require_final_turn_grading`, and `no_regression_after_pass`.
- `trajectory_report.json` records required-tool and tool-order failures independently of
  deterministic test results.
- `artifact_report.json` records file-change assertions independently of deterministic test
  results and is written even when a scenario has no artifact assertions.
- `run_summary.json` is the compact cross-run surface: final verdict, turn count, tool
  histogram, changed files, required-tool satisfaction, deterministic-check status, typed
  assertion status, and `infra_fail_reason`.

`no_regression_after_pass` protects long-running scenarios from a pass-then-regress shape:
if an earlier turn reaches a passing deterministic state and a later follow-up breaks that
state, the final run must not be reported as a clean `PASS`. The run should expose the
regression in `turns.json`, fail the relevant `turn_report.json` assertion, and summarize the
failed turn/assertion in `run_summary.json` or the summary command output.
If no turn ever passes, `no_regression_after_pass` fails with `no passing turn observed`;
use `require_at_least_one_passing_turn` when that contract should be explicit without
also checking pass-then-regress behavior.

Scripted follow-ups can intentionally expand scope after a passing turn. In that case the
runner marks the next turn with `scope_changed_after_pass: true`; a temporary failure on that
expanded scope is not counted as a regression unless the session later fails without recovering.

When reviewing a multi-turn run, inspect artifacts in this order:

1. `grading_report.json` for the final verdict and top-level typed assertion booleans.
2. `run_summary.json` for the compact explanation of tool, turn, artifact, and infra state.
3. `artifact_report.json` for forbidden/missing file-change assertions.
4. `turns.json` and `turn_report.json` for pass-then-regress, no-passing-turn, or missing-final-turn issues.
4. `trajectory_report.json` and `tool_calls.jsonl` for missing required tool calls.
5. `diff.patch` and `test_log.txt` for final code/test evidence.

## Live Provider Canaries

Live-provider canary tests use deterministic substrate hard-asserts with fixtures. They do **not**
use permanent `pytest.skipif` on missing-fixture or live-provider paths. If a live provider is
unstable, the blocker is captured as an `INFRA_FAIL` artifact with a documented re-attempt rule
(7-day re-attempt cycle recommended). This ensures the test suite hard-asserts the typed-assertion
path rather than silently skipping.

## Protocol Version

The harness protocol version is `0.2.0-harness`. All new structured tool events carry this version
in the `protocol_version` field. Legacy events may still carry `0.1.0-c6g5-subset` for backward
compatibility.
