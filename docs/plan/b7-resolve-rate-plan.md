# B7 Resolve Rate Improvement Plan

> Created: 2026-02-21
> Updated: 2026-02-21 — Revised to harness-driven outer retry loop (simpler, no loop.py changes)
> Status: IN PROGRESS — outer grading retry loop implemented in `scripts/adapters/autocode_adapter.py`, awaiting rerun validation

## Root Cause (confirmed across 3 models, R0-R2)

The agent does NOT fix source code. It adds/modifies test files, runs grading, sees failure, and gives up. Evidence:

- Git diffs in failed sandboxes show ONLY test file modifications, zero source code changes
- AgentLoop exits immediately on text-only LLM responses (no retry)
- Agent uses 3-14 tool calls out of 100 budget (gives up early)
- Agent never reads test failure output to understand what went wrong
- All 3 models (qwen2.5-coder, qwen3-coder, glm-4.7-flash) fail identically — confirms harness issue, not model

## Solution: Harness-Driven Outer Grading Retry Loop

Research on SWE-agent, mini-SWE-agent, Agentless, OpenHands, Aider, AutoCodeRover shows that
the most reliable pattern is **harness-driven completion checking**, not model-driven signals.

### Design (implemented)

```
┌─────────────────────────────────────────────────────┐
│  HARNESS outer loop (MAX_GRADE_ATTEMPTS = 3)        │
│                                                     │
│  1. Build initial prompt (with grading command)     │
│  2. Run AgentLoop (same session across attempts)    │
│  3. Grade: run grading_command in sandbox           │
│  4. If pass → DONE                                  │
│  5. If fail → inject failure output as next msg     │
│  6. Go to 2 (agent sees full prior context)         │
│  7. After MAX attempts or budget exhausted → stop   │
└─────────────────────────────────────────────────────┘
```

### Key properties

| Property | Value |
|----------|-------|
| Max outer attempts | 3 (configurable via `MAX_GRADE_ATTEMPTS`) |
| Min budget per attempt | 60s (configurable via `MIN_ATTEMPT_BUDGET_S`) |
| Budget strategy | **First-attempt priority** (see below) |
| Session reuse | YES — same `AgentLoop` instance, same `session_id` |
| Agent context across retries | Full history preserved (agent sees what it did before) |
| Human intervention | None — fully autonomous |
| Changes to loop.py | None |
| Changes to tools.py | None |

### Budget strategy: first-attempt priority (intentional)

Each attempt receives `timeout = remaining_budget` (not `budget / MAX_GRADE_ATTEMPTS`).
This means attempt 1 can consume most or all of the budget, leaving little for retries.

**Why this is correct:**
- Most tasks should resolve on attempt 1 with good prompting. Capping attempt 1 at 1/3 budget
  would reduce first-attempt quality for the common case.
- The `MIN_ATTEMPT_BUDGET_S` check prevents starting a doomed retry with < 60s remaining.
- Retries are **opportunistic**: they fire when attempt 1 finishes quickly but fails grading.
  For long-thinking models (glm-4.7-flash at ~2000s/task), practical behavior collapses to one
  attempt — this is expected and acceptable.

**When retries are most effective:** fast models (qwen3-coder at ~60s/task) that produce wrong
fixes quickly. The harness can re-drive with feedback 2-3 times within budget.

### Why same session matters

When the harness calls `loop.run(feedback_prompt)` a second time on the same `AgentLoop`
instance, the agent sees the full conversation: initial prompt → all its tool calls and
results → harness feedback → new attempt. The agent knows exactly what it tried and what
failed. It doesn't start blind.

## Changes Made

### `scripts/adapters/autocode_adapter.py` (primary)

1. **Outer grading retry loop** in `solve_task()`:
   - `AgentLoop` created once, reused across all attempts
   - Grade after each agent run
   - Inject `grade_tail` (last 2000 chars of pytest output) as next user message
   - Track per-attempt info in `AgentResult.artifacts["grade_attempts"]`

2. **Updated `_build_prompt()`**:
   - Explicitly states test_patch is pre-applied
   - Includes the grading command so agent can self-test
   - Clear step-by-step workflow: run tests → read error → fix source → verify

3. **New `_build_feedback_prompt()`**:
   - Called when grading fails
   - Injects the test failure output (tail of pytest output)
   - Includes the test command so agent can re-run

## What This Replaces (Old Fix 1-5 Plan)

| Old Fix | Status | Reason |
|---------|--------|--------|
| Fix 1: Rewrite prompt | DONE | Merged into new `_build_prompt()` |
| Fix 2: force_tool_use in loop.py | DROPPED | Outer retry handles this — text-only exit on attempt 1 just triggers attempt 2 |
| Fix 3: Include grading command in prompt | DONE | Part of new `_build_prompt()` |
| Fix 4: Grading feedback loop | DONE | This IS the outer retry loop — elevated to primary mechanism |
| Fix 5: write_file guard for test files | DEFERRED | Prompt instruction sufficient per research; SWE-bench harness resets test files via git anyway |

## Test Plan

After implementing:
1. `make test` — all unit tests must pass
2. Re-run B7 with `qwen3-coder:latest` on same 5 tasks (R3)
3. Compare: target >= 3/5 (60%), stretch 4/5 (80%)
4. Verify `AgentResult.artifacts["grade_attempts"]` shows multiple attempts when first fails
5. Verify budget tracking works: each attempt gets remaining budget, stops if < 60s left

## Notes

- pytest-10081 already passes — it's the "easy" task that validates our baseline
- The 4 failing tasks require REAL source code fixes (Django ORM SQL, SymPy evalf, sklearn BaseSearchCV, matplotlib hist)
- With full test failure output injected back, the agent finally sees what it needs to fix
- The outer retry is cumulative: attempt 2 knows what attempt 1 tried (full history), so it shouldn't repeat the same wrong fix
