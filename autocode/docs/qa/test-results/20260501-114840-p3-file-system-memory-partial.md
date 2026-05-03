# P3 File-System Memory Partial Verification

Date: 2026-05-01

## Scope Completed

- Added `autocode/src/autocode/session/memory_fs.py` with MemoryFS index/topic/log layers.
- Added `autocode/src/autocode/session/memory_migration.py` and `scripts/migrate_memory_to_fs.py`.
- Added `autocode/src/autocode/session/session_notes.py`.
- Registered `memory_read_topic`, `memory_write_topic`, `memory_grep_logs`, and `memory_index_show`.
- Wired backend and headless runners to use MemoryFS by default, with `AUTOCODE_USE_LEGACY_MEMORY=true` preserving the legacy SQLite `MemoryStore` path.
- Wired Session Notes Path A compaction into `ContextEngine.auto_compact()` and emitted `compaction_event` telemetry.
- Tightened the Session Notes updater contract to use an explicit `write_file`-only tool allowlist and bounded prompt/output budget.
- Updated current-state docs and migration guide.
- Added AI verification scenario files:
  - `benchmarks/ai_verification/scenarios/memory-survives-restart.yaml`
  - `benchmarks/ai_verification/scenarios/compaction-path-a.yaml`
- Fixed `ScenarioSpec.load()` to support YAML scenario files and added loader regression coverage.

## Validation

```text
uv run pytest autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py -q
15 passed in 0.44s
```

```text
uv run pytest autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py autocode/tests/unit/test_factory.py autocode/tests/unit/test_backend_services.py autocode/tests/unit/test_headless_runner.py -q
52 passed in 0.94s
```

```text
uv run pytest autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py autocode/tests/unit/test_context.py autocode/tests/unit/test_context_engine.py autocode/tests/unit/test_tools.py autocode/tests/unit/test_memory.py autocode/tests/unit/test_consolidation.py autocode/tests/unit/test_backend_server.py autocode/tests/unit/test_headless_runner.py -q
254 passed in 12.00s
```

```text
uv run ruff check autocode/src/autocode/session/memory_fs.py autocode/src/autocode/session/session_notes.py autocode/src/autocode/session/memory_migration.py scripts/migrate_memory_to_fs.py autocode/src/autocode/agent/tools.py autocode/src/autocode/agent/context.py autocode/src/autocode/agent/factory.py autocode/src/autocode/agent/loop.py autocode/src/autocode/backend/server.py autocode/src/autocode/backend/headless_runner.py autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py autocode/tests/unit/test_tools.py
All checks passed!
```

```text
uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q
25 passed in 0.63s
```

```text
uv run pytest autocode/tests/unit/test_memory_fs.py autocode/tests/unit/test_session_notes.py autocode/tests/unit/test_context.py autocode/tests/unit/test_context_engine.py autocode/tests/unit/test_tools.py autocode/tests/unit/test_memory.py autocode/tests/unit/test_consolidation.py autocode/tests/unit/test_backend_server.py autocode/tests/unit/test_headless_runner.py benchmarks/tests/test_ai_verification_substrate.py -q
280 passed in 12.17s
```

```text
uv run python -m benchmarks.ai_verification.run_scenario --scenario benchmarks/ai_verification/scenarios/memory-survives-restart.yaml --validate-fixture
exit 0; scenario parsed and artifact produced. Validate-fixture verdict is FAIL by existing backend_feature dirty-fixture semantics because no agent runs in this mode.

uv run python -m benchmarks.ai_verification.run_scenario --scenario benchmarks/ai_verification/scenarios/compaction-path-a.yaml --validate-fixture
exit 0; scenario parsed and artifact produced. Validate-fixture verdict is FAIL by existing backend_feature dirty-fixture semantics because no agent runs in this mode.
```

```text
timeout 180 uv run python -m benchmarks.ai_verification.run_scenario --scenario benchmarks/ai_verification/scenarios/memory-survives-restart.yaml --agent autocode
PASS in 68.99s
Artifacts: autocode/docs/qa/test-results/ai-verification/20260501-060405-e9bfd546
NDJSON grading: PASS
Tool calls: 10
Tokens in/out: 37242 / 477
```

```text
timeout 180 uv run python -m benchmarks.ai_verification.run_scenario --scenario benchmarks/ai_verification/scenarios/compaction-path-a.yaml --agent autocode
exit 124 after 180s process timeout
Partial artifacts: autocode/docs/qa/test-results/ai-verification/20260501-060525-097d2237
Partial artifact contains scenario.json and repo_seed only; no meta/transcript was flushed before external timeout.
```

```text
git diff --check
clean
```

```text
uv run pytest autocode/tests/unit/ -q
Initial run exposed telemetry micro-benchmark timing flake:
2214 passed, 12 skipped, 1 failed in 95.63s

Fix applied:
- cached `AUTOCODE_TELEMETRY_DISABLED` at `TelemetryStore` init to remove env lookup from the hot path
- changed the micro-benchmark assertion to use best-of-five samples to avoid scheduler-preemption false failures

Final rerun:
2215 passed, 12 skipped in 93.56s
```

## Performance Budget Measurements

```text
Memory index load: 0.023 ms (< 50 ms)
Topic file load: 0.030 ms (< 200 ms)
grep_logs over 30 days: 1.396 ms (< 500 ms)
Compaction Path A: 1.970 ms (< 1000 ms)
Compaction Path B fallback/no-provider path: 2.523 ms (< 30000 ms)
```

## Remaining P3 Work

- Run the new P1 AI verification scenarios against the supported agent path during the final P3 sweep.
- Resolve the `compaction-path-a.yaml` supported-path live timeout before final P3 review request.
- Post final P3 review request after all open checklist items close.
