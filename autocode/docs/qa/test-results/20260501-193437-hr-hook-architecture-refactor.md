# HR Hook Architecture Refactor — Verification Artifact

> **Phase:** HR — Hook Architecture Refactor
> **Date:** 2026-05-01
> **Status:** Backend hook extraction built; review requested

## Scope Completed

- Added internal `Hook` Protocol and `HookDispatcher` in `autocode/src/autocode/agent/hooks.py`.
- Added ordered exception isolation for sync and async lifecycle dispatch.
- Wired `AgentLoop` and `factory.py` to use the dispatcher by default.
- Preserved existing external `HookRegistry` shell-hook behavior.
- Migrated concrete backend lifecycle behaviors to declarative adapters:
  - `ScratchOffloadHook`
  - `GitAwareStagingHook`
  - `PerToolCheckpointHook`
  - `AutoVerifyHook`

## Explicit Non-Migrations

These remain inline intentionally because the current hook payload does not
carry the required context without losing behavior:

- Prompt-cache keepalive/cache telemetry: needs prompt/static-prefix context.
- LLM and tool telemetry emission: needs full model/tool payloads and timing.
- Memory load: factory/bootstrap concern, not a turn/tool lifecycle concern.

## TDD Evidence

- RED: async dispatcher and `AutoVerifyHook` tests failed with missing method/import.
- GREEN: focused tests passed after adding async dispatch and adapter.

## Validation

| Command | Result |
|---|---|
| `uv run pytest autocode/tests/unit/test_hook_dispatcher.py::test_dispatcher_chains_async_success_result_overrides autocode/tests/unit/test_hook_dispatcher.py::test_auto_verify_hook_appends_success_note -q` | RED first: 2 failed as expected |
| `uv run pytest autocode/tests/unit/test_hook_dispatcher.py::test_dispatcher_chains_async_success_result_overrides autocode/tests/unit/test_hook_dispatcher.py::test_auto_verify_hook_appends_success_note autocode/tests/unit/test_auto_verify.py -q` | `10 passed` |
| `uv run pytest autocode/tests/unit/test_hook_dispatcher.py autocode/tests/unit/test_hooks.py autocode/tests/unit/test_agent_loop.py autocode/tests/unit/test_auto_verify.py autocode/tests/unit/test_factory.py autocode/tests/unit/test_checkpoint.py -q` | `133 passed` |
| `uv run ruff check autocode/src/autocode/agent/hooks.py autocode/src/autocode/agent/loop.py autocode/src/autocode/agent/factory.py autocode/tests/unit/test_hook_dispatcher.py autocode/tests/unit/test_agent_loop.py autocode/tests/unit/test_auto_verify.py autocode/tests/unit/test_factory.py` | All checks passed |
| `uv run pytest autocode/tests/unit/ -q` | `2230 passed, 12 skipped, 1 warning` |

## Count Contract

Claude Entry 1736 clarified the HR zero-behavior-change contract as:
pre-existing tests must still pass, and total count may increase only by
expected HR-specific tests. The full unit count grew from the pre-HR baseline
because HR added dispatcher/adapter tests; all tests are green.

## TUI/PTY Note

TUI Track 1, Track 4, VHS, and PTY smokes were not run for HR. User direction
captured in Entry 1736 deferred TUI work out of this pass; this slice only
changes backend `AgentLoop` hook ownership.
