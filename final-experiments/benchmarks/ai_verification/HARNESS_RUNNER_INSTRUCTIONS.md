# AI Verification Harness — Runner Instructions

These instructions govern how the harness must be operated.

> **All 541 scenarios now have `followup_prompts`.** Single-prompt scenarios are deprecated — every canary scenario delivers at least 2 scripted follow-up turns after the initial prompt. Scenarios 501–560 are purpose-built multi-turn scenarios with 3–4 turns each. The 477 legacy scenarios (001–477) have had 2 category-based follow-up prompts added automatically.

## Core Requirement: Human-Like Multi-Turn Sessions

**The harness must be tested by a human-like prompter — a human user, Claude Code, or any coding agent — that sends prompts to autocode over a multi-turn session, observes output, and prompts again until the scenario is done.**

This means:
- The prompter reads the task, watches autocode work, and decides what follow-up to send.
- The prompter does NOT look at solution files.
- Each scenario exercises ALL relevant features: file reads, edits, test runs, multi-file changes, etc.
- A full scenario run is only valid if the prompter goes through at least one full loop: prompt → agent works → check result → (optionally) follow-up → done.

## Role Split

- **Claude Code** = human prompter. Sets up the sandbox, sends prompts to autocode, reads output, and sends follow-up prompts as needed.
- **autocode** = AI agent. Does all code reading, editing, and tool calls.
- Scenarios are complete when the grading command exits 0.

## How to Run a Scenario (Real Agent Mode)

1. Pick a scenario JSON from `benchmarks/ai_verification/canary_scenarios/`.
2. Create a sandbox with **only the `repo_seed` files** — no solution files.
3. Confirm the grading command **fails** on the raw seed (for `dirty_cleanup`/`repo_init`) or is ready to run (for `repo_init` with stubs).
4. Run autocode against the sandbox with `task_spec.prompt` as the initial message.
5. Read the output. If tests still fail, send a follow-up prompt with the failure output.
6. Repeat until grading passes OR `max_turns` is reached.
7. Capture the full NDJSON transcript and grading result as a QA artifact.

## Session Continuity Rule

**Single session per scenario.** Do NOT spin up a new autocode session for each follow-up turn. Use one `HeadlessRunner` instance and call `runner.run()` multiple times on the same object. The agent loop and conversation context persist across calls.

Use `multiturn_runner.py` (in-process), not raw `autocode exec` subprocess calls, for multi-turn testing.

## Prompt Style

Claude Code acts like a human user:
- First message: task_spec.prompt verbatim.
- Follow-up: "Tests failed:\n<test output>\nPlease fix the remaining issues."
- Do NOT look at solution files. The agent must solve the scenario independently.

## Scenario Quality Rules

- All scenarios created must **pass** when a capable agent runs them.
- `dirty_cleanup`: seed must have the grading command **fail** before the fix.
- `repo_init`: seed must have stubs (`panic!`, `raise NotImplementedError`, etc.).
- Vary: language (Python, Go, Rust, TypeScript, Java), category, difficulty, greenfield vs brownfield.
- Cover features from `docs/features/inventory.md` — tool use, multi-file edits, shell execution, etc.

## Artifact Storage

Each real agent run stores:
- `scenario.json` — frozen scenario input
- `repo_seed/` — pre-agent snapshot
- `agent_transcript.jsonl` — full NDJSON event log
- `test_log.txt` — grading output
- `diff.patch` — what the agent changed
- `grading_report.json` — verdict (PASS/FAIL/PARTIAL/INFRA_FAIL) with trajectory/artifact/turn pass booleans and embedded artifact assertion details
- `meta.json` — timing, token usage, tool call count, infra_fail_reason
- `tool_calls.jsonl` — one structured record per tool execution (HFIX-1)
- `turns.json` — per-turn event count and grading state (HFIX-3)
- `run_summary.json` — compact human/machine summary (HFIX-3)
- `trajectory_report.json` — trajectory assertion results (HFIX-2)
- `artifact_report.json` — artifact assertion results, written for every run so summaries can diff artifact-state consistently
- `turn_report.json` — turn assertion results when `turn_assertions` are configured

Path: `autocode/docs/qa/test-results/ai-verification/<run_id>/`

### Verdict Composition Table

| Layer | Condition | Result |
|---|---|---|
| Infrastructure health | sandbox setup failed, agent timeout with no usable transcript, grading command could not execute, provider empty turns | `INFRA_FAIL` |
| Deterministic checks | fail with no partial progress proof | `FAIL` |
| Deterministic checks | pass but trajectory_assertions fail | `FAIL` |
| Deterministic checks | pass but artifact_assertions fail | `FAIL` |
| Deterministic checks | pass + all typed assertions pass | `PASS` |
| Deterministic checks | some pass + turn_assertions like min_turns unmet | `PARTIAL` |

Top-level `PASS` must never be based only on an inverted fixture expectation or a missing command.

### Structured Tool Event Contract

New NDJSON events emitted alongside legacy `item_started`/`item_completed`:

- `tool_call_started` — tool execution begins
- `tool_call_completed` — tool execution succeeds with metrics
- `tool_call_failed` — tool execution fails with error type

Privacy defaults: args stored as shape + SHA-256 hash, results as byte count + hash. Full previews opt-in via `AUTOCODE_HARNESS_CAPTURE_TOOL_PREVIEWS=true`. Secret keys (api_key, token, etc.) are scrubbed before hashing.

## Batch Automation

For automated live-agent batch runs, prefer the supervised runner so provider
stalls and outer timeouts produce complete `INFRA_FAIL` artifacts:
```sh
uv run python -m benchmarks.ai_verification.run_scenario_supervised \
  --scenario benchmarks/ai_verification/canary_scenarios/<file>.json \
  --agent autocode \
  --timeout-seconds 420
```

The supervised runner retries transient `INFRA_FAIL` by default with the
long infra-recovery schedule:

```text
5s, 30s,
1m, 2m, 3m, 4m, 5m, 6m, 7m, 8m, 9m, 10m,
20m, 30m,
1h, 2h, 3h, 4h, 5h, 6h, 7h, 8h, 9h, 10h
```

With a 600s per-attempt timeout this gives more than 57 hours of recovery
window. Each attempt gets its own run directory, and the parent supervised
report writes `retry_report.json` with every attempt run ID, verdict, reason,
delay, and final decision. Use `--no-retry-transient-infra` for fast local
debugging, or `--retry-schedule "5s,30s,1m"` to shorten the schedule.

For direct single-process runs:
```sh
uv run python -m benchmarks.ai_verification.run_scenario \
  --scenario benchmarks/ai_verification/canary_scenarios/<file>.json \
  --agent autocode
```

> **Note:** Use `python -m benchmarks.ai_verification.run_scenario` (module form), not
> `python benchmarks/ai_verification/run_scenario.py` (file form). The file form produces
> `ModuleNotFoundError: No module named 'benchmarks.ai_verification'`.

> **Warning:** Real-agent runs can take 1–5 minutes per scenario. If the gateway is
> slow or misconfigured, the direct runner may hang. Use `run_scenario_supervised`
> for acceptance and batch work so timed-out runs are completed as auditable
> `INFRA_FAIL` directories with `grading_report.json`, `meta.json`,
> `run_summary.json`, transcript, diff, tool-call, turn, and assertion artifacts.

## Plans for Testing Each Category

### dirty_cleanup (brownfield bug-fix)
1. Seed has real code with deliberate bugs (wrong operators, off-by-one, swapped logic).
2. Confirm `go test ./...` / `pytest` / `cargo test` FAILS on seed.
3. Send prompt: "Fix the bugs so all tests pass."
4. Turn 1: agent reads files, finds bugs, applies edits, optionally runs tests.
5. Run grading — should PASS in 1 turn for easy/medium; may need turn 2 for hard.
6. Follow-up if needed: "Tests still failing:\n<output>\nContinue fixing."

### repo_init (greenfield implementation)
1. Seed has function stubs (`panic!`, `raise NotImplementedError`, `TODO`).
2. Grading command should FAIL on stubs (unimplemented returns/panics).
3. Send prompt: "Implement the functions so all tests pass."
4. Turn 1: agent reads test file to understand expected behavior, implements each function.
5. Run grading — may take 2 turns for hard algorithms (e.g., DP, monotone deque).
6. Follow-up if needed: "Tests still failing:\n<output>\nFix the remaining functions."

### backend_feature
1. Seed is a working service missing one endpoint or handler.
2. Prompt: "Add the <feature> endpoint so the integration test passes."
3. Agent reads existing code style, adds the endpoint, runs the test.

### refactor
1. Seed has working code with poor structure (duplicated logic, magic numbers, etc.).
2. Tests exist and PASS on seed. Prompt: "Refactor <X> while keeping all tests green."
3. Agent refactors; grading checks tests still pass + optional lint.

### migration
1. Seed uses deprecated API. Tests fail due to migration gap.
2. Prompt: "Migrate from <old API> to <new API>."

### long_horizon
1. Multi-step task requiring reading docs, writing code, updating tests.
2. First prompt: task overview. Follow-ups steer agent toward next step.
3. Up to 5 turns allowed.

## Plans for Covering Features (docs/features/inventory.md)

| Feature area | Scenario type |
|---|---|
| `edit_file` multi-file | brownfield with bugs spread across 2+ files |
| `run_command` (shell) | scenario requires running a build step or formatter |
| `search_text` / `grep_content` | refactor where agent must find all call sites |
| `git_status` / `git_diff` | long_horizon that checks git state |
| `semantic_search` | large codebase scenario (10+ files) |
| `spawn_subagent` | long_horizon with parallel subtasks |
| `todo_write` / task planning | any multi-step scenario to verify planner behavior |
| `ask_user` interaction | scenario with an ambiguous requirement |

Trajectory contracts should use exact tool names only when the exact tool is the
feature under test. For product scenarios that only need code-mutation evidence,
`must_use_tools: ["edit_file"]` is treated as satisfied by any `file_write`
family event, so agents that create/patch files with `write_file` or
`apply_patch` are not incorrectly failed after producing a passing product.
Use `max_tool_calls` for total-call budgets and `max_tool_calls_by_name` for
per-tool repetition budgets when a scenario needs to catch runaway loops such as
hundreds of repeated `run_command` calls.
Scenarios that seed grader tests should also use `must_not_change_files` for
those test files unless the task explicitly asks the agent to update tests.
The runner classifies `pytest` output with `collected 0 items` or `no tests ran`
as `zero_tests_collected`, so accidental test deletion is a contract failure
even if the shell command exits successfully.

## Multi-Turn Patterns

All scenarios use one of 7 category-based follow-up patterns. Each pattern's turns are designed to:
1. Prompt for verification (run tests, observe failures)
2. Drive deeper coverage (edge cases, error handling, or final completion)

| Category | Turn 2 | Turn 3 |
|---|---|---|
| `repo_init` | Run tests, fix failures, pay attention to edge cases | Final: run tests again, all must be green |
| `dirty_cleanup` | Run tests, explain bugs found/fixed, fix remaining | Final: confirm completely clean build |
| `refactor` | Run tests to confirm no regressions, review remaining issues | Final: run tests, give one-line summary |
| `backend_feature` | Add input validation and error handling | Run tests to verify complete feature |
| `migration` | Run tests to verify migration correctness, check edge cases | Final: confirm safe for production |
| `long_horizon` | Run tests, continue with remaining steps | Final: fix remaining failures, confirm complete |
| `frontend_feature` | Add edge case states (empty, loading, error) | Run tests to verify all UI states |

Long-horizon scenarios (541–550, 559–560) have 4 turns and follow a progressive build pattern: each turn adds a major capability, with turn 4 being the final integration test.

## New Scenarios (501–560)

60 purpose-built multi-turn scenarios added 2026-05-01:

**Python repo_init (501–505):**
- 501: LRU cache (eviction, clear)
- 502: Event bus (subscribe/publish, unsubscribe/once, wildcards)
- 503: Retry decorator (basic, backoff, exception filtering)
- 504: Priority task queue (enqueue/dequeue, peek/size/is_empty)
- 505: Finite state machine (transitions, guards, callbacks)

**Python dirty_cleanup (506–508):**
- 506: Binary search off-by-one bug
- 507: Word counter with 3 bugs (case, punctuation, empty string)
- 508: BFS/DFS visited-set bugs, has_path extension

**Python backend_feature (509–510):**
- 509: FastAPI per-IP rate limiting middleware
- 510: FastAPI cursor-based pagination

**Go repo_init (511–515):**
- 511: Token bucket rate limiter (with race safety)
- 512: Worker pool (Submit/Start/Shutdown)
- 513: Trie (Insert/Search/Delete/StartsWith)
- 514: Circuit breaker (closed/open/half-open states)
- 515: TTL cache (expiry on Get, cleanup goroutine)

**Go dirty_cleanup (516–518):**
- 516: Nil map panic and concurrent write race
- 517: Goroutine leak (missing defer Close) and WaitGroup misuse
- 518: Slice aliasing bugs (append result discarded, Copy shares array)

**Go backend_feature (519–520):**
- 519: HTTP middleware chain (logging, auth, compose)
- 520: HTTP client with retry (exponential backoff, context cancellation)

**Rust repo_init (521–525):**
- 521: Singly linked list (push_front/pop_front, IntoIterator)
- 522: Generic stack (push/pop/peek, From<Vec<T>>)
- 523: Fixed-size ring buffer (push/pop, wrap-around, Iterator)
- 524: RPN calculator (add/sub/mul/div, dup/swap)
- 525: DFA (add_state/transition, accepts, reachable_states)

**Rust dirty_cleanup (526–528):**
- 526: Integer overflow in Fibonacci (u32 -> u64, checked_add)
- 527: Lifetime bug (dangling reference fixed to owned value)
- 528: Double borrow / wrong computation in RefCell code

**Rust backend_feature (529–530):**
- 529: Add serde Serialize/Deserialize with custom field names
- 530: Add tracing #[instrument] with structured fields

**TypeScript repo_init (531–535):**
- 531: React useCounter hook (increment/decrement/reset/setValue/step)
- 532: Typed fetch API client (GET/POST with generic types)
- 533: Form validator (required/email/number/minLength/async)
- 534: Simple Observable (subscribe/next/error/complete/pipe/map)
- 535: Client-side router (addRoute/navigate/:params)

**TypeScript dirty_cleanup (536–538):**
- 536: useEffect missing cleanup (event listener + interval leaks)
- 537: Stale closure in empty dependency array
- 538: === vs == type coercion bugs

**TypeScript frontend_feature (539–540):**
- 539: Pagination hook (page state, prev/next, setPageSize)
- 540: React ErrorBoundary (getDerivedStateFromError, fallback fn, reset)

**Long horizon (541–550):**
- 541 Python: ETL pipeline (CSV read, transform/validate, write, integration test)
- 542 Go: REST HTTP server (GET/POST/DELETE /items)
- 543 Rust: CLI word count tool (clap args, file reading, counting, tests)
- 544 TypeScript: Full todo app (add/remove/toggle/filter/sort)
- 545 Python: Web scraper framework (fetch, parse, extract links, crawl)
- 546 Go: Job scheduler (define job, queue, retry, metrics)
- 547 Rust: TCP echo/broadcast server (accept, echo, broadcast, shutdown)
- 548 TypeScript: XState-like state machine (states, actions, guards, history)
- 549 Python: Mini ORM (model definition, create/save, query/filter)
- 550 Go: In-memory KV store server (set/get, delete/list, TTL, snapshot)

**Mixed debugging + extend (551–560):**
- 551 Python: Refactor monolith analyze() → helpers, add mode()
- 552 Go: Refactor god struct → split + UserStorer interface
- 553 Rust: Reduce clone-heavy code → &str, add Display impl
- 554 TypeScript: Callbacks → async/await, add withRetry wrapper
- 555 Python: Raw dict → dataclass, add validators
- 556 Go: raw sql → sqlx, add JOIN query
- 557 Rust: String → &str params, add From<&str>
- 558 TypeScript: JS → TypeScript generics, add DeepPartial type
- 559 Python: 3-bug debugging (wrong algo, off-by-one, missing edge case)
- 560 Go: 3-bug debugging (data race, nil deref, logic error) + -race flag

## What NOT to Do

- Never copy solution files into the sandbox before running the agent.
- Never use `--validate-fixture` and call it a real agent run.
- Never use `simulate_agent_run.py` and claim it tested an AI.
- Never start from a clean (passing) state for `dirty_cleanup` scenarios.
