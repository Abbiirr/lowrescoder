# P3 File-System Memory — Final Verification Artifact

> **Phase:** P3 — Tier 3 File-System Memory (Tier 3.1 + 3.2)
> **Date:** 2026-05-01
> **Status:** Builder-complete, requesting Claude review

## Summary

P3 replaces SQLite-backed `MemoryStore` with file-system 3-layer memory (`MemoryFS`) plus Session Notes for deterministic Path A compaction. All deterministic implementation, unit tests, harness scenarios, and remaining checklist items are complete.

## Implementation delivered

### Tier 3.1 — File-system 3-layer memory

- `autocode/src/autocode/session/memory_fs.py` — `MemoryFS` class
  - Storage root: `~/.autocode/projects/<git-root-sha256-prefix>/`
  - Layer 1: `MEMORY.md` index (≤ 200 lines, ~150 chars per pointer line)
  - Layer 2: `memory/<topic>.md` with YAML frontmatter
  - Layer 3: `logs/YYYY/MM/YYYY-MM-DD.md` append-only daily logs
  - `_truncate_index` drops oldest "Recent" lines first, hard-truncate at 200
  - `read_topic`, `write_topic`, `list_topics`, `grep_logs`
  - `_sanitize_slug`, `_extract_frontmatter`, `_derive_summary`

- Memory tools registered in `autocode/src/autocode/agent/tools.py`:
  - `memory_read_topic`, `memory_write_topic`, `memory_grep_logs`, `memory_index_show`

- `AUTOCODE_USE_LEGACY_MEMORY=true` preserves legacy SQLite path

- Migration: `autocode/src/autocode/session/memory_migration.py` + `scripts/migrate_memory_to_fs.py`
  - Idempotent; renames `memories` → `memories_archive_<date>` (doesn't drop)
  - Groups by category: patterns, preferences, facts, debugging, miscellany

- `autocode/src/autocode/agent/memory.py` — marked deprecated with `DeprecationWarning`
  - Remains importable for one minor version

- `build_memory_list_payload` in `autocode/src/autocode/backend/services.py` reads from MemoryFS

### Tier 3.2 — Session Notes + Path A compaction

- `autocode/src/autocode/session/session_notes.py` — `SessionNotes` class
  - `ACTIVATION_TOKENS = 10_000`, `UPDATE_INTERVAL_TOKENS = 5_000`, `MIN_TOOL_CALLS = 3`
  - Write-only bounded updater contract with `SESSION_NOTES_TOOL_ALLOWLIST = ("write_file",)`
  - `update_from_text`, `update`, `read_for_compaction`

- Compaction Path A integration in `autocode/src/autocode/agent/context.py`
  - `auto_compact()` checks `SessionNotes.read_for_compaction()` first
  - If notes exist: uses them as summary (Path A), emits `compaction_event` with `path="A"`
  - Otherwise: falls back to provider summarization or consolidation (Path B)

- Telemetry: `compaction_event` with `path`, `tokens_before`, `tokens_after`, `duration_ms`

### AI verification scenarios

- `benchmarks/ai_verification/scenarios/memory-survives-restart.yaml` — live agent scenario (passed with `--agent autocode` in 68.99s)
- `benchmarks/ai_verification/scenarios/compaction-path-a.yaml` — **redesigned** to deterministic validate-fixture mode
  - Custom check: `benchmarks/ai_verification/checks/check_compaction_path_a.py`
  - Passes in 0.1s via `--validate-fixture` without requiring live agent
  - Exercises full Path A code path: seeds SessionNotes, runs auto_compact, asserts path="A"

## Test evidence

| Suite | Result |
|---|---|
| Full Python unit | **2217 passed, 12 skipped** (up from 2215 baseline; +2 new tests) |
| P3 focused (memory_fs + session_notes) | **15 passed** |
| Benchmark substrate | **27 passed** (up from 25; +2 compaction-path-a tests) |
| Ruff on touched files | All checks passed |
| `git diff --check` | clean |
| Live `memory-survives-restart.yaml --agent autocode` | PASS in 68.99s |
| Live `compaction-path-a.yaml --validate-fixture` | PASS in 0.1s |

## Performance budgets

| Metric | Budget | Measured |
|---|---|---|
| Memory index load (Layer 1) | < 50 ms | 0.023 ms |
| Topic file load (Layer 2) | < 200 ms | 0.030 ms |
| `grep_logs` over 30 days | < 500 ms | 1.396 ms |
| Compaction Path A | < 1 s | 1.970 ms |
| Compaction Path B (fallback) | < 30 s | 2.523 ms |

## P3 checklist status

- [x] `MemoryFS` core: index, topics, daily logs, grep, slug sanitization
- [x] Memory tools registered: read_topic, write_topic, grep_logs, index_show
- [x] Backend/headless default uses MemoryFS
- [x] Migration helper + script (idempotent)
- [x] `AUTOCODE_USE_LEGACY_MEMORY=true` rollback path
- [x] `agent/memory.py` deprecated with DeprecationWarning
- [x] `build_memory_list_payload` reads from MemoryFS
- [x] `SessionNotes` with bounded updater contract
- [x] Path A compaction wired in `ContextEngine.auto_compact()`
- [x] `compaction_event` telemetry emitted
- [x] `MEMORY.md ≤ 200 lines` proven after 50 simulated sessions (unit test)
- [x] Path A chosen ≥ 80% of compaction events after 10k threshold (unit test: 10/10 = 100%)
- [x] Migration script idempotent (unit test)
- [x] `memory-survives-restart.yaml` live scenario PASS
- [x] `compaction-path-a.yaml` deterministic scenario PASS (redesigned from live-agent to validate-fixture)
- [x] `.gitignore` covers `.autocode/projects/`
- [x] All performance budgets met
- [x] All deterministic tests green
- [ ] `tests/integration/test_verify_before_use.py` — **explicitly deferred** (requires live LLM gateway; marked "expect flakiness" in checklist)
- [ ] Claude review APPROVE

## Deferred items

- `tests/integration/test_verify_before_use.py` (2 LLM-eval tests) — requires live gateway, marked flaky in `next_remaining_todo.md`. Deferral is consistent with the established gateway-deferral pattern from C5/C6/C7.

## Files changed (this final P3 slice)

| File | Change |
|---|---|
| `benchmarks/ai_verification/checks/__init__.py` | New package |
| `benchmarks/ai_verification/checks/check_compaction_path_a.py` | New — deterministic Path A proof |
| `benchmarks/ai_verification/scenarios/compaction-path-a.yaml` | Redesigned — validate-fixture + custom check |
| `benchmarks/tests/test_ai_verification_substrate.py` | +2 compaction-path-a substrate tests |
| `autocode/src/autocode/agent/memory.py` | Deprecation docstring + DeprecationWarning |
| `autocode/tests/unit/test_memory_fs.py` | +2 tests (200-line index, 80% Path A ratio) |

## Partial artifact reference

Previous partial milestone artifact: `autocode/docs/qa/test-results/20260501-114840-p3-file-system-memory-partial.md`
