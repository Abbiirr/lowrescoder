# Flow step executor — has a bug.
# This file exists to be fixed by the agent.
import asyncio


async def run_step(step_name: str, data: str) -> dict:
    """Execute one flow step asynchronously."""
    return {"step": step_name, "result": data.upper(), "status": "ok"}


def execute_flow(steps: list, initial_data: str) -> list:
    """Execute a list of named steps sequentially, passing output to next step.

    Bug: run_step is a coroutine function. Calling it without await (or
    asyncio.run) returns a coroutine object, not the dict result.
    Each iteration therefore appends a coroutine to results and passes
    its string repr as input to the next step.
    """
    data = initial_data
    results = []
    for step in steps:
        # BUG: missing asyncio.run() — returns coroutine object, not dict
        result = run_step(step, data)
        results.append(result)
        data = str(result)
    return results
