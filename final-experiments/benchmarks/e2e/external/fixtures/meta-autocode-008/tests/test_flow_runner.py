"""Tests for flow_runner — inspired by langflow-ai/langflow async patterns.

Calling an async function without await/asyncio.run() returns a coroutine
object, not the actual result. This is a common harness-bench v2 failure mode
in async Python frameworks (langflow, fastapi background tasks, etc.).
"""
import sys, os, inspect
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_result_is_dict_not_coroutine():
    from flow_runner import execute_flow
    results = execute_flow(["step1"], "hello")
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, dict), f"Expected dict, got {type(r).__name__}: {r}"


def test_result_has_status_ok():
    from flow_runner import execute_flow
    results = execute_flow(["normalize"], "world")
    assert results[0].get("status") == "ok"


def test_result_uppercases_data():
    from flow_runner import execute_flow
    results = execute_flow(["upper"], "hello")
    assert results[0]["result"] == "HELLO"


def test_step_name_recorded():
    from flow_runner import execute_flow
    results = execute_flow(["myStep"], "data")
    assert results[0]["step"] == "myStep"


def test_data_flows_between_steps():
    from flow_runner import execute_flow
    # step1 uppercases "ab" → "AB", step2 should receive "AB" and uppercase it
    results = execute_flow(["step1", "step2"], "ab")
    assert results[1]["result"] == "AB", \
        f"step2 should receive 'AB' from step1, got {results[1]}"


def test_empty_steps_returns_empty():
    from flow_runner import execute_flow
    assert execute_flow([], "anything") == []


def test_run_step_directly_is_async():
    from flow_runner import run_step
    # run_step must be a coroutine function (the fix should keep it async)
    assert inspect.iscoroutinefunction(run_step), \
        "run_step should remain async — fix execute_flow, not run_step"
