# B7 Django Wrong-Fix Remediation Note

## Context

Focused rerun: `focused-20260310-071247`

Task: `django__django-10880`

Observed result:
- The task no longer failed as infra or request-timeout.
- The harness reached three real grading attempts and classified the outcome as `WRONG_FIX`.
- Evidence lives in:
  - `sandboxes/bench_B7_django__django-10880_20260310_071247/grading_attempt_1.txt`
  - `sandboxes/bench_B7_django__django-10880_20260310_071247/grading_attempt_2.txt`
  - `sandboxes/progress/B7_autocode_focused-20260310-071247_progress.json`

## What Went Wrong

The agent found the relevant aggregate-SQL code path, but it did not preserve Django's exact SQL contract across retries.

Failure progression:
- Attempt 1 generated invalid SQL: `OperationalError('near "WHEN": syntax error')`
- Attempt 2 changed behavior but introduced a formatting regression: `COUNT( *)` instead of `COUNT(*)`
- Attempt 3 regressed back to the invalid-SQL failure

This is a model-side semantic miss with incomplete retry steering, not a harness infra failure.

## How The Harness Could Have Helped More

### 1. Add invariant-aware retry feedback

Current feedback tells the agent that tests still fail, but it does not restate the exact output contract it just violated.

For this case, retry feedback should have explicitly said:
- the generated SQL must remain syntactically valid
- `COUNT(*)` formatting must be preserved exactly
- the previous edit changed the SQL shape in a way that broke an existing passing assertion

### 2. Detect oscillation between bad states

The attempts alternated between two distinct failures:
- invalid SQL
- valid SQL with wrong formatting

The harness should detect that the failure signature changed and then returned, and warn:
- "You are oscillating between two incorrect fixes."
- "Do not revert to the earlier SQL shape."

### 3. Feed back a narrow reproducer instead of only the full grading tail

This task was localized. The agent would likely have done better with a short targeted reproducer such as:
- failing test name
- exact assertion fragment
- offending SQL snippet from the last run

That is higher signal than the full parallel-runner traceback.

### 4. Surface the agent's own changed diff in retry context

The harness already tracks changed files. It should also include a short diff snippet from the last attempted edit in the next prompt.

For this case, the next retry should have seen:
- the exact aggregate SQL rendering lines it changed
- the exact output string that changed from `COUNT(*)` to `COUNT( *)`

### 5. Add a SQL-shape regression heuristic for this class of failure

When grading output contains:
- SQL syntax errors
- exact SQL-string assertion failures

the retry prompt should switch to a stricter mode:
- preserve surrounding SQL token formatting
- make the smallest possible edit
- avoid broad template rewrites

## Minimal Harness Follow-Up

The smallest useful harness improvements from this case are:
- Add repeated-failure and oscillation warnings keyed by parsed failure signatures.
- Include a short "last changed diff" block in retry prompts.
- When assertions compare exact rendered SQL, quote the expected and actual SQL fragments directly in retry guidance.

## Conclusion

The harness could not have guaranteed a fix here, but it likely could have improved the odds of recovery on attempts 2 and 3.

The important benchmark result is still positive for harness quality:
- this failure is now exposed as a real `WRONG_FIX`
- it is no longer masked as infra or provider timeout
