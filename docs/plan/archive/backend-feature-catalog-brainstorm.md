# Backend Feature Catalog + Improvement Brainstorm

> **Status:** BRAINSTORM — not an implementation plan.
> **Author:** Claude (Reviewer/Architect).
> **Date:** 2026-04-24.
> **Complements:** `docs/plan/backend-tightening-refinement-plan.md` (Codex, method-first); `AGENTS_CONVERSATION.MD` Entry 1417 (TDD framing).
> **User ask (verbatim):** "brainstorm backend improvements... start with what features we should have a full list of them for the backend and then how to do them, exiting features and if we need improve them, start researching."

---

## 1. Relationship to Codex's Work

Codex's `backend-tightening-refinement-plan.md` is **method-first**:

- Stage 1: transport/chat conformance depth
- Stage 2: task/subagent/todo/loop surfaces
- Stage 3: context/memory
- Stage 4: host hygiene

Codex's Entry 1417 adds a **TDD framing**: three test layers (A unit, B transport-parametrized contract, C live PTY), behavior-matrix targets, Red → Green → Refactor per slice.

**I concur with both.** This brainstorm is **feature-first**: a catalog of what the backend should offer, what it actually offers today, and where the gaps are. The catalog feeds *which behaviors* each of Codex's stages should tighten, and flags extra features that don't fit the current plan but probably should.

---

## 2. Method

- Agent-driven survey (Explore) across 12 backend subsystems
- Manual spot-check of high-impact claims via grep/read
- Cross-reference against `requirements_and_features.md` (baseline, ~stale), `features_behavior.md` (current), `rpc-schema-v1.md` (contract), `docs/plan/deferred/modular_migration_todo.md` (open architecture items)

### 2.1 Spot-check corrections to the Explore audit

Several Explore claims overreached. I verified and correct here so downstream planning isn't built on wrong premises:

| Explore claim | Reality | Evidence |
|---|---|---|
| "Hooks never fired from AgentLoop" | **WRONG** — STOP/STOP_FAILURE/PreToolUse all fire | `loop.py:148, 182, 155-191, 881` |
| "Middleware never runs" | **WRONG** — 8 call sites for `_run_middleware` | `loop.py:430, 438, 496, 517, 588, 1033, 1068, 1103` |
| "SubagentManager unreachable by default" | **WRONG** — created unconditionally at ensure-agent-resources | `server.py:451`; tools registered at `:461` |
| "Memory `learn_from_session` never called" | **WRONG** — called on session end | `server.py:556` |
| "Layer 2 search never invoked" | **WRONG** — reachable via `search_code` tool call | `tools.py:1642, 1658, 1681`; handler at `tools.py:1026-1034` |

### 2.2 Confirmed genuine gaps

Items where Explore's finding holds on verification:

- `ToolResultCache` **built** in `tools.py` but **never queried** by the loop — the LRU cache is live but cache hits are impossible.
- Layer 2 retrieval **not auto-injected into prompts** — the agent can *call* `search_code`, but iteration-zero context has only tool-name listings, no retrieval preview.
- Thinking tokens **parsed from model output** (`<think>` tag, reasoning blocks) but **never explicitly requested** from providers that support a thinking flag — so thinking output is best-effort only.
- Tool metadata `interruptible` and `output_budget_tokens` — **captured on `ToolDefinition`** but **no code path honors them**.
- Task status lifecycle — tools transition `pending → completed`; **`in_progress` is never set** by any handler.
- Checkpoint store — saves task DAG JSON; **message history is not included**, so "restore" loses conversational context.

---

## 3. Target Feature Catalog — "What We Should Have"

For each subsystem: **Target** (what "complete" looks like) → **Today** (what currently exists) → **Gaps** (what's missing or shallow).

Keep each subsystem tight; full implementation specifics belong in a later plan, not this brainstorm.

### 3.1 Agent Loop

**Target.** Deterministic LLM ↔ tool turn executor with visible liveness, mode-aware tool filtering, graceful compaction, middleware + hook fan-out, cancellation + steer + retry, and per-iteration observability.

**Today.** Multi-mode loop (NORMAL/PLANNING/RESEARCH/BUILD/REVIEW); prompt caching split (static prefix + dynamic suffix); environment snapshot on turn 0 (deferred Layer 2 warmup — Entry 1377 fix); middleware + hook fan-out genuinely wired; first-turn bootstrap stable (fix landed).

**Gaps.**
- Per-iteration profiler accepted (`_profiler`) but never called — no timing telemetry from default runs.
- Session stats (`_session_stats`) injected but never updated.
- Text-nudge retry (`MAX_TEXT_NUDGES = 2`) defined but never triggered on empty responses.
- Emergency compaction at 90% discards summary without residual — lossy.
- `on_warning` (Entry 1408) wired end-to-end but the loop itself never emits one; only provider-layer code does.

### 3.2 Subagents + Delegation

**Target.** Spawn isolated mini-agents with capability-filtered tools, honest permission enforcement, parallelism caps, status projection to frontend, scheduler-based fairness, and failure-bounded circuit breakers.

**Today.** `LLMScheduler` (single-worker priority queue); `SubagentLoop` (restricted mini-agent with circuit breaker at 2 consecutive errors); `SubagentManager` (depth cap 2, parallelism cap 3, total cap 10); `DelegationPolicy` (role presets: scout/engineer/architect); `AgentTeam` persistence; SOP pipeline; 4 subagent tools registered.

**Gaps.**
- **Permission enforcement is cosmetic.** `DelegationPolicy.check_spawn_permission` is consulted *only* for spawn — downstream tool access inside a subagent is governed by `ApprovalManager`, which never consults `DelegationPolicy.role_permissions`. So a "scout" with `file_write=DENY` in its policy can still call `write_file` through the same approval path.
- `LLMScheduler` priority tiers (foreground=0, background=1) exist but all subagent calls hardcode `foreground=False` (`subagent.py:190`) — prioritization is effectively dead.
- Subagent circuit breaker has no backoff/retry strategy — 2 errors → hard exit.
- `SOPPipeline._default_executor` returns the step description as a string (`sop_runner.py:177`) — no real SOP execution.
- Role presets in `delegation.py:109-120` are never consulted by `SubagentManager.spawn()` beyond permission check.

### 3.3 Context Management

**Target.** Token-budgeted prompt assembly with priority-weighted sections, auto-compaction before limits, lossless checkpoint on significant turns, adaptive tool-result truncation, and transparent observability when context is dropped.

**Today.** `ContextEngine` (heuristic token count = chars/4; auto-compact at 75%; emergency at 90%); `ContextAssembler` (5000-token budget across rules/repomap/search/file/history); `ArtifactCollector` (commands.log + git diff).

**Gaps.**
- `ContextAssembler.assemble()` accepts `search_results` parameter but **doesn't use it** when building sections (`core/context.py:44-110`).
- Token counting is heuristic everywhere; `provider.count_tokens()` exists and is never consulted for calibration.
- Truncation is fixed head/tail (60/40 split); no content-structure awareness.
- `CompactionResult` generated but never logged or returned to caller — no visibility into compactions.
- `ArtifactCollector` writes to filesystem only; never persisted to session/episode store.
- Tool result truncation uses hard 500-token cap regardless of `output_budget_tokens` metadata.

### 3.4 Memory Management

**Target.** Project-scoped memories with dedup, relevance decay, session-boundary consolidation, cross-session promotion, query by semantic/category, and honest retention caps.

**Today.** `MemoryStore` (SQLite + Jaccard-0.7 dedup; 0.95 relevance decay per session; 200-entry cap); 4 categories (tool_pattern, user_preference, project_fact, error_resolution); `learn_from_session` invoked at session end (`server.py:556`); `SessionConsolidator` 4-phase pipeline (orient → gather → consolidate → prune).

**Gaps.**
- `SessionConsolidator.gather()` extracts learnings **but never persists them** — `gather()` returns learnings; no call site saves them to `MemoryStore`. So consolidation is implemented but inert.
- LLM JSON parsing in `learn_from_session` (`memory.py:196-202`) is fragile string-based `[...]` extraction — will fail on preamble.
- Memory context injection (`memory.py:100-118`) returns a formatted string but no caller wires it into the system prompt.
- No cross-session memory promotion: high-relevance memories never "graduate" to permanent project facts.
- Decay/consolidation have no transaction boundaries — can interleave.

### 3.5 Tasks / Todo

**Target.** DAG-based task tracking with full lifecycle (pending → in_progress → completed/failed), cycle detection, dependency ordering, artifact attachment, projection notifications to frontend, and checkpoint-safe snapshots.

**Today.** `TaskStore` (SQLite + topological sort + cycle detection); 4 tools (create/update/list/add_dependency); JSON snapshot/restore; dependency readiness queries; `on_task_state` notification.

**Gaps.**
- **`in_progress` status is never set** by any tool. Lifecycle is binary (pending ↔ completed) despite the schema.
- Task artifacts table exists but `TaskStore` has no artifact CRUD methods.
- No cascading delete — orphaned dependency edges remain when a task is deleted.
- Blocked-reason string is only surfaced via `summary()`; no dedicated RPC to query blocking state.
- Task tools registered **conditionally** (only if `task_store` passed) — consistent with current backend, but makes isolated testing harder.

### 3.6 Tool Registry

**Target.** Self-describing tools with accurate metadata (mutates_fs, executes_shell, interruptible, output_budget, approval requirement), token-efficient core/deferred split, cache + working set awareness, and pluggable filtering per mode.

**Today.** `ToolRegistry` with core/deferred split (14 core tools: read/write/edit/run/search/list/tool_search/git_{status,diff,log}/web_fetch/apply_patch/todo_{write,read}); 8 metadata fields on `ToolDefinition`; ~60 built-in handlers; `ToolResultCache` (LRU 100 entries, 10min TTL); `WorkingSet` (recent files).

**Gaps.**
- **`ToolResultCache` is not consulted** by `AgentLoop` — cache is built and ready but results are never memoized between iterations.
- **`WorkingSet` data collected but not surfaced** — `get_active_working_set` is referenced in `loop.py:277-283` and IS surfaced in the bootstrap snapshot, but **not refreshed mid-turn** and not used for retrieval ranking.
- `interruptible` metadata never checked — no interrupt mechanism.
- `output_budget_tokens` per-tool is ignored; truncation is globally 500 tokens.
- `tool_search` uses substring matching only — no semantic/embedding rank.
- Tool registration is scattered across 4+ modules — hard to audit total tool surface.

### 3.7 Middleware + Hooks

**Target.** Pluggable event fan-out (before_model, after_model, before_tool, after_tool, on_iteration, on_error, before/after_compaction, session_start/stop, pre/post_tool_use), typed context object, skip/override semantics, and shared-state across a turn.

**Today.** `MiddlewareStack` with 8 event types; `MiddlewareContext` supports skip + modified_result; `HookRegistry` loads from project + user `.claude/settings.json`; STOP/STOP_FAILURE/SessionStart/PreToolUse all fire from loop.

**Gaps.**
- **PostToolUse hook firing needs verification** — I see `_fire_pre_tool_use` explicit, but a `_fire_post_tool_use` method was not grep-visible in my spot-check. If missing, that's a real gap (PostToolUse hooks would be declared in `settings.json` and silently ignored).
- Default middleware registration is sparse — stack runs, but few middleware are actually installed by default. Infrastructure > usage.
- `looks_multi_step_request()` heuristic returns True but there's no handler that then decomposes; signal is unused.
- Hook matcher supports globs only — no regex.
- Hook timeout handling doesn't distinguish timeout from other errors in the log.

### 3.8 Routing / Policy

**Target.** Deterministic request classification (L1 lookup) → retrieval escalation (L2) → local constrained (L3) → LLM (L4) → external opt-in, with cost/latency budgets and honest fallback on missing dependencies.

**Today.** `core/router.py` 3-stage classifier (regex → feature extraction → weighted scoring); `PolicyRouter` 5-layer escalation with task-type routing; RequestType enum; `StrategyOverlay` per task family (HTML_OUTPUT, PYTHON_BUILD, GENERAL).

**Gaps.**
- **Two routing systems don't share decisions.** `core/router.py:Router.route()` returns `RequestType`, but `PolicyRouter.route()` at `policy_router.py:52+` ignores `RequestType` and routes by `(task_type, complexity)` instead.
- Feature extraction scores are summed into a dict but **never thresholded** — scores calculated for nothing.
- External escalation has no per-session cost cap.
- Benchmark prompt heuristic is magic-number based (2 markers OR 1 + 8 newlines + 80 words) — no config.
- No routing cache; every call re-runs regex matching.

### 3.9 Layers 1-4

**Layer 1 (deterministic).** Target: tree-sitter parse + symbol queries reachable via tool calls AND pre-emptively surfaced in context. **Today:** tools `list_symbols`, `find_definition`, `find_references`, `get_type_info` all registered and callable; tree-sitter parser cached. **Gap:** L1 results are tool-call-only; iteration-zero context does not preview symbols from recently-touched files.

**Layer 2 (retrieval).** Target: hybrid BM25 + vector search with graceful degradation, auto-warm on first-turn, integrated with context assembler. **Today:** `HybridSearch` works; `search_code` tool reachable; iteration-zero bootstrap explicitly defers warmup (Entry 1377 fix). **Gap:** retrieval results not injected into prompt unless the LLM explicitly calls `search_code`. The `ContextAssembler.search_results` parameter exists but is never consumed (see 3.3).

**Layer 3 (local constrained).** Target: llama-cpp-python + Outlines for structured generation; used for simple edits with JSON schema. **Today:** `L3Provider` coded; never instantiated by default runtime (`layer3/provider.py:114`). **Gap:** L3 is pure scaffolding; no `_l3_provider` is actually loaded. `BackendServer._l3_provider` is `None` on the default path.

**Layer 4 (remote LLM).** Target: streaming generation with tool calls, thinking support, structured JSON, graceful retry. **Today:** Ollama + OpenRouter providers; fail-fast classification landed (Entry 1408); `on_warning` surfacing landed; 400/401/403/404/422 treated as permanent. **Gap:** Thinking mode is never *requested* (only parsed from response); OpenRouter provider shape is narrower than Ollama.

### 3.10 Sessions + Checkpoints

**Target.** Durable session store + message history, checkpoint with complete state (messages + tasks + memory snapshots), event-sourced episode store with bounded retention, blob-addressed large payloads.

**Today.** `SessionStore` (WAL-mode SQLite, auto-titled); `CheckpointStore` (JSON DAG + transactional rollback); `EpisodeStore` (200 events/session cap, auto-purge oldest); `BlobStore` (SHA-256 dedup).

**Gaps.**
- **Checkpoints capture task state only** — message history is not part of a checkpoint, so `checkpoint.restore` loses turn context.
- Tool calls stored in separate table but no query API; must reconstruct from messages.
- Session `summary` field exists but is never populated by any tool.
- `token_count` per message tracked but never aggregated into `session.token_count`.
- Episode retention is hard cap — no summarization mercy rule; events just get purged.
- `BlobStore` integration is partial (used by episodes, not by sessions or checkpoints).

### 3.11 Approvals + Permissions

**Target.** Mode-driven gating (READ_ONLY/SUGGEST/AUTO/AUTONOMOUS), per-tool approval with session memory, dangerous-command heuristics across all write/shell tools, sandbox resource limits enforced, delegation policy honored.

**Today.** `ApprovalManager` with 4 modes; 6 hardcoded blocked shell patterns (rm -rf, mkfs, etc.); session-level approval memory (`_session_approved_tools`); shell enable/disable.

**Gaps.**
- **`is_blocked()` only checks `run_command`**; `write_file`, `edit_file`, `apply_patch` are not scanned for dangerous patterns.
- **Sandbox resource tracking is passive** — fds/processes counted but limits never enforced; `ApprovalManager` never consults sandbox.
- **`ApprovalManager` never consults `DelegationPolicy`** — role permissions are not applied during subagent execution.
- Blocked patterns are hardcoded list; no config override.
- Approval mode is static; no in-turn change except `enable_shell`.

### 3.12 Providers

**Target.** Lazy-loaded providers with VRAM budget eviction, multiple concurrent model registries per layer, per-provider cost/token tracking, graceful unload.

**Today.** `ProviderRegistry` with max 2 models, LRU eviction; Ollama + OpenRouter; cost tracking via `token_tracker`.

**Gaps.**
- `ProviderRegistry.get_for_spec()` only returns existing providers; does not auto-load new ones.
- VRAM budget is a counter, not an actual memory measurement.
- LRU eviction is insertion-order; no access-frequency tracking.
- Provider state not persisted; unload loses caches.

---

## 4. Gap Prioritization

### P0 — Wire-up gaps (features exist; connect them)

Low-risk, high-value — the code exists.

1. **`ToolResultCache` → loop** — consult cache before running identical tool calls within a session.
2. **`ContextAssembler.search_results` consumption** — wire the accepted parameter into section building.
3. **`SessionConsolidator.gather` → `MemoryStore.save`** — persist extracted learnings.
4. **`in_progress` task state** — `update_task` tool transitions to `in_progress` when a task's work starts.
5. **Thinking request flag** — when provider supports `thinking`, explicitly request it (don't just parse).
6. **PostToolUse hook firing** — verify; add if missing.
7. **`is_blocked` coverage** — scan `write_file`/`edit_file`/`apply_patch` args for dangerous patterns.

### P1 — Shallow-to-deep (works but fragile or partial)

Medium risk — requires design choices.

8. **DelegationPolicy enforcement across tools** — `ApprovalManager` consults role permissions inside subagent context.
9. **Context priority thresholding** — when a section overruns its budget, reduce proportionally instead of keeping-all.
10. **Memory extraction robustness** — replace string `[...]` search with structured provider JSON request.
11. **Checkpoint includes message history** — otherwise restore is lossy.
12. **Token count calibration** — use `provider.count_tokens()` where available, not chars/4.
13. **SubagentLoop scheduling fairness** — priority tiers must actually differentiate foreground from background.

### P2 — New capabilities (genuinely missing)

Higher effort — new design.

14. **Adaptive tool-result truncation** — adapt to content structure, not fixed head/tail.
15. **Cross-session memory promotion** — high-relevance memories graduate to durable project facts.
16. **Per-session cost limits + abort** — optional user-set cap triggers visible stop.
17. **Tool interruption honoring `interruptible` flag** — cancel running tool cleanly.
18. **L1/L2 context auto-preview on iteration-zero** — small, cheap preview; defer full search.
19. **Episode store summarization mercy rule** — before purge, summarize into a checkpoint-tier entry.

### P3 — Architecture cleanup (already in Codex plan / `docs/plan/deferred/modular_migration_todo.md`)

Overlaps with Codex Stage 4 and the Phase 2-4 Follow-through list. No new items here; tracked elsewhere.

---

## 5. Integration with Codex's Stage Plan

| Codex Stage | This brainstorm's P0 items | This brainstorm's P1 items | This brainstorm's P2 items |
|---|---|---|---|
| **Stage 1** — transport/chat conformance | #5 thinking request flag, #6 PostToolUse hook audit | #12 token count calibration | — |
| **Stage 2** — task/subagent/todo/loop | #4 task `in_progress` state | #8 DelegationPolicy enforcement, #13 subagent scheduler fairness | #17 tool interruption |
| **Stage 3** — context/memory | #1 tool-result cache wiring, #2 ContextAssembler search_results, #3 memory persist | #9 context priority thresholding, #10 memory extraction robustness | #14 adaptive truncation, #15 cross-session memory, #18 L1/L2 auto-preview |
| **Stage 4** — host hygiene | #7 `is_blocked` coverage | #11 checkpoint with messages | #16 cost limits, #19 episode summarization |

**Reading:** each of Codex's stages already has a natural home for 2-4 of the P0/P1/P2 items above. This brainstorm's feature lens doesn't displace the TDD approach — it gives Codex specific *behaviors* to write failing tests for within each stage.

---

## 6. Open Questions for User

1. **Scope.** Aim for all P0+P1 in this tranche, or ship P0-only and reassess?
2. **Thinking tokens.** Do we want thinking-mode as an always-on flag or a per-session toggle via `/thinking` (already implemented in commands)?
3. **Subagents.** Are subagents on the critical path for this tranche, or defer deep work there to after `/cc` binding? The permission enforcement gap (#8) is nontrivial.
4. **Memory.** Should cross-session memory promotion (#15) land before release, or is session-scoped memory enough for v1?
5. **Cost limits.** Hard abort on cap hit, or warning + continue?
6. **L3 Layer.** L3Provider is scaffolded but unused. Do we invest to wire it, or mark it deferred and remove the stub import?
7. **`requirements_and_features.md` freshness.** That catalog is last-updated 2026-02-17 and predates most recent work. Worth a dedicated sync pass, or let `features_behavior.md` carry the load?

---

## 7. Proposed Next Steps

1. **User reads this + Codex's `backend-tightening-refinement-plan.md` + Entry 1417** and picks:
   - Priority axis (P0-first vs P1-first vs mixed)
   - Answers to the 7 open questions above.
2. **Once direction is set**, this brainstorm is replaced by `docs/plan/backend-feature-improvement-plan.md` — a concrete plan with per-slice exit criteria tied to Codex's Stage 1-4.
3. **Codex or OpenCode executes** slices one at a time. Claude reviews each.
4. **Stage gate test matrix** (per Codex Entry 1417):
   - Layer A: unit tests for new helpers
   - Layer B: transport-parametrized contract tests — THIS is where new P0/P1 features get their conformance proof
   - Layer C: live PTY canary after each stage completes

---

## 8. References

- `docs/plan/backend-tightening-refinement-plan.md` — Codex's method plan
- `AGENTS_CONVERSATION.MD` Entry 1417 — TDD framing
- `docs/plan/deferred/modular_migration_todo.md` — Phase 2-4 Follow-through items (architecture cleanup overlap)
- `docs/features_behavior.md` — current runtime inventory
- `docs/reference/rpc-schema-v1.md` — wire contract
- `docs/requirements_and_features.md` — 2026-02-17 feature catalog (baseline; stale)
- `autocode/src/autocode/agent/loop.py` — agent loop
- `autocode/src/autocode/agent/subagent.py` — subagent manager + scheduler
- `autocode/src/autocode/agent/context.py` — ContextEngine
- `autocode/src/autocode/agent/memory.py` — MemoryStore
- `autocode/src/autocode/session/task_store.py` — TaskStore
- `autocode/src/autocode/agent/tools.py` — Tool registry (1912 lines)
- `autocode/src/autocode/agent/middleware.py` — Middleware stack
- `autocode/src/autocode/agent/hooks.py` — Hook registry
- `autocode/src/autocode/core/router.py` + `autocode/src/autocode/agent/policy_router.py` — routing
- `autocode/src/autocode/backend/server.py` — BackendServer (wiring point for most subsystems)

---

## 9. Honest Caveats

- This brainstorm is based on one Explore pass + targeted spot-checks. It is not a line-by-line audit. Before any P0 item lands as code, the author of that slice should re-verify the specific "shallow/unwired" claim for that feature.
- Five Explore claims were found to be overreaching and have been corrected in §2.1. Others may remain — assume 85% signal, 15% noise until spot-checked.
- The `requirements_and_features.md` catalog was last updated 2026-02-17 and predates §1h Rust migration, modular Phases 1-5, and most recent runtime work. Treat it as historical baseline, not ground truth.
- The priority labels (P0/P1/P2/P3) are my suggestion based on risk/value tradeoffs. The user is the final arbiter of sequence.
