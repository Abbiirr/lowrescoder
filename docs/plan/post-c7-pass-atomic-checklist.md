# Post-C7 Pass — Master Atomic Checklist

> **Parent plan:** `docs/plan/post-c7-stable-commit-roadmap.md`
> **Builder handoff:** `docs/plan/post-c7-builder-handoff.md`
> **Telemetry spec:** `docs/plan/post-c7-telemetry-spec.md`
> **Date:** 2026-04-30
> **Use:** OpenCode (primary) picks up the next unchecked task in order. Each phase block has its own exit gate. Every slice and every gate updates `docs/features/backend_features.md` AND stores a verification artifact at `autocode/docs/qa/test-results/<ts>-<slice-id>-<short-description>.md` BEFORE posting the Review Request (Constraint #8).

Legend:
- `[ ]` open
- `[x]` done (with verification artifact path)
- `[~]` in flight

---

## Pass scope (locked from User decisions 2026-04-30)

**Main focus:** harden and measure the existing single-surface AutoCode. No new client surfaces, no TUI rewrite, no new infrastructure for verification — instead deepen reliability, sensors, cost efficiency, and durability of what we already shipped in `386ef04 Implements till c7`.

**IN SCOPE for this pass (11 phase blocks):**
- P1, P1a, P2, P2a, P3, hook-refactor, P3a, P3b, P3c, P3d, P4a (Path A only), P5 (Tier 4.1 KAIROS only)

**OUT OF SCOPE for this pass (deferred):**
- P4 — Tier 2 Item/Turn/Thread (decision #2: no second client surface)
- P4a Path B — TUI rewrite (decision #4: refactor only; rewrite gated on P4)
- Tier 4.2 ephemeral fork (depends on P4)
- Tier 4.3 sticky env per turn (depends on P4)

**Locked decisions:**
1. P2 timing — strictly post-commit (already satisfied; commits happen at user discretion later, not gating phase boundaries)
2. Second client surface — out of scope; P4 stays DEFERRED
3. AI verification harness — narrow substrate using existing features and interfaces only; no new infrastructure
4. TUI path — Path A refactor only (Path B rewrite eliminated by #2)
5. Telemetry CI gate strictness — deferred to be locked when P1a + P3d ship; spec at `docs/plan/post-c7-telemetry-spec.md`
6. `agent/loop.py` hook-architecture refactor — yes, between P3 and P3a

**Hard constraints (carry forward unchanged):**
- No commits / pushes / tags / tree-mutating git ops by any agent
- Repo-wide forbidden-git scan from C4.G7' enforces mechanically
- First-turn latency invariant preserved across all post-commit work
- Constraint #8 (docs + artifact BEFORE Review Request) per slice
- No auto-rollback in any verify/edit pipeline (carried from C5.G4)
- TDD: RED first, then GREEN
- Active checklist (this file) is the authoritative slice contract

---

## P1 — AI Verification Harness Narrow Substrate (uses existing features only)

**Goal:** deterministic verification scaffold that downstream phases use to prove cache-hit, memory-survival, drift-detection, etc. Per User decision #3: **leverage existing features and interfaces, do not build new infrastructure**.

**Existing surfaces to reuse:**
- `benchmarks/` directory (runner, adapters, fixtures already shipped)
- C6.G5 NDJSON output (`autocode exec --json`)
- C7.G12 recipe YAML schema (already validates structured task specs)
- PTY harness pattern (`autocode/tests/pty/pty_e2e_real_gateway.py`)
- Test-result artifact format (`autocode/docs/qa/test-results/`)

### Substrate

- [x] Map existing scenario primitives in `benchmarks/`, recipes (`autocode/src/autocode/agent/recipes.py`), and PTY tests; document in design notes inside the verification module — mapped in Entry 1700 pre-task intent; harness already existed
- [x] Define scenario file format **reusing existing recipe YAML schema** plus a small `expected_outcomes` extension; do not invent a new schema — `benchmarks/ai_verification/scenario_yaml.py`
- [x] Co-locate harness in `benchmarks/ai_verification/` (substrate dir already created in `git status` snapshot) — already existed, extended
- [x] `benchmarks/ai_verification/sandbox.py` — sandbox repo builder (clone fixture → tmp dir → seed git history) — reused existing `sandbox_builder.py` unchanged
- [x] `benchmarks/ai_verification/runner.py` — spawns `autocode exec --json` against the sandbox, captures NDJSON output via subprocess + parses the C6.G5 `headless_schema.py` event types — `ndjson_runner.py` + upgraded `run_scenario.py._run_autocode()`
- [x] `benchmarks/ai_verification/grader.py` — deterministic exit-code checker; uses pytest assertions for must-have/must-not-have predicates over the NDJSON event stream — `ndjson_grader.py`

### Scenarios (3-5 hand-graded, YAML)

- [x] `benchmarks/ai_verification/scenarios/01-simple-edit.yaml` — minimal "edit one file, verify diff" flow
- [x] `benchmarks/ai_verification/scenarios/02-tool-output-shape.yaml` — `read_file` returns expected schema (used by P3a drift validation)
- [x] `benchmarks/ai_verification/scenarios/03-session-persistence.yaml` — restart-survival probe (used by P3 memory validation)
- [x] `benchmarks/ai_verification/scenarios/04-cost-routing.yaml` — Layer 4.5 routes correctly (already shipped in C6.G6)
- [x] `benchmarks/ai_verification/scenarios/05-headless-ndjson.yaml` — C6.G5 protocol invariant probe

### Tests

- [x] `benchmarks/tests/test_ai_verification_substrate.py` — schema validation, sandbox isolation, runner determinism, grader correctness
- [x] RED first; 16 tests (exceeded ~10 target)

### Exit gate

- [ ] All 5 scenarios run deterministically against `autocode exec --json` from a fresh sandbox — deferred: requires live gateway (per docs/plan/deferred/deferred-pending-todo.md §6.6)
- [ ] Each scenario produces a verification artifact at `autocode/docs/qa/test-results/<ts>-ai-verification-<scenario>.md` — deferred: requires live gateway
- [ ] Runner exits non-zero if any scenario's NDJSON stream fails grader expectations — deferred: requires live gateway
- [x] `git diff --check` clean
- [x] Update `docs/features/backend_features.md` with verification-harness entry
- [x] Update `autocode/TESTING.md` with how to run verification scenarios
- [x] P1 verification artifact at `autocode/docs/qa/test-results/<ts>-p1-ai-verification-substrate.md` — `20260430-154816-p1-ai-verification-substrate.md`
- [ ] Claude review APPROVE

---

## P1a — Telemetry Plumbing (Tier 8.1)

**Goal:** local-only JSONL event store + aggregator + CLI. Foundational for every subsequent phase. Detailed spec at `docs/plan/post-c7-telemetry-spec.md`.

### Module

- [ ] `autocode/src/autocode/telemetry/__init__.py` — package init
- [ ] `autocode/src/autocode/telemetry/store.py` — `TelemetryStore` class with append-only JSONL + daily rotation + background writer thread + bounded queue (10_000) with drop-on-full
- [ ] `autocode/src/autocode/telemetry/aggregator.py` — read jsonl files in date range, group by kind/session, produce summary structures
- [ ] `autocode/src/autocode/telemetry/events.py` — typed event-kind catalog matching `docs/plan/post-c7-telemetry-spec.md`

### CLI surfaces

- [ ] `autocode telemetry summary [--last 7d|30d|all]`
- [ ] `autocode telemetry events --kind <name> [--last <window>] [--session <id>]`
- [ ] `autocode telemetry session <session_id>`
- [ ] `autocode telemetry export [--since <date>] [--format jsonl|csv]`
- [ ] `autocode telemetry purge`
- [ ] CLI extension lands in `autocode/src/autocode/cli.py`

### Lifecycle hook wiring

- [ ] `agent/loop.py` — emit `session_start`, `turn_start`, `turn_completed`, `tool_call_started`, `tool_call_completed`, `tool_call_failed`, `slash_command_invoked`
- [ ] `backend/server.py` — emit `thread_start`, `thread_fork`, `thread_archive`
- [ ] `agent/cost_dashboard.py` integration — emit `llm_call_completed` with full usage block
- [ ] `agent/approval.py` integration — emit `approval_requested`, `approval_granted`, `approval_denied`

### Privacy + safety

- [ ] `AUTOCODE_TELEMETRY_DISABLED=true` env var → emit() becomes no-op
- [ ] Add `~/.autocode/telemetry/` to repo `.gitignore`
- [ ] CI test asserting no `import requests`/`urllib`/`http`/`socket` in `autocode/src/autocode/telemetry/`
- [ ] README privacy section updated
- [ ] `autocode telemetry purge` deletes everything under `~/.autocode/telemetry/`

### Tests

- [ ] `tests/unit/test_telemetry_store.py` — emit, queue, file rotation, drop-on-full, disable flag
- [ ] `tests/unit/test_telemetry_aggregator.py` — summary, filters, export formats
- [ ] RED first

### Exit gate

- [ ] All event kinds from spec catalog emit in expected scenarios
- [ ] `autocode telemetry summary --last 7d` produces non-empty table after a real session
- [ ] Daily file rotation under `~/.autocode/telemetry/events-YYYY-MM-DD.jsonl`
- [ ] P1 harness scenario: emit 100 events, summary correctly aggregates them
- [ ] Update `docs/features/backend_features.md`
- [ ] Update `docs/plan/post-c7-telemetry-spec.md` "Open questions" → "Resolved"
- [ ] Update `autocode/TESTING.md` with `autocode telemetry` CLI usage
- [ ] `git diff --check` clean
- [ ] P1a verification artifact at `autocode/docs/qa/test-results/<ts>-p1a-telemetry-plumbing.md`
- [ ] Claude review APPROVE

---

## P2 — Tier 1 Prompt Cache + Verify-Before-Use (atomic — must ship together)

**Goal:** 40-80% LLM cost cut on long agent runs. **Atomic constraint:** ship Tier 1.1 + 1.2 in the same PR. Shipping 1.1 alone busts cache every turn (current date / cwd / git status in stable region) → 25% cache-write premium with zero read benefit.

### Tier 1.1 — Cache breakpoint injection

- [ ] `autocode/src/autocode/layer4/llm.py` — extend `OpenRouterProvider` (~line 1024+) to inject `cache_control: {"type": "ephemeral", "ttl": "1h"}` on the LAST block of stable system prefix
- [ ] Inject `extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}` for OpenRouter→Anthropic models
- [ ] Capture `cache_creation_input_tokens` + `cache_read_input_tokens` + `cache_read_input_tokens` from response usage
- [ ] Provider detection: `_supports_explicit_cache(provider, model)` for Anthropic + OpenRouter→Anthropic + OpenRouter→Gemini
- [ ] OllamaProvider stays no-op; ensure no crash when `cache_control` field passed

### Tier 1.2 — Stable/dynamic prompt boundary

- [ ] Refactor `autocode/src/autocode/agent/prompts.py` `SYSTEM_PROMPT` into:
  - `STABLE_INSTRUCTIONS` constant
  - `build_stable_prefix(tool_definitions_json, rules_text, skill_catalog_index)`
  - `build_dynamic_tail(cwd, git_status_summary, current_iso_date, current_todo_state, open_tasks_summary)`
  - `assemble_system_prompt(...)` putting `CACHE_BOUNDARY_MARKER` between them
- [ ] `CACHE_BOUNDARY_MARKER = "# === DANGEROUS_uncachedSystemPromptSection_BELOW ==="`
- [ ] Provider layer (1.1) splits the system message at this marker before applying cache_control
- [ ] Deterministic tool-def serialization helper: `serialize_tool_defs_stable(tools)` with `sort_keys=True`, `separators=(",", ":")`, sorted by `tool.name`

### Tier 1.3 — Token tracker + `/cost` cache breakdown

- [ ] Extend `autocode/src/autocode/agent/token_tracker.py` `TokenUsage` dataclass with:
  - `cache_creation_tokens: int = 0`
  - `reasoning_tokens: int = 0`
  - `billable_input_cost_factor` property (weighted multiplier: cache reads at 0.10x, writes at 1.25x, regular 1.0x)
- [ ] `record_cache(provider, cache_read_tokens, cache_write_tokens)` aggregator
- [ ] `/cost` slash command shows cache reads / writes / reasoning / effective multiplier
- [ ] SQLite migration `ALTER TABLE` for token persistence schema
- [ ] Status bar cache-hit indicator in `rtui/src/render/view.rs`: `⚡N% cached`

### Tier 3.3 — Verify-before-use (folded in; touches `prompts.py` once)

- [ ] Append verify-before-use section to `STABLE_INSTRUCTIONS`:
  - "Treat any fact recalled from memory or past sessions as a HINT, not as ground truth..."
  - "Before acting on remembered information: re-read with read_file, check tools with tool_search, confirm decisions with grep or user..."

### Tests

- [ ] `tests/integration/test_prompt_cache.py` — first call cache_creation > 0; second call cache_read ≥ 1024 within 5 min on identical 2k-token system prompt
- [ ] `tests/unit/test_prompt_cache_boundary.py` — proves no time/path/git/todo strings leak above `CACHE_BOUNDARY_MARKER`
- [ ] `tests/unit/test_token_tracker_cache.py` — `record_cache` aggregation, billable_input_cost_factor math
- [ ] Cassette fixtures in `tests/fixtures/cassettes/` for cache-hit/miss verification
- [ ] RED first

### Telemetry

- [ ] `cache_breakpoint_applied` event emitted per request
- [ ] `llm_call_completed` event includes `cached_input_tokens`, `cache_creation_tokens`, `reasoning_tokens` fields

### P1 harness validation

- [ ] Run `cache-validation` scenario in P1 harness: cache-hit ratio > 0.5 deterministically across simulated 5-min session restart

### Exit gate

- [ ] All RED → GREEN
- [ ] Update `docs/features/backend_features.md` with cache feature entry
- [ ] Update `autocode/TESTING.md` with cache-test instructions
- [ ] `git diff --check` clean
- [ ] P2 verification artifact at `autocode/docs/qa/test-results/<ts>-p2-prompt-cache-and-verify.md`
- [ ] Claude review APPROVE

---

## P2a — Scratch Store (Tier 7.1)

**Goal:** offload large tool outputs to disk; keep only stub + summary in agent context.

### Module

- [ ] `autocode/src/autocode/agent/scratch.py` — `ScratchStore` class
- [ ] Threshold constants: `SCRATCH_THRESHOLD_BYTES = 5_000`, `SCRATCH_NEVER_FOR = {"todo_read", "ask_user", "memory_index_show"}`, `SCRATCH_ALWAYS_FOR = {"web_fetch", "git_log"}`
- [ ] Per-turn dir layout: `.autocode/scratch/<thread-id>/<turn-id>/<NNN>-<tool-name>.md`
- [ ] manifest.json per turn directory recording each offload
- [ ] Cleanup keeps last N=10 turn dirs per thread; deletes older

### Integration

- [ ] Wrap large tool outputs in `agent/loop.py` `_execute_tool_call` post-execute
- [ ] Adjust truncation rules in `agent/context.py` to respect scratch stubs
- [ ] Stub format: `[Tool output offloaded — N bytes saved to <path>]\n\nSummary: <line>\n\nFirst 5 lines:\n```\n<preview>\n```\nUse read_file on the path above to see the full output.`

### Telemetry

- [ ] `tool_output_offloaded` event with `tool_name`, `result_bytes`, `scratch_path`

### Tests

- [ ] `tests/unit/test_scratch.py` — small inlined, large offloaded, manifest correct, cleanup keeps N recent, never/always lists honored
- [ ] RED first

### P1 harness validation

- [ ] Scenario `large-tool-output-offload`: simulated 100-file `list_files` produces stub; scratch file exists; `read_file` on stub path returns full content

### Exit gate

- [ ] All RED → GREEN
- [ ] Update `docs/features/backend_features.md`
- [ ] `git diff --check` clean
- [ ] P2a verification artifact at `autocode/docs/qa/test-results/<ts>-p2a-scratch-store.md`
- [ ] Claude review APPROVE

---

## P3 — Tier 3 File-System Memory (Tier 3.1 + 3.2)

**Goal:** durable cross-session memory via 3-layer filesystem store. Replaces SQLite `MemoryStore` (deprecate, don't drop).

### Tier 3.1 — File-system 3-layer memory

- [ ] Create `autocode/src/autocode/session/memory_fs.py` (~600 LOC) — `MemoryFS` class
- [ ] Storage root: `~/.autocode/projects/<git-root-sha256-prefix>/`
- [ ] Layer 1: `MEMORY.md` index — ≤ 200 lines, ~150 chars per pointer line, pointers only
- [ ] Layer 2: `memory/<topic>.md` — soft 1000-line cap; auto-split into `<topic>-<sub>.md` over cap
- [ ] Layer 3: `logs/YYYY/MM/YYYY-MM-DD.md` — append-only daily logs
- [ ] Canonical git-root hashing — `git rev-parse --show-toplevel` SHA-256 prefix; same project across worktrees gets same memory dir
- [ ] New tools: `memory_read_topic`, `memory_write_topic`, `memory_grep_logs`, `memory_index_show`
- [ ] Auto-load `MEMORY.md` index at session start (in `backend/server.py::_ensure_agent_loop` after RulesLoader)
- [ ] One-shot SQLite `MemoryStore` → topic-files migration script at `scripts/migrate_memory_to_fs.py`
- [ ] Deprecate `agent/memory.py` (mark deprecated; rename `memories` table to `memories_archive_<date>`)
- [ ] Re-target `consolidation.py` autoDream writes from SQLite to topic files

### Tier 3.2 — Session Notes

- [ ] Create `autocode/src/autocode/session/session_notes.py` (~250 LOC) — `SessionNotes` class
- [ ] Activation: 10k tokens; update interval: 5k tokens; gate: ≥ 3 tool calls between updates
- [ ] Compaction Path A integration in `agent/context.py` — use Session Notes as summary instead of fresh API call
- [ ] Telemetry: `compaction_event` with `path: A | B`, `tokens_before`, `tokens_after`

### Tests

- [ ] `tests/unit/test_memory_fs.py` — index 200-line cap, pointer 150-char cap, topic frontmatter, daily log append, grep_logs, git-root hashing, worktree consistency, slug sanitization, migration path
- [ ] `tests/unit/test_session_notes.py` — activation threshold, update interval, tool-call gate, Path A vs B selection
- [ ] `tests/integration/test_verify_before_use.py` — model re-reads file before relying on memory (LLM-eval; expect flakiness)
- [ ] RED first

### Tool list cleanup

- [ ] Re-implement `memory_list` legacy tool against `MemoryFS` OR remove it with deprecation cycle (cross-cutting §"Risk: agent still references old SQLite")

### P1 harness validation

- [ ] Scenario `memory-survives-restart`: write topic, simulate session restart, agent reads topic, content intact
- [ ] Scenario `compaction-path-a`: trigger 10k-token threshold, Path A chosen, summary references session notes

### Exit gate

- [ ] All RED → GREEN
- [ ] `MEMORY.md ≤ 200 lines` after 50 simulated sessions
- [ ] Path A chosen ≥ 80% of compaction events once 10k threshold passed
- [ ] Migration script idempotent; safe to re-run
- [ ] Update `docs/features/backend_features.md`
- [ ] Update `autocode/TESTING.md` with memory_fs harness usage
- [ ] `git diff --check` clean
- [ ] P3 verification artifact at `autocode/docs/qa/test-results/<ts>-p3-file-system-memory.md`
- [ ] Claude review APPROVE

---

## Hook Architecture Refactor (between P3 and P3a)

**Goal:** extract `agent/loop.py` hook protocol so subsequent phases (drift, PEV, Ralph, telemetry, entropy, verify-nudge) plug in declaratively rather than piling into the loop body.

**Why now:** by P3b the loop has ~12 hooks. Without this refactor, P3a-d become difficult to land cleanly.

### Tasks

- [ ] Audit current hooks in `agent/loop.py`: auto-verify (C5.G4), atomic checkpoint (C4.G1), git-aware staging (C4.G7'), prompt-cache keepalive (C7.G11), scratch (P2a), memory load (P3), telemetry emit (P1a)
- [ ] Define `Hook` Protocol in `autocode/src/autocode/agent/hooks.py` with method signatures: `pre_tool_call(tc) -> None`, `post_tool_call_success(tc, result) -> str | None`, `post_tool_call_error(tc, exc) -> None`, `pre_turn(turn_id) -> None`, `post_turn(turn_id, status) -> None`, `on_token(text) -> None`
- [ ] `HookDispatcher` class — registry of hooks, ordered execution, exception isolation (one bad hook doesn't break the loop)
- [ ] Migrate existing hooks to declarative `Hook` instances + register in `factory.py::create_orchestrator`
- [ ] No behavioral change — proven by full unit suite passing pre-refactor and post-refactor with identical results

### Tests

- [ ] `tests/unit/test_hook_dispatcher.py` — registration, order, exception isolation, conditional skip
- [ ] Full unit suite (current ~2159 baseline) green pre + post

### Exit gate

- [ ] Full unit suite still green (zero diff in pass/fail)
- [ ] All Track 1 + Track 4 + VHS + PTY smokes green
- [ ] `git diff --check` clean
- [ ] Update `docs/architecture.md` with hook architecture section
- [ ] Hook-refactor verification artifact at `autocode/docs/qa/test-results/<ts>-hook-architecture-refactor.md`
- [ ] Claude review APPROVE

---

## P3a — Drift Detectors (Tier 5.1)

### Module

- [ ] `autocode/src/autocode/agent/drift.py` (~400 LOC)
- [ ] `SchemaDriftDetector` — sensitivity = low/medium/high; per-`(tool, args_hash)` shape fingerprint; alerts on type changes (medium) or new keys (high)
- [ ] `ContextStalenessDetector` — topic-file age threshold (default 7 days, configurable)
- [ ] `ToolConsistencyDetector` — `read_file`, `list_files`, `git_status`, `list_symbols` should return identical results within one turn

### Integration

- [ ] Register all three detectors as Hooks via the dispatcher (post-refactor)
- [ ] Drift warning injection: `[Drift detected — <kind>, severity <level>]` system message before next turn
- [ ] Latency budget: < 5 ms per detection (benchmark in CI)
- [ ] Per-detector disable flags in `~/.autocode/config.yaml`: `agent.drift.{schema,staleness,consistency}.enabled`

### Telemetry

- [ ] `tool_drift_detected` event with `tool_name`, `drift_kind`, `severity`
- [ ] `autocode telemetry drift --last 7d` aggregation CLI

### Tests

- [ ] `tests/unit/test_drift.py` — schema drift on column rename, staleness fires on > 7-day topic, consistency fires on same-turn mismatch, sensitivity thresholds, latency benchmark
- [ ] RED first

### P1 harness validation

- [ ] Scenario `drift-schema-detection`: simulated tool output schema change → exact detector fires → agent acknowledges in next turn

### Exit gate

- [ ] All RED → GREEN
- [ ] Latency benchmark < 5 ms per detector
- [ ] Update `docs/features/backend_features.md`
- [ ] `git diff --check` clean
- [ ] P3a verification artifact at `autocode/docs/qa/test-results/<ts>-p3a-drift-detectors.md`
- [ ] Claude review APPROVE

---

## P3b — PEV + Ralph Reliability Loops (Tier 5.2 + 5.3)

### PEV (Plan-Execute-Verify)

- [ ] `autocode/src/autocode/agent/pev.py` (~350 LOC) — `PEVRunner` with model role separation
- [ ] `Plan` + `PlanStep` + `StepResult` dataclasses
- [ ] Verifier system prompt added to `agent/prompts.py`
- [ ] Auto-detect: `todo_write` with > 3 items → wrap subsequent execution in PEV
- [ ] One retry with verifier feedback on `next_action: retry_step`
- [ ] Rollback strategy honors C5.G4 contract (no auto-rollback; surface `/rollback` to user)

### Ralph Loop

- [ ] `autocode/src/autocode/session/intent_store.py` (~150 LOC) — SQLite `IntentStore`
- [ ] `autocode/src/autocode/agent/ralph_loop.py` (~250 LOC) — `RalphRecoveryDetector` + `RalphLoop`
- [ ] Triggers: give-up phrase + zero tool calls; 3 consecutive zero-progress turns; context > 85% with zero tool calls in last 3 turns
- [ ] Don't fire on first turn
- [ ] Cap 3 fires per session
- [ ] `AUTOCODE_DISABLE_RALPH=true` env var
- [ ] Recovery: snapshot progress → aggressive compaction → re-inject intent as user message starting with `[Ralph recovery`

### Hook integration

- [ ] PEV runner registered as Hook
- [ ] Ralph loop registered as post-turn Hook

### Telemetry

- [ ] `pev_step_failed` event with `plan_step_id`, `verdict`
- [ ] `ralph_recovery_fired` event with `trigger_kind`, `context_fraction`

### Tests

- [ ] `tests/integration/test_pev.py` — 4-step plan with verifier predicates runs end-to-end; step failure with retry; abort_plan path
- [ ] `tests/integration/test_ralph.py` — fires on give-up phrase + zero tool calls; doesn't fire on first turn; cap-3-per-session honored
- [ ] `tests/unit/test_intent_store.py` — capture, persist across simulated restart, append progress

### Exit gate

- [ ] All RED → GREEN
- [ ] Update `docs/features/backend_features.md`
- [ ] `git diff --check` clean
- [ ] P3b verification artifact at `autocode/docs/qa/test-results/<ts>-p3b-pev-ralph.md`
- [ ] Claude review APPROVE

---

## P3c — Entropy + Verify Tightening (Tier 7.2 + 7.3)

### Entropy auditor

- [ ] `autocode/src/autocode/agent/entropy.py` (~150 LOC) — `EntropyAuditor`
- [ ] Audit interval: every 10 turns; max 20 messages; cheap fast model
- [ ] Categories: naming drift, decision reversal, stale reference, fact conflict
- [ ] High severity → inject system warning + recommend rollback to last checkpoint
- [ ] Medium → inject warning + log telemetry
- [ ] Low → log only
- [ ] Auto-disable on cost cap

### Anti-entropy prompt

- [ ] Add §"Internal consistency" section to `STABLE_INSTRUCTIONS`

### Memory-fact runtime nudge

- [ ] In `agent/loop.py` (via Hook): when agent's response cites a memory-derived fact path without preceding `read_file`, inject `[Reminder: you're acting on memory of X without re-reading it...]` system message

### Telemetry

- [ ] `entropy_audit_completed` event with `severity_max`, `incident_count`

### Tests

- [ ] `tests/integration/test_entropy.py` — naming-drift detected, decision-reversal detected, audit cadence honored
- [ ] `tests/integration/test_verify_nudge.py` — nudge fires when memory-fact path cited without read_file

### Exit gate

- [ ] All RED → GREEN
- [ ] Update `docs/features/backend_features.md`
- [ ] `git diff --check` clean
- [ ] P3c verification artifact at `autocode/docs/qa/test-results/<ts>-p3c-entropy-verify.md`
- [ ] Claude review APPROVE

---

## P3d — Eval Suite Expansion (Tier 8.2 + 8.3 + 8.4 + optional 8.5)

### Eval case schema

- [ ] `evals/cases/_schema.yaml` reference (or equivalent docstring) — must_have, must_not_have, judge_criteria, config, baseline
- [ ] Convert each P1 hand-graded scenario into a full eval case with `baseline.<criterion>_score`

### Runner + judge

- [ ] `evals/runner.py` (~300 LOC) — fixture setup, autocode session launch, telemetry collection, judge invocation, result struct
- [ ] `evals/judge.py` (~150 LOC) — LLM-as-judge with structured JSON output; agent on `qwen3-coder:free`, judge on stronger model

### CI gate

- [ ] `.github/workflows/evals.yml` — runs stratified case sample on PR, soft-warn for first 2 weeks, then promote to hard merge-blocking
- [ ] `--baseline-tolerance 0.10` (10% drift allowed)
- [ ] `--max-budget-usd 5.00` cost cap

### Drift-derived eval generator

- [ ] `scripts/generate_evals_from_drift.py` — read `tool_drift_detected` events from telemetry, group by `(tool_name, drift_kind)` over 30-day windows, ≥ 3 occurrences proposes new eval case
- [ ] Run weekly; engineer reviews + accepts or rejects

### Optional public stats

- [ ] `autocode telemetry public-report --output public-stats.json` (per `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` §8.5; OPTIONAL)

### Tests

- [ ] `tests/unit/test_eval_runner.py` — case load, fixture setup, must_have / must_not_have predicates
- [ ] `tests/unit/test_eval_judge.py` — structured-output validation, score range, deterministic temperature

### Regression discipline (Tier 8.3 — five rules)

- [ ] PR template updated to require `evals/cases/<id>.yaml` for every bug fix
- [ ] Drift incident → eval case workflow documented in `autocode/TESTING.md`
- [ ] Baseline updates require justification in PR description
- [ ] Eval cases append-only; archive via `archived: true` field, never delete
- [ ] Eval execution reproducible: fix model + temperature + seed + fixture commit hash

### Exit gate

- [ ] All RED → GREEN
- [ ] Eval case fails on `main` for known-buggy fixture; passes on fixed branch
- [ ] CI workflow gates merges on baseline tolerance
- [ ] Drift-derived eval generator proposes ≥ 1 case from 30 days of seeded drift events
- [ ] Update `docs/features/backend_features.md`
- [ ] Update `autocode/TESTING.md` with eval workflow + 5 regression discipline rules
- [ ] `git diff --check` clean
- [ ] P3d verification artifact at `autocode/docs/qa/test-results/<ts>-p3d-eval-suite-expansion.md`
- [ ] Telemetry CI gate strictness LOCKED (was decision #5; now finalized: soft for 2 weeks then hard)
- [ ] Claude review APPROVE

---

## P4 — Tier 2 Item/Turn/Thread (DEFERRED — out of scope for this pass)

**Status:** OUT OF SCOPE per User decision #2 (no second client surface within 6 months). Skip.

If second client surface materializes during the pass, raise a Concern entry directed to Claude + User; do not start P4 unilaterally.

---

## P4a — TUI Refactor (Path A only — Tier 6 refactor option)

**Status:** PATH A REFACTOR ONLY. Path B rewrite is OUT (gated on P4 which is deferred).

### Refactor scope (~−2900 LOC)

- [ ] `rtui/src/render/view.rs` — replace 9 × 9 stage × detail-surface match arms with widget-per-mode pattern (~−2000 LOC); each mode renders into ~30-60 line function; no layout recursion deeper than 2 levels
- [ ] Cache `Lines<'static>` per history entry (`HistoryEntry::cached_lines: RefCell<Option<(u16, Vec<Line<'static>>)>>`); invalidate on entry mutation or width change (~−400 LOC of streaming buffer hacks)
- [ ] `rtui/src/state/reducer.rs` — collapse 40+ Event variants into one `RpcMsg(Value)` + sub-reducer pattern where appropriate (~−500 LOC of boilerplate)

### Performance budgets (refactor targets)

- [ ] Cold start to first frame < 150 ms
- [ ] Resident memory at idle < 60 MB
- [ ] Frame time during streaming < 5 ms
- [ ] `cells_changed_per_streaming_delta` benchmark < 30
- [ ] Binary size < 1.8 MB

### Tests

- [ ] All Track 1 (runtime invariants) green
- [ ] All Track 4 (design-target ratchet) green
- [ ] All VHS PNG snapshots green (no rebaseline without User signoff per `feedback_vhs_rebaseline_user_gated.md`)
- [ ] All PTY smokes green (slash surfaces, real-gateway canary)
- [ ] New `cells_changed_per_streaming_delta` benchmark in CI

### Out of scope (skipped because P4 deferred)

- 44 RPC structs → 3 primitives collapse — DEFERRED with P4
- Item/Turn/Thread protocol consumption — DEFERRED with P4

### Exit gate

- [ ] Final size ~4600 LOC (vs current 7500)
- [ ] No behavioral regression
- [ ] All performance budget targets met
- [ ] Update `docs/features/backend_features.md` (TUI refactor entry)
- [ ] Update `docs/tui-testing/tui-testing-strategy.md` if testing dimensions changed
- [ ] `git diff --check` clean
- [ ] P4a verification artifact at `autocode/docs/qa/test-results/<ts>-p4a-tui-refactor.md`
- [ ] Claude review APPROVE

---

## P5 — Tier 4 Feature-Flag Tracks (KAIROS only; 4.2/4.3 deferred)

**Status:** KAIROS ONLY. Tier 4.2 (ephemeral fork) and 4.3 (sticky env) require P4 → DEFERRED with P4.

### Tier 4.1 — KAIROS proactive mode

- [ ] `autocode/src/autocode/agent/proactive.py` (~400 LOC) — `ProactiveLoop` + `TickConfig`
- [ ] `<tick>` injection format with local time + "you're awake" prompt
- [ ] `SleepTool` in `agent/tools.py` (~80 LOC) — wait + reason; cap at 10x cache TTL
- [ ] 15-second blocking budget for tick-triggered tool calls (`asyncio.wait_for` wrapper)
- [ ] Anti-narration system prompt section (when KAIROS active)
- [ ] `autocode daemon --watch /path/to/repo` CLI subcommand
- [ ] Terminal-focus-awareness: pause ticks when user mid-typing
- [ ] Cap 3 Ralph fires per session (overlap with P3b Ralph contract)

### Feature flag

- [ ] `AUTOCODE_FEATURE_KAIROS=false` default-off
- [ ] Promotion criterion: ≥ 4 weeks of P1a telemetry baseline + observability story (per `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` §"Why this is last")

### Telemetry

- [ ] `tick_count`, `sleep_call_ratio`, `anti_narration_violations`, `kairos_action_blast_radius` events
- [ ] Alert if `anti_narration_violations` > 5%

### Tests

- [ ] `tests/integration/test_kairos.py` — tick injection, sleep tool delay, blocking-budget enforcement, anti-narration detection, terminal-focus pause, batched ticks

### Exit gate

- [ ] All RED → GREEN
- [ ] Default-off flag honored (no behavioral change without env var)
- [ ] Update `docs/features/backend_features.md`
- [ ] `git diff --check` clean
- [ ] P5 verification artifact at `autocode/docs/qa/test-results/<ts>-p5-kairos.md`
- [ ] Claude review APPROVE

---

## Pass exit gate

After all 11 phase blocks ship:

- [ ] Full unit suite green (target: ~2400+ tests; +240 vs C7.GATE baseline `2159`)
- [ ] Benchmark harness green
- [ ] All PTY smokes green (LSP × 8, auto-verify, slash surfaces, real-gateway canary)
- [ ] All Track 1 + Track 4 + VHS green
- [ ] Eval suite green (P3d baselines)
- [ ] `autocode telemetry summary --last 7d` produces meaningful data
- [ ] `git diff --check` clean
- [ ] All P-phase verification artifacts present
- [ ] Top-level state docs synced: `current_directives.md`, `EXECUTION_CHECKLIST.md`, `PLAN.md`, `docs/features/backend_features.md`, `docs/plan/post-c7-stable-commit-roadmap.md`, this checklist
- [ ] Comms log archived; user runs the next stable commit
- [ ] Optional: `autocode telemetry public-report` snapshot stored

---

## Builder routing (locked from Entry 1695)

- **OpenCode** — primary Builder
- **Codex** — Reviewer/Architect (default); Builder fallback if OpenCode unavailable
- **Claude** — Reviewer (primary); spawns checklists; coordinates phase boundaries
- **User** — Product Owner; commits at user's discretion

## Workflow per slice/phase

1. Pre-task intent in `AGENTS_CONVERSATION.MD` directed to Claude
2. RED tests first → GREEN
3. Constraint #8: docs + verification artifact + checklist boxes BEFORE Review Request
4. Review Request directed to Claude with test counts + artifact path + tripwire check
5. Claude APPROVE → next slice/phase auto-flows

No fast-forward authorization unless User explicitly grants it. Each phase/slice gets its own pre-task + Review Request cycle.
