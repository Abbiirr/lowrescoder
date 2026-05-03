# P3 File-System Memory — Final Verification Artifact (v2)

> **Phase:** P3 — Tier 3 File-System Memory (Tier 3.1 + 3.2)
> **Date:** 2026-05-01
> **Status:** Builder-complete (false-positive fix applied), requesting Claude re-review
> **Supersedes:** `20260501-064500-p3-file-system-memory-final.md` (contained false-positive claim)

## Erratum

The initial P3 review request (Entry 1722) claimed `compaction-path-a.yaml --validate-fixture PASS in 0.1s`. Codex (Entry 1723) and Claude (Entry 1724) identified this as a false positive: the check command ran with `cwd=sandbox` where the script didn't exist, and the `backend_feature` validate-fixture inversion turned the resulting failure into PASS. This artifact documents the fix and provides truthful evidence.

## False-positive root causes and fixes

| Root cause | Fix |
|---|---|
| Check command `uv run python benchmarks/...check_compaction_path_a.py` resolved inside sandbox (not repo root) | Changed to `uv run python -m benchmarks.ai_verification.checks.check_compaction_path_a` + added repo root to `PYTHONPATH` in `_grading_env()` |
| `backend_feature` category triggers validate-fixture inversion (failed check → PASS) | Added `expect_fixture_failure: false` field to `GradingSpec` + `compaction-path-a.yaml`; updated `run_scenario.py` to honor the flag |
| Substrate test only asserted top-level `report.verdict` | Strengthened: asserts `check_results[0].passed == True`, test_log contains `PASS: Path A compaction deterministic proof succeeded`, no `can't open file` / `No module named` |

## Truthful compaction-path-a evidence

**Run ID:** `20260501-121014-976672ea`
**Run command:** `uv run python -m benchmarks.ai_verification.run_scenario --scenario benchmarks/ai_verification/scenarios/compaction-path-a.yaml --validate-fixture`
**Verdict:** PASS in 0.4s

### test_log.txt (confirmed)

```
=== snapshot: uv run python -m benchmarks.ai_verification.checks.check_compaction_path_a ===
PASS: Path A compaction deterministic proof succeeded
```

### grading_report.json (confirmed)

```json
{
  "verdict": "PASS",
  "check_results": [
    {
      "check": "snapshot",
      "passed": true,
      "command": "uv run python -m benchmarks.ai_verification.checks.check_compaction_path_a",
      "output": "PASS: Path A compaction deterministic proof succeeded\n",
      "exit_code": 0
    }
  ]
}
```

The check **actually executed**: `passed: true`, output contains the PASS marker, no file-not-found errors.

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
- `benchmarks/ai_verification/scenarios/compaction-path-a.yaml` — deterministic validate-fixture mode
  - Custom check: `benchmarks/ai_verification/checks/check_compaction_path_a.py`
  - Invoked via `python -m` (cwd-independent) + `PYTHONPATH` injection in `_grading_env()`
  - `expect_fixture_failure: false` prevents validate-fixture inversion
  - Passes in 0.4s with check actually executing (proven by test_log + grading_report above)

## Test evidence

| Suite | Result |
|---|---|
| Full Python unit | **2217 passed, 12 skipped** |
| P3 focused (memory_fs + session_notes) | **17 passed** |
| Benchmark substrate | **28 passed** (up from 27; +1 strengthened test_log test) |
| Ruff on touched files | All checks passed |
| `git diff --check` | clean |
| Live `memory-survives-restart.yaml --agent autocode` | PASS in 68.99s |
| Deterministic `compaction-path-a.yaml --validate-fixture` | **PASS in 0.4s** (run ID `20260501-121014-976672ea`, check_results[0].passed=true, test_log confirmed) |

## Performance budgets (all met)

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
- [x] `compaction-path-a.yaml` deterministic scenario PASS (cwd-independent `python -m` invocation + `expect_fixture_failure: false` + check actually executed)
- [x] `.gitignore` covers `.autocode/projects/`
- [x] All performance budgets met
- [x] All deterministic tests green
- [x] Harness invariant: substrate tests assert underlying check_results passed + test_log content (per Codex Entry 1723 / Claude Entry 1724 requirement)
- [ ] `tests/integration/test_verify_before_use.py` — **explicitly deferred** (requires live LLM gateway)
- [ ] Claude review APPROVE

## Deferred items

- `tests/integration/test_verify_before_use.py` (2 LLM-eval tests) — requires live gateway, marked flaky in `next_remaining_todo.md`. Deferral is consistent with the established gateway-deferral pattern from C5/C6/C7.

## Files changed (full P3, both slices combined)

| File | Change |
|---|---|
| `benchmarks/ai_verification/checks/__init__.py` | New package |
| `benchmarks/ai_verification/checks/check_compaction_path_a.py` | New — deterministic Path A proof |
| `benchmarks/ai_verification/scenarios/compaction-path-a.yaml` | Deterministic validate-fixture + `python -m` + `expect_fixture_failure: false` |
| `benchmarks/ai_verification/run_scenario.py` | `PYTHONPATH` injection in `_grading_env()` + `expect_fixture_failure` flag support |
| `benchmarks/ai_verification/schema.py` | `expect_fixture_failure` field on `GradingSpec` |
| `benchmarks/ai_verification/scenario_yaml.py` | Pass-through `expect_fixture_failure` from YAML |
| `benchmarks/tests/test_ai_verification_substrate.py` | +3 compaction-path-a tests (check script, scenario verdict + check_results, test_log content) |
| `autocode/src/autocode/agent/memory.py` | Deprecation docstring + DeprecationWarning |
| `autocode/tests/unit/test_memory_fs.py` | +2 tests (200-line index, 80% Path A ratio) |
| `CHANGELOG.md` | P3 entry |
| `next_remaining_todo.md` | P3 boxes flipped + harness invariant |

## Partial artifact references

- Previous partial: `autocode/docs/qa/test-results/20260501-114840-p3-file-system-memory-partial.md`
- Superseded v1 final: `autocode/docs/qa/test-results/20260501-064500-p3-file-system-memory-final.md`
- Confirmed compaction-path-a run: `autocode/docs/qa/test-results/ai-verification/20260501-121014-976672ea/`
