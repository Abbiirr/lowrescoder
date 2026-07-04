# TASK-008: Fix Async Coroutine Not Awaited (langflow pattern)

## Source
Inspired by langflow-ai/langflow and similar async Python frameworks.
Common harness-bench v2 failure mode: async function called without await
returns a coroutine object instead of the result.

## Goal
Fix `src/flow_runner.py` so `execute_flow()` actually runs each async step
and collects dict results, not coroutine objects.

## The bug
```python
# Current — returns coroutine object, not dict:
result = run_step(step, data)       # missing asyncio.run()

# Fix — run the coroutine synchronously:
result = asyncio.run(run_step(step, data))
```

## Constraints
- Do NOT make `run_step` synchronous — it must remain `async def`
- `execute_flow` can stay synchronous (use `asyncio.run` inside) or go async
- All 7 tests must pass

## Failing tests (5/7 currently fail)
```
test_result_is_dict_not_coroutine   ← FAILS (returns coroutine)
test_result_has_status_ok           ← FAILS
test_result_uppercases_data         ← FAILS
test_step_name_recorded             ← FAILS
test_data_flows_between_steps       ← FAILS
test_empty_steps_returns_empty      ← passes
test_run_step_directly_is_async     ← passes
```
