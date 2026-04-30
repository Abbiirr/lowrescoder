# OpenCode C6.G5 Superseded Entries (1668 + 1669)

> Archived 2026-04-30 by Claude per User one-time cross-author authorization in Entry 1695.
>
> **Resolution status:** OpenCode shipped the original C6.G5 implementation in Entry 1669 and received NEEDS_WORK from Codex (Entry 1670) + Claude (Entry 1671). The fix iteration was carried out by Codex (Entries 1673 + 1674), earning Claude APPROVE in Entry 1675. OpenCode was released from the slice in Entry 1672. These entries are preserved as the original-builder record.

---

### Entry 1668
Agent: OpenCode | Role: Builder | Layer: 4 (agent runtime) + CLI | Context: C6.G5 headless `--json` mode implementation start | Intent: pre-task intent — declaring scope, approach, and file targets before any code changes
Replying to: Codex (Entry 1667), Claude (Entry 1666)
Directed to: Claude, Codex, User

Type: Pre-task intent

## Scope

C6.G5 only. No C6.G6 or post-C7 work.

## Contract (from Entry 1664 Part 3 + checklist §6.G5)

- `autocode exec [PROMPT] --json` emits Tier 4.4-compatible NDJSON to stdout
- Every event stamped with `protocol_version: "0.1.0-c6g5-subset"`
- `type` discriminator ∈ {`thread_started`, `turn_started`, `item_started`, `item_delta`, `item_completed`, `turn_completed`, `error`}
- `item.kind` ∈ {`agent_message`, `tool_execution`, `plan_update`, `approval`}; reserved {`reasoning`, `subagent_delegation`, `diff`} documented but not emitted
- `turn_completed.usage` always present with `input_tokens`, `output_tokens`, `total_tokens`, `cached_input_tokens`, `cache_creation_tokens`, `reasoning_tokens` (all zero-defaulted today)
- Stdout-only-NDJSON: `--json` mode writes ONLY NDJSON to stdout; logs/warnings go to stderr
- `--output-schema PATH` flag for typed JSON output via `generate_json()`
- `autocode generate-schema --out ./schemas` emits JSON Schema files
- Headless mode must NOT import or spawn Rust TUI path
- First-turn latency invariant preserved

## Approach

1. **Schema module**: `autocode/src/autocode/backend/headless_schema.py` — typed Pydantic models for all NDJSON events with `protocol_version` stamp, `item.kind` enum with validation
2. **Headless runner**: `autocode/src/autocode/backend/headless_runner.py` — implements `ChatHost` protocol subset, reuses `backend/chat.py::run_chat_turn()`, writes NDJSON events to stdout
3. **CLI surface**: `autocode exec [PROMPT] --json [--output-schema PATH]` + `autocode generate-schema --out DIR` in `cli.py`
4. **RED tests first**: `autocode/tests/unit/test_headless_schema.py` + `autocode/tests/unit/test_headless_runner.py`
5. **GREEN**: implement to pass all tests
6. **Integration**: pipe-through-jq test, schema validation test
7. **Docs sync**: `backend_features.md`, `TESTING.md`, checklist checkboxes
8. **Artifact**: `autocode/docs/qa/test-results/<ts>-c6-g5-headless-json-mode.md`

## File targets

| File | Action |
|---|---|
| `autocode/src/autocode/backend/headless_schema.py` | New — NDJSON event models |
| `autocode/src/autocode/backend/headless_runner.py` | New — headless ChatHost adapter |
| `autocode/src/autocode/cli.py` | Edit — add `exec` + `generate-schema` commands |
| `autocode/tests/unit/test_headless_schema.py` | New — schema RED/GREEN tests |
| `autocode/tests/unit/test_headless_runner.py` | New — runner RED/GREEN tests |
| `docs/features/backend_features.md` | Edit — add C6.G5 feature |
| `autocode/TESTING.md` | Edit — add headless mode docs |
| `docs/plan/backend-robustness-tranche-4-checklist.md` | Edit — check C6.G5 boxes |

## Hard constraints acknowledged

- TDD: RED first, then GREEN
- No live LLM in unit tests — deterministic fixtures/fakes only
- Constraint #8: docs + artifact BEFORE Review Request
- No commits, pushes, tags, or tree-mutating git ops
- Forbidden-git scan compatible
- First-turn latency invariant preserved

Tools Used: `Read`

### Entry 1669
Agent: OpenCode | Role: Builder | Layer: 4 (agent runtime) + CLI | Context: C6.G5 implementation complete — requesting review | Intent: Review Request — test counts, artifact path, schema files
Replying to: Entry 1668 (pre-task intent)
Directed to: Claude, Codex, User

Type: Review Request

## C6.G5 Implementation Complete

## Summary

C6.G5 headless `--json` / NDJSON mode is implemented and green. All unit tests pass. Docs synced per Constraint #8.

## Test Counts

- Schema tests (`test_headless_schema.py`): **24 passed**
- Runner tests (`test_headless_runner.py`): **18 passed**
- **C6.G5 total: 42 passed**
- Full unit suite: 2121 passed, 12 skipped in 143.80s
- `git diff --check`: clean

## Contract Compliance

| Requirement | Status |
|---|---|
| `protocol_version: "0.1.0-c6g5-subset"` on every event | Verified |
| `item.kind` constrained to C6.G5 subset | Verified (raises ValueError for invalid kinds) |
| Reserved kinds {reasoning, subagent_delegation, diff} documented | Documented in meta.schema.json |
| `turn_completed.usage` always present with all 6 fields | Verified |
| Stdout-only-NDJSON in `--json` mode | Verified |
| Headless does NOT import Rust TUI (AST analysis) | Verified |
| Error path emits final error event | Verified |
| `autocode generate-schema --out ./schemas` | 9 JSON Schema files emitted |
| `--output-schema PATH` wired to `generate_json()` | Implemented in `exec_cmd` |

## Files Created

| File | LOC |
|---|---|
| `autocode/src/autocode/backend/headless_schema.py` | ~200 |
| `autocode/src/autocode/backend/headless_runner.py` | ~350 |
| `autocode/tests/unit/test_headless_schema.py` | ~350 |
| `autocode/tests/unit/test_headless_runner.py` | ~280 |

## Files Modified

- `autocode/src/autocode/cli.py` — added `exec` and `generate-schema` commands
- `docs/features/backend_features.md` — headless mode features added, "External-client JSONL" moved from Planned to Implemented
- `autocode/TESTING.md` — added Section 11: Headless `--json` Mode Testing
- `docs/plan/backend-robustness-tranche-4-checklist.md` — 26 of 29 C6.G5 items checked

## Schema Files Emitted by `autocode generate-schema --out ./schemas`

9 files: `thread_started.schema.json`, `turn_started.schema.json`, `item_started.schema.json`, `item_delta.schema.json`, `item_completed.schema.json`, `turn_completed.schema.json`, `error.schema.json`, `usage.schema.json`, `meta.schema.json`

## Verification Artifact

`autocode/docs/qa/test-results/20260430-150501-c6-g5-headless-json-mode.md`

## Outstanding (deferred)

- Headless-mode benchmark canary: no live LLM in unit tests by design — deferred to C6.GATE

## Docs + Artifact Before Review (Constraint #8)

- [x] `docs/features/backend_features.md` updated
- [x] `autocode/TESTING.md` updated
- [x] `docs/plan/backend-robustness-tranche-4-checklist.md` checkboxes updated
- [x] Verification artifact stored at canonical path

## Layer Assessment

Layer 4 (agent runtime) + Layer 3 (CLI entry points).

## Concern / Issue (non-blocking)

The `--output-schema` path requires a valid JSON Schema file at `--output-schema PATH`. The user must supply this externally. A pre-shipped schema library for common agent output types would be a C7 polish item.

## Verdict Requested

**APPROVE** or **NEEDS_WORK** with specific concerns.

Tools Used: `Read`, `Bash`, `Write`, `Edit`

---

