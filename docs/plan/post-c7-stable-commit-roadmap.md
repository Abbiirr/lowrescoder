# Post-C7.GATE Stable-Commit Roadmap

> **Status:** LOCKED FOR POST-COMMIT — Tranche 4 is agent-closed and Claude-approved in `AGENTS_CONVERSATION.MD` Entry 1694.
> **Activation:** no phase starts until the user lands the stable commit and signals the six user-decision defaults or overrides.
> **Authoritative source-of-truth:** this document is the master post-commit reference. Per-tier deep specs live in the root-level roadmap files (`00-INDEX.md` through `05-cross-cutting-concerns.md`).
> **Builder handoff:** `docs/plan/post-c7-builder-handoff.md`.

---

## Why this document exists

After C7.GATE closes and the user lands the stable commit, AutoCode enters a new program: a 4-tier roadmap drafted 2026-04-30 covering prompt cache, app-server protocol, file-system memory, and proactive/future tracks. The roadmap files at repo root contain ~2000 lines of tier specs. This document distills that into the **sequenced execution order** the team agreed on, with file targets, contracts, acceptance gates, and dependencies — enough to start work without re-reading the source roadmap files for routine reference.

When a phase activates, spawn a per-phase atomic checklist following the `docs/plan/backend-robustness-tranche-4-checklist.md` pattern. Until then this document is the plan.

---

## Source documents (deep dive — read when implementing)

| File | Topic |
|---|---|
| `00-INDEX.md` | Roadmap overview + execution order + dependency graph (covers Tiers 1-4) |
| `01-tier1-prompt-cache.md` | Tier 1 prompt cache breakpoint injection, stable/dynamic boundary, reasoning-token capture |
| `02-tier2-app-server-protocol.md` | Tier 2 Item/Turn/Thread refactor, transports, `turn/steer` |
| `03-tier3-memory-architecture.md` | Tier 3 file-system 3-layer memory, Session Notes, verify-before-use |
| `04-tier4-future-tracks.md` | Tier 4 KAIROS, ephemeral forks, sticky envs, headless `--json` |
| `05-cross-cutting-concerns.md` | Testing strategy, telemetry, migration safety, rollback, performance budgets, sequencing risks |
| `07-tier5-harness-reliability.md` | Tier 5 drift detectors + PEV loop + Ralph Loop (added 2026-04-30) |
| `08-tier6-minimal-tui.md` | Tier 6 minimal lightweight TUI rewrite (or refactor) (added 2026-04-30) |
| `09-tier7-context-engineering.md` | Tier 7 filesystem-as-context scratch store + entropy management + verify-tightening (added 2026-04-30) |
| `10-tier8-observability-evals.md` | Tier 8 telemetry plumbing + eval suite + regression discipline (added 2026-04-30) |

---

## Sequencing decision (Entry 1664 + 1665, revised 2026-04-30 with Tiers 5-8)

The roadmap's own "best-bang-for-buck" order is `1.1 → 1.2 → 1.3 → 3.3 → 2.1 → 2.3 → 2.2 → 3.1 → 3.2 → 4.4 → 4.2 → 4.3 → 4.1`. We deviate on three axes:

1. **AI verification harness narrow substrate goes FIRST.** It de-risks every downstream tier. Claude proposed it in Entry 1662 as Phase 3 candidate; Codex pushed it to Phase 1 in Entry 1663; Claude ratified in Entry 1664. Substrate-only scope, not the full 7-milestone plan in `docs/plan/ai-verification-harness-plan.md`.
2. **Tier 3 (memory) comes BEFORE Tier 2 (app-server protocol).** The roadmap itself acknowledges this in `05-cross-cutting-concerns.md` §"Things I'd do differently": "Memory before App Server. Tier 3 doesn't depend on Tier 2 and the 3-layer memory delivers immediately visible quality." Given no concrete 2nd-client surface signal from the user, the Tier 2.1 ROI is purely speculative.
3. **Sensors-first doctrine for Tiers 5-8.** Tier 8 explicitly argues "If the team wants to ship one thing from Tiers 5-8, ship Tier 8 first" because evals/telemetry are how you know if other tiers actually help. We honor this by interleaving small sensor phases (P1a telemetry, P3a drift detectors) BEFORE the big optimizations (P3 memory, P5 file-system). Each small sensor phase fits between two large existing phases without disrupting them.

### Final phase order (P1 → P5 unchanged; P-letter interleaves added)

```
P1   AI verification harness narrow substrate          (existing — first sensor)
P1a  NEW Telemetry plumbing (Tier 8.1)                 (sensors-first; foundational)
P2   Tier 1 prompt cache + verify-before-use           (existing — biggest cost win)
P2a  NEW Scratch store (Tier 7.1)                      (small, independent, big context relief)
P3   Tier 3 file-system memory                         (existing — durable user value)
P3a  NEW Drift detectors (Tier 5.1)                    (depends on P3 + P1a)
P3b  NEW PEV + Ralph reliability loops (Tier 5.2/5.3)  (independent + intent store)
P3c  NEW Entropy + verify tightening (Tier 7.2/7.3)    (small, prompt-only changes)
P3d  NEW Eval suite expansion (Tier 8.2-8.5)           (natural growth from P1)
P4   Tier 2 Item/Turn/Thread                           (existing — DEFERRED conditional)
P4a  NEW TUI refactor or rewrite (Tier 6)              (refactor independent; rewrite gated on P4)
P5   Tier 4 feature-flag tracks                        (existing — KAIROS / fork / sticky env)
```

**Phase letter convention:** existing phase numbers (P1-P5) preserved to keep external references stable; new phases interleave with letter suffixes (P1a, P2a, P3a-d, P4a) showing time-ordering. Letter suffixes are ordered alphabetically within their parent number.

**Total estimated cost:** ~14-18 weeks of post-commit work, NET −2000 to −3000 LOC (Tier 6 deletion outweighs new tier additions).

---

## P1 — AI Verification Harness Narrow Substrate

**Cost:** ~1-2 weeks, ~500 LOC.
**Why first:** every downstream phase needs deterministic verification across simulated session restarts. Without this, Phase 2 cache-hit-ratio claims and Phase 3 memory-survival claims are unfalsifiable.

### Scope (substrate only)

| Component | Target file | Approx LOC |
|---|---|---|
| Scenario schema (YAML or JSON) | `benchmarks/ai_verification/schema.py` (or co-locate with existing `benchmarks/ai_verification/`) | ~50 |
| Sandbox repo builder (clone fixture → tmp dir → seed git history) | `benchmarks/ai_verification/sandbox.py` | ~150 |
| Deterministic agent runner (spawn `autocode` against sandbox + capture NDJSON output via C6.G5) | `benchmarks/ai_verification/runner.py` | ~200 |
| Hand-graded evaluator stub (3-5 hand-written scenarios, deterministic exit-code grading) | `benchmarks/ai_verification/grader.py` + `benchmarks/ai_verification/scenarios/*.yaml` | ~100 |

### Hard dependencies

- C6.G5 NDJSON output ships in Tranche 4 (provides the captureable event stream the runner consumes)
- Stable commit landed (no in-flight Tranche-4 changes during substrate development)

### Out of scope (defer to full harness plan in `docs/plan/ai-verification-harness-plan.md`)

- Generated-scenario corpus
- ML-graded scoring
- Multi-language scenario library
- The full 7-milestone plan
- Cloud sandbox parallelism

### Acceptance

- 3-5 hand-written scenarios run deterministically against `autocode exec --json`
- Each scenario produces a verification artifact at `autocode/docs/qa/test-results/<ts>-ai-verification-<scenario>.md`
- Same artifact format as existing QA results — pluggable into existing tooling
- Runner exits non-zero if any scenario's NDJSON stream fails grader expectations
- Substrate tests in `benchmarks/tests/test_ai_verification_substrate.py` cover schema validation, sandbox isolation, runner determinism

---

## P1a — Telemetry Plumbing (Tier 8.1) [NEW]

**Cost:** ~3 days, ~350 LOC.
**Why now:** sensors-first doctrine. Every subsequent phase emits events; without P1a in place first, you can't measure whether the optimizations actually help. This is the smallest phase in the post-commit horizon and unlocks the largest downstream signal.

### Scope

| Component | Target file | Approx LOC |
|---|---|---|
| Append-only JSONL event store with daily file rotation + background writer thread | `autocode/src/autocode/telemetry/store.py` (NEW) | ~200 |
| Aggregator: read jsonl, group, summarize | `autocode/src/autocode/telemetry/aggregator.py` (NEW) | ~150 |
| `autocode telemetry summary/events/session/export/purge` CLI subcommands | `autocode/src/autocode/cli.py` (extend) | ~100 |
| Emit hooks at key lifecycle points | `autocode/src/autocode/agent/loop.py` + `backend/server.py` (extend) | ~50 scattered |

### Event-kind catalog (from Tier 8.1)

Session lifecycle (`session_start`, `thread_start`, `turn_start`, etc.); tool execution (`tool_call_completed`, `tool_output_offloaded`, `tool_drift_detected`); cost & cache (`llm_call_completed`, `cache_breakpoint_applied`, `compaction_event`); approval & permissions; reliability events (`ralph_recovery_fired`, `entropy_audit_completed`, `pev_step_failed`); user actions (`slash_command_invoked`, `feature_flag_toggled`).

### Hard constraints

- **Local-only.** Never sent off-machine. CI test asserts no network call from telemetry path. README documents this prominently.
- **`AUTOCODE_TELEMETRY_DISABLED=true` opts out** — instant kill switch.
- **Bounded queue with back-pressure** — `queue.Full` drops events to stderr rather than blocking the agent loop.
- **`~/.autocode/telemetry/` is in `.gitignore`** in every project that ships with one.
- **`autocode telemetry purge` deletes everything** — privacy escape hatch.

### Acceptance

- Single emit call writes JSONL line within 5ms (background writer)
- `autocode telemetry summary --last 7d` produces the table from Tier 8.1 §"`autocode telemetry summary` output"
- Daily file rotation under `~/.autocode/telemetry/events-YYYY-MM-DD.jsonl`
- Disable flag round-trips correctly (no events emitted, no errors)
- P1 harness scenario: emit 100 events, summary correctly aggregates them

### Cross-tier integration (events emitted by later phases)

| Phase | Events |
|---|---|
| P2 | `cache_breakpoint_applied`, `llm_call_completed` (with cache_read_tokens) |
| P2a | `tool_output_offloaded` |
| P3 | `compaction_event` (path A vs B) |
| P3a | `tool_drift_detected` |
| P3b | `ralph_recovery_fired`, `pev_step_failed` |
| P3c | `entropy_audit_completed` |
| P3d | (consumes events; doesn't emit) |

---

## P2 — Tier 1 Prompt Cache + Verify-Before-Use (atomic)

**Cost:** ~1 week, ~270 LOC.
**Why second:** highest-leverage immediate cost win (40-80% reduction per the roadmap). P1 harness validates the cache-hit ratio empirically before claiming the win.
**Atomic constraint:** PR includes 1.1 + 1.2 together. Shipping 1.1 alone busts cache every turn (current date / git status / cwd in stable region) → 25% cache-write premium with zero read benefit.

### Tier 1.1 — cache breakpoint injection

| Action | Target file | LOC |
|---|---|---|
| Inject `cache_control: ephemeral 1h` on stable prefix in OpenRouter provider | `autocode/src/autocode/layer4/llm.py` (line 1024+, `OpenRouterProvider`) | ~120 |
| Inject `anthropic-beta: prompt-caching-2024-07-31` header for OpenRouter→Anthropic | same file | (in same delta) |
| Capture `cache_creation_input_tokens` + `cache_read_input_tokens` from response | same file | (in same delta) |
| OllamaProvider no-op guard | `autocode/src/autocode/layer4/llm.py` (line 639+) | minimal |

**Detection rules** per `01-tier1-prompt-cache.md` §"Detection rules":
- Anthropic direct → all current models support explicit cache_control
- OpenRouter → only `anthropic/*` and `google/gemini-*` (passes cache_control through)
- OpenAI → automatic prefix caching, no markup needed

### Tier 1.2 — stable/dynamic prompt boundary

| Action | Target file | LOC |
|---|---|---|
| Refactor `SYSTEM_PROMPT` into `STABLE_INSTRUCTIONS` + `build_stable_prefix` + `build_dynamic_tail` with `CACHE_BOUNDARY_MARKER` sentinel | `autocode/src/autocode/agent/prompts.py` (currently 193 LOC, grows to ~270) | refactor + ~80 |
| Deterministic tool-def serialization (`sort_keys=True, separators=(",",":")`, sorted by name) | same file | ~30 |
| Wire RulesLoader output + skill catalog into stable prefix; cwd / git status / current date / todos into dynamic tail | same file + caller in `agent/loop.py` or `agent/context.py` | ~40 |

**Cache boundary marker:** literal sentinel string `# === DANGEROUS_uncachedSystemPromptSection_BELOW ===`. Provider layer in 1.1 splits the system message at this marker.

### Tier 1.3 — reasoning-token capture + `/cost` cache breakdown

| Action | Target file | LOC |
|---|---|---|
| Extend `TokenUsage` dataclass with `cache_creation_tokens`, `reasoning_tokens`, `billable_input_cost_factor` property | `autocode/src/autocode/agent/token_tracker.py` | +40 |
| `record_cache(provider, cache_read_tokens, cache_write_tokens)` aggregation | same file | (in same delta) |
| `/cost` slash command shows cache reads / writes / reasoning / effective multiplier | `autocode/src/autocode/tui/commands.py` (already wired) | small |
| SQLite persistence for resumed-thread token replay | session schema migration + `TokenTracker` hydrate | ~30 |
| Status bar cache-hit indicator `⚡N% cached` | `rtui/src/render/view.rs` | small |

### Tier 3.3 — verify-before-use prompt section (folded in)

| Action | Target file | LOC |
|---|---|---|
| Append "memory is a HINT, not truth; verify with `read_file` / `list_files` before acting" section to `STABLE_INSTRUCTIONS` | `autocode/src/autocode/agent/prompts.py` (touched anyway by 1.2) | +50 |

**Why folded:** `prompts.py` is being refactored in 1.2 anyway. Touch once, not twice.

### Acceptance

- `cache_creation_input_tokens > 0` on first call to a fresh prefix
- `cache_read_input_tokens ≥ 1024` on second call within 5 min of identical 2k-token system prompt
- `tests/unit/test_prompt_cache_boundary.py` proves no time/path/git/todo strings leak above `CACHE_BOUNDARY_MARKER`
- Tool-def serialization is byte-identical across calls (sorted keys, no whitespace variability)
- `/cost` shows cache breakdown lines + effective multiplier < 1.0 after warmup
- LLM-eval test (best-effort): model re-reads file before relying on stale memory
- P1 harness scenario: cache-hit ratio > 0.5 measured deterministically across simulated 5-min session restart

### Hard constraints (per `01-tier1-prompt-cache.md` §"Risk & mitigation")

- Do NOT manually override `provider.order` on OpenRouter — that disables sticky routing
- Cache_control breakpoints have a hard limit of 4 per request — reserve them: system / tool defs / RulesLoader / optional CLAUDE.md
- TTL expiry is silent — first call after >5 min (or >1h with extended TTL) becomes a cache write again
- Workspace isolation (Anthropic, since Feb 5 2026): caches are per-workspace, not per-org

---

## P2a — Scratch Store (Tier 7.1) [NEW]

**Cost:** ~3-4 days, ~250 LOC.
**Why now:** smallest, most-independent context-relief win. When a tool produces > 5 KB output (a 50-file `list_files`, a 200-line `git_log`, a `web_fetch`), instead of middle-truncating it, write the full output to disk and keep only a path + summary in context. Drops in cleanly between cache (P2) and memory (P3) — memory then has more headroom because tool exhaust no longer crowds the cache.

### Scope

| Component | Target file | Approx LOC |
|---|---|---|
| `ScratchStore` class — per-turn dirs + manifest + threshold rule | `autocode/src/autocode/agent/scratch.py` (NEW) | ~200 |
| Wrap large tool outputs at execute-call boundary | `autocode/src/autocode/agent/loop.py` (extend) | ~50 |
| Adjust truncation rules in compaction path | `autocode/src/autocode/agent/context.py` | ~30 |

### Threshold rules (from Tier 7.1)

```python
SCRATCH_THRESHOLD_BYTES = 5_000        # ~1250 tokens
SCRATCH_NEVER_FOR = {"todo_read", "ask_user", "memory_index_show"}  # always inline
SCRATCH_ALWAYS_FOR = {"web_fetch", "git_log"}  # always offload
```

### Layout

```
.autocode/scratch/<thread-id>/<turn-id>/
├── manifest.json
├── 001-list_files.md
├── 002-git_log.md
└── 003-web_fetch.md
```

### Behavior change for the agent

Agent organically learns to use narrower queries because broad ones produce stub-only summaries. This is harness-driven behavior change, not prompt-driven. No prompt edits required.

### Acceptance

- Output < 5 KB inlined unchanged
- Output ≥ 5 KB or in `SCRATCH_ALWAYS_FOR` writes to disk, returns context stub with preview + summary + path
- `manifest.json` records each offload with size + tool + summary
- Cleanup keeps last N=10 turn dirs, deletes older
- `tool_output_offloaded` telemetry event emitted (consumes P1a)
- P1 harness scenario: simulated 100-file `list_files` produces stub, scratch file exists, `read_file` on stub path returns full content

### Cross-tier integration

- **Compaction** (existing in `context.py`): no longer needs to re-summarize old tool results — they're on disk and can be re-read or grep'd if relevant. Reduces compaction LLM cost.
- **Cross-turn debugging**: a 100-turn session that produced a weird outcome can be debugged by reading the scratch dir chronologically — every tool result is intact.
- **Regression testing** (P3d): capture scratch dirs from production runs, replay them to verify the agent makes the same decisions.

---

## P3 — Tier 3 File-System Memory

**Cost:** ~3 weeks, ~1100 LOC.
**Why third:** highest user-perceived value (memory survives across restarts). P1 harness validates `MEMORY.md` survival; P2 cache lets memory file reads stay cheap.

### Tier 3.1 — file-system 3-layer memory

| Action | Target file | LOC |
|---|---|---|
| Create `MemoryFS` class — 3-layer index/topic/log storage at `~/.autocode/projects/<git-root-sha256-prefix>/` | `autocode/src/autocode/session/memory_fs.py` | ~600 (NEW) |
| New tools: `memory_read_topic`, `memory_write_topic`, `memory_grep_logs`, `memory_index_show` | `autocode/src/autocode/agent/tools.py` | ~120 |
| Auto-load `MEMORY.md` index at session start | `autocode/src/autocode/agent/loop.py` or `backend/server.py` | ~40 |
| One-shot SQLite `MemoryStore` → topic-files migration script | `scripts/migrate_memory_to_fs.py` | ~80 |
| Deprecate (don't drop) `agent/memory.py` — leave for one minor version | rename + re-export | minimal |
| Re-target `consolidation.py` (autoDream) writes from SQLite to topic files | `autocode/src/autocode/session/consolidation.py` | ~120 delta |

**Hard rules** from `03-tier3-memory-architecture.md`:
- `MEMORY.md` ≤ 200 lines, ~150 chars per pointer line, pointers only (no content)
- Topic files: soft limit 1000 lines, then split into `<topic>-<sub>.md`
- Daily logs: append-only (`logs/YYYY/MM/YYYY-MM-DD.md`), never auto-loaded
- Canonical git-root hashing — same project across worktrees gets same memory dir

### Tier 3.2 — Session Notes living document

| Action | Target file | LOC |
|---|---|---|
| Create `SessionNotes` class — incremental update at 10k token activation, every 5k after, gated by ≥3 tool calls | `autocode/src/autocode/session/session_notes.py` | ~250 (NEW) |
| Compaction Path A integration — use Session Notes as summary instead of fresh API call | `autocode/src/autocode/agent/context.py` | +80 delta |
| Telemetry: track Path A vs Path B usage, target ≥80% Path A after activation | `autocode/src/autocode/agent/loop.py` metrics | small |

### Acceptance

- `~/.autocode/projects/<hash>/MEMORY.md` exists and ≤ 200 lines after 50 sessions
- Topic files present: `architecture.md`, `debugging.md`, `decisions.md` populated by autoDream
- Daily logs append-only (filesystem ACL or convention via tool refusal)
- Compaction Path A chosen ≥ 80% of compaction events once 10k tokens consumed
- P1 harness scenario: `MEMORY.md` survives simulated session restart with content intact
- Migration: `memory_list` legacy tool either re-implemented against `MemoryFS` or removed with deprecation cycle (cross-cutting §"Risk: agent still references old SQLite")

---

## P3a — Drift Detectors (Tier 5.1) [NEW]

**Cost:** ~2 weeks, ~400 LOC.
**Why now:** P3 ships file-system memory; P3a adds the sensors that watch for memory becoming stale + tool outputs changing shape + same-turn tool calls returning different results. Per Tier 5: 65% of agent failures are harness defects (drift, schema mismatch, state degradation). Without sensors, you ship blind.

### Scope

| Component | Target file | Approx LOC |
|---|---|---|
| `SchemaDriftDetector` — hash structural shape of tool outputs, alert on change | `autocode/src/autocode/agent/drift.py` (NEW) | ~150 |
| `ContextStalenessDetector` — alert when topic-file age > threshold | (same file) | ~80 |
| `ToolConsistencyDetector` — alert when deterministic tool returns different results within one turn | (same file) | ~70 |
| Sensor invocation hooks at PostToolUse | `autocode/src/autocode/agent/loop.py` (extend) | ~50 |
| Drift warning injection into next-turn context | (same loop.py) | ~30 |
| Tests | `autocode/tests/unit/test_drift.py` (NEW) | covered by phase |

### Three detector classes (from Tier 5.1)

1. **Schema drift** — sensitivity = low/medium/high; tracks per-(tool, args_hash) shape fingerprint; alerts on type changes (medium) or new keys (high)
2. **Context staleness** — topic-file age threshold (default 7 days); fires when agent acts on stale memory
3. **Tool consistency** — `read_file`, `list_files`, `git_status`, `list_symbols` should be deterministic within one turn; mismatch suggests external mutation

### Hard constraints

- **Latency budget per detection:** < 5ms (detectors run after every tool call)
- **Alert injection format:** drift warning becomes a `system`-role message with `[Drift detected — <kind>, severity <level>]` prefix; agent must acknowledge in next response
- **Telemetry emission required:** every drift detection writes `tool_drift_detected` event (consumes P1a)
- **Sensitivity is configurable** per-detector via `~/.autocode/config.yaml` `agent.drift.{schema,staleness,consistency}.sensitivity`

### Acceptance

- Schema drift fires on column rename in tool output
- Context staleness fires on topic file > 7 days old when referenced
- Tool consistency fires when `read_file` returns different content twice in one turn
- `autocode telemetry drift --last 7d` aggregates incidents (uses P1a substrate)
- P1 harness scenario: simulated drift triggers exactly the right detector, agent acknowledges in next turn

---

## P3b — PEV + Ralph Reliability Loops (Tier 5.2 + 5.3) [NEW]

**Cost:** ~2 weeks, ~600 LOC.
**Why now:** with sensors in place (P3a), the next layer is recovery. PEV catches errors at step boundaries instead of letting them compound; Ralph recovers from context-anxiety stall points (give-up phrases, stagnation, context approaching saturation).

### Scope

| Component | Target file | Approx LOC |
|---|---|---|
| `PEVRunner` — Plan-Execute-Verify pipeline with model role separation | `autocode/src/autocode/agent/pev.py` (NEW) | ~350 |
| `IntentStore` — SQLite store of crystallized user intent per session | `autocode/src/autocode/session/intent_store.py` (NEW) | ~150 |
| `RalphRecoveryDetector` + `RalphLoop` — detect give-up signals, compact + re-inject intent | `autocode/src/autocode/agent/ralph_loop.py` (NEW) | ~250 |
| Verifier system prompt | `autocode/src/autocode/agent/prompts.py` (extend) | small |
| Wiring into agent loop | `autocode/src/autocode/agent/loop.py` (extend) | ~60 |

### PEV decision rule (when to use vs straight-line agent loop)

| Use straight-line | Use PEV |
|---|---|
| Single-tool tasks, conversational | Multi-step refactors, > 3 todos |
| User said "just do it" | User invoked `/plan` first |
| Trivial fixes | Touches auth/security/data |
| < 3 expected tool calls | > 5 expected tool calls |

**Auto-detect:** if straight-line agent calls `todo_write` with > 3 items, automatically wrap subsequent execution in PEV.

### Ralph triggers

- Phrase detection: agent produces "I'll stop here", "this is too complex", "unable to continue", etc. without a tool call
- Stagnation: 3 consecutive zero-progress turns
- Context approaching saturation (>85%) with zero tool calls in last 3 turns

### Hard constraints

- **Don't fire Ralph on first turn** — agent hasn't "given up" if it's the first response
- **Cap at 3 Ralph fires per session** — beyond that surface to user
- **`AUTOCODE_DISABLE_RALPH=true`** for users who prefer loud failure
- **PEV verifier model can be different from executor model** — Reasoning Sandwich pattern (expensive cognition at boundaries, cheap execution in middle)

### Acceptance

- PEV plan with 4 steps + verifier predicates runs end-to-end
- Step failure with `next_action: "retry_step"` retries once with verifier feedback
- Ralph fires on simulated give-up phrase + zero tool calls; recovery message starts with `[Ralph recovery`
- `ralph_recoveries` and `pev_step_failed` telemetry events emitted
- IntentStore persists intent across simulated session restart (uses P3 memory infra)

### Cost analysis

PEV adds plan creation + per-step verification calls. Net cost is often the *same* as straight-line because plan/verify use cheaper models or shorter context. The win is reliability, not cost.

---

## P3c — Entropy + Verify Tightening (Tier 7.2 + 7.3) [NEW]

**Cost:** ~1 week, ~200 LOC.
**Why now:** small but valuable additions to context engineering. Entropy audits catch internal-consistency drift; verify-tightening makes the verify-before-use prompt section (P2 Tier 3.3) operational via runtime nudges.

### Scope

| Component | Target file | Approx LOC |
|---|---|---|
| `EntropyAuditor` — periodic LLM-judged consistency check (every 10 turns, last 20 messages) | `autocode/src/autocode/agent/entropy.py` (NEW) | ~150 |
| Anti-entropy section in `STABLE_INSTRUCTIONS` | `autocode/src/autocode/agent/prompts.py` (extend) | ~30 |
| Memory-fact runtime nudge — soft warning when agent acts on memory-derived fact without re-reading | `autocode/src/autocode/agent/loop.py` (extend) | ~20 |

### Entropy audit categories (from Tier 7.2)

- **Naming drift** — variable names that change spelling between mentions (`state_token` vs `stateToken`)
- **Decision reversal** — turn 4 says "use JWT", turn 11 says "use cookies" without acknowledgment
- **Stale reference** — file path mentioned that doesn't exist
- **Fact conflict** — turn 2 "test passes", turn 9 same test failing without explanation

### Anti-entropy prompt (from Tier 7.2)

```
## Internal consistency

If you find your own statements contradicting earlier statements in this
conversation, acknowledge the contradiction explicitly:
- "I earlier said X but now I'm seeing Y. Let me reconcile."
- "I'm changing my recommendation from X to Y because [evidence]."

If a file path or variable name you mentioned earlier doesn't appear when
you read the file, do NOT silently substitute. Stop and ask the user, or
verify with another tool.

If a decision was made earlier in this conversation, do not reverse it
without flagging the reversal.
```

### Acceptance

- Naming-drift test passes (auditor flags `state_token` vs `stateToken` mix)
- Audit runs every 10 turns; cheaper model than agent
- High-severity entropy fires `entropy_audit_completed` event with `severity: high`
- Memory-fact nudge appears when agent cites file path from memory without `read_file`

---

## P3d — Eval Suite Expansion (Tier 8.2-8.5) [NEW]

**Cost:** ~2 weeks, ~450 LOC.
**Why now:** P1 shipped a narrow substrate (3-5 hand-graded scenarios). P3d expands it into a production eval suite with LLM-as-judge for non-deterministic outputs, CI gating with baseline tolerance, and drift-derived eval auto-generation. This closes the Mitchell Hashimoto loop: bug → eval → fix → eval-passes → bug-never-returns.

### Scope

| Component | Target file | Approx LOC |
|---|---|---|
| Eval case YAML schema (must_have / must_not_have / judge_criteria / config / baseline) | `evals/cases/<id>.yaml` (NEW dir) | per-case |
| Eval execution engine — fixture setup, autocode session launch, telemetry collection, judge invocation | `evals/runner.py` (NEW) | ~300 |
| LLM judge — structured-output scoring with stronger model than agent | `evals/judge.py` (NEW) | ~150 |
| CI workflow gate — score within 10% of baseline | `.github/workflows/evals.yml` (NEW) | small |
| Drift-derived eval generator — weekly script proposing eval cases from production drift events (consumes P3a) | `scripts/generate_evals_from_drift.py` (NEW) | ~100 |
| Optional: public-safe stats export | `autocode telemetry public-report` | small |

### Eval case anatomy (from Tier 8.2)

YAML defines: `id` / `name` / `provenance` (bug_id, recorded_at) / `setup` (fixture_repo, initial_files) / `input` (user_message) / `expected_outcomes` (must_have, must_not_have, judge_criteria) / `config` (model, max_turns, timeout) / `baseline` (correctness_score, minimality_score, cost_usd_p50).

### Regression discipline (Tier 8.3 — five rules)

1. **Every fixed bug becomes an eval case.** PR template requires `evals/cases/<id>.yaml` for every bug fix.
2. **Drift detector incidents become eval cases.** If `autocode telemetry summary` shows a recurring drift kind, write an eval that exercises it.
3. **Baseline updates require justification.** Score changes are reviewed code changes.
4. **Eval cases never delete.** Archive (`archived: true`) but never delete.
5. **Eval execution must be reproducible.** Fix model + temperature + seed + fixture commit hash.

### LLM judge

Judge is a different (stronger) model than the agent. AutoCode pattern: agent on `qwen3-coder:free`, judge on `claude-opus-4-7`. Structured JSON output with `score` (0.0-1.0) + `justification` + `evidence`.

### Acceptance

- Eval case fails on `main` for known-buggy fixture, passes on fixed branch
- LLM judge returns structured JSON scores reproducibly (temp=0)
- CI workflow gates merges on baseline tolerance (10%)
- Drift-derived eval generator proposes ≥ 1 eval case from 30 days of drift events
- Cost cap (`--max-budget-usd`) enforced

### Why this is "the highest-leverage defensive investment"

Per Tier 8 file: **without evals, every later tier is a guess about whether things are getting better.** The eval suite becomes the product's institutional memory. Engineers leave; the evals stay. Each one encodes a lesson learned.

---

## P4 — Tier 2 Item/Turn/Thread (DEFERRED, conditional)

**Cost when activated:** ~2-3 weeks, ~1100 LOC across Rust + Python.
**Status:** deferred indefinitely. Hold-release triggers below.

### Why deferred

Per `05-cross-cutting-concerns.md` §"Things I'd do differently" #3: "If no second client is on the horizon, you're paying ~2 weeks of refactor for purely speculative future value. Defer if no concrete client surface is planned within 6 months."

### Hold-release triggers — ship Tier 2.x only when ≥ 1 of these is true

- A concrete Tauri / Electron / web / IDE plugin / programmatic third-party consumer is being kicked off
- `rtui/src/rpc/protocol.rs` has accumulated > 60 ad-hoc structs (currently 44; growth driver = TUI parity work resuming)
- Two human or AI agents need to consume the backend concurrently from different surfaces

If none hold ~3 months post-stable-commit, re-evaluate against the full AI verification harness plan (`docs/plan/ai-verification-harness-plan.md`) — that may be the better Phase 3.5 candidate.

### Scope when activated (high level)

| Tier | Scope |
|---|---|
| 2.1 | Item/Turn/Thread refactor — replace 44 RPC structs with 3 primitives + initialize handshake + thread/fork/archive/list methods |
| 2.2 | Unix socket + WebSocket transports + capability-token auth + bounded queue with -32001 overload |
| 2.3 | `turn/steer` mid-flight input append |

Forward-compatibility: C6.G5 NDJSON subset (`item.kind` ∈ {`agent_message`, `tool_execution`, `plan_update`, `approval`}) reserves room for the full enum (`reasoning`, `subagent_delegation`, `diff` documented as reserved). When 2.1 lands, bump `protocol_version` from `0.1.0-c6g5-subset` to `0.2.0`. No breaking change for C6.G5 consumers.

---

## P4a — TUI Refactor or Rewrite (Tier 6) [NEW]

**Cost:** ~1.5 weeks refactor (NET −2900 LOC) OR ~3 weeks rewrite (NET −6000 LOC).
**Status:** refactor option is **independent** and can ship anytime; rewrite option is **gated on P4 (Tier 2.1) shipping** because the rewrite consumes the App Server protocol.

### Two paths — pick one when phase activates

#### Path A — Refactor (recommended default)

- Keep `rtui/` directory + binary
- Replace `view.rs`'s 9 × 9 match arms with one widget-per-mode pattern: ~−2000 LOC
- Cache `Lines<'static>` per history entry to fix streaming buffer hacks: ~−400 LOC
- Wait on the 44-RPC-struct → 3 primitives collapse until P4 ships (then ~−500 more LOC)
- **Final size:** ~4600 LOC (vs current 7500)
- **Risk:** low — incremental, no protocol coupling, no behavioral regression from rewrite

**Recommended unless team explicitly wants the binary-size and startup-time wins from a rewrite.**

#### Path B — Rewrite (gated on P4)

- New `rtui-min/` directory at repo root, parallel to `rtui/`
- 1500 LOC hard cap; immediate-mode rendering; one `Mode` enum replaces 9-stage × 9-detail-surface combinatorial tree
- Drops mouse, multi-theme config, altscreen flag, editor launch, clipboard, complex PTY (~700 LOC saved)
- **Final size:** ~1500 LOC (vs current 7500 — net −6000)
- **Risk:** medium — full rewrite + parallel maintenance window
- **Hard prerequisite:** P4 (Tier 2.1 Item/Turn/Thread) shipped — rewrite consumes the new protocol directly

### Performance budgets (from Tier 6, both paths apply)

| Metric | Current rtui | Refactor target | Rewrite target |
|---|---|---|---|
| Cold start | ~250 ms | < 150 ms | < 80 ms |
| Resident memory | ~85 MB | < 60 MB | < 30 MB |
| Frame time (streaming) | ~8-12 ms | < 5 ms | < 3 ms |
| Cells changed per delta frame | unknown | < 30 | < 10 |
| Binary size | ~2.2 MB | ~1.8 MB | < 1.5 MB |
| LOC | ~7500 | ~4600 | < 1500 |

### Migration plan (rewrite path only)

1. Build `rtui-min` alongside `rtui`; both install
2. Ship behind `AUTOCODE_TUI_BACKEND=min` opt-in flag
3. Two-week parity sweep (bug reports + fixes; no new features)
4. Flip default to `min`; `legacy` accessible via env var
5. After 2 minor versions clean: delete `rtui/`, rename `rtui-min/` → `rtui/`

### Acceptance (refactor)

- `view.rs` reduced from 3479 to ~1000 LOC; widget-per-mode pattern in place
- All existing TUI runtime invariants (Track 1 + Track 4 + VHS + PTY smokes) still green
- `cells_changed_per_streaming_delta` benchmark < 30
- No behavioral regression vs prior rtui

### Acceptance (rewrite)

- `rtui-min/` builds and ships behind opt-in flag
- All P4 protocol lifecycle events handled (`item_started/delta/completed`, `turn_started/completed`, etc.)
- Render snapshot tests cover all `Mode` variants
- Performance budget table targets met
- Two-week parity sweep produces zero unfixed regressions

### Decision criterion

If P4 stays DEFERRED indefinitely, ship Path A refactor at any P-letter slot. If P4 activates, evaluate Path B rewrite at that point — by then the team has more telemetry (P1a) and eval coverage (P3d) to gate the rewrite.

---

## P5 — Tier 4 Feature-Flag Tracks (default-off)

**All tracks gated behind environment variables. Promote to default-on only after 4+ weeks of clean telemetry.**

### Tier 4.1 — KAIROS proactive mode

- **Flag:** `AUTOCODE_FEATURE_KAIROS=true`
- **Hard prerequisite:** ≥ 4 weeks of P2 Tier-1.3 telemetry baseline + observability story per `05-cross-cutting-concerns.md` §"KAIROS won't ship cleanly without a strong observability story first"
- **Files:** `autocode/src/autocode/agent/proactive.py` (NEW, ~400 LOC) + SleepTool in `agent/tools.py` + 15-second blocking-budget enforcement in `agent/loop.py`
- **Telemetry:** tick_count / sleep_call_ratio / anti_narration_violations / blast_radius (files changed during proactive runs)

### Tier 4.2 — ephemeral fork

- **Flag:** `AUTOCODE_FEATURE_EPHEMERAL_FORK=true`
- **Hard dependency:** P4 Tier 2.1 (`thread/fork ephemeral=true`)

### Tier 4.3 — sticky environments per turn

- **Flag:** `AUTOCODE_FEATURE_STICKY_ENV=true`
- **Hard dependency:** P4 Tier 2.1 (per-thread environment binding)
- **Files:** `autocode/src/autocode/agent/sticky_env.py` (NEW, ~200 LOC)

### Tier 4.4 — headless `--json` mode

**Already shipped as Tranche 4 C6.G5** with the forward-compatible subset contract. This entry exists to record that the original tier mapping has been consumed by the active program.

---

## Cross-cutting concerns (apply to every phase)

These are inherited unchanged from `05-cross-cutting-concerns.md` — no deviations proposed.

### Testing budget per phase

| Phase | New test files | Approx test count |
|---|---|---|
| P1 | `benchmarks/tests/test_ai_verification_substrate.py` | ~10 |
| P1a | `tests/unit/test_telemetry_store.py` + `tests/unit/test_telemetry_aggregator.py` | ~10 |
| P2 | `tests/integration/test_prompt_cache.py` + `tests/unit/test_prompt_cache_boundary.py` + `tests/unit/test_token_tracker_cache.py` | ~15 |
| P2a | `tests/unit/test_scratch.py` | ~6 |
| P3 | `tests/unit/test_memory_fs.py` + `tests/unit/test_session_notes.py` + `tests/integration/test_verify_before_use.py` | ~17 |
| P3a | `tests/unit/test_drift.py` (schema + staleness + consistency detectors) | ~10 |
| P3b | `tests/integration/test_pev.py` + `tests/integration/test_ralph.py` + `tests/unit/test_intent_store.py` | ~12 |
| P3c | `tests/integration/test_entropy.py` + `tests/integration/test_verify_nudge.py` | ~6 |
| P3d | `evals/cases/*.yaml` (case-by-case) + `tests/unit/test_eval_runner.py` + `tests/unit/test_eval_judge.py` | ~10 unit + N cases |
| P4 (when activated) | `tests/integration/test_app_server_protocol.py` + `tests/integration/test_transports.py` + `tests/integration/test_turn_steer.py` | ~21 |
| P4a refactor | `rtui/tests/render_snapshots.rs` (extend) + Track 1/4 invariants stay green | covered by existing |
| P4a rewrite | `rtui-min/tests/render_snapshots.rs` (NEW) + perf benchmark in CI | ~10 + perf gate |
| P5 (when activated) | `tests/integration/test_kairos.py` + `tests/integration/test_ephemeral_fork.py` + `tests/integration/test_sticky_env.py` | ~13 |

Per-test LLM cassette fixtures under `tests/fixtures/cassettes/` for cache verification. CI budget: keep `pytest tests/` < 5 min total. P3d eval suite runs on its own GH workflow with `--max-budget-usd` cap.

### Telemetry per phase

| Phase | Metric | Why |
|---|---|---|
| P1a | event throughput, queue depth, drop rate | Verify telemetry is healthy and not dropping events under load |
| P2 | `cache_hit_ratio` (= `cache_read_tokens / prompt_tokens`) | Verify cache fires; alert if drops below 0.5 after warmup |
| P2 | `cache_write_premium_paid` | Track cost of cache misses |
| P2 | `cost_savings_per_session` | Justify the program's payback |
| P2a | `tool_output_offloaded_count`, `bytes_offloaded_per_session` | Verify scratch threshold is right; tune if too noisy |
| P3 | `memory_index_line_count` | Should stay ≤ 200 |
| P3 | `topic_file_count` | Growth-rate signal |
| P3 | `compaction_path_a_ratio` | Goal: > 80% after activation threshold |
| P3a | `tool_drift_detected` by kind (schema / staleness / consistency) + per-tool breakdown | Identify which tools are drifty in production |
| P3b | `ralph_recoveries_per_session`, `pev_step_failure_rate` | Reliability dashboard signal |
| P3c | `entropy_audit_high_severity_count` | Alert when context coherence is failing |
| P3d | eval baseline drift, eval pass rate, judge agreement rate | CI-gated; baseline updates require justification |
| P4 | `turn_completion_latency_p50/p95` | Detect regressions from Item refactor |
| P5 | `tick_count`, `sleep_call_ratio`, `anti_narration_violations` | Safety telemetry for KAIROS |

Local-only — never sent off-machine. Document in README. Provide `autocode telemetry purge`.

### Migration safety per phase

| Phase | Rollback path |
|---|---|
| P1 | Substrate is additive — disable by removing `benchmarks/ai_verification/` runner usage |
| P1a | `AUTOCODE_TELEMETRY_DISABLED=true` skips emission entirely; `autocode telemetry purge` deletes data |
| P2 | `AUTOCODE_DISABLE_PROMPT_CACHE=true` falls back to non-cached requests; boundary marker is just a comment string |
| P2a | `AUTOCODE_DISABLE_SCRATCH=true` inlines all tool outputs (current behavior) |
| P3 | Old SQLite `memories_archive_<date>` table preserved; `AUTOCODE_USE_LEGACY_MEMORY=true` reads from it |
| P3a | Per-detector disable: `agent.drift.{schema,staleness,consistency}.enabled=false` |
| P3b | `AUTOCODE_DISABLE_RALPH=true`; PEV is opt-in via `/plan` so default is straight-line agent |
| P3c | Entropy audits are passive (read-only); auto-disable on cost cap; prompt section can be removed via `STABLE_INSTRUCTIONS` edit |
| P3d | Eval suite is additive; CI gate can be soft (warn-only) before promoting to merge-blocking |
| P4 | `--legacy-rpc-v1` flag re-enables old method aliases without deprecation warnings |
| P4a refactor | Behavioral parity preserved; revert PR if issue found |
| P4a rewrite | `AUTOCODE_TUI_BACKEND=legacy` keeps old TUI for 2 minor versions before deletion |
| P5 | Each feature flag defaults to false |

### Performance budgets

| Operation | Budget |
|---|---|
| `initialize` round trip | < 100 ms |
| `thread/start` round trip | < 200 ms |
| `turn/start` → first `item/started` | < 300 ms |
| Memory index load (Layer 1) | < 50 ms |
| Topic file load (Layer 2) | < 200 ms per file |
| `grep_logs` over 30 days | < 500 ms |
| Compaction Path A | < 1 sec |
| Compaction Path B (LLM call) | < 30 sec |

### Documentation deliverables per phase

1. CHANGELOG.md entry — user-visible changes
2. `docs/reference/` page (Tier 2.1 specifically: `rpc-schema-v2.md` matching Codex's app-server README format)
3. Migration guide (P3 SQLite→FS, P4 RPC v1→v2)
4. Configuration docs (P5 feature flags)
5. Telemetry guide — what's logged where

---

## Open user-decisions (still on the table)

The original 3 questions from Entry 1662 + 3 new questions raised by Tiers 5-8 integration:

1. **P2 timing:** strictly post-C7.GATE, or interleave between C5.GATE and C6.G5? Current default = strictly post-commit. User can override.
2. **Second client surface:** any concrete Tauri / Electron / web / IDE plugin / programmatic consumer planned within 6 months? Decides whether P4 stays deferred AND whether P4a rewrite path is unlocked.
3. **AI verification harness scope:** narrow substrate (this doc) vs full 7-milestone plan (`docs/plan/ai-verification-harness-plan.md`). Codex Entry 1665 ratified narrow substrate; user can expand later. P3d expands narrow substrate into production eval suite.
4. **TUI Path A (refactor) vs Path B (rewrite):** Path A is independent and safer (~−2900 LOC, low risk). Path B is gated on P4 and gives bigger wins (~−6000 LOC, lower binary size, faster startup). Default recommendation: Path A unless team explicitly wants the rewrite.
5. **Telemetry CI gate strictness:** P3d eval suite gate can be soft (warn-only) or hard (merge-blocking). Recommendation: start soft for 2 weeks of stability, then promote to hard.
6. **`agent/loop.py` modular refactor:** by P3b the loop will have ~12 hooks (auto-verify, atomic checkpoint, git-aware staging, cache, memory, scratch, drift, PEV, Ralph, telemetry, entropy, verify-nudge). Strong recommendation: insert a hook-architecture refactor between P3 and P3a — extract hook protocol + dispatcher, register hooks declaratively. Cost: ~2-3 days, ~150 LOC delta. Without this, P3a-d become difficult to land cleanly.

---

## What this roadmap deliberately omits

Per `00-INDEX.md` §"What this roadmap deliberately omits":

- 5-tier compaction parity — current 3-tier covers ~90% of value
- Anti-distillation tooling — irrelevant for non-distilled product
- Undercover mode — Anthropic-employee-specific
- Buddy/Tamagotchi — pure entertainment
- Voice mode — no clear path without Realtime API budget
- Multi-agent Coordinator — scope creep relative to current goals
- Cron tools / GitHub webhook subscriptions — depend on hosted infrastructure AutoCode doesn't have
- Anthropic-style "Auto Memory" with LLM-decided saving — defer until P3 baseline proves stable

---

## Activation runbook (when C7.GATE closes and stable commit lands)

1. Confirm C7.GATE artifact stored, full regression sweep green, Claude Entry 1694 APPROVE present, and user committed stable
2. Re-read this document + `00-INDEX.md` + Tier 5-8 source docs
3. Answer the 6 open user-decisions (or note that defaults stand)
4. Spawn `docs/plan/post-c7-phase-1-checklist.md` from `docs/plan/backend-robustness-tranche-4-checklist.md` template (each P-letter phase gets its own checklist when activated)
5. Open `AGENTS_CONVERSATION.MD` pre-task intent for P1 substrate
6. Builder routing: OpenCode primary, Codex fallback
7. Reviewer: Claude default
8. After P3 ships and before P3a starts: pause for `agent/loop.py` modular hook-architecture refactor (~2-3 days, ~150 LOC delta) — see Open user-decisions §6

Until step 1 happens, no post-commit work begins. Tranche 4 has priority.

---

## Provenance

| Decision | Source |
|---|---|
| Tier 4.4 NDJSON shape consumed by C6.G5 | Entry 1664 (Claude) + Entry 1665 (Codex) |
| Cache-multiplier hook in C6.G6 | Entry 1664 (Claude) + Entry 1665 (Codex hardening: 1.25 cache-write-premium test) |
| Verify-before-use folded into P2 (not Tranche 4) | Entry 1664 (Claude) |
| AI verification harness as P1 (narrow substrate) | Entry 1663 (Codex) + Entry 1664 (Claude ratify) + Entry 1665 (Codex confirm) |
| Tier 3 before Tier 2 sequencing | Entry 1664 (Claude) + `05-cross-cutting-concerns.md` §"Things I'd do differently" |
| P4 Tier 2.1 deferred conditional | Entry 1664 (Claude hold-release triggers) |
| KAIROS gated on 4-week telemetry baseline | `04-tier4-future-tracks.md` + Entry 1664 |
| Tier 5-8 integration (P1a, P2a, P3a-d, P4a phases) | Entry 1684 (Claude); Tiers 5-8 source files added 2026-04-30 |
| Sensors-first doctrine (P1a + P3a interleave before big optimizations) | `10-tier8-observability-evals.md` §"Why this is last but not optional" + `07-tier5-harness-reliability.md` §"Why this matters now" |
| TUI Path A (refactor) recommended default; Path B (rewrite) gated on P4 | `08-tier6-minimal-tui.md` §"Counterargument: don't rewrite, refactor" + Entry 1684 (Claude) |
| `agent/loop.py` hook-architecture refactor required between P3 and P3a | Entry 1684 (Claude) — preventive, no source-doc mandate |
| Mitchell Hashimoto rule (every mistake → eval) operationalized in P3d Tier 8.3 | `10-tier8-observability-evals.md` §"Tier 8.3 — Regression discipline" |
