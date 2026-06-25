# Next Remaining TODO — Post-C7 Atomic Checklist

> **Parent plan:** `next_remaining_plan.md`.
> **Use:** OpenCode (primary Builder) picks up the next unchecked task in order. Codex Reviewer/Architect by default; Builder fallback per User redirect. Claude primary Reviewer.
> **Date:** 2026-05-06. Stable commits: `386ef04 Implements till c7`, `5e6d4e8 Stabilize post-C7 harness and retry policy`. Backend Harness Solidification B1-B6 is builder-complete. Canonical active plan: `docs/plan/backend-harness-solidification-plan.md`. Remaining backend cleanup: B7 modular follow-through. TUI is locked in `TUI_PLAN.md` and unblocked by B6 closure, but not started unless user directs it.

Legend: `[ ]` open · `[x]` done · `[~]` in flight

---

## Standing per-phase requirements (every phase exit gate)

Before posting a Review Request for any phase, confirm:

- [ ] **Constraint #8:** `docs/features/backend_features.md` updated AND verification artifact stored at `autocode/docs/qa/test-results/<ts>-<phase-id>-<short-description>.md`
- [ ] **CHANGELOG.md entry** — user-visible changes added under "Unreleased" or current version
- [ ] **`autocode/TESTING.md` updated** if new test commands or harnesses introduced
- [ ] **`docs/architecture.md` updated** if architecture changes
- [ ] **`.gitignore` extended** to cover any new artifact paths
- [ ] **`git diff --check` clean**
- [ ] **Disable/rollback flag documented** per phase (env var, feature flag)
- [ ] **Performance budget** measured + reported in artifact (when applicable)
- [ ] **Quantitative success criteria** (where defined) honored in artifact

## Hard constraints (apply across all phases)

- No commits / pushes / tags / tree-mutating git ops by any agent
- Repo-wide forbidden-git scan from C4.G7' enforces mechanically
- First-turn latency invariant preserved across all phases
- No auto-rollback in any verify/edit pipeline (carried from C5.G4)

### Substrate-test assertion strength (harness invariant)

Any test that asserts a scenario produces a verdict (PASS/FAIL) MUST also assert:
1. The underlying check actually executed — no `can't open file` / `No module named` / `module not found` in test_log.txt
2. `all(r.passed for r in report.check_results)` is True when expecting PASS

Top-level verdict alone is not sufficient evidence. This invariant was established after Codex Entry 1723 caught a false-positive in `compaction-path-a.yaml` where the validate-fixture inversion + cwd mismatch produced a PASS without the check actually executing.
- TDD: RED first, then GREEN; deterministic fixtures only
- Active checklist (this file) is the authoritative slice contract

---

## Pass scope (locked from User decisions 2026-04-30)

**IN SCOPE:** P0, P1a, P2, P2a, P3, hook-refactor (HR), P3a, HFIX AI verification harness fixes, P3b, P3c, P3d, P5 (Tier 4.1 KAIROS only)

**CURRENT ACTIVE PRIORITY:** Backend Harness Solidification B1-B6 is builder-complete. B7 modular migration follow-through remains the backend cleanup track. B0 and B8 are standing rules. TUI is unblocked by B6 closure but requires user direction before implementation starts.

**OUT OF SCOPE — DEFERRED:**
- **Tier 2 entirety** — P4 (Item/Turn/Thread), Tier 2.2 transports, Tier 2.3 turn/steer
- **Tier 4.2** ephemeral fork — depends on P4
- **Tier 4.3** sticky env per turn — depends on P4
- **Tier 6 Path B** TUI rewrite — eliminated by no-second-client-surface
- **P4a/TUI v9 Path A refactor** — parked behind Backend Harness Solidification B6 per current user direction; canonical plan: `TUI_PLAN.md`

**OUT OF SCOPE — DELIBERATELY OMITTED:**
- Voice mode, Multi-agent Coordinator, MCP server hosting, Web UI, Replay/debugger, Buddy/Tamagotchi, Anti-distillation, Undercover mode, Cron tools, GitHub webhooks, LLM-decided "Auto Memory", Auto Dream advanced features, Multi-agent broker, Vector-based semantic retrieval, 5-tier compaction parity

## Backend Harness Solidification — Active B0-B8 Plan

Canonical plan: `docs/plan/backend-harness-solidification-plan.md`.

- [~] **B0 standing rule:** backend harness first; TUI parked until B6 or user override; active docs must point at this plan.
- [x] **B1 audit/gap map:** compare tracked harness/eval/backend files to the HFIX plan; store audit artifact: `autocode/docs/qa/test-results/20260506-110548-backend-harness-audit.md`.
- [x] **B2 deterministic verdict truthfulness:** prevent false PASS for zero tests, missing grading, hidden-test failure, no-op pass, rewritten visible tests, and vacuous no-regression. Fixes landed: direct runner emits neutral reports for absent trajectory/turn assertions; retained-sandbox regrading fails empty/zero-test cached grading output; missing default grading commands fail explicitly; supervised missing-verdict child runs complete as deterministic `INFRA_FAIL`.
- [x] **B3 scenario contract hardening:** hidden immutable tests, `must_not_change_files`, semantic tool families, and stricter seeded-test scenarios. Fixes landed: seeded visible-test lint plus HFIX scenario protections; early substrate scenarios now have explicit snapshot commands and behavior-specific trajectory/artifact/turn contracts.
- [x] **B4 structured artifacts and batch reporting:** always write diagnostic JSON artifacts and summarize current batches only. Fixes landed: direct runner always writes `trajectory_report.json` and `turn_report.json`; summarizer requires `turn_report.json`; supervised INFRA_FAIL completion always writes trajectory/turn/artifact reports.
- [x] **B5 infra classifier and retry validation:** cover gateway, timeout, missing dependency, no-stream, mixed infra+agent, and long retry policy.
- [x] **B6 backend feature surface coverage:** prove thinking/tool/task/todo/subagent/context/memory/cost/KAIROS/transport surfaces without TUI. Artifact: `autocode/docs/qa/test-results/20260506-113250-backend-feature-surface-coverage.md`.
- [ ] **B7 modular follow-through:** parallel cleanup from `docs/plan/deferred/modular_migration_todo.md`.
- [ ] **B8 standing rule:** deferred backend roadmap items require explicit user direction or a Concern entry before implementation.

---

## P0 — Hardening / reconciliation (PRIORITY, before P1a)

**Goal:** lock P1 substrate, reconcile comms, generalize gitignore. ~1-2 days.

### P1 substrate verification

- [ ] Re-run `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` — confirm all current tests pass
- [x] Verify `RunMeta.status` correctly reflects `ndjson_grader_result.passed` AND `all(check_results.passed)` per `run_scenario.py` verdict-composition logic — locked by focused regression tests
- [x] Add a regression test asserting: when `must_have` predicates pass AND deterministic checks pass, `RunMeta.status == Verdict.PASS`
- [x] Add a regression test asserting: when `must_have` passes BUT deterministic check fails, status reports the failing check (not silently `PASS`)
- [x] Confirm `ndjson_runner.py:82-83` dead `prompt_file` write is removed (audit F2 from Entry 1702)
- [x] Confirm `ndjson_runner.py:86-91` dead-code block is removed (audit F1 from Entry 1702)

### Comms reconciliation

- [x] Read `AGENTS_CONVERSATION.MD` — duplicate Entry 1702 persists but was superseded by Claude Entry 1705
- [ ] If duplicate: archive resolved/superseded Entry 1702 variants when protocol ownership/user override permits
- [ ] Single bilateral P1 closeout entry confirms current 20/20 GREEN status
- [ ] Active log returns to lean state (≤ 5 entries) before P1a kickoff where protocol ownership permits

### `.gitignore` generalization

- [x] Audit `.gitignore` for phase-artifact patterns
- [x] Generalize patterns to cover `<phase>{a,b,c,d}-*` style (e.g. `*p2a-*`, `*p3a-*`, etc.)
- [x] Verify `.autocode/scratch/`, `.autocode/snapshots/`, `.autocode/telemetry/`, `.autocode/projects/`, `.autocode/sessions/` are ignored in project trees
- [x] Test: temp-create `autocode/docs/qa/test-results/<ts>-p2a-test.md`, run `git status`, confirm visible as intended phase artifact

### Exit gate

- [x] Substrate test count locked at current value with all green — `20 passed in 0.31s`
- [ ] Comms log lean where protocol ownership permits
- [x] `.gitignore` patterns generalized
- [x] P0 verification artifact at `autocode/docs/qa/test-results/20260430-225654-p0-hardening-reconciliation.md`
- [x] Claude review APPROVE — final P5 GATE APPROVE in Claude Entry 1934
- [ ] Auto-flow to P1a

---

## P1a — Telemetry Plumbing (Tier 8.1)

**Goal:** local-only JSONL event store + aggregator + CLI. Foundational. ~3 days, ~350 LOC.
**Spec:** `docs/plan/post-c7-telemetry-spec.md`.

### Module

- [x] `autocode/src/autocode/telemetry/__init__.py` — package init
- [x] `autocode/src/autocode/telemetry/events.py` — typed event-kind catalog (matches spec doc)
- [x] `autocode/src/autocode/telemetry/store.py` — `TelemetryStore` with append-only JSONL + daily rotation + background writer thread + bounded queue (10_000) with drop-on-full
- [x] `autocode/src/autocode/telemetry/aggregator.py` — read jsonl files in date range, group by kind/session, produce summary structures

### CLI

- [x] `autocode telemetry summary [--last 7d|30d|all]`
- [x] `autocode telemetry events --kind <name> [--last <window>] [--session <id>]`
- [x] `autocode telemetry session <session_id>`
- [x] `autocode telemetry export [--since <date>] [--format jsonl|csv]`
- [x] `autocode telemetry purge`
- [x] CLI extension lands in `autocode/src/autocode/cli.py`

### Lifecycle hook wiring

- [x] `agent/loop.py` emit: `session_start`, `turn_start`, `turn_completed`, `turn_interrupted`, `tool_call_started`, `tool_call_completed`, `tool_call_failed`
- [x] `backend/server.py` emit: `session_end`, `session_resumed`, `thread_start`, `thread_fork`, `turn_steered`, `slash_command_invoked`
- [x] Agent-loop integration emits `llm_call_completed` with full usage block (cache/reasoning fields zero-defaulted until P2 lands)
- [x] Agent-loop approval integration emits `approval_requested`, `approval_granted`, `approval_denied`, `permission_escalation`
- [x] Reserved kinds (emitted by later phases): `tool_output_offloaded` (P2a), `cache_breakpoint_applied` (P2), `compaction_event` (P3), `tool_drift_detected` (P3a), `pev_step_failed` (P3b), `ralph_recovery_fired` (P3b), `entropy_audit_completed` (P3c), `feature_flag_toggled` (P5)

### Privacy + safety

- [x] `AUTOCODE_TELEMETRY_DISABLED=true` env var → `emit()` no-op, hot path zero overhead
- [x] Add `~/.autocode/telemetry/` to repo `.gitignore`
- [x] CI test asserting no `import requests`/`urllib`/`http`/`socket` from `autocode/src/autocode/telemetry/`
- [x] README privacy section updated
- [x] `autocode telemetry purge` deletes everything under `~/.autocode/telemetry/`
- [x] Background writer thread daemon=True; clean shutdown via `shutdown()`

### Tests (RED first)

- [x] `tests/unit/test_telemetry_store.py` — emit, queue, file rotation, drop-on-full, disable flag
- [x] `tests/unit/test_telemetry_aggregator.py` — summary, filters, export formats
- [x] CI test: no network calls in telemetry path

### Performance budget verification

- [x] `emit()` < 5 µs (queue put) — measured 1.97 µs/event
- [x] Background writer flush < 50 ms per batch — measured 24.08 ms for 1000 queued events
- [x] `summary --last 7d` < 500 ms over ~50k events — measured 172.98 ms over 50,000 events

### Exit gate

- [x] All P1a-owned event kinds from spec catalog emit in expected scenarios; later-phase reserved kinds remain catalog-only until owning phases
- [x] `autocode telemetry summary --last 7d` produces non-empty table after emitted local events
- [x] Daily file rotation under `~/.autocode/telemetry/events-YYYY-MM-DD.jsonl`
- [x] P1 harness scenario: emit 100 events, summary correctly aggregates them
- [x] CHANGELOG.md updated
- [x] `autocode/TESTING.md` updated with `autocode telemetry` CLI
- [x] Update `docs/plan/post-c7-telemetry-spec.md` "Open questions" → "Resolved"
- [x] `git diff --check` clean
- [x] `.gitignore` extended for telemetry path
- [x] P1a verification artifact at `autocode/docs/qa/test-results/20260430-231126-p1a-telemetry-plumbing.md`
- [ ] Claude review APPROVE

---

## P2 — Tier 1 Prompt Cache + Verify-Before-Use (ATOMIC — must ship together)

**Goal:** 40-80% LLM cost cut. ~1 week, ~270 LOC.
**Atomic constraint:** Tier 1.1 + 1.2 ship in one PR. Shipping 1.1 alone busts cache every turn.

### Tier 1.1 — Cache breakpoint injection (`autocode/src/autocode/layer4/llm.py`)

- [x] Add `_supports_explicit_cache(provider, model)` — returns True for: `provider == "anthropic"` (all models); `provider == "openrouter" and model.startswith("anthropic/")`; `provider == "openrouter" and model.startswith("google/gemini-")`
- [x] Add `_supports_implicit_cache(provider, model)` — informational; returns True for OpenAI / OpenRouter→OpenAI / OpenRouter→DeepSeek
- [x] Extend `OpenRouterProvider.chat_completion` (~line 1024+) to inject `cache_control: {"type": "ephemeral", "ttl": "1h"}` on the LAST block of stable system prefix when `_supports_explicit_cache` returns True
- [x] Inject `extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"` for OpenRouter→Anthropic
- [x] Add `_inject_cache_breakpoint(messages)` helper — splits system message at `CACHE_BOUNDARY_MARKER` from `prompts.py`; converts to multipart content with `cache_control` on stable block only
- [x] Add `_capture_cache_usage(response)` — extracts both Anthropic-direct format (`cache_read_input_tokens`, `cache_creation_input_tokens`) AND OpenRouter/OpenAI nested format (`prompt_tokens_details.cached_tokens`); passes to token accounting
- [x] OllamaProvider (~line 639+) — ensure no crash when `cache_control` field passed; treat as no-op
- [x] **Risk mitigation:** wrap call in try/except; on `cache_control`-rejection error from provider, fall back to non-cached request
- [x] **Sticky routing rule:** never override `provider.order` on OpenRouter — preserves automatic sticky routing

### Tier 1.2 — Stable/dynamic prompt boundary (`autocode/src/autocode/agent/prompts.py`)

- [x] Define `CACHE_BOUNDARY_MARKER = "# === DANGEROUS_uncachedSystemPromptSection_BELOW ==="`
- [x] Refactor `SYSTEM_PROMPT` constant into `STABLE_INSTRUCTIONS` (deterministic core) — rest of current SYSTEM_PROMPT body
- [x] Add `build_stable_prefix(*, tool_definitions_json, rules_text, skill_catalog_index)` — assembles cacheable portion; MUST be deterministic (no timestamps, IDs, dates)
- [x] Add `build_dynamic_tail(*, cwd, git_status_summary, current_iso_date, current_todo_state, open_tasks_summary)` — per-request portion
- [x] Add `assemble_system_prompt(...)` — returns `f"{stable}\n\n{CACHE_BOUNDARY_MARKER}\n\n{dynamic}"`
- [x] Add `serialize_tool_defs_stable(tools)` — `sort_keys=True`, `separators=(",", ":")`, sorted by `tool.name`; deterministic JSON
- [x] Migrate caller in `agent/loop.py` or `agent/context.py` from `system_prompt = SYSTEM_PROMPT` to `system_prompt = assemble_system_prompt(...)`

### Tier 1.3 — Token tracker + `/cost` cache breakdown

- [x] Extend `TokenUsage` dataclass in `autocode/src/autocode/agent/token_tracker.py` with: `cache_creation_tokens: int = 0`, `reasoning_tokens: int = 0`
- [x] Add `billable_input_cost_factor` property on `TokenUsage` — weighted multiplier (cache reads 0.10x, writes 1.25x, regular 1.0x)
- [x] Add `record_cache(provider, cache_read_tokens, cache_write_tokens)` to `TokenTracker`
- [x] `/cost` slash command shows: total tokens (input/output), cache reads (with % saved), cache writes (premium paid), reasoning tokens, provider, effective cost multiplier
- [x] SQLite migration: add `session_token_usage` table (session_id, prompt_tokens, completion_tokens, cached_input_tokens, cache_creation_tokens, reasoning_tokens, per_provider_json, updated_at)
- [x] On `session_resume`: hydrate `TokenTracker` from SQLite; on session pause / new turn: write row
- [x] Status bar cache-hit indicator in `rtui/src/render/view.rs`: `⚡N% cached` shown when `cached_input_tokens / prompt_tokens * 100 > 0`

### Tier 3.3 — Verify-before-use (folded in)

- [x] Append "Memory and recall discipline" section to `STABLE_INSTRUCTIONS` (text from `docs/plan/roadmaps/2026-04-30-tier-roadmap/03-tier3-memory-architecture.md` §"Suggested wording")

### Hard constraints from Tier 1 edge cases

- [x] **4-breakpoint hard limit reservation** — system prompt / tool defs / RulesLoader output / optional CLAUDE.md (no 5th cache_control attached anywhere else)
- [x] **Workspace isolation note** added to `docs/features/backend_features.md` — caches per-workspace since Anthropic Feb 5 2026
- [x] **TTL silent expiry** — first call after >5 min (or >1h with extended TTL) triggers cache write; metric tracks this

### Tests (RED first)

- [x] `tests/integration/test_prompt_cache.py` — first call: `cache_creation_input_tokens > 0`, `cache_read_input_tokens == 0`; second call within 5 min: `cache_read_input_tokens >= 1024` (opt-in live provider test; skipped unless explicitly enabled)
- [x] `tests/unit/test_prompt_cache_boundary.py` — proves NO time/path/git/todo/Date/Working-directory strings leak above `CACHE_BOUNDARY_MARKER`
- [x] `tests/unit/test_token_tracker_cache.py` — `record_cache` aggregation, per-provider breakdown, `billable_input_cost_factor` math, persistence round-trip
- [x] Provider-rejection fallback test — synthetic "model doesn't support cache_control" error → falls back to non-cached
- [x] 4-breakpoint enforcement test — adding 5th `cache_control` raises ValueError
- [x] Cassette fixtures under `tests/fixtures/cassettes/`: one with `cache_creation_input_tokens > 0`, one with `cache_read_input_tokens > 0`

### Telemetry events emitted

- [x] `cache_breakpoint_applied` per request: `breakpoint_count`, `stable_prefix_bytes`
- [x] `llm_call_completed` includes `cached_input_tokens`, `cache_creation_tokens`, `reasoning_tokens` fields populated

### P1 harness validation

- [x] Add scenario `cache-hit-ratio.yaml` to `benchmarks/ai_verification/scenarios/`: cache-hit ratio > 0.5 deterministically across simulated 5-min session restart

### Exit gate

- [x] `AUTOCODE_DISABLE_PROMPT_CACHE=true` env var works (falls back to non-cached requests)
- [x] All RED → GREEN
- [x] `/cost` displays effective multiplier < 1.0 after warmup
- [x] CHANGELOG.md updated
- [x] `docs/features/backend_features.md` updated with cache feature entry
- [x] `autocode/TESTING.md` updated with cache-test instructions
- [x] `git diff --check` clean
- [x] P2 verification artifact at `autocode/docs/qa/test-results/20260430-234932-p2-prompt-cache-and-verify.md`
- [ ] Claude review APPROVE

---

## P2a — Scratch Store (Tier 7.1)

**Goal:** offload large tool outputs to disk. ~3-4 days, ~250 LOC.

### Module

- [x] `autocode/src/autocode/agent/scratch.py` — `ScratchStore` class
- [x] Constants: `SCRATCH_THRESHOLD_BYTES = 5_000`, `HEADER_LINES_KEPT = 5`, `SUMMARY_MAX_CHARS = 300`
- [x] Lists: `SCRATCH_NEVER_FOR = {"todo_read", "ask_user", "memory_index_show"}`, `SCRATCH_ALWAYS_FOR = {"web_fetch", "git_log"}`
- [x] Per-turn dir layout: `.autocode/scratch/<thread-id>/<turn-id>/<NNN>-<tool-name>.md`
- [x] `manifest.json` per turn dir recording each offload
- [x] `offload_if_large(tool_name, args, result) -> str` — returns context-friendly stub OR original result if under threshold
- [x] `_compute_summary(tool_name, args, result)` — per-tool one-line summary (list_files: count + dir; git_log: commit count; web_fetch: URL + bytes; grep_content: match count + pattern; default: first line)
- [x] `cleanup_after_n_turns(current_turn_count, keep_n=10)` — delete oldest scratch dirs

### Integration

- [x] Wire into `agent/loop.py` — wrap large tool outputs at execute boundary; use offloaded stub instead of full result
- [x] Adjust truncation rules in `agent/context.py` to respect scratch stubs (don't double-truncate)
- [x] Stub format: `[Tool output offloaded — N bytes saved to <path>]\n\nSummary: <line>\n\nFirst 5 lines:\n```\n<preview>\n```\nUse read_file on the path above to see the full output.`

### Telemetry

- [x] `tool_output_offloaded` event with `tool_name`, `result_bytes`, `scratch_path`

### Tests (RED first)

- [x] `tests/unit/test_scratch.py`:
  - [x] Small output inlined unchanged
  - [x] Large output offloaded; stub contains "[Tool output offloaded" + byte count + "First 5 lines"
  - [x] `manifest.json` records each offload with size + tool + summary
  - [x] Cleanup keeps last N=10 turn dirs, deletes older
  - [x] `SCRATCH_NEVER_FOR` honored — even at 50 KB inlined
  - [x] `SCRATCH_ALWAYS_FOR` honored — even at 100 bytes offloaded
  - [x] Per-turn dir isolation (turn-001 scratch ≠ turn-002 scratch)

### P1 harness validation

- [x] Add scenario `large-tool-output-offload.yaml`: simulated 100-file `list_files` produces stub; scratch file exists; `read_file` on stub path returns full content

### Exit gate

- [x] `AUTOCODE_DISABLE_SCRATCH=true` env var works (inlines all outputs — current behavior)
- [x] All RED → GREEN
- [x] CHANGELOG.md updated
- [x] `docs/features/backend_features.md` updated
- [x] `.gitignore` confirms `.autocode/scratch/` is excluded from project worktrees
- [x] `git diff --check` clean
- [x] P2a verification artifact at `autocode/docs/qa/test-results/20260501-082815-p2a-scratch-store.md`
- [ ] Claude review APPROVE

---

## P3 — Tier 3 File-System Memory (Tier 3.1 + 3.2)

**Goal:** durable cross-session memory. ~3 weeks, ~1100 LOC.

### Tier 3.1 — File-system 3-layer memory

- [x] Create `autocode/src/autocode/session/memory_fs.py` — `MemoryFS` class (~600 LOC)
- [x] Storage root: `~/.autocode/projects/<git-root-sha256-prefix>/`
- [x] `_compute_base_dir` uses `git rev-parse --show-toplevel`; canonical hashing means same project across worktrees → same memory dir
- [x] Layer 1 — `MEMORY.md` index: ≤ 200 lines, ~150 chars per pointer line, pointers only (no content)
- [x] `read_index()`, `_initial_index()`, `update_index_pointer(slug, summary)`, `_truncate_index(content)` (drop oldest "Recent" lines first; hard truncate to 200 if still over)
- [x] Layer 2 — `memory/<topic>.md`: YAML frontmatter (topic, type, created, updated, size_lines) + Markdown body
- [x] Soft 1000-line cap; auto-warn when exceeded; recommend split into `<topic>-<sub>.md`
- [x] `read_topic(slug)`, `write_topic(slug, content, summary=None)` (writes topic FIRST then index pointer to avoid dead pointers), `list_topics()`
- [x] `_sanitize_slug(slug)`, `_extract_frontmatter(content)`, `_derive_summary(body)`
- [x] Layer 3 — `logs/YYYY/MM/YYYY-MM-DD.md`: append-only daily logs
- [x] `append_log(session_id, entry)` — entry shape: session_id, model, provider, goal, done, decisions, open_threads, stats
- [x] `_format_log_block(time_str, entry)`, `grep_logs(pattern, days=30, max_matches=50)`

### New tools registered

- [x] `memory_read_topic` in `autocode/src/autocode/agent/tools.py`
- [x] `memory_write_topic`
- [x] `memory_grep_logs`
- [x] `memory_index_show`

### Auto-load + integration

- [x] Auto-load `MEMORY.md` index at session start (via `load_project_memory_content()` used by backend/headless after RulesLoader)
- [x] Re-target `consolidation.py` (autoDream) writes from SQLite to topic files via the active `MemoryFS.save()` backend/headless memory store

### Migration

- [x] One-shot script `scripts/migrate_memory_to_fs.py`:
  - [x] Read all rows from `memories` table
  - [x] Group by category: `tool_pattern` → `patterns.md`, `user_preference` → `preferences.md`, `project_fact` → `facts.md`, `error_resolution` → `debugging.md`, default → `miscellany.md`
  - [x] Write each group to a topic file with summary "Migrated N entries from SQLite memory"
  - [x] Rename old SQLite table to `memories_archive_<date>` (don't drop)
- [x] Idempotent (safe to re-run)
- [x] **Migration guide:** `docs/reference/memory-migration-v1.md` (cross-cutting deliverable)

### Deprecation

- [x] Mark `agent/memory.py` deprecated; keep for one minor version
- [x] Re-implement legacy `memory_list` tool against `MemoryFS` OR remove with deprecation cycle (cross-cutting risk: agent calling stale SQLite-backed tool)

### Tier 3.2 — Session Notes

- [x] Create `autocode/src/autocode/session/session_notes.py` — `SessionNotes` class (~250 LOC)
- [x] Constants: `ACTIVATION_TOKENS = 10_000`, `UPDATE_INTERVAL_TOKENS = 5_000`, `MIN_TOOL_CALLS = 3`
- [x] `should_update(total_tokens)`, `update(*, agent_loop, total_tokens)`, `record_tool_call()`, `read_for_compaction()`
- [x] Subagent pattern: cheap fast model with limited tool access (`write_file` only); subagent token budget bounded
- [x] Compaction Path A integration in `agent/context.py` — `auto_compact` uses Session Notes when available; falls back to Path B (LLM call) when not

### Telemetry

- [x] `compaction_event` with `path: "A" | "B"`, `tokens_before`, `tokens_after`, `duration_ms`

### Tests (RED first)

- [x] `tests/unit/test_memory_fs.py` (~10 tests):
  - [x] Index ≤ 200 lines after 500-line input
  - [x] Pointer line ≤ 150 chars
  - [x] Topic file frontmatter contains required fields
  - [x] Daily log appends new block under existing date file
  - [x] `grep_logs` finds match in recent log
  - [x] Git root hash stable across worktrees (`make_git_repo` + `make_git_worktree`)
  - [x] Slug sanitization: spaces → hyphens, lowercase
  - [x] Topic file write creates index pointer pointing to topic
  - [x] Migration path: SQLite memories → topic files (4 categories grouped correctly)
  - [x] `memory_list` legacy tool either reads from MemoryFS OR raises deprecation
- [x] `tests/unit/test_session_notes.py` (~5 tests):
  - [x] `should_update` returns False until 10k tokens consumed
  - [x] `should_update` respects 5k interval
  - [x] `should_update` requires ≥ 3 tool calls between updates
  - [x] Path A vs Path B selection (Path A when Session Notes file exists)
  - [x] Subagent budget enforced
- [ ] `tests/integration/test_verify_before_use.py` (~2 tests, LLM-eval — expect flakiness):
  - [ ] Model re-reads file before relying on memory
  - [ ] Model updates topic file when memory contradicts reality

### Performance budgets verified

- [x] Memory index load (Layer 1) < 50 ms
- [x] Topic file load (Layer 2) < 200 ms per file
- [x] `grep_logs` over 30 days < 500 ms
- [x] Compaction Path A < 1 sec
- [x] Compaction Path B (fallback/no-provider path) < 30 sec

### P1 harness validation

- [x] Scenario `memory-survives-restart.yaml`: write topic, simulate session restart, agent reads topic, content intact (scenario added; PASS)
- [x] Scenario `compaction-path-a.yaml`: trigger 10k-token threshold, Path A chosen, summary references session notes (scenario added; PASS)

### Exit gate

- [x] `AUTOCODE_USE_LEGACY_MEMORY=true` env var works (selects legacy SQLite `MemoryStore`; archive read-back remains via renamed SQLite table)
- [x] All RED → GREEN
- [x] `MEMORY.md ≤ 200 lines` after 50 simulated sessions
- [x] Path A chosen ≥ 80% of compaction events once 10k threshold passed
- [x] Migration script idempotent
- [x] CHANGELOG.md updated
- [x] `docs/features/backend_features.md` updated
- [x] `docs/reference/memory-migration-v1.md` created (migration guide)
- [x] `autocode/TESTING.md` updated with memory_fs harness usage
- [x] `.gitignore` confirms `~/.autocode/projects/` isn't accidentally tracked anywhere
- [x] `git diff --check` clean
- [x] P3 verification artifact at `autocode/docs/qa/test-results/20260501-124900-p3-file-system-memory-final-v3.md`
- [ ] Claude review APPROVE

---

## HR — Hook Architecture Refactor (between P3 and P3a)

**Goal:** extract `agent/loop.py` hook protocol so subsequent phases plug in declaratively. ~2-3 days, ~150 LOC.

### Tasks

- [x] Audit current hooks in `agent/loop.py`:
  - auto-verify (C5.G4)
  - atomic checkpoint (C4.G1)
  - git-aware staging (C4.G7')
  - prompt-cache keepalive (C7.G11)
  - scratch (P2a)
  - memory load (P3)
  - telemetry emit (P1a)
- [x] Define `Hook` Protocol in `autocode/src/autocode/agent/hooks.py`:
  - `pre_tool_call(tc) -> None`
  - `post_tool_call_success(tc, result) -> str | None` (optional augmented result)
  - `post_tool_call_error(tc, exc) -> None`
  - `pre_turn(turn_id) -> None`
  - `post_turn(turn_id, status) -> None`
  - `on_token(text) -> None`
- [x] `HookDispatcher` class — registry of hooks, ordered execution, exception isolation
- [ ] Migrate existing hooks to declarative `Hook` instances
  - [x] scratch output offload migrated to `ScratchOffloadHook`
  - [x] git-aware staging migrated to `GitAwareStagingHook`
  - [x] atomic checkpoint migrated to `PerToolCheckpointHook`
  - [x] auto-verify migrated to async `AutoVerifyHook`
  - [ ] prompt-cache keepalive/cache telemetry: requires prompt-aware turn hook context
  - [ ] memory load: factory/bootstrap concern, not yet a lifecycle hook
  - [ ] telemetry emit: requires richer event payloads to avoid losing metrics
- [x] Register in `factory.py::create_orchestrator`

### Tests

- [x] `tests/unit/test_hook_dispatcher.py` — registration, order, exception isolation, conditional skip
- [x] Full unit suite green with expected HR-specific test growth — `2230 passed, 12 skipped, 1 warning`

### Exit gate

- [x] Zero behavioral change for migrated sync/async tool hooks; pre-existing tests still pass and new HR tests account for count growth
- [ ] TUI Track 1 + Track 4 + VHS + PTY smokes not run for HR; TUI work is deferred out of this pass per Entry 1736
- [x] CHANGELOG.md updated (developer-facing)
- [x] `docs/architecture.md` updated with hook architecture section
- [x] `git diff --check` clean
- [x] HR verification artifact at `autocode/docs/qa/test-results/20260501-193437-hr-hook-architecture-refactor.md`
- [ ] Claude review APPROVE

---

## P3a — Drift Detectors (Tier 5.1)

**Goal:** sensors for context drift / staleness / tool inconsistency. ~2 weeks, ~400 LOC.

### Module

- [x] `autocode/src/autocode/agent/drift.py` (~400 LOC)
- [x] `SchemaSnapshot` dataclass
- [x] `DriftWarning` dataclass with `kind`, `severity`, `recommendation`, optional `diff`
- [x] `SchemaDriftDetector(*, sensitivity: "low" | "medium" | "high" = "medium")`
  - [x] `_compute_shape(value, depth=0, max_depth=3)` — recursive structure summarization
  - [x] `_diff_shapes(prior, new)` — produce diff representation
  - [x] `_meets_sensitivity_threshold(diff)` — low: missing top-level keys; medium: type changes; high: new keys too
  - [x] `observe(tool_name, args, result) -> DriftWarning | None`
- [x] `ContextStalenessDetector(memory_fs, threshold=timedelta(days=7))`
  - [x] `check_fact_freshness(fact_topic) -> DriftWarning | None`
- [x] `ToolConsistencyDetector` with `DETERMINISTIC_TOOLS = {"read_file", "list_files", "git_status", "list_symbols"}`
  - [x] `reset_turn()`, `observe(tool_name, args, result) -> DriftWarning | None`

### Integration

- [x] Register all three detectors as Hooks via the HR dispatcher
- [x] Drift warning injection: `[Drift detected — <kind>, severity <level>]\n<recommendation>\nDiff: ...\nAcknowledge this warning in your next response and adjust accordingly.` system message before next turn
- [x] Per-detector disable in `~/.autocode/config.yaml`: `agent.drift.{schema,staleness,consistency}.enabled`
- [x] Sensitivity configurable: `agent.drift.schema.sensitivity = "medium"`

### Telemetry

- [x] `tool_drift_detected` event with `tool_name`, `drift_kind`, `severity`
- [x] `autocode telemetry drift --last 7d` aggregation CLI (extends P1a CLI)

### Tests (RED first)

- [x] `tests/unit/test_drift.py` (~10 tests):
  - [x] Schema drift fires on column rename (`email_certified` → `email_verified`)
  - [x] Staleness fires on > 7-day topic file mtime
  - [x] Consistency fires on same-turn `read_file` returning different content
  - [x] Sensitivity "low" doesn't fire on type changes
  - [x] Sensitivity "high" fires on new keys
  - [x] Per-detector disable flag honored
  - [x] Latency benchmark: each detector < 5 ms per detection (in CI)
  - [x] Drift warning injection format matches contract
  - [x] `args_hash` deterministic (sha256 truncated, sorted JSON)
  - [x] `_compute_shape` handles dicts/lists/scalars/depth limit

### Quantitative success criteria (from `docs/plan/roadmaps/2026-04-30-tier-roadmap/06-INDEX-part2.md`)

- [x] Schema drift detector flags ≥ 90% of column renames within 1 turn (validated via P1 harness scenario)
- [x] Latency budget: < 5 ms per detection

### P1 harness validation

- [x] Scenario `drift-schema-detection.yaml`: simulated tool output schema change → exact detector fires → agent acknowledges in next turn

### Exit gate

- [x] All RED → GREEN
- [x] Latency benchmark < 5 ms per detector in CI
- [x] CHANGELOG.md updated
- [x] `docs/features/backend_features.md` updated
- [x] `git diff --check` clean
- [x] P3a verification artifact at `autocode/docs/qa/test-results/20260501-195031-p3a-drift-detectors.md`
- [ ] Claude review APPROVE

---

## HFIX — AI Verification Harness Fixes (CLOSED 2026-05-04)

**Plan:** `docs/plan/ai-verification-harness-fixes-plan.md`.
**Goal:** make harness verdicts explainable, replayable, and resistant to false PASS outcomes before reliability-loop work depends on them.
**Status:** CLOSED under gateway-deferral policy via Claude Entry 1825. Deterministic tests green (39 substrate, 343 benchmark, 2244 unit). The benchmark-runner/retry-classifier subset is committed in `5e6d4e8 Stabilize post-C7 harness and retry policy`; `benchmarks/ai_verification/` substrate files are working-tree additions pending the next user commit. Live `ask-user-scripted` and `multi-turn-regression` canaries remained gateway-bound `INFRA_FAIL`; this is not a harness-quality blocker. P3b is unblocked.

### HFIX-0 — Baseline and file map

- [x] Run `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` and record the starting result (was 20 passed; now 37 passed after HFIX additions)
- [x] Read `schema.py`, `scenario_yaml.py`, `ndjson_runner.py`, `multiturn_runner.py`, and `run_scenario.py`; record implementation ownership in the HFIX artifact
- [x] Confirm no P3b files are touched in this pass

### HFIX-1 — Structured trace contract

- [x] Extend `autocode/src/autocode/backend/headless_schema.py` for structured tool events
- [x] Emit typed tool-call events from `autocode/src/autocode/backend/headless_runner.py`
- [x] Define the canonical typed event schema for turn, tool, follow-up, grader, and infrastructure events
- [x] Add schema validation for `agent_transcript.jsonl` and `tool_calls.jsonl`
- [x] Emit tool events with `tool_name`, args summary/shape, status, duration, and error type
- [x] Remove grading dependence on free-form `item_completed.result` prefixes
- [x] Tests: typed tool events validate; malformed events reject; legacy `item_started(kind="tool_execution")` still counts; `tool_calls.jsonl` writes on PASS and FAIL
- [x] Fixed 9 stale tests in `test_headless_runner.py`, `test_headless_schema.py`, and `test_cli.py` for protocol version bump `0.2.0-harness` and new structured tool event sequence

### HFIX-2 — Typed assertions and graders

- [x] Extend `ScenarioSpec` with `trajectory_assertions`, `artifact_assertions`, and `turn_assertions`
- [x] Extend YAML/JSON loading for the new assertion blocks
- [x] Implement `trajectory_grader.py`
- [x] Implement `artifact_grader.py`
- [x] Include assertion results in `grading_report.json`
- [x] Tests: exact/in-order/any-order/family/forbidden tool; non-empty diff; must/must-not change files; must-contain/must-remove; typed assertion failure forces `FAIL`

### HFIX-3 — Per-turn and per-run artifacts

- [x] Write `turns.json` for every multi-turn run
- [x] Write `trajectory_report.json`
- [x] Write `run_summary.json` with turn count, per-turn verdicts, required tool coverage, tool histogram, changed files, and infra status
- [x] Keep `grading_report.json` verdicts traceable back to specific turn/check/tool evidence
- [x] Tests: simulated three-turn run writes three rows; pass-then-regress run records final FAIL; tool histogram and changed files match source artifacts

### HFIX-4 — Infrastructure classification

- [x] Detect empty turns, provider/rate-limit failures, per-turn timeouts, whole-scenario timeouts, sandbox setup failures, and grading-command execution failures
- [x] Add subprocess-isolated per-task benchmark worker boundary for lane tasks
- [x] On per-task timeout, terminate worker process group with SIGTERM then SIGKILL fallback
- [x] Tests: serialized worker result, process-group timeout kill, cancellation-suppression hard-return, task timeout artifact, route-rejection retry
- [x] Add structured transient retry classification via `failure_evidence.transient_class` with legacy keyword fallback only when no structured class is present
- [x] Tests: structured transient class retries; structured non-transient class suppresses broad `Connection` keyword retry
- [x] Add `infra_fail_reason` to `meta.json` and `run_summary.json`
- [x] Ensure deterministic test/assertion failures still classify as `FAIL` or `PARTIAL`
- [x] Tests: empty turn -> `INFRA_FAIL`; 429/rate-limit -> `INFRA_FAIL`; sandbox failure -> `INFRA_FAIL`; missing grading target cannot PASS; real assertion failure remains `FAIL`

### HFIX-5 — Required canaries and feature inventory coverage

- [x] Add `spawn_subagent` canary scenario through the normal harness workflow
- [x] Add `ask_user` ambiguous-requirement canary through the normal harness workflow
- [x] Add `semantic-search-required.yaml`
- [x] Add `refactor-noop-guard.yaml`
- [x] Add `multi-turn-regression.yaml`
- [x] Add `tool-trajectory-git.yaml`
- [x] Ensure canary artifacts show both the model decision and the harness interpretation
- [x] Update `docs/features/inventory.md` coverage mapping for the current harness workflow
- [x] Tests: each canary loads/validates; deterministic grader tests cover each canary's typed assertions
- [~] At least one fresh run demonstrates enforcement — closed under gateway-deferral policy via Claude Entry 1825. Live evidence includes supervised `ask-user-scripted` and `multi-turn-regression` INFRA_FAIL runs, including retry reports under `autocode/docs/qa/test-results/ai-verification-supervised/20260503-120217-ask-user-scripted-retry-supervised/` and `autocode/docs/qa/test-results/ai-verification-supervised/20260503-120204-multi-turn-regression-retry-supervised/`.

### HFIX-6 — Summary, docs, and closeout verification

- [x] Add `benchmarks/ai_verification/summarize_runs.py`
- [x] Summary reports verdict counts, infra reasons, tool coverage, assertion failures, missing artifacts, and slowest runs
- [x] Malformed NDJSON predicates are surfaced as explicit grader warnings in addition to failing the predicate
- [x] Harden `multi-turn-regression.yaml` against test-shape erosion by requiring original `test_get_set` and `test_delete` checks to remain present
- [x] Update `benchmarks/ai_verification/HARNESS_RUNNER_INSTRUCTIONS.md` with the new artifacts and verdict composition contract
- [x] Update `benchmarks/ai_verification/MULTITURN_GUIDE.md` with per-turn artifact interpretation and regression semantics
- [~] Run a small fresh multi-turn batch and inspect artifacts manually for verdict explainability — closed under gateway-deferral policy via Claude Entry 1825. The fresh `multi-turn-regression` supervised long-retry run reached repeated `INFRA_FAIL` timeouts and preserved retry artifacts; deterministic artifact tests remain the binding gate.
- [x] Store HFIX verification artifact under `autocode/docs/qa/test-results/<ts>-hfix-ai-verification-harness.md`
- [x] Tests: summary handles old/new run dirs, flags missing required new-format artifacts, and reports structured assertion failures
- [x] Tests: docs mention all new artifacts and verdict composition
- [x] Tests: malformed `cache_hit_ratio>=` predicate fails gracefully and reports `WARN: malformed predicate ...`

### Exit gate

- [x] `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` passes — 39 passed (Codex added 2 retry tests)
- [x] All new focused HFIX tests pass
- [x] `git diff --check` clean
- [~] At least one fresh multi-turn run includes `tool_calls.jsonl`, `turns.json`, `trajectory_report.json`, `artifact_report.json`, and `run_summary.json` — closed under gateway-deferral policy via Claude Entry 1825; deterministic/simulated artifact coverage is green and live gateway attempts remained `INFRA_FAIL`.
- [x] Post-run hardening from 2026-05-04 live validation: persist `artifact_report.json`, embed artifact assertion details in `grading_report.json`, fail `no_regression_after_pass` when no turn ever passed, add explicit `require_at_least_one_passing_turn`, classify zero-test pytest collection, add `max_tool_calls_by_name`, and add summary `--run-id` / `--run-ids` filtering.
- [x] `grading_report.json` links verdicts to structured check/tool/turn evidence
- [x] No-op refactor PASS is blocked
- [x] Explicit required-tool failure cannot PASS
- [x] Missing grading command/module/file cannot PASS
- [~] `semantic_search`, `spawn_subagent`, and `ask_user` have canaries or explicit User-accepted unsupported markers — canaries exist; live enforcement closed under gateway-deferral policy via Claude Entry 1825
- [x] `current_directives.md`, `EXECUTION_CHECKLIST.md`, `next_remaining_plan.md`, and this checklist all reflect HFIX closure and P3b as active
- [~] Comms log remains lean after closeout — archival pending explicit user authorization for cross-author cleanup
- [x] Claude review APPROVE — Entry 1825

---

## P3b — PEV + Ralph Reliability Loops (Tier 5.2 + 5.3)

**Goal:** Plan-Execute-Verify pipeline + Ralph long-horizon recovery. ~2 weeks, ~600 LOC.

### PEV (Plan-Execute-Verify)

- [x] `autocode/src/autocode/agent/pev.py` (~350 LOC) — pure callback runner implemented; async command-runner support added; model/tool-surface wiring remains later
- [x] `PlanStep` dataclass: `id`, `description`, `tools_allowed`, `success_predicate`, `failure_predicate`, `max_iterations`
- [x] `Plan` dataclass: `goal`, `steps`, `overall_success_criteria`, `rollback_strategy: "checkpoint" | "revert" | "abort"`
- [x] `StepResult` dataclass with `success` / `failure` constructors
- [x] `PlanResult` dataclass: `plan`, `results`, `status: "succeeded" | "failed" | "user_aborted"`, `evidence`
- [x] `Verdict` enum (used by verifier)
- [~] `PEVRunner.execute_plan(plan)` — pure deterministic callback runner complete; `AsyncPEVRunner.execute_plan(plan)` now supports awaited UI/backend command execution; restricted tool surface/model-role separation remains for AgentLoop wiring
- [x] `_verify(step, execution)` — callback verifier seam plus LLM-backed verifier adapter/parser complete; AgentLoop provider/model wiring remains later
- [ ] On `uncertain`: escalate to user via `_ask_user_about_uncertainty`
- [x] On `fail` with `next_action == retry_step`: retry once
- [~] On `fail` final: rollback per strategy (checkpoint = restore last G1 checkpoint) — currently surfaces rollback handler evidence; actual checkpoint restore remains later
- [x] **Honors C5.G4 contract: NO auto-rollback** — surfaces `/rollback` to user

### Verifier prompt template

- [x] Add `VERIFIER_PROMPT` to `autocode/src/autocode/agent/prompts.py` (text from `docs/plan/roadmaps/2026-04-30-tier-roadmap/07-tier5-harness-reliability.md` §"Verifier prompt template")
- [x] Add LLM-backed `LLMVerifier` callable: prompt construction, PASS/FAIL/UNCERTAIN JSON parsing, malformed-response fallback, rollback→abort mapping

### Auto-detect

- [~] If straight-line agent calls `todo_write` with > 3 items → automatically wrap subsequent execution in PEV — activation policy, deterministic todo-to-`Plan` boundary construction, AgentLoop plan storage, telemetry, and model-visible note complete; full PEVRunner wrapping remains
- [~] User invokes `/plan run <goal>` → manual PEV mode; implemented as four awaited PEV steps through the existing frontend/backend `run_loop_prompt` seam. Backend contexts now verify steps through provider-backed `VERIFIER_PROMPT` parsing; non-backend contexts keep the explicit dispatch-only fallback. Remaining: broader integration coverage.
- [x] `PEVPlanningHook` registered in the shared factory hook dispatcher as a passive large-plan observer; full execution wrapping remains a later P3b integration step.

### Ralph Loop

- [x] `autocode/src/autocode/session/intent_store.py` (~150 LOC) — SQLite-backed `IntentStore`
- [x] `Intent` dataclass: `session_id`, `original_goal`, `captured_at`, `success_criteria`, `constraints`, `progress_so_far`
- [x] `IntentStore.capture(session_id, user_message, agent_loop)` — deterministic extractor callback supported for testability; real high-reasoning extractor wiring remains for Ralph integration
- [x] `IntentStore.get(session_id)`, `IntentStore.update(intent)`
- [x] `AgentLoop.close()` closes the AgentLoop-owned `IntentStore`; backend/headless teardown calls the close path
- [x] `autocode/src/autocode/agent/ralph_loop.py` (~250 LOC) — pure detector/result/message construction implemented; AgentLoop compaction/injection wiring remains later
- [x] `RalphRecoveryDetector.GIVE_UP_PHRASES` list ("i'll stop here", "this is too complex", "unable to continue", etc.)
- [x] `RalphRecoveryDetector.check(agent_state) -> bool`:
  - [x] Phrase detection AND last turn had no tool calls
  - [x] Stagnation: 3 consecutive zero-progress turns
  - [x] Context > 85% AND zero tool calls in last 3 turns
- [x] `RalphLoop.maybe_recover() -> bool` — checks detector, fires recovery if true
- [x] `_recover(intent, state)`: snapshot progress → aggressive `compact_full(keep_messages=2)` → re-inject intent as user message starting with `[Ralph recovery — session resumed after context exhaustion]` — deterministic `SessionStore.compact_session(..., kept_messages=2)` wiring and recovery message injection complete
- [x] **Don't fire on first turn**
- [x] **Cap 3 fires per session** — if exceeded, surface to user
- [ ] **Preserve checkpoints** — SQLite session_store still has original messages

### Hook integration

- [~] PEV runner registered as Hook — `PEVPlanningHook` is registered through the shared factory and observes large `todo_write` plans without mutating results; full runner-boundary execution remains
- [x] Ralph loop registered as post-turn Hook

### Telemetry

- [x] `pev_step_failed` event with `plan_step_id`, `verdict`
- [x] `ralph_recovery_fired` event with `trigger_kind` ("give_up_phrase" | "stagnation" | "context_saturation"), `context_fraction`

### Disable flag

- [x] `AUTOCODE_DISABLE_RALPH=true` env var → Ralph never fires; PEV is opt-in via `/plan` so default is straight-line agent
- [x] `AUTOCODE_DISABLE_PEV=true` env var → pure activation policy and AgentLoop lightweight activation wiring both suppress PEV activation

### Tests (RED first)

- [x] `tests/unit/test_pev.py`:
  - [x] 4-step plan with verifier predicates runs end-to-end
  - [x] Async PEV runner executes awaited step callbacks and passes verifier feedback into retry
  - [x] Step failure with `retry_step` next_action retries once
  - [x] `abort_plan` path triggers checkpoint rollback (or surfaces /rollback)
  - [x] `todo_write` with 4+ todos triggers pure PEV activation policy unless `AUTOCODE_DISABLE_PEV=true`
  - [x] `todo_write` with 4+ todos builds deterministic PEV `Plan` step boundaries
  - [x] `PEVPlanningHook` observes large `todo_write` plans and emits activation telemetry without mutating tool results
  - [x] LLM verifier parses PASS, FAIL retry, FAIL abort, UNCERTAIN, rollback, and malformed verifier responses
- [x] `tests/unit/test_factory.py`:
  - [x] Shared AgentLoop factory registers `PEVPlanningHook` in the default hook dispatcher
- [x] `tests/unit/test_commands.py`:
  - [x] `/plan run <goal>` emits four manual PEV prompts and reports verified completion
  - [x] `/plan run <goal>` uses app-provided async verifier results and fails the plan when a step verifier fails
- [x] `tests/unit/test_backend_server.py`:
  - [x] Backend `handle_command("/plan run <goal>")` dispatches four manual PEV prompts through the backend chat seam
  - [x] Backend `handle_command("/plan run <goal>")` uses provider-backed verifier responses and stops on verifier failure
- [ ] `tests/integration/test_pev.py`:
  - [x] Unit-level AgentLoop auto-detect: `todo_write` with 4 items activates PEV state/telemetry and injects a model-visible note
  - [x] Unit-level AgentLoop auto-detect stores a deterministic PEV `Plan` from the `todo_write` payload
  - [x] Unit-level AgentLoop auto-detect honors `AUTOCODE_DISABLE_PEV=true`
  - [ ] Integration-level auto-detect: `todo_write` with 4 items wraps in PEV
  - [ ] AgentLoop/model-role wiring path exercises verifier prompt/parser
- [x] `tests/unit/test_ralph_loop.py`:
  - [x] Fires on simulated "I'm not sure how to proceed" + zero tool calls
  - [x] Doesn't fire on first turn
  - [x] Cap-3-per-session honored (4th call returns False, surfaces to user)
  - [x] Recovery message starts with `[Ralph recovery`
  - [x] Recovery hook invokes aggressive compaction before injecting the recovery message
  - [x] `AUTOCODE_DISABLE_RALPH=true` suppresses recovery and emits no recovery telemetry
- [~] `tests/integration/test_ralph.py` — AgentLoop/compaction/hook integration is covered at unit level; dedicated integration file remains optional for P3b gate
  - [x] Unit-level AgentLoop hook path persists initial intent, compacts with `kept_messages=2`, and injects a Ralph recovery user message
  - [x] Unit-level AgentLoop recreation/session-resume path reuses persisted intent, compacts with `kept_messages=2`, and injects the original goal
- [x] `tests/unit/test_intent_store.py`:
  - [x] Capture creates persistent SQLite row
  - [x] Persists across simulated session restart
  - [x] `progress_so_far` appends, never overwrites

### Quantitative success criteria (from `docs/plan/roadmaps/2026-04-30-tier-roadmap/06-INDEX-part2.md`)

- [x] PEV catches ≥ 50% of plans that would have produced failing tests — deterministic P1-harness-adjacent check added at `benchmarks/ai_verification/checks/check_p3b_reliability_criteria.py` and covered by `benchmarks/tests/test_p3b_reliability_criteria.py`
- [x] Ralph recovers ≥ 80% of sessions that hit context limits — deterministic P1-harness-adjacent check added at `benchmarks/ai_verification/checks/check_p3b_reliability_criteria.py` and covered by `benchmarks/tests/test_p3b_reliability_criteria.py`

### Cost analysis verification

- [ ] PEV adds plan + per-step verification calls; net cost benchmarked vs straight-line on 4-step task; document in artifact

### Exit gate

- [ ] All RED → GREEN
- [ ] CHANGELOG.md updated
- [ ] `docs/features/backend_features.md` updated
- [ ] `git diff --check` clean
- [x] P3b verification artifact at `autocode/docs/qa/test-results/<ts>-p3b-pev-ralph.md` — `autocode/docs/qa/test-results/20260504-141442-p3b-pev-ralph.md`
- [ ] Claude review APPROVE

---

## P3c — Entropy + Verify Tightening (Tier 7.2 + 7.3)

**Goal:** internal-consistency audits + memory-fact runtime nudges. ~1 week, ~200 LOC.

### Entropy auditor

- [x] `autocode/src/autocode/agent/entropy.py` (~150 LOC)
- [x] `EntropyAuditor` constants: `AUDIT_INTERVAL_TURNS = 10`, `MAX_MESSAGES_AUDITED = 20`
- [x] `ENTROPY_AUDIT_PROMPT` text (from `docs/plan/roadmaps/2026-04-30-tier-roadmap/09-tier7-context-engineering.md` §"Tier 7.2")
- [x] `EntropyAuditor.maybe_audit(current_turn, messages)` — runs cheap fast model; returns structured JSON report
- [x] Categories: `naming_drift` | `decision_reversal` | `stale_reference` | `fact_conflict`
- [~] Severity routing:
  - [x] high → structured warning message recommends rollback to last checkpoint
  - [x] medium → structured warning message + telemetry
  - [x] low → log/telemetry only
  - [x] AgentLoop warning injection for medium/high reports before the next model turn
- [x] Auto-disable on cost cap (entropy audit costs subagent LLM call)

### Anti-entropy prompt

- [x] Add `## Internal consistency` section to `STABLE_INSTRUCTIONS` (text from `docs/plan/roadmaps/2026-04-30-tier-roadmap/09-tier7-context-engineering.md` §"2. Anti-entropy system prompt section")

### Memory-fact runtime nudge

- [x] In `agent/loop.py`: when agent's response cites a file path that's in memory but no `read_file` call has occurred this turn, inject `[Reminder: you're acting on memory of <path> without re-reading it. If your changes depend on its current contents, consider read_file first.]` system message
- [x] Heuristic detection: scan agent message text for paths matching memory topic file mentions; track last `read_file` per path within turn

### Telemetry

- [x] `entropy_audit_completed` event with `severity_max`, `incident_count`

### Tests (RED first)

- [x] `tests/unit/test_entropy.py` covers pure entropy substrate:
  - [x] Naming-drift detected (`state_token` vs `stateToken` mix)
  - [x] Decision-reversal detected (turn 4 says JWT, turn 11 says cookies, no acknowledgment)
  - [x] Audit cadence honored (every 10 turns)
  - [x] High severity builds warning text
  - [x] Malformed JSON returns deterministic medium incident
- [x] `tests/unit/test_agent_loop.py`:
  - [x] High severity injects warning before the next model turn
  - [x] Low severity logs telemetry without warning injection
  - [x] Cost-cap reached skips entropy audit calls
- [ ] `tests/integration/test_verify_nudge.py`:
  - [x] Unit-level AgentLoop test: nudge fires when memory-fact path cited without preceding `read_file`
  - [x] Unit-level AgentLoop test: nudge does NOT fire when `read_file` already called this turn
  - [x] Unit-level AgentLoop test: nudge ignores paths not present in memory context

### Exit gate

- [x] All RED → GREEN
- [x] CHANGELOG.md updated
- [x] `docs/features/backend_features.md` updated
- [x] `git diff --check` clean
- [x] P3c verification artifact at `autocode/docs/qa/test-results/<ts>-p3c-entropy-verify.md` — final artifact: `autocode/docs/qa/test-results/20260504-163104-p3c-entropy-verify.md`; partial artifacts: `autocode/docs/qa/test-results/20260504-162340-p3c-entropy-substrate.md`, `autocode/docs/qa/test-results/20260504-162720-p3c-entropy-loop-injection.md`
- [x] Claude review APPROVE — Entry 1888 APPROVE-with-explicit-followup

### P3c.PROD follow-up (must land before claiming entropy auditor is production-enabled)

- [x] Add `EntropyAuditConfig` with `enabled`, `model_alias`, `audit_interval_turns`, and `max_messages_audited`
- [x] Backend provider executor constructs `EntropyAuditor` only when config enables it
- [x] Pass auditor through `create_orchestrator(..., entropy_auditor=...)`
- [x] Add `AUTOCODE_DISABLE_ENTROPY=true` rollback flag
- [x] Focused wiring test exercises mocked provider JSON response and configured cadence/window
- [x] `docs/features/backend_features.md` states entropy production wiring is opt-in and rollback-guarded
- [x] P3c.PROD verification artifact at `autocode/docs/qa/test-results/20260504-170101-p3c-prod-entropy-wiring.md`

---

## P3d — Eval Suite Expansion (Tier 8.2 + 8.3 + 8.4 + optional 8.5)

**Goal:** production-grade eval suite + regression discipline + drift→eval automation. ~2 weeks, ~450 LOC.

### Eval case schema

- [x] `evals/cases/_schema.yaml` reference (or equivalent docstring)
- [x] Schema fields: `id`, `name`, `provenance` (source, bug_id, recorded_at), `setup` (fixture_repo, initial_files), `input` (user_message), `expected_outcomes` (must_have, must_not_have, judge_criteria), `config` (model, max_turns, timeout_sec), `baseline` (correctness_score, minimality_score, test_quality_score, cost_usd_p50)
- [x] Convert each P1 hand-graded scenario into a full eval case with baseline scores — original five P1 substrate scenarios plus P1 compaction canary are represented under `evals/cases/`

### Runner + judge

- [x] `evals/runner.py` (~300 LOC)
- [x] `EvalCase.load(path)`, `EvalRunner.run(case, run_input) -> EvalResult`, and `EvalRunner.run_live(case) -> EvalResult`
- [x] Fixture setup: copy fixture repo to tmp dir, isolated
- [x] Run AutoCode against fixture; capture telemetry events; collect diff/test output — subprocess-backed `EvalAgentCommand` seam drives `autocode exec <prompt> --json --auto-approve` by default, parses NDJSON, captures post-run `git diff --no-index` output, and can run a configured scenario test command for judge evidence
- [x] Verify must_have / must_not_have predicates against telemetry
- [x] Run LLM judge for qualitative scoring when a judge provider is configured
- [x] `evals/judge.py` (~150 LOC)
- [x] LLM judge with structured JSON output: `{<criterion>: {score: 0.0-1.0, justification: ..., evidence: ...}}`
- [x] Judge model > agent model contract represented by configurable judge model (`coding-judge` default; CI/harness can override to stronger alias)
- [x] `LLMJudge.score(criteria, diff, test_output)` returns dict

### CI gate

- [x] `.github/workflows/evals.yml` (or equivalent CI config)
- [x] Runs stratified sample on PR (NOT all 200 cases)
- [x] `--baseline-tolerance 0.10` (10% drift allowed)
- [x] `--max-budget-usd 5.00` cost cap
- [x] Soft gate (warn-only) for first 2 weeks of stability; promote to hard merge-blocking after
- [~] Pre-merge eval gate runs in < 3 min (quantitative success criterion from 06-INDEX-part2) — deterministic substrate tests/CLI are sub-second locally; live-agent gate pending

### Drift-derived eval generator

- [x] `evals/scripts/generate_evals_from_drift.py`
- [x] Reads `tool_drift_detected` events from telemetry JSONL
- [x] Groups by `(tool_name, drift_kind)`; ≥ 3 occurrences proposes eval case
- [x] Uses original session as fixture seed — drift proposals preserve source session ids and seed `setup.fixture_repo` / `setup.initial_files` from representative telemetry metadata when present
- [~] Run weekly; engineer reviews + accepts/rejects — script writes proposed YAML; scheduler/weekly automation remains future

### Tier 8.3 — 5 regression-discipline rules

- [x] **Rule 1:** PR template updated to require `evals/cases/<id>.yaml` for every bug fix
- [x] **Rule 2:** Drift incident → eval case workflow documented in `autocode/TESTING.md`
- [x] **Rule 3:** Baseline updates require justification in PR description (process rule, no code)
- [x] **Rule 4:** Eval cases append-only — `archived: true` field, never delete
- [x] **Rule 5:** Eval execution reproducible — fix model + temperature 0.0 + seed + fixture commit hash

### Optional Tier 8.5 — Public dashboards

- [x] (OPTIONAL) `autocode telemetry public-report --output public-stats.json` — public-safe summary (no PII, no private content)

### Tests (RED first)

- [x] `tests/unit/test_eval_runner.py`:
  - [x] Case load from YAML
  - [x] Fixture setup creates isolated tmp dir
  - [x] `must_have` predicate matches against telemetry
  - [x] `must_not_have` violation flagged
  - [x] EvalResult.passed reflects all predicates + must_not_have absence
- [x] `tests/unit/test_eval_judge.py`:
  - [x] Structured-output validation
  - [x] Score range 0.0-1.0
  - [x] Deterministic with `temperature=0.0`
  - [x] Multi-criteria parsing
- [~] At least one eval case fails on `main` for known-buggy fixture; passes on fixed branch — deterministic failing path covered by `test_eval_runner_must_not_have_violation_fails`; historical main-vs-fixed branch replay remains unavailable in this checkout
- [~] CI workflow gates merges on baseline tolerance — `.github/workflows/evals.yml` exists as a soft gate during the locked two-week stability window; hard merge-blocking promotion remains time-gated

### Telemetry CI strictness — LOCKED in this phase (resolves decision #5)

- [x] v1 default = soft gate (warn-only) for 2 weeks
- [~] After 2 weeks: promote to hard merge-blocking on baseline drift > 10% — time-gated operational step
- [x] Document in `docs/plan/post-c7-telemetry-spec.md` §"CI gate strictness"

### Quantitative success criterion

- [x] Drift-derived eval generator proposes ≥ 1 case from 30 days of seeded drift events

### Harness-quality items

Promoted to HFIX by user direction on 2026-05-02. P3d consumes the corrected harness artifacts and assertion contract; do not duplicate these as late P3d-only work.

### Exit gate

- [x] All RED → GREEN
- [x] CHANGELOG.md updated
- [x] `docs/features/backend_features.md` updated
- [x] `autocode/TESTING.md` updated with eval workflow + 5 regression discipline rules
- [x] `git diff --check` clean
- [x] P3d verification artifact at `autocode/docs/qa/test-results/<ts>-p3d-eval-suite-expansion.md` — slice artifacts plus final gate artifact: `autocode/docs/qa/test-results/20260505-094408-p3d-gate-review.md`
- [x] Telemetry CI gate strictness FINALIZED in spec doc
- [ ] Claude review APPROVE

---

## P4a — TUI Path A Refactor (DEFERRED — out of this pass per Entry 1736)

**OUT of this pass per User direction "no TUI now, that is for later" (Entry 1736).** No work in `rtui/` during this pass.

Original scope retained below for the follow-up tranche when User signals — DO NOT execute these tasks now.

<details>
<summary>Click to expand deferred P4a checklist</summary>

**Goal (deferred):** trim `rtui/` from ~7500 LOC to ~4600 LOC. Path A only — Path B rewrite OUT (decision #4). ~1.5 weeks, ~−2900 LOC.

### Refactor scope (deferred)

- [ ] `rtui/src/render/view.rs` — replace 9 × 9 stage × detail-surface match arms with widget-per-mode pattern; each mode renders into 30-60 line function; no layout recursion deeper than 2 levels (~−2000 LOC)
- [ ] `HistoryEntry::cached_lines: RefCell<Option<(u16, Vec<Line<'static>>)>>` — cache rendered Lines per entry; invalidate on mutation or width change (~−400 LOC of streaming buffer hacks)
- [ ] `rtui/src/state/reducer.rs` — collapse 40+ Event variants into one `RpcMsg(Value)` + sub-reducer pattern where appropriate (~−500 LOC)
- [ ] **SKIP:** 44 RPC structs → 3 primitives collapse (DEFERRED with P4)

### Performance budget targets (deferred)

- [ ] Cold start to first frame < 150 ms (from current ~250 ms)
- [ ] Resident memory at idle < 60 MB (from current ~85 MB)
- [ ] Frame time during streaming < 5 ms (from current ~8-12 ms)
- [ ] `cells_changed_per_streaming_delta` benchmark < 30
- [ ] Binary size < 1.8 MB (from current ~2.2 MB)
- [ ] Final LOC ~4600 (from current ~7500)

### Tests (deferred)

- [ ] All Track 1 (runtime invariants) green
- [ ] All Track 4 (design-target ratchet) green
- [ ] All VHS PNG snapshots green (no rebaseline without User signoff per `feedback_vhs_rebaseline_user_gated.md`)
- [ ] All PTY smokes green (slash surfaces, real-gateway canary)
- [ ] New `cells_changed_per_streaming_delta` benchmark in CI

### Exit gate (deferred)

- [ ] All performance budgets met (or clearly justified miss)
- [ ] No behavioral regression
- [ ] CHANGELOG.md updated
- [ ] `docs/features/backend_features.md` updated (TUI refactor entry)
- [ ] `docs/tui-testing/tui-testing-strategy.md` updated if testing dimensions changed
- [ ] `git diff --check` clean
- [ ] P4a verification artifact at `autocode/docs/qa/test-results/<ts>-p4a-tui-refactor.md`
- [ ] Claude review APPROVE

</details>

---

## P5 — Tier 4.1 KAIROS Feature-Flag Track

**Goal:** proactive `<tick>` mode behind feature flag. ~1 week, ~400 LOC. **DEFAULT OFF.**
**Tier 4.2 (ephemeral fork) and 4.3 (sticky env) are DEFERRED with P4 (out of scope this pass).**

### Module

- [x] `autocode/src/autocode/agent/proactive.py` (~400 LOC)
- [x] `TickConfig` dataclass: `enabled=False`, `base_interval_sec=30.0`, `blocking_budget_sec=15.0`, `cache_ttl_sec=300`, `terminal_focus_aware=True`
- [x] `ProactiveLoop.start()`, `stop()`, `_tick_loop()`, `_inject_tick()`, `request_sleep(duration)`, `set_terminal_focused(focused)`
- [x] `<tick>` injection format with local time + "you're awake" prompt
- [x] `request_sleep` caps at 10x cache TTL

### SleepTool

- [x] Add `sleep` tool to `agent/tools.py`
- [x] Description: "Wait for a specified duration. Prefer this over `run_command(\"sleep ...\")` — it doesn't hold a shell process."
- [x] Parameters: `seconds: number`, `reason: string`
- [x] Safe by metadata (`requires_approval=False`, `mutates_fs=False`, `executes_shell=False`)

### 15-second blocking budget

- [x] In `agent/loop.py`: `_execute_tool_call_with_budget(tc, blocking_budget_sec)` — `asyncio.wait_for` wrapper
- [x] On timeout: return deferred `ToolExecutionOutcome`
- [x] Budget only applies through the explicit KAIROS wrapper; manual user requests continue to use `_execute_tool_call`

### System prompt section (when KAIROS active)

- [x] Add `PROACTIVE_MODE_PROMPT` in `agent/prompts.py` (text from `docs/plan/roadmaps/2026-04-30-tier-roadmap/04-tier4-future-tracks.md` §"System prompt section")
- [x] Anti-narration rule: "If you have nothing useful to do on a tick, you MUST call Sleep. Never respond with only a status message."

### CLI

- [x] `autocode daemon --watch /path/to/repo` subcommand
- [x] Daemon connects via existing backend TCP JSON-RPC attach seam (`--attach HOST:PORT`)
- [x] Sends one proactive tick in canary mode via `--once --no-dry-run`
- [x] Supports repeated scheduling with `--interval` and bounded validation via `--max-ticks`
- [x] Logs to `~/.autocode/daemon.log` when enabled
- [ ] Desktop notifications via libnotify / osx-notifier

### Feature flag

- [x] `AUTOCODE_FEATURE_KAIROS=false` default-off
- [x] Flag check at startup; flip requires restart (no mid-session toggling)
- [ ] **Pre-shipping gate:** ≥ 4 weeks of P1a telemetry baseline + observability story exists; document in artifact
- [ ] **Initial rollout:** `--dry-run` mode for first 2 weeks of opt-in
- [x] **Hard cap:** KAIROS can never call tools with `requires_approval=True` unless user is interactively present
- [x] **Ralph cap overlap:** Ralph recovery remains capped at 3 fires per session via `RalphRecoveryDetector.MAX_RECOVERIES_PER_SESSION = 3`; focused test `test_detector_honors_cap_three_recoveries_per_session` passed on 2026-05-05
- [x] **Blast radius log:** every file touched by KAIROS persisted; queryable via `autocode kairos audit`
- [x] Tick UUID is propagated in daemon tick RPC metadata and audit records
- [x] Cost-cap skip guard prevents daemon tick dispatch when configured cap is already reached
- [x] **P5.PROD-ENFORCE:** backend honors proactive `read_only` ticks through a dedicated `kairos.tick` RPC path; read-only ticks temporarily run in `AgentMode.REVIEW`, which blocks mutating and shell-executing tools, then restore the prior session mode.
- [ ] Future hardening: evaluate whether to replace review-mode enforcement with a separate restricted proactive tool registry before any default-on KAIROS promotion.

### Telemetry

- [x] `tick_count` per hour event substrate (`kairos_tick`)
- [x] `sleep_call_ratio` event substrate (`kairos_sleep`)
- [x] `anti_narration_violations` event substrate (`kairos_anti_narration`)
- [x] `anti_narration_violations > 5%` alert — `autocode telemetry summary` reports a KAIROS alert when `kairos_anti_narration / kairos_tick > 0.05`
- [x] `kairos_action_blast_radius` event substrate and audit log
- [x] User-facing: optional `/kairos pulse` shows "what KAIROS did while you were away" by summarizing the local KAIROS audit log with record/session/file/action counts and recent tick/tool activity

### Tests (RED first)

- [ ] `tests/integration/test_kairos.py`:
  - [x] Tick injection format correct
  - [x] SleepTool delays next tick by requested seconds (capped at 10x cache TTL)
  - [x] Blocking budget enforcement (15s timeout returns deferred status)
  - [x] Anti-narration detection: tick → text-only response with no tool call → flagged
  - [x] Terminal focus pause: when `_terminal_focused` true and `has_pending_user_input()` true → tick paused
  - [x] Batched ticks: multiple ticks coalesce into single message; agent processes only the latest
  - [x] Cap: KAIROS doesn't call `requires_approval=True` tools without user-present flag

### Exit gate

- [x] Default-off flag honored (no behavioral change without env var) — `test_daemon_watch_is_default_off` passed in focused KAIROS CLI coverage on 2026-05-05
- [x] All RED → GREEN for substrate/safety/default-off CLI seams
- [x] CHANGELOG.md updated
- [x] `docs/features/backend_features.md` updated (with feature-flag note)
- [x] `git diff --check` clean
- [x] P5 verification artifact at `autocode/docs/qa/test-results/<ts>-p5-kairos.md`
- [ ] Claude review APPROVE

---

## Pass exit gate

After all 12 phase blocks ship (P0 through P5):

- [x] Full unit suite green — `uv run pytest autocode/tests/unit/ -q` -> `2348 passed, 12 skipped, 1 known legacy memory deprecation warning` on 2026-05-05 after `/kairos pulse` landed
- [x] Benchmark harness green — `uv run pytest benchmarks/tests -q` -> `358 passed in 15.86s` on 2026-05-05
- [ ] All PTY smokes green (LSP × 8, auto-verify, slash surfaces, real-gateway canary)
- [ ] All Track 1 + Track 4 + VHS green
- [x] Eval suite green (P3d baselines locked) — deterministic eval CLI `uv run python -m evals.runner --cases evals/cases --stratified-sample --sample-size 20 --baseline-tolerance 0.10 --max-budget-usd 5.00 --soft-gate` passed on 2026-05-05 with 7 selected cases; artifact `autocode/docs/qa/test-results/20260505-150225-pass-exit-local-gates/evals-runner.json`
- [x] `autocode telemetry summary --last 7d` cache-ratio claim recorded as variance — local telemetry summary is meaningful/non-empty, but it does not expose a first-class cache-hit-ratio metric yet; tracked as post-pass follow-up "`autocode telemetry summary` cache-ratio claim" below instead of a P5 blocker.
- [x] All disable env vars work (zero-overhead opt-out per phase) — focused rollback matrix passed on 2026-05-05: prompt cache, scratch, PEV policy, AgentLoop PEV auto-detect, Ralph, entropy, KAIROS default-off CLI, backend legacy memory, and headless legacy memory (`10 passed, 1 known legacy memory deprecation warning`).
- [x] All performance budgets met (or clearly justified miss documented) — deterministic P0-P5 budgets met where local; TUI/Tier 2/KAIROS promotion budgets are deferred or time-gated. Variance artifact: `autocode/docs/qa/test-results/20260505-160110-pass-exit-variance-closeout.md`.
- [x] All quantitative success criteria from `docs/plan/roadmaps/2026-04-30-tier-roadmap/06-INDEX-part2.md` met or recorded as variances — P3a/P3b/P3d deterministic criteria met; live eval timing and TUI criteria recorded as variances/deferred. Artifact: `autocode/docs/qa/test-results/20260505-160110-pass-exit-variance-closeout.md`.
- [x] `git diff --check` clean on 2026-05-05 after P5.PROD-ENFORCE
- [x] All shipped P-phase verification artifacts present — P0/P1/P1a/P2/P2a/P3/HR/P3a/P3b/P3c/P3c.PROD/P3d/P5 artifacts verified present on 2026-05-05; P4a remains deferred and excluded from this pass gate.
- [x] Top-level state docs synced: `current_directives.md`, `EXECUTION_CHECKLIST.md`, `PLAN.md`, `docs/features/backend_features.md`, `next_remaining_plan.md`, this checklist — stale scan on 2026-05-05 found no remaining outdated P5-awaiting-review, HFIX-before-P3b, or future-P5 status strings across these files.
- [ ] Comms log lean with Entry 1942 active; user runs the pass-closure stable commit
- [x] Optional: `autocode telemetry public-report` snapshot stored at `autocode/docs/qa/test-results/20260505-150225-pass-exit-local-gates/public-telemetry-report.json`

---

## Post-pass-exit follow-ups (not P5 blockers)

Tracked from Claude Entry 1934. These should not reopen P5; pick them up only after user chooses the next track.

- [ ] Live PTY/canary gates — run when the supported live environment is available and user directs kickoff.
- [ ] Four-week KAIROS telemetry/promotion evidence — time-gated stability window before any default-on discussion.
- [ ] Initial KAIROS rollout policy — decide default-on criteria and dry-run/opt-in rollout path before promotion.
- [ ] Restricted KAIROS tool registry evaluation — future hardening before any default-on KAIROS promotion.
- [ ] KAIROS concurrent-tick stress test — validate same-`BackendServer` mode-swap behavior under concurrent `kairos.tick` calls.
- [ ] `autocode telemetry summary` cache-ratio claim — either add first-class cache-ratio output or document why the pass-exit cache-ratio gate should use public-report/eval evidence instead.
- [ ] P4a/TUI v9 Path A refactor — parked behind Backend Harness Solidification B6; canonical plan: `TUI_PLAN.md`; only pick up after B6 closes or user explicitly overrides.
- [ ] HR-EXT-{1,2,3} hook-context extension — deferred follow-up tranche for richer hook payloads.

---

## Builder routing (locked)

- **OpenCode** — primary Builder
- **Codex** — Reviewer/Architect (default); Builder fallback if OpenCode unavailable for a slice
- **Claude** — Reviewer (primary); spawns checklists; coordinates phase boundaries

## Workflow per slice/phase

1. Pre-task intent comms entry directed to Claude
2. RED tests first → GREEN
3. Constraint #8 + standing per-phase requirements (top of this file) BEFORE Review Request
4. Review Request comms entry directed to Claude with test counts + artifact path + tripwire check
5. Claude APPROVE → next slice/phase auto-flows
6. No fast-forward authorization unless User explicitly grants it
