# Next Remaining Plan — Post-C7 Pass

> **Status:** AUTHORITATIVE master plan. Consolidates `docs/plan/post-c7-stable-commit-roadmap.md`, `docs/plan/post-c7-pass-atomic-checklist.md`, `docs/plan/post-c7-builder-handoff.md`, `docs/plan/post-c7-telemetry-spec.md`, and the 9 gap categories from the 2026-04-30 audit. Use this file + `next_remaining_todo.md` (atomic checklist) as the single pair of references for builders.
> **Date:** 2026-05-06. Updated for backend-harness-first redirect after the TUI v9 plan was locked. `docs/plan/backend-harness-solidification-plan.md` B1-B6 are builder-complete; B7 modular follow-through remains. `TUI_PLAN.md` is locked and unblocked by B6 closure, but not started unless user directs it.
> **Stable commit:** `386ef04 Implements till c7` (Tranche 4 closed).
> **Tier source docs:** `docs/plan/roadmaps/2026-04-30-tier-roadmap/00-INDEX.md` through `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md`.

---

## Status snapshot

### Done in `386ef04 Implements till c7`

| Capability | Slice | Notes |
|---|---|---|
| Per-tool atomic checkpoints + `/rollback` | C4.G1 | `~/.autocode/snapshots/<session>/<tool_call>/`; no tree-mutating git |
| Ranked tree-sitter repo-map + `/repomap` | C4.G2 | Token-budget ranked builder |
| Git-aware staging + repo-wide forbidden-git scan | C4.G7' | Mechanical enforcement |
| 8-language LSP framework (Java/JS/TS/C/Kotlin/Python/Go/Rust) | C5.G3.0-8 | All 8 PTY smokes green |
| Auto-verify-after-edit loop + `/verify` | C5.G4 | No auto-rollback per contract |
| Headless `--json` Tier 4.4 NDJSON subset + `autocode generate-schema` | C6.G5 | Tier 4.4 from `docs/plan/roadmaps/2026-04-30-tier-roadmap/04-tier4-future-tracks.md` IS DONE |
| Layer 4.5 cost-aware router with cache-multiplier hook | C6.G6 | `billable_input_cost_factor` plumbed through; defaults to 1.0 until Tier 1 lands |
| Plan/Architect ↔ Editor model split | C7.G8 | `agent.architect_model`, `agent.editor_model`; `/architect`, `/editor` |
| AGENTS.md nestable per-directory memory | C7.G9 | Parent-to-child rules ordering; `/agents reload` (PARTIAL Tier 3 overlap; different mechanism) |
| Session fork/branch + rollout replay payload | C7.G10 | Simpler than full Tier 2.1 thread/fork; `/fork`, `/tree` |
| Intra-session prompt cache keepalive | C7.G11 | DIFFERENT from Tier 1.1 cross-session breakpoint cache; provider-gated keepalive scheduler |
| Recipe/workflow YAML packaging | C7.G12 | Bundled `refactor`, `add-feature`, `fix-bug` recipes; `/recipe list|run` |
| Worktree subagent handoff | C7.G13 | Read-only diff-to-`apply_patch` plan; no forbidden git |
| Watch mode parser + command | C7.G14 | `# AUTOCODE: <instruction>` parser; persistent observer DEFERRED |
| Static marketplace registry pointer | C7.G15 | Local-only; remote fetch DEFERRED |
| **AI verification harness narrow substrate (P1)** | post-commit | YAML scenarios + NDJSON runner + grader; 20 substrate tests green |

**Test surface at `386ef04`:** `2159 passed, 12 skipped` unit; `220 passed` benchmark (= `204` C7.GATE + `16` P1; new test count after subsequent P0 hardening is `20` for P1/P0 substrate coverage).

### Active override — backend harness solidification (2026-05-06)

User direction has advanced the post-C7 pass through HFIX, P3b, P3c, P3d, and P5, then redirected the next work to backend harness solidity before TUI implementation. Treat `docs/plan/backend-harness-solidification-plan.md` as the active backend closeout plan and `next_remaining_todo.md` as the atomic checklist context. P5 remains builder-complete and Claude-approved with default-off daemon ticks, dedicated `kairos.tick`, backend-enforced read-only ticks, anti-narration telemetry alerts, `/kairos pulse`, deterministic eval evidence, and public telemetry snapshot evidence. The active sequence is B1 audit/gap map → B2 deterministic verdict truthfulness → B3 scenario contract hardening → B4 structured artifacts/batch reporting → B5 infra classifier/retry validation → B6 backend feature surface coverage.

### Active blockers and loose ends

- **Claude final review:** P5 final gate review is closed by Claude Entry 1934 (`FINAL APPROVE`); post-pass-exit closeout is closed by Claude Entry 1942 (`APPROVE`).
- **Live gates:** PTY/canary, Track 1/Track 4/VHS, and broad live product-path gates remain open because they require the supported live gateway/TUI environment.
- **Promotion gates:** the four-week telemetry baseline, initial dry-run rollout policy, and any default-on KAIROS promotion decision remain future-scoped.
- **Parked TUI work:** P4a/TUI v9 work is locked in `TUI_PLAN.md` but parked until Backend Harness Solidification B6 closes or the user explicitly overrides.

### Tier coverage (audit 2026-04-30)

| Source doc | Status |
|---|---|
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/01-tier1-prompt-cache.md` (Tier 1.1+1.2+1.3) | Builder-complete as P2. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/02-tier2-app-server-protocol.md` (Tier 2.1+2.2+2.3) | DEFERRED as P4 + P4-dependents per User decision #2. Not done. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/03-tier3-memory-architecture.md` (Tier 3.1+3.2+3.3) | Builder-complete as P2/P3. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/04-tier4-future-tracks.md` (Tier 4.1+4.2+4.3+4.4) | 4.4 DONE (C6.G5); 4.1 builder-complete as P5 default-off KAIROS; 4.2/4.3 DEFERRED with P4. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/05-cross-cutting-concerns.md` | Accounted for as per-phase gates. Not fully executed (each phase enforces as it lands). |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/06-INDEX-part2.md` | Accounted for (sequencing index for Tiers 5-8). Not itself implementation. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/07-tier5-harness-reliability.md` (5.1+5.2+5.3) | Builder-complete as P3a/P3b after HFIX. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/08-tier6-minimal-tui.md` | Path A refactor planned as P4a; Path B rewrite OUT (decision #4). Not done. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/09-tier7-context-engineering.md` (7.1+7.2+7.3) | Builder-complete as P2a/P3c. |
| `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` (8.1+8.2+8.3+8.4+8.5) | Builder-complete as P1a/P3d, with public-report snapshot evidence captured at pass exit. |

---

## Locked User Decisions (2026-04-30)

| # | Decision | Outcome |
|---|---|---|
| 1 | P2 timing | Strictly post-commit (already satisfied). Builder works continuously through phases; commits at User discretion. |
| 2 | Second client surface | OUT OF SCOPE. P4 (Tier 2 Item/Turn/Thread) DEFERRED. Tier 4.2 ephemeral fork + 4.3 sticky env DEFERRED with P4. |
| 3 | AI verification harness | Narrow substrate using EXISTING features and interfaces only. No new infrastructure for the harness itself. |
| 4 | TUI path | Path A refactor only. Path B rewrite OUT (eliminated by #2; and no new client surface). |
| 5 | Telemetry CI gate strictness | DEFERRED to spec. Final strictness locked when P1a + P3d ship; v1 default = soft gate first 2 weeks, then hard. |
| 6 | `agent/loop.py` hook-architecture refactor | YES. Insert between P3 and P3a. ~2-3 days, ~150 LOC. |

---

## Phase order

```
P0   Hardening / reconciliation                            (~1-2 days)
P1   AI verification harness narrow substrate              [DONE — 20 substrate tests green; reconciled in P0]
P1a  Telemetry plumbing (Tier 8.1)                         [BUILDER-COMPLETE]
P2   Tier 1 prompt cache + verify-before-use (atomic)      [BUILDER-COMPLETE]
P2a  Scratch store (Tier 7.1)                              [BUILDER-COMPLETE]
P3   Tier 3 file-system memory (Tier 3.1+3.2)              [BUILDER-COMPLETE]
HR   Hook architecture refactor                            [BUILDER-COMPLETE]
P3a  Drift detectors (Tier 5.1)                            [BUILDER-COMPLETE]
HFIX AI verification harness fixes                         [CLOSED under gateway-deferral policy]
P3b  PEV + Ralph reliability loops (Tier 5.2+5.3)          [BUILDER-COMPLETE; Claude approved Entry 1880]
P3c  Entropy + verify tightening (Tier 7.2+7.3)            [BUILDER-COMPLETE; Claude approved-with-followup Entry 1888]
P3d  Eval suite expansion (Tier 8.2-8.5)                   [BUILDER-COMPLETE]
P5   Tier 4.1 KAIROS feature-flag track                    [BUILDER-COMPLETE; Claude approved Entry 1934; post-pass-exit approved Entry 1942]
```

**Total estimated post-commit cost:** ~9-12 weeks, NET +1700 to +2700 LOC (P4a refactor deferred — TUI work explicitly out per User Entry 1736 direction).

**Parked behind backend harness closeout:**
- P4a/TUI v9 Path A refactor — canonical plan: `TUI_PLAN.md`. Do not start TUI implementation until Backend Harness Solidification B6 closes or the user explicitly overrides.

**Stable-codebase commit point (LOCKED):** **Option C** — User pick per Entry 1743. Single commit at full pass close (post-P5 KAIROS). No intermediate commits at HR / P3a / P3d boundaries. The full pass is now closed deterministically; user stable commit is the next action.

---

## Per-phase narrative

### P0 — Hardening / reconciliation [PRIORITY]

**Goal:** lock P1 substrate, reconcile comms, generalize gitignore before more phases land.

**Why now:** P1 was approved at 16 tests but is now at 19 (with one regression caught during expansion). User audit flagged duplicate Entry 1702. `.gitignore` patterns were tuned for early phases only.

**Atomic tasks:** see `next_remaining_todo.md` §P0.

**Acceptance:** `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q` → all current tests GREEN; `RunMeta.status` records the final verdict; `.gitignore` covers post-C7 phase artifact suffixes through P5.

### P1a — Telemetry plumbing (Tier 8.1)

**Goal:** local-only JSONL event store + aggregator + CLI. Foundational for every subsequent phase.

**Reference spec:** `docs/plan/post-c7-telemetry-spec.md`.

**File targets:**
- `autocode/src/autocode/telemetry/store.py` — `TelemetryStore` (~200 LOC)
- `autocode/src/autocode/telemetry/aggregator.py` (~150 LOC)
- `autocode/src/autocode/telemetry/events.py` — typed event-kind catalog
- `autocode/src/autocode/cli.py` — `autocode telemetry` subcommands (~100 LOC)
- `autocode/src/autocode/agent/loop.py` + `backend/server.py` + `agent/cost_dashboard.py` + `agent/approval.py` — emit hooks (~50 LOC scattered)

**Privacy hard rules:**
- Local-only. `AUTOCODE_TELEMETRY_DISABLED=true` zero-overhead opt-out.
- `~/.autocode/telemetry/` in `.gitignore`.
- CI test asserts no `import requests`/`urllib`/`http`/`socket` from telemetry path.
- `autocode telemetry purge` deletes everything.
- Bounded queue (10_000) with drop-on-full.

**Event kinds (from spec):** session/thread/turn lifecycle; `tool_call_started/completed/failed`; `tool_output_offloaded` (P2a); `tool_drift_detected` (P3a); `llm_call_completed`, `cache_breakpoint_applied` (P2), `compaction_event`; approval events; `ralph_recovery_fired` (P3b), `entropy_audit_completed` (P3c), `pev_step_failed` (P3b); `slash_command_invoked`, `feature_flag_toggled`.

**Performance budgets:**
- `emit()` < 5 µs (queue put)
- Background writer flush < 50 ms per batch
- `summary --last 7d` aggregation < 500 ms over ~50k events
- Background thread < 1% CPU at steady state

### P2 — Tier 1 prompt cache + verify-before-use (ATOMIC)

**Goal:** 40-80% LLM cost cut on agent runs > 2 turns.

**Atomic constraint:** Tier 1.1 + 1.2 ship together. Shipping 1.1 alone busts cache every turn (current date / git status / cwd in stable region) → 25% cache-write premium with zero read benefit.

**Tier 1.1 — Cache breakpoint injection** (`autocode/src/autocode/layer4/llm.py`)
- Inject `cache_control: {"type": "ephemeral", "ttl": "1h"}` on last block of stable prefix
- Inject `extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}` for OpenRouter→Anthropic
- Capture `cache_creation_input_tokens` + `cache_read_input_tokens` from response
- Provider detection: `_supports_explicit_cache(provider, model)` — Anthropic direct, OpenRouter→Anthropic, OpenRouter→Gemini
- Ollama no-op guard

**Tier 1.2 — Stable/dynamic boundary** (`autocode/src/autocode/agent/prompts.py`)
- Refactor `SYSTEM_PROMPT` into `STABLE_INSTRUCTIONS` + `build_stable_prefix` + `build_dynamic_tail`
- `CACHE_BOUNDARY_MARKER = "# === DANGEROUS_uncachedSystemPromptSection_BELOW ==="`
- Provider layer (1.1) splits at this marker before applying `cache_control`
- Deterministic tool-def serialization (`sort_keys=True`, sorted by `tool.name`)

**Tier 1.3 — Token tracker + `/cost` cache breakdown**
- Extend `TokenUsage` with `cache_creation_tokens`, `reasoning_tokens`, `billable_input_cost_factor`
- `record_cache(provider, cache_read_tokens, cache_write_tokens)` aggregator
- `/cost` shows cache reads / writes / reasoning / effective multiplier
- SQLite migration `ALTER TABLE` for token persistence
- Status bar cache-hit indicator in `rtui/src/render/view.rs`: `⚡N% cached`

**Tier 3.3 — Verify-before-use (folded in)**
- Append verify-before-use section to `STABLE_INSTRUCTIONS`

**Edge cases (from `docs/plan/roadmaps/2026-04-30-tier-roadmap/01-tier1-prompt-cache.md` §"Edge cases" + §"Risk & mitigation"):**
- 4-breakpoint hard limit per request — reserve: system / tool defs / RulesLoader / optional CLAUDE.md
- Workspace isolation (Anthropic Feb 5 2026): caches per-workspace, not per-org
- Don't override `provider.order` on OpenRouter — disables sticky routing
- Wrap call in try/except → fall back to non-cached request if provider rejects `cache_control`

**Rollback:** `AUTOCODE_DISABLE_PROMPT_CACHE=true` falls back to non-cached.

### P2a — Scratch store (Tier 7.1)

**Goal:** offload large tool outputs to disk; keep stub + summary in agent context.

**File targets:**
- `autocode/src/autocode/agent/scratch.py` — `ScratchStore` (~250 LOC)
- `autocode/src/autocode/agent/loop.py` — wrap large tool outputs at execute boundary
- `autocode/src/autocode/agent/context.py` — adjust truncation rules

**Threshold rules:**
- `SCRATCH_THRESHOLD_BYTES = 5_000`
- `SCRATCH_NEVER_FOR = {"todo_read", "ask_user", "memory_index_show"}`
- `SCRATCH_ALWAYS_FOR = {"web_fetch", "git_log"}`

**Layout:** `.autocode/scratch/<thread-id>/<turn-id>/<NNN>-<tool>.md` + `manifest.json`. Cleanup keeps last N=10 turn dirs.

**Telemetry:** `tool_output_offloaded` event (consumes P1a).

**Rollback:** `AUTOCODE_DISABLE_SCRATCH=true` inlines all outputs.

### P3 — Tier 3 file-system memory (Tier 3.1 + 3.2)

**Goal:** durable cross-session memory via 3-layer filesystem store. Replaces SQLite `MemoryStore` (deprecate, don't drop).

**Tier 3.1:**
- `autocode/src/autocode/session/memory_fs.py` — `MemoryFS` (~600 LOC)
- Storage root: `~/.autocode/projects/<git-root-sha256-prefix>/`
- Layer 1: `MEMORY.md` index ≤ 200 lines, ~150 chars per pointer line, pointers only
- Layer 2: `memory/<topic>.md` — soft 1000-line cap; auto-split into `<topic>-<sub>.md` over cap
- Layer 3: `logs/YYYY/MM/YYYY-MM-DD.md` append-only daily logs
- Tools: `memory_read_topic`, `memory_write_topic`, `memory_grep_logs`, `memory_index_show`
- Auto-load `MEMORY.md` at session start
- One-shot SQLite `MemoryStore` → topic-files migration script `scripts/migrate_memory_to_fs.py`
- Deprecate `agent/memory.py` (rename `memories` table to `memories_archive_<date>`)
- Re-target `consolidation.py` (autoDream) writes to topic files
- **Re-implement `memory_list` against `MemoryFS` OR remove with deprecation cycle** (cross-cutting risk)
- **Migration guide:** new doc `docs/reference/memory-migration-v1.md`

**Tier 3.2:**
- `autocode/src/autocode/session/session_notes.py` — `SessionNotes` (~250 LOC)
- Activation: 10k tokens; update interval: 5k tokens; tool-call gate ≥ 3
- Compaction Path A integration in `agent/context.py`
- Telemetry: `compaction_event` with `path: A | B`, `tokens_before`, `tokens_after`

**Performance budgets (P3 acceptance):**
- Memory index load (Layer 1) < 50 ms
- Topic file load (Layer 2) < 200 ms per file
- `grep_logs` over 30 days < 500 ms
- Compaction Path A < 1 sec
- Compaction Path B (LLM call) < 30 sec

**Rollback:** `AUTOCODE_USE_LEGACY_MEMORY=true` reads `memories_archive_<date>` table.

### Hook Architecture Refactor (between P3 and P3a)

**Goal:** extract `agent/loop.py` hook protocol so subsequent phases plug in declaratively.

**File targets:**
- `autocode/src/autocode/agent/hooks.py` — `Hook` Protocol + `HookDispatcher`
- `factory.py::create_orchestrator` — declarative registration

**Hooks audited:** auto-verify (C5.G4), atomic checkpoint (C4.G1), git-aware staging (C4.G7'), prompt-cache keepalive (C7.G11), scratch (P2a), memory load (P3), telemetry emit (P1a) — and forward: drift (P3a), PEV (P3b), Ralph (P3b), entropy (P3c), verify-nudge (P3c).

**Acceptance:** zero behavioral change. Full unit suite green pre + post with identical pass/fail counts.

### P3a — Drift detectors (Tier 5.1)

**File targets:**
- `autocode/src/autocode/agent/drift.py` (~400 LOC)
- 3 detector classes: `SchemaDriftDetector`, `ContextStalenessDetector`, `ToolConsistencyDetector`
- Hook registration via dispatcher

**Quantitative success criteria (from `docs/plan/roadmaps/2026-04-30-tier-roadmap/06-INDEX-part2.md`):**
- Schema drift detector flags ≥ 90% of column renames within 1 turn
- Context staleness sensor warns when memory facts older than 7 days
- Latency budget: < 5 ms per detection

**Per-detector disable in `~/.autocode/config.yaml`:** `agent.drift.{schema,staleness,consistency}.enabled`.

**Telemetry:** `tool_drift_detected` events with `tool_name`, `drift_kind`, `severity`. CLI: `autocode telemetry drift --last 7d`.

### HFIX — AI verification harness fixes [CLOSED]

**Goal:** make harness verdicts explainable, replayable, and resistant to false PASS outcomes before reliability-loop work depends on them.

**Reference plan:** `docs/plan/ai-verification-harness-fixes-plan.md`.

**Work packages:**
- HFIX-1 structured trace contract: typed tool/turn events with schema tests.
- HFIX-2 per-turn and per-run summaries: diffable JSON artifacts that separate agent behavior, grader checks, and infrastructure status.
- HFIX-3 assertion-strength upgrades: `must_use_tools`, `require_non_empty_diff`, deterministic check execution guards, and no-op PASS prevention.
- HFIX-4 real-agent interaction canaries: `spawn_subagent` and `ask_user` coverage through the normal harness workflow.
- HFIX-5 semantic/tool-use canaries for feature-inventory coverage, especially search and multi-file behavior.
- HFIX-6 harness self-validation: meta-tests that prove bad scenarios fail for the right reason instead of passing through infrastructure gaps.

**Acceptance:** HFIX closed under the gateway-deferral policy via Claude Entry 1825. Deterministic substrate and benchmark tests are green; live `ask-user-scripted` and `multi-turn-regression` canaries remained gateway-bound `INFRA_FAIL` and are not code blockers.

### P3b — PEV + Ralph reliability loops (Tier 5.2 + 5.3)

**PEV (Plan-Execute-Verify):**
- `autocode/src/autocode/agent/pev.py` (~350 LOC)
- `Plan`, `PlanStep`, `StepResult` dataclasses
- Verifier system prompt
- Auto-detect: `todo_write` with > 3 items → wrap in PEV
- Rollback: honors C5.G4 contract (no auto-rollback; surface `/rollback`)

**Ralph Loop:**
- `autocode/src/autocode/session/intent_store.py` — `IntentStore` SQLite-backed (~150 LOC)
- `autocode/src/autocode/agent/ralph_loop.py` — `RalphRecoveryDetector` + `RalphLoop` (~250 LOC)
- Triggers: give-up phrase + zero tool calls; 3 consecutive zero-progress turns; context > 85% with zero tool calls in last 3 turns
- Don't fire on first turn; cap 3 fires per session
- `AUTOCODE_DISABLE_RALPH=true` env var

**Quantitative success criteria:**
- PEV catches ≥ 50% of plans that would have produced failing tests
- Ralph recovers ≥ 80% of sessions that hit context limits

**Telemetry:** `pev_step_failed`, `ralph_recovery_fired`.

### P3c — Entropy + verify tightening (Tier 7.2 + 7.3)

**File targets:**
- `autocode/src/autocode/agent/entropy.py` (~150 LOC) — `EntropyAuditor`
- Audit interval: every 10 turns; max 20 messages; cheap fast model
- Anti-entropy section in `STABLE_INSTRUCTIONS`
- Memory-fact runtime nudge in `agent/loop.py` (via Hook)

**Categories:** naming drift, decision reversal, stale reference, fact conflict.

**Severity routing:** high → system warning + recommend rollback; medium → log; low → log only.

**Telemetry:** `entropy_audit_completed` event with `severity_max`, `incident_count`.

### P3d — Eval suite expansion (Tier 8.2 + 8.3 + 8.4 + optional 8.5)

**File targets:**
- `evals/cases/<id>.yaml` — eval cases
- `evals/runner.py` (~300 LOC) — fixture setup, autocode session launch, telemetry collection, judge invocation
- `evals/judge.py` (~150 LOC) — LLM-as-judge with structured JSON output (judge model > agent model)
- `.github/workflows/evals.yml` — CI gate, `--baseline-tolerance 0.10`, `--max-budget-usd 5.00`, **stratified sample** (not all 200 cases)
- `evals/scripts/generate_evals_from_drift.py` — weekly drift-derived eval generation (consumes P3a events; ≥ 3 occurrences proposes case)
- (optional) `autocode telemetry public-report --output public-stats.json`

**Tier 8.3 — 5 regression-discipline rules:**
1. Every fixed bug becomes an eval case (PR template enforces)
2. Drift detector incidents become eval cases
3. Baseline updates require justification
4. Eval cases append-only (`archived: true` flag, never delete)
5. Eval execution reproducible (fix model + temperature 0.0 + seed + fixture commit hash)

**Quantitative success criteria:**
- Pre-merge eval gate runs in < 3 min
- Drift-derived eval generator proposes ≥ 1 case from 30 days of drift events

**Telemetry CI strictness (decision #5 finalized here):** soft gate (warn-only) for first 2 weeks of stability; promote to hard merge-blocking on baseline drift > 10%.

### P4 — Tier 2 Item/Turn/Thread (DEFERRED — out of scope)

OUT per User decision #2. If a concrete Tauri / Electron / web / IDE plugin / programmatic third-party consumer materializes within 6 months, raise a Concern entry directed to Claude + User; do NOT start P4 unilaterally.

**Hold-release triggers:** ≥ 1 of (concrete second client surface; `rtui/src/rpc/protocol.rs` > 60 ad-hoc structs (currently 44); two concurrent backend consumers).

**Out with P4:** Tier 2.2 (Unix socket / WebSocket transports), Tier 2.3 (`turn/steer` mid-flight input), Tier 4.2 (ephemeral fork), Tier 4.3 (sticky env per turn), Tier 6 Path B rewrite.

### P4a — TUI Path A refactor (DEFERRED — out of scope per Entry 1736)

**OUT of this pass per User direction "no TUI now, that is for later" (Entry 1736).**

Refactor scope and budgets retained below for the follow-up tranche; do NOT touch `rtui/` in this pass.

**Refactor scope (~−2900 LOC) — for follow-up tranche:**
- `rtui/src/render/view.rs` — replace 9 × 9 stage × detail-surface match arms with widget-per-mode pattern (~−2000 LOC)
- Cache `Lines<'static>` per `HistoryEntry` with `cached_lines: RefCell<Option<(u16, Vec<Line<'static>>)>>` (~−400 LOC of streaming buffer hacks)
- `rtui/src/state/reducer.rs` — collapse 40+ Event variants into one `RpcMsg(Value)` + sub-reducer where appropriate (~−500 LOC)

**SKIP (with P4):** 44 RPC structs → 3 primitives collapse.

**Performance budgets (refactor targets) — for follow-up tranche:**
- Cold start to first frame < 150 ms (from current ~250 ms)
- Resident memory at idle < 60 MB (from current ~85 MB)
- Frame time during streaming < 5 ms (from current ~8-12 ms)
- `cells_changed_per_streaming_delta` benchmark < 30
- Binary size < 1.8 MB (from current ~2.2 MB)
- Final LOC ~4600 (from current ~7500)

**Acceptance (when picked up later):**
- All Track 1 (runtime invariants) green
- All Track 4 (design-target ratchet) green
- All VHS PNG snapshots green (no rebaseline without User signoff per `feedback_vhs_rebaseline_user_gated.md`)
- All PTY smokes green (slash surfaces, real-gateway canary)

### P5 — Tier 4.1 KAIROS feature-flag track

**KAIROS ONLY** for this pass. Tier 4.2 (ephemeral fork) and 4.3 (sticky env) DEFERRED with P4.

**File targets:**
- `autocode/src/autocode/agent/proactive.py` (~400 LOC) — `ProactiveLoop` + `TickConfig`
- `<tick>` injection format with local time
- `SleepTool` in `agent/tools.py` — capped at 10x cache TTL
- 15-second blocking budget for tick-triggered tool calls
- Anti-narration system prompt section
- `autocode daemon --watch /path/to/repo` CLI subcommand
- Terminal-focus-awareness: pause ticks when user mid-typing

**Feature flag:** `AUTOCODE_FEATURE_KAIROS=false` default-off.

**Pre-shipping gate:** ≥ 4 weeks of P1a telemetry baseline + observability story.

**Telemetry:** `tick_count`, `sleep_call_ratio`, `anti_narration_violations`, `kairos_action_blast_radius`.

**Sequencing risk (from `docs/plan/roadmaps/2026-04-30-tier-roadmap/05-cross-cutting-concerns.md`):** mitigation = default off, `--dry-run` mode for first 2 weeks of opt-in, hard cap that KAIROS never calls `requires_approval=True` tools unless user is interactively present, persist a "blast radius log" queryable via `autocode kairos audit`.

---

## Cross-cutting concerns (apply to every phase)

### Standing per-phase requirements (each phase exit gate)

1. **Constraint #8** — `docs/features/backend_features.md` updated AND verification artifact stored at `autocode/docs/qa/test-results/<ts>-<slice-id>-<short-description>.md` BEFORE Review Request
2. **CHANGELOG.md entry** — user-visible changes per phase (NEW per audit gap C)
3. **`autocode/TESTING.md` updated** when test surface changes
4. **`docs/architecture.md` updated** when architecture changes
5. **`.gitignore` extended** to cover the phase's artifact paths if not already (Codex Entry 1703 finding #1 — generalize patterns so each phase doesn't re-litigate)
6. **`git diff --check` clean**
7. **Disable/rollback flag documented** per phase (audit gap G)
8. **Performance budgets benchmarked** in CI when applicable (audit gap E)
9. **Quantitative success criteria** from `docs/plan/roadmaps/2026-04-30-tier-roadmap/06-INDEX-part2.md` honored where applicable (audit gap D)

### Migration guides required

- **P3:** `docs/reference/memory-migration-v1.md` (SQLite `MemoryStore` → file-system; user rollback path documented)
- **P4 (deferred):** `docs/reference/rpc-schema-v2.md` (Codex app-server README format) — NOT for this pass

### Performance budgets table (consolidated)

| Operation | Budget | Phase |
|---|---|---|
| `emit()` telemetry call | < 5 µs | P1a |
| Telemetry summary aggregation `--last 7d` | < 500 ms | P1a |
| Tier 1 cache breakpoint round trip | n/a (provider-side) | P2 |
| Scratch offload write (5-50 KB) | < 1 ms | P2a |
| Memory index load (Layer 1) | < 50 ms | P3 |
| Topic file load (Layer 2) | < 200 ms per file | P3 |
| `grep_logs` over 30 days | < 500 ms | P3 |
| Compaction Path A (file read) | < 1 sec | P3 |
| Compaction Path B (LLM call) | < 30 sec | P3 |
| Drift detector | < 5 ms per detection | P3a |
| Eval pre-merge gate | < 3 min | P3d |
| TUI cold start to first frame | < 150 ms | P4a (DEFERRED) |
| TUI frame time during streaming | < 5 ms | P4a (DEFERRED) |
| TUI cells changed per streaming delta | < 30 | P4a (DEFERRED) |
| TUI binary size | < 1.8 MB | P4a (DEFERRED) |
| TUI resident memory at idle | < 60 MB | P4a (DEFERRED) |

### Disable / rollback env vars (consolidated)

| Phase | Env var | Effect |
|---|---|---|
| P1a | `AUTOCODE_TELEMETRY_DISABLED=true` | emit() no-op; zero overhead |
| P2 | `AUTOCODE_DISABLE_PROMPT_CACHE=true` | Provider falls back to non-cached |
| P2a | `AUTOCODE_DISABLE_SCRATCH=true` | Inlines all tool outputs (current behavior) |
| P3 | `AUTOCODE_USE_LEGACY_MEMORY=true` | Reads `memories_archive_<date>` SQLite table |
| P3b | `AUTOCODE_DISABLE_RALPH=true` | Ralph never fires; PEV is opt-in via `/plan` |
| P5 | `AUTOCODE_FEATURE_KAIROS=true` | Default-off feature flag for KAIROS |

### Disaster recovery (audit gap H — listed in cross-cutting, not in any phase)

`autocode session export <session_id>` writes complete session to JSONL; `autocode session import <file>` reads it back. Use to:
- Snapshot before risky migrations
- Move sessions between machines
- Debug specific sessions in isolation

**Status:** Listed in `docs/plan/roadmaps/2026-04-30-tier-roadmap/05-cross-cutting-concerns.md` §"Disaster recovery"; **not currently in any phase.** Add to P3d or post-pass polish backlog (User call).

---

## Out of scope for this pass (comprehensive)

### Hard out-of-scope (won't ship in this pass)

- **Tier 2 entire** — Item/Turn/Thread (P4), Unix socket / WebSocket transports (Tier 2.2), `turn/steer` mid-flight input (Tier 2.3) — all per User decision #2
- **Tier 4.2** ephemeral fork — depends on Tier 2.1
- **Tier 4.3** sticky env per turn — depends on Tier 2.1
- **Tier 6 Path B** rewrite — OUT per User decision #4
- **Disaster recovery** (`session export`/`import`) — defer to polish backlog OR P3d closure (User call)

### Deliberately omitted from the entire roadmap

From `docs/plan/roadmaps/2026-04-30-tier-roadmap/00-INDEX.md`, `docs/plan/roadmaps/2026-04-30-tier-roadmap/04-tier4-future-tracks.md`, `docs/plan/roadmaps/2026-04-30-tier-roadmap/06-INDEX-part2.md`, and `docs/plan/roadmaps/2026-04-30-tier-roadmap/05-cross-cutting-concerns.md`:

- **Voice mode** — no Realtime API budget
- **Multi-agent Coordinator** — scope creep; only worth doing if a concrete second specialized agent is needed
- **MCP server hosting** — AutoCode is already a consumer of MCP; becoming a host adds surface area without clear benefit
- **Web UI** — covered by Tier 2 protocol (deferred); a thin Vercel/Tauri client would be ~3 days post-Tier-2
- **Replay/debugger** — useful but expensive to build well; defer until evals (P3d) reveal it's needed
- **Buddy/Tamagotchi** — pure entertainment
- **Anti-distillation** — irrelevant for non-distilled product
- **Undercover mode** — Anthropic-employee-specific
- **Cron tools / GitHub webhook subscriptions** — depend on hosted infrastructure AutoCode doesn't have
- **Auto Memory** with LLM-decided saving — defer until P3 baseline proves stable
- **Auto Dream advanced features** (timestamp normalization, contradiction resolution) — `consolidation.py` has structure; flesh out incrementally
- **Multi-agent broker pattern** — not needed until concurrent agents
- **Vector-based semantic retrieval** — research shows filesystem-based retrieval beats vector RAG below 100+ documents
- **5-tier compaction parity** — current 3-tier covers ~90% of value; marginal Claude Code tiers addressable later

---

## Open user-decisions still on the table

All 6 from prior round are now LOCKED. Remaining decisions surface only if:

- A second client surface materializes → reopen #2 + #4
- Baseline drift in P3d > 10% → reopen #5 (telemetry CI strictness)
- Hook refactor reveals deeper coupling → may extend beyond ~2-3 days; reopen #6 if timeline doubles

---

## Pass exit gate

After all phases ship:

- Full unit suite green (target: ~2400+ tests; +240 vs C7.GATE baseline `2159`)
- Benchmark harness green
- All PTY smokes green (LSP × 8, auto-verify, slash surfaces, real-gateway canary)
- All Track 1 + Track 4 + VHS green
- Eval suite green (P3d baselines)
- `autocode telemetry summary --last 7d` produces meaningful data
- `git diff --check` clean
- All P-phase verification artifacts present
- Top-level state docs synced: `current_directives.md`, `EXECUTION_CHECKLIST.md`, `PLAN.md`, `docs/features/backend_features.md`, this plan, `next_remaining_todo.md`
- Comms log archived; user runs the pass-closure stable commit
- Optional: `autocode telemetry public-report` snapshot stored

---

## Provenance

| Decision | Source |
|---|---|
| Pass scope (locked decisions 1-6) | User direction 2026-04-30 |
| Sensors-first doctrine | `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` §"Why this is last but not optional" |
| TUI Path A default; Path B gated on Tier 2 | `docs/plan/roadmaps/2026-04-30-tier-roadmap/08-tier6-minimal-tui.md` §"Counterargument: don't rewrite, refactor" |
| Hook refactor between P3 and P3a | Audit gap; preventive |
| Mitchell Hashimoto rule (every mistake → eval) | `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` §"Tier 8.3 — Regression discipline" |
| Memory before App Server | `docs/plan/roadmaps/2026-04-30-tier-roadmap/05-cross-cutting-concerns.md` §"Things I'd do differently" |
| KAIROS gated on 4-week telemetry baseline | `docs/plan/roadmaps/2026-04-30-tier-roadmap/04-tier4-future-tracks.md` |
| Audit gap reconciliation (B/C/D/E/F/G/H valid; A narrowed; I dropped) | Claude audit 2026-04-30 + Codex correction in Entry 1705. Gap I (stratified eval sampling) was invalid — already at `post-c7-pass-atomic-checklist.md:485`. Gap A is a docs-clarity issue: Tier 2.2/2.3 deferral IS in `post-c7-stable-commit-roadmap.md:513`; what was missing was atomic checklist OUT-OF-SCOPE explicit listing (now in `next_remaining_todo.md`). |
| Existing post-c7-* docs | `docs/plan/post-c7-stable-commit-roadmap.md`, `post-c7-pass-atomic-checklist.md`, `post-c7-builder-handoff.md`, `post-c7-telemetry-spec.md` (this file consolidates and supersedes for active use; old docs preserved for reference) |
| Tranche-4 closure | `AGENTS_CONVERSATION.MD` archived Entry 1664-1697 → `docs/communication/old/2026-04-30-*` files |

---

## Next concrete actions

1. **Builder (OpenCode primary; Codex while user-directed):** execute HFIX in `next_remaining_todo.md` and `docs/plan/ai-verification-harness-fixes-plan.md`, starting with the structured trace contract and artifact schemas.
2. **Reviewer (Claude default):** review HFIX for harness-quality regressions: false PASS risk, missing tool-call evidence, verdict explainability, and artifact usefulness.
3. **User:** no new decision is needed unless you want to reprioritize P3b ahead of HFIX.
