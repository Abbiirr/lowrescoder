# Changelog

## Unreleased

- Hardened the P1 AI verification substrate by recording scenario verdicts in `RunMeta.status`, adding meta-status regression coverage, and generalizing post-C7 QA artifact visibility for later phase artifacts.
- Added P1a local telemetry plumbing: JSONL event store, aggregator, `autocode telemetry` CLI commands, agent-loop lifecycle/tool/LLM/approval hooks, backend session transition hooks, and local-only privacy safeguards.
- Added P2 prompt-cache and verify-before-use support: stable/dynamic system prompt boundary, OpenRouter cache breakpoint injection with rejection fallback, cache/reasoning token accounting, persisted `/cost --detail` cache breakdown, Rust TUI cache-hit status indicator, deterministic cassette coverage, and the cache-hit AI verification scenario.
- Added P2a scratch-store support: large tool outputs are offloaded to `.autocode/scratch/` with manifest metadata, compact context stubs, read-back paths, retention cleanup, telemetry, disable flag, and AI verification harness coverage.
- Started P3 file-system memory: added `MemoryFS` durable project memory, memory topic/index/log tools, SQLite-memory migration helper, Session Notes Path A compaction, backend/headless default MemoryFS wiring, and legacy rollback via `AUTOCODE_USE_LEGACY_MEMORY=true`.
- Added P3a drift-detector foundation: schema drift, context staleness, and same-turn tool consistency detectors; drift warning injection through the internal hook dispatcher; `tool_drift_detected` telemetry; configurable `agent.drift.*` flags; and `autocode telemetry drift`.
- Hardened benchmark lane task timeouts with a subprocess-isolated worker boundary that returns structured `INFRA_FAIL` artifacts and kills worker process groups on timeout.
- Improved AI verification NDJSON grading diagnostics by surfacing malformed predicate warnings in `ndjson_grading.json`.
- Hardened AI verification run summaries so missing `turns.json` and `trajectory_report.json` are flagged, and tightened the pinned multi-turn regression canary against test-shape erosion.
- Tightened benchmark infra retry classification with structured `failure_evidence.transient_class` support and legacy keyword fallback only when no structured class is present.
- Made supervised AI verification transient-infra retry the default, using the long recovery schedule `5s,30s,1m,2m,3m,4m,5m,6m,7m,8m,9m,10m,20m,30m,1h,2h,3h,4h,5h,6h,7h,8h,9h,10h`; each attempt is artifacted and the parent supervised report writes `retry_report.json`.
- Completed HFIX AI verification harness fixes: bumped headless protocol to `0.2.0-harness` with structured `tool_call_started/completed/failed` events, added typed trajectory/artifact/turn assertion graders, per-turn `turns.json` and `trajectory_report.json` and `run_summary.json` artifacts, infra-classification for empty turns/429s/timeouts/sandbox failures, subprocess-isolated benchmark lane workers, structured transient retry classification, `refactor-noop-guard.yaml`/`multi-turn-regression.yaml`/`tool-trajectory-git.yaml` canaries, `ask-user-scripted.yaml` canary (gateway-deferred live validation), `summarize_runs.py` report CLI, and updated harness docs. All deterministic tests green (2244 unit, 341 benchmark, Rust TUI green, PTY smokes green). Live `ask-user-scripted` canary remains gateway-deferred (3 supervised INFRA_FAIL due to provider timeout/rate-limit, not harness quality).

### P3 — Tier 3 File-System Memory (Tier 3.1 + 3.2)
- Replace SQLite MemoryStore with file-system 3-layer memory (MemoryFS): index, topics, daily logs
- Add memory tools: memory_read_topic, memory_write_topic, memory_grep_logs, memory_index_show
- Add SessionNotes for deterministic Path A compaction (auto_compact uses notes when available)
- Deprecate agent/memory.py (DeprecationWarning, one minor version grace)
- Migration helper: scripts/migrate_memory_to_fs.py (idempotent, renames SQLite table)
- AUTOCODE_USE_LEGACY_MEMORY=true rollback path
- AI verification: memory-survives-restart.yaml (live PASS), compaction-path-a.yaml (deterministic PASS)
- AI verification harness: shared grading subprocess env for `run_scenario` and standalone `grade_run --run-id`; retained-sandbox regrade now passes module-form checks
- Unit count: 2217 passed (+2 from baseline); benchmark substrate count 29 after retained-sandbox regrade regression coverage
- Continued HR hook architecture refactor: added internal `Hook` Protocol, ordered exception-isolating sync/async `HookDispatcher`, AgentLoop/factory dispatcher wiring, focused dispatcher/loop/factory tests, and migrated scratch offload, git-aware staging, per-tool checkpoints, and post-edit auto-verify to internal hook adapters. Prompt-cache/model telemetry and memory bootstrap remain intentionally inline until the hook API carries prompt/model/bootstrap context.
