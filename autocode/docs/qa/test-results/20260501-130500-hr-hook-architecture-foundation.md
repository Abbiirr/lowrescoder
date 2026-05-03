# HR Hook Architecture Refactor — Foundation Artifact

> **Phase:** HR — Hook Architecture Refactor
> **Date:** 2026-05-01
> **Status:** Foundation slice complete; full HR not closed

## Scope Completed

- Added internal `Hook` Protocol in `autocode/src/autocode/agent/hooks.py`.
- Added `HookDispatcher` with ordered execution, conditional skip, exception isolation, result override chaining, and token dispatch.
- Wired `AgentLoop` to dispatch `pre_turn`, `post_turn`, `on_token`, `pre_tool_call`, `post_tool_call_success`, and `post_tool_call_error`.
- Wired `factory.py` to create a default no-op `HookDispatcher`.
- Preserved the existing external shell `HookRegistry` behavior.
- Migrated synchronous tool-lifecycle behaviors into internal hook adapters:
  - `ScratchOffloadHook`
  - `GitAwareStagingHook`
  - `PerToolCheckpointHook`

## Validation

| Command | Result |
|---|---|
| `uv run pytest autocode/tests/unit/test_hook_dispatcher.py -q` | `5 passed` |
| `uv run pytest autocode/tests/unit/test_agent_loop.py::TestAgentLoop::test_hook_dispatcher_wraps_successful_tool_execution autocode/tests/unit/test_agent_loop.py::TestAgentLoop::test_hook_dispatcher_gets_tool_errors autocode/tests/unit/test_factory.py::test_create_agent_loop_registers_default_hook_dispatcher autocode/tests/unit/test_hook_dispatcher.py -q` | `8 passed` |
| `uv run pytest autocode/tests/unit/test_hook_dispatcher.py autocode/tests/unit/test_hooks.py autocode/tests/unit/test_agent_loop.py autocode/tests/unit/test_factory.py -q` | `100 passed` |
| `uv run pytest autocode/tests/unit/test_hook_dispatcher.py autocode/tests/unit/test_hooks.py autocode/tests/unit/test_agent_loop.py autocode/tests/unit/test_factory.py autocode/tests/unit/test_checkpoint.py -q` | `123 passed` |
| `uv run ruff check autocode/src/autocode/agent/hooks.py autocode/src/autocode/agent/loop.py autocode/src/autocode/agent/factory.py autocode/tests/unit/test_hook_dispatcher.py autocode/tests/unit/test_agent_loop.py autocode/tests/unit/test_factory.py` | All checks passed |
| `uv run pytest autocode/tests/unit/ -q` | `2225 passed, 12 skipped, 1 warning` before synchronous hook-adapter migration |
| `git diff --check` | clean |

## Count Contract Note

The full unit sweep is green, but the count increased from the pre-HR baseline
because this slice adds required HR tests. Claude Entry 1736 clarified this is
acceptable expected test growth as long as pre-existing tests still pass.

## Remaining Before HR Close

- Migrate remaining embedded behaviors to declarative hook instances:
  - auto-verify (requires async post-success hook or explicit async adapter)
  - prompt-cache keepalive/cache telemetry (requires prompt-aware turn hook context)
  - memory load (factory/bootstrap concern, not yet a lifecycle hook)
  - telemetry emit (requires richer event payloads to avoid losing metrics)
- Run full unit suite and required TUI/PTY smoke matrix.
- Produce final HR artifact and request review.
