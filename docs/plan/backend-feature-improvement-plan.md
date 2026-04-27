# Backend Feature Improvement Plan

> **Status:** LOCAL REGRESSION COMPLETE — user-directed backend tranche, authorized 2026-04-24. Live gateway canary remains before broad benchmark sweeps or product-path release claims.
> **Supersedes:** `docs/plan/archive/backend-feature-catalog-brainstorm.md` (brainstorm is now archival reference).
> **Complements:** `docs/plan/backend-tightening-refinement-plan.md` (Codex's method/TDD plan).
> **Current implementation inventory:** `docs/features/backend_features.md`.
> **Author:** Claude (Reviewer/Architect).
> **Delegate:** Codex (Builder) executes slices; Claude reviews each.

---

## 1. User Decisions (2026-04-24)

Verbatim captured from user direction:

1. **Scope:** P0 + P1 + P2 (all three tiers from the brainstorm catalog).
2. **Thinking tokens:** toggle controls the model's thinking capability (not just frontend display). When thinking is ON, stream thinking tokens to the TUI Claude-Code-style; when OFF, request the model to NOT think.
3. **Subagents:** deep work deferred to post-`/cc`. Subagent permission enforcement (P1 #8) and scheduler fairness (P1 #13) are OUT OF SCOPE for this tranche.
4. **Memory:** cross-session memory promotion (P2 #15) deferred to after v1. Session-scoped memory is sufficient now.
5. **Cost limits:** warn + continue (P2 #16). User later locked S-COST to
   Tier B from `docs/research/cost-display-comparative-analysis.md`: cache
   tracking now, threshold default unset/opt-in, `/cost` default plus
   `/cost --detail`, status bar cadence unchanged, cross-session rollup
   deferred.
6. **L3 Layer:** user wants clarification. See §3.
7. **Docs refresh:** all stale docs. See §5.

**In-scope item count:** 16 feature items + L3 decision + doc-refresh pass = 17 slices + 1 decision record.

---

## 2. Relationship to Codex's Stage Plan

Codex's `backend-tightening-refinement-plan.md` sequence is preserved. Each slice maps to exactly one Codex stage:

| Codex Stage | Slices (this plan) |
|---|---|
| **Stage 1** — transport/chat conformance | S-THINK-A, S-THINK-B, S-POSTTOOL, S-TOKENCAL |
| **Stage 2** — tasks/subagents/todo/loop | S-INPROGRESS, S-INTERRUPT |
| **Stage 3** — context/memory | S-CLEAR-RESULTS, S-SEARCHRES, S-MEMPERSIST, S-PRIORITY, S-MEMROBUST, S-TRUNCATE, S-L1L2PREVIEW |
| **Stage 4** — host hygiene | S-BLOCKED, S-CKPTMSG, S-COST, S-EPISODESUM |
| **Parallel** (docs/decision) | S-L3DOC, S-DOCSREFRESH |

Codex's TDD framing (Entry 1417) applies unchanged: Layer A unit, Layer B transport-parametrized contract, Layer C live PTY. Every slice exit gate must include a failing-then-green Layer B contract test where the behavior crosses the backend wire; otherwise it lives in Layer A.

---

## 3. Layer 3 Explanation + Decision

**What Layer 3 is.** In the AutoCode layer model, Layer 3 is **local constrained generation** using `llama-cpp-python` + Outlines. Intended use: run a small local model (e.g., Qwen2.5-Coder-1.5B Q4_K_M) on a ~2GB VRAM budget, with grammar-constrained output, to handle structured-JSON tasks (simple edits, form-filling, tool-call-only routing) without paying a full Layer 4 cloud call.

**Why it's opt-in rather than core.** `layer3/provider.py` defines `L3Provider` with async model loading and constrained generation. `BackendServer` can instantiate it and route `SIMPLE_EDIT` requests to it when the `layer3` optional extra is installed and `config.layer3.enabled` remains true. Core installs do not include the heavy native `llama-cpp-python` / Outlines dependency stack, so startup catches `ImportError`, leaves `_l3_provider = None`, and falls back to Layer 4.

**Decision for this tranche.** Do not broaden Layer 3 routing or make it a supported default path. Keep it opt-in with a docstring that points to this decision + future-revisit criteria. Rationale:

- L4 gateway (`http://localhost:4000/v1`) already covers structured-JSON use cases cheaply.
- Truly offline/airgapped deployment is not on the current roadmap.
- End-to-end validation for active L3 generation is not in place yet; current coverage is unit-level provider/degradation coverage.
- Keeping the opt-in path costs little; removing it would require pruning routing/config/test references.

**Revisit trigger.** Add L3 back to the roadmap when either (a) offline-first deployment becomes a product requirement, or (b) L4 gateway costs exceed a configurable per-session budget frequently enough to warrant local fallback.

**Slice:** `S-L3DOC` adds a clear opt-in/experimental docstring + TODO comment and records this decision in `modular_migration_todo.md` under a new "Opt-in Capabilities" section.

---

## 4. Thinking Token Specification

User ask: "thinking toggle but if model thinks then we stream it and show it similar to claude code and thinking toggle turns off model's thinking not just front end."

### 4.1 Behavioral contract

- **Toggle ON (default):** provider requests thinking enabled. If model emits thinking tokens, backend streams them via `on_thinking` notification as they arrive. Frontend renders them distinctly (muted style or separate block), above the main response area. When `on_done` fires, the thinking block collapses (or stays pinned to the completed turn as context).
- **Toggle OFF:** provider request includes explicit thinking-disable flag. Model should not emit thinking tokens. Backend does not emit `on_thinking` notifications. If the model emits thinking tokens despite the flag (provider limitation), backend drops them silently AND emits a single `on_warning` the first time per session.
- **Per-session state:** toggle lives on `_ServerAppContext.show_thinking` (already exists). `/thinking` slash command toggles it. Current behavior: frontend hide/show only. New behavior: request-level + frontend streaming.

### 4.2 Provider adapter contract

Each `LLMProvider` implementation in `layer4/llm.py` gains a `thinking_enabled` parameter to `generate_with_tools()`. Provider-specific translation:

| Provider | ON translation | OFF translation | Fallback |
|---|---|---|---|
| OpenRouter | `extra_body={"reasoning": {"enabled": True}}` (current code already does this when api_base contains `openrouter.ai`) | `extra_body={"reasoning": {"enabled": False}}` — **currently the OFF branch silently skips sending the field; must be fixed to explicitly send disabled** | If api_base is an OpenAI-compatible gateway other than `openrouter.ai`, skip (current behavior) |
| Ollama | per-model: `think: true` for reasoning-capable models (DeepSeek-R1, Qwen-reasoning, etc.) | `think: false` (Ollama 0.3.14+). For older versions: no-op silently | No-op for models without think param; log once |
| Future providers | implement per API | implement per API | Fail-safe no-op |

The parameter is advisory for providers that can't control thinking. The per-session single-warning-on-mismatch rule avoids warning spam.

### 4.3 Streaming path — VERIFIED 2026-04-25; SCOPE NARROWED

Verified the actual streaming code in `autocode/src/autocode/layer4/llm.py`:

- **OpenRouter (`_tools_streaming` at `llm.py:1033-1140`):** ALREADY streams reasoning correctly. Two paths interleave:
  - SDK-native: `delta.reasoning` field is read at line 1068 and `on_thinking_chunk` fires per chunk.
  - Tag-based: `<think>` and `</think>` are detected per chunk at lines 1078-1107 with an `in_think_tag` state flag; chunks before/after the tag boundary route correctly to `on_chunk` vs `on_thinking_chunk`.
  - **No work needed** for OpenRouter streaming. Already correct.
- **Ollama (`generate_with_tools` at `llm.py:721-749`):** BATCHED. Calls `_parse_think_tags()` on `raw_content` AFTER the full response arrives, then calls `on_thinking_chunk(reasoning)` ONCE with the entire reasoning text.
  - **This is the S-THINK-B target.**

S-THINK-B scope narrows to **Ollama only**. Reuse the same state-machine pattern OpenRouter already implements at lines 1078-1107 (in_think_tag flag + chunk partitioning at tag boundaries). Move that logic into a shared helper so both providers (and any future Anthropic/OpenAI direct path) share one implementation.

```python
# Pseudocode mirroring OpenRouter's existing logic, refactored to a shared helper:
class StreamingThinkTagParser:
    def __init__(self):
        self.in_think_tag = False
    def feed(self, text: str) -> tuple[str, str]:
        """Returns (content_chunk, thinking_chunk) for this text."""
        # mirrors llm.py:1078-1107
```

**Edge case** (applies to both providers when using tag-based parsing): if `<think>` or `</think>` is split across two streamed chunks (e.g., chunk N ends with `<thi`, chunk N+1 starts with `nk>...`), the `if "<think>" in text` check fails in chunk N and the partial tail leaks to `on_chunk`. Fix: buffer the last 8 bytes of any chunk that ends with a `<` if no closing `>` was seen, and prepend to the next chunk before the tag check.

OpenRouter SDK reasoning streaming via `delta.reasoning` doesn't have this edge case (the SDK presents reasoning as a separate field); only the tag-based fallback path needs the buffer.

### 4.4 Frontend contract (out of scope for backend, but noted)

Frontend renders `on_thinking` in a distinct visual channel (dimmed text, italic, collapsed by default after `on_done`). The frontend work itself is HR-5 Phase C territory; backend's job is to emit structured, transport-safe thinking events in order.

### 4.5 Tests

- Layer A: unit test for `LLMProvider.generate_with_tools(thinking_enabled=False)` — assert param propagation.
- Layer B: transport-parametrized contract test — assert `on_thinking` ordering when toggle ON, absence when toggle OFF.
- Layer C: live PTY smoke on a provider that supports thinking — verify streaming visibility.

### 4.6 Exit criteria

- User can `/thinking off` and see a measurable token-budget reduction on the next turn.
- Thinking tokens render in the TUI as they stream, not just at the end.
- Providers that can't honor toggle log once per session and continue.

---

## 5. Cost Limits Specification (warn + continue)

User chose warn + continue. The final S-COST design is Tier B from
`docs/research/cost-display-comparative-analysis.md`: balanced display,
cache-aware accounting, and no cross-session rollup yet.

### 5.1 Behavioral contract

- Backend accumulates per-session cost via `TokenTracker` forwarding real
  provider usage into `CostDashboard`.
- Threshold configured via `AutoCodeConfig.agent.cost_limit_usd` (default: unset → no limit; user must opt in).
- When accumulated cost crosses the threshold mid-session: emit a single `on_warning` with the current total and the threshold. Continue execution.
- Warning content: `"Session cost limit reached: $X.XXXX / $Y.YYYY threshold. Continuing; use /cost to view."`
- Cache reads are tracked separately from uncached prompt tokens. OpenRouter
  provider usage captures `prompt_tokens_details.cached_tokens`; Ollama records
  cached reads as zero.
- `/cost` shows real session spend, tokens, turns, input/output split,
  provider/model, cache hit ratio when present, and threshold progress when set.
- `/cost --detail` adds per-provider/model totals and estimated cache savings.
- No hard abort in this slice. Hard-abort is a separate future slice.

### 5.2 Tests

- Layer A: `CostDashboard.check_limit(...)`, cache accounting, cache savings,
  cache hit ratio, and `TokenTracker.record(..., cached_input_tokens=...)`.
- Layer A: OpenRouter/Ollama usage extraction, `/cost`, and `/cost --detail`.
- Layer B: backend chat emits a single `on_warning` when threshold crossed
  (not repeated every subsequent turn unless threshold is raised and re-crossed).

### 5.3 Exit criteria

- User can set `cost_limit_usd: 5.00` in config; receives a visible warning on first crossing; execution continues normally.
- No warning spam: second and subsequent turns over threshold emit no additional warnings (unless threshold is raised and re-crossed).
- `/cost` no longer uses message-character heuristics; it reads from
  `CostDashboard`.

---

## 6. Slice Catalog (Execution Order)

Each slice below follows Codex's TDD Red → Green → Refactor order.

### Stage 1 — Transport/Chat Conformance

**S-THINK-A — Thinking toggle plumbing + bidirectional provider flag (P0 #5a, user-clarified)**
- **Scope:** propagate `_show_thinking` from `_ServerAppContext` → `BackendServer` → `ChatHost` → `AgentLoop.run()` → `provider.generate_with_tools(reasoning_enabled=X)`. Update both providers so the OFF branch explicitly sends the disable flag (OpenRouter: `extra_body["reasoning"] = {"enabled": False}`; Ollama: `think: false` in request body for 0.3.14+). Single `on_warning` per session when provider can't honor the toggle.
- **Files:** `autocode/src/autocode/layer4/llm.py` (both provider `generate_with_tools` implementations), `autocode/src/autocode/agent/loop.py` (accept + pass through), `autocode/src/autocode/backend/chat.py` (read `host._show_thinking`), `autocode/src/autocode/backend/server.py` (expose `_show_thinking` on ChatHost protocol), `docs/reference/rpc-schema-v1.md` (document toggle contract).
- **Tests:** `test_llm.py::test_openrouter_reasoning_flag_bidirectional`; `test_llm.py::test_ollama_think_param_bidirectional`; `test_backend_chat.py::test_show_thinking_propagates_to_provider`.
- **Exit:** measurable token reduction on `/thinking off` for reasoning-capable models; no warning spam; toggle state round-trips through the stack.
- **Priority:** HIGHEST (user-named).

**S-THINK-B — Streaming-aware thinking parser, Ollama-only target (P0 #5b, narrowed 2026-04-25)**
- **Scope:** §4.3 verified — OpenRouter streaming already implements both `delta.reasoning` SDK-field streaming AND `<think>` tag state machine at `llm.py:1068-1107`. **S-THINK-B is Ollama-only.** Replace `_parse_think_tags` post-hoc parse at `llm.py:721-749` with a streaming state machine that mirrors OpenRouter's existing pattern. Extract the tag-parsing logic into a shared helper module so both providers (and any future direct Anthropic/OpenAI path) share one implementation. Add the partial-tag-tail buffer (§4.3) to fix the chunk-split edge case in BOTH providers' tag-based paths.
- **Files:** new `autocode/src/autocode/layer4/thinking_parser.py` (shared helper with the `StreamingThinkTagParser` class), `autocode/src/autocode/layer4/llm.py` (Ollama path uses helper; OpenRouter tag-based fallback uses the helper too — replaces inline logic at lines 1078-1107 with the helper call to dedupe).
- **Tests:** `test_thinking_parser.py::test_tag_split_across_chunks`; `test_thinking_parser.py::test_nested_text_routing`; `test_thinking_parser.py::test_unclosed_tag_emits_on_done`; `test_backend_chat.py::test_on_thinking_interleaved_with_on_token` (parametrized across stdio + TCP).
- **Exit:** Ollama thinking tokens appear in the TUI as the model generates them (not as a batch at turn end). OpenRouter behavior unchanged in observable output but its tag-fallback path now uses the shared helper. Tag-split edge case test passes for both providers.
- **Priority:** HIGH (depends on S-THINK-A for the provider flag plumbing).

**S-POSTTOOL — PostToolUse hook firing audit (P0 #6)**
- **Scope:** Verify `_fire_post_tool_use` method exists and is called after every tool exec. Add if missing.
- **Files:** `autocode/src/autocode/agent/loop.py`, `autocode/src/autocode/agent/hooks.py` (if new fire method needed).
- **Tests:** `test_agent_loop.py::test_post_tool_use_hook_fires` — register a PostToolUse hook, run a tool, assert hook invoked with tool_name + result.
- **Exit:** `settings.json` PostToolUse entries run. Documented in `rpc-schema-v1.md` if observable.

**S-TOKENCAL — Provider-based token counting (P1 #12)**
- **Scope:** Where available, call `provider.count_tokens()` instead of `len(text) // 4`.
- **Files:** `autocode/src/autocode/agent/context.py`; `autocode/src/autocode/layer4/llm.py` already exposes provider `count_tokens()` methods.
- **Tests:** `test_context_engine.py::test_count_tokens_uses_provider_when_available`.
- **Exit:** Context engine uses provider counts when provider supports it; falls back to heuristic otherwise.

### Stage 2 — Tasks/Todo/Loop

**S-INPROGRESS — Task `in_progress` state lifecycle (P0 #4)**
- **Scope:** `update_task` tool accepts `status: "in_progress"`; emits `on_task_state`. Agent-loop convention: when a task's first action begins, transition to `in_progress`. **Rust frontend already supports this status** — `view.rs:899 status_icon()` matches `"in_progress"` to "⏳" today (verified 2026-04-25). This slice is Python-only.
- **Files:** `autocode/src/autocode/agent/task_tools.py`, `autocode/src/autocode/session/task_store.py`, `autocode/src/autocode/agent/prompts.py` (document the state in system prompt so the LLM uses it).
- **Tests:** `test_task_tools.py::test_in_progress_transition`; transport-parametrized `on_task_state` assertion.
- **Exit:** TUI shows pending → in_progress → completed; no backward transitions.
- **Status 2026-04-25:** Complete. `update_task` status schema lists the lifecycle values, generic task status updates record history and reject backward movement, stale `plan.sync` markdown skips backward transitions instead of crashing, prompt guidance requires `in_progress` before the first concrete action, and stdio/TCP conformance covers `update_task` emitting `on_task_state` with `in_progress`.

**S-INTERRUPT — Tool interruption honoring `interruptible` flag (P2 #17)**
- **Scope:** When user cancels a turn, tools with `interruptible=True` get a cooperative cancellation signal (asyncio `CancelledError`); tools with `interruptible=False` run to completion.
- **Files:** `autocode/src/autocode/agent/loop.py` (handle_cancel wiring), `autocode/src/autocode/agent/tools.py` (cancellation plumbing).
- **Tests:** `test_agent_loop.py::test_cancel_interrupts_interruptible_tools`.
- **Exit:** Long-running `run_command` cancellation works cleanly; `write_file` completes if in-flight.
- **Status 2026-04-25:** Complete. `AgentLoop` awaits coroutine tool handlers, persists `cancelled` status for interruptible tool cancellation, shields non-interruptible coroutine tools until completion, and the default `run_command` handler now uses an async sandbox subprocess path so cancellation can terminate the process group with SIGKILL fallback if needed.

### Stage 3 — Context/Memory

**S-CLEAR-RESULTS — Expose tool-result clearing primitive to the agent (P0 #1, renamed from S-CACHE)**
- **Scope:** `ToolResultCache` is designed as a **prompt-pressure-relief primitive** (verified 2026-04-24 via `tool_result_cache.py:1-23` docstring), not execution memoization. This slice exposes the clear primitive to the LLM so it can prune stale tool results from its own context. Add two agent tools: `clear_tool_result(id|tool|age|all)` and `list_tool_results()`. Update system prompt so the agent knows to use them when context is tight.
- **Files:** `autocode/src/autocode/agent/tools.py` (new handlers), `autocode/src/autocode/agent/prompts.py` (system prompt guidance), `autocode/src/autocode/agent/tool_result_cache.py` (already built; expose on BackendServer ToolRegistry).
- **Tests:** `test_tool_result_cache.py::test_clear_by_tool_name`, `test_tool_result_cache.py::test_list_returns_current_entries`, `test_backend_chat.py::test_clear_tool_result_tool_is_exposed`.
- **Exit:** agent can list + selectively drop tool results via tool calls; cache populated when tools run with results over a size threshold.
- **Config:** `agent.tool_result_cache_enabled: bool` (default True). Max entries / max bytes already tunable on `ToolResultCache`.
- **Status 2026-04-25:** Complete. `list_tool_results` and `clear_tool_result` are core-visible agent tools when the cache is enabled, the old `clear_tool_results` compatibility tool remains available, `AgentLoop` records successful non-cache-management tool outputs above the size threshold, backend and TUI loop factories pass the same cache instance through to execution, and the system prompt tells the model when to inspect/prune stale tool output.
- **Note:** Tool-call **memoization** (original S-CACHE plan — skip execution on cache hit) is now in Non-Goals §10. Invalidation risk for file-reading tools is nontrivial and warrants its own slice later.

**S-SEARCHRES — ContextAssembler consumes search_results (P0 #2)**
- **Scope:** The `search_results` parameter on `ContextAssembler.assemble()` is currently accepted but ignored. Wire it into section building with a `search` token budget.
- **Files:** `autocode/src/autocode/core/context.py`.
- **Tests:** `test_context.py::test_search_results_appear_in_assembled_context`.
- **Exit:** When `search_code` runs, results feed subsequent prompts until context flushes.
- **Status 2026-04-25:** Complete by existing implementation, verified during Stage 3 follow-through. `ContextAssembler.assemble(search_results=...)` emits `## Relevant Code` entries with file ranges, language fences, match type, and score under the search budget; `backend.chat` passes `HybridSearch.search()` results into the assembler on Layer 2 semantic-search routes. Validation: `uv run pytest autocode/tests/unit/test_context.py autocode/tests/unit/test_l2_wiring.py -q` -> `17 passed`; `uv run pytest autocode/tests/unit/test_backend_chat.py -q` -> `5 passed`. Artifact: `autocode/docs/qa/test-results/20260425-153728-s-searchres-verification.md`.

**S-MEMPERSIST — SessionConsolidator.gather() → MemoryStore persist (P0 #3)**
- **Scope:** `SessionConsolidator.gather()` currently returns learnings without saving. Add a persist step that routes through `MemoryStore.save()` with dedup.
- **Files:** `autocode/src/autocode/session/consolidation.py`, `autocode/src/autocode/agent/memory.py` (verify save-with-dedup contract).
- **Tests:** `test_consolidation.py::test_gathered_learnings_are_persisted`.
- **Exit:** Memories actually appear in SQLite after session end.
- **Status 2026-04-25:** Complete. `SessionConsolidator.run(..., memory_store=..., session_id=...)` now persists pruned durable learnings through `MemoryStore.save()` while preserving the old non-persistent path when no store is supplied. `ConsolidationResult` reports `memories_saved` and `memory_ids`; durable-memory filtering uses `should_promote_to_durable()` and maps consolidation categories into `MemoryStore` categories. Production wiring follow-up is also complete: `BackendServer._teardown_agent_resources()` runs deterministic consolidation over `SessionStore.get_messages_with_tool_calls()` before the existing LLM-based `MemoryStore.learn_from_session()` enrichment path. Artifacts: `autocode/docs/qa/test-results/20260425-154142-s-mempersist-verification.md`, `autocode/docs/qa/test-results/20260425-164044-s-mempersist-wire-verification.md`.

**S-PRIORITY — Context priority thresholding (P1 #9)**
- **Scope:** When a context section exceeds its budget, reduce proportionally instead of keep-all. E.g., if `rules` budget is 300 tokens but actual rules are 600, truncate to 300 (not include all 600).
- **Files:** `autocode/src/autocode/core/context.py`.
- **Tests:** `test_context.py::test_section_respects_budget`.
- **Exit:** Total assembled prompt stays within budget under pressure.
- **Status 2026-04-25:** Complete by existing implementation, with explicit regression coverage added. `ContextAssembler` scales `_BUDGET` allocations, truncates scalar sections with `_truncate(..., self._allocations[section])`, formats `search_results` under the search allocation, and applies a final overall budget cap. Artifact: `autocode/docs/qa/test-results/20260425-164452-s-priority-verification.md`.

**S-MEMROBUST — Memory extraction JSON robustness (P1 #10)**
- **Scope:** Replace fragile `[...]` string match in `learn_from_session` with structured provider JSON request (`provider.generate_json(schema=...)`).
- **Files:** `autocode/src/autocode/agent/memory.py`.
- **Tests:** `test_memory.py::test_learn_from_session_with_preamble` (LLM response with prefix doesn't break parsing).
- **Exit:** Extraction robust to LLM preamble/postamble.
- **Status 2026-04-25:** Complete. `MemoryStore.learn_from_session()` now scans model text for the first syntactically valid JSON array instead of trusting the first `[` and last `]`; malformed bracketed prose before the memory array no longer breaks extraction. Artifact: `autocode/docs/qa/test-results/20260425-164800-s-memrobust-verification.md`.

**S-TRUNCATE — Adaptive tool-result truncation (P2 #14)**
- **Scope:** Replace fixed head/tail (60/40, 500 tokens) with content-structure-aware truncation. For code output: keep function signatures + error markers + tails. For list output: keep first N + "... X more" + last N. Honor `ToolDefinition.output_budget_tokens` per tool.
- **Files:** `autocode/src/autocode/agent/context.py` or new `agent/truncation.py`.
- **Tests:** `test_truncation.py::test_code_truncation_preserves_signatures`.
- **Exit:** Long tool outputs remain informative after truncation. Per-tool budgets honored.
- **Status 2026-04-25:** Complete. `ContextEngine.truncate_tool_result()` now uses adaptive micro-compaction: code/error-like outputs preserve function/class signatures and traceback/error markers, list-like outputs preserve first/last logical records with a line-omission marker, and dense unstructured output keeps the prior middle-char fallback. `AgentLoop` now passes each `ToolDefinition.output_budget_tokens` value into truncation, while task tools remain exempt to avoid corrupting task-state payloads. Artifact: `autocode/docs/qa/test-results/20260425-165646-s-truncate-verification.md`.

**S-L1L2PREVIEW — L1 iteration-zero symbol preview (P2 #18, tightened 2026-04-24)**
- **Scope:** Entry 1377 explicitly defers Layer 2 warmup on iteration zero. This slice adds ONLY a cheap L1 symbol preview for files **already in the active working set** (no filesystem scan, no new tree-sitter parses of cold files, no repomap generation — those are what Entry 1377 fixed). Reuse the existing tree-sitter mtime-LRU cache. Bounded: **max 5 files × max 10 symbols each × max 200 tokens total**, wrapped in a **100ms soft deadline**; if the deadline trips, the preview is skipped and the snapshot continues without it. No repomap in this slice.
- **Files:** `autocode/src/autocode/agent/loop.py` (snapshot builder extended with L1 preview call), `autocode/src/autocode/layer1/symbols.py` (or a new helper that reads cached parses only).
- **Tests:** `test_agent_loop.py::test_bootstrap_includes_l1_preview_for_active_files` (happy path); `test_agent_loop.py::test_bootstrap_skips_l1_preview_on_deadline` (deadline enforcement).
- **Exit:** First turn sees cheap symbol summary **only** from already-cached parses; no regression in first-turn latency from the Entry 1377 baseline (`3257ms` on `hello`).
- **Explicitly out of scope:** repomap generation (Entry 1377 fix retained), cold-file parse, filesystem scan.
- **Status 2026-04-25:** Complete. The iteration-zero workspace bootstrap now appends an `Active symbol preview` only for files already in the active working set and only when their Layer 1 parse is already present in the shared mtime-LRU parser cache. The preview builder never calls `parse()`, is bounded to 5 files / 10 symbols per file / 200 tokens, and skips on an expired preview budget; `AgentLoop` also wraps it in an outer 100ms daemon-thread soft timeout to satisfy R5. Deterministic Layer 1 query handling now uses the shared parser so an explicit `list_symbols`/definition query can warm the cache for a later bootstrap without forcing cold parses. Artifact: `autocode/docs/qa/test-results/20260425-171054-s-l1l2preview-verification.md`.

### Stage 4 — Host Hygiene

**S-BLOCKED — `is_blocked` coverage expansion (P0 #7)**
- **Scope:** `ApprovalManager.is_blocked()` currently scans `run_command` args only. Extend to also scan `write_file`, `edit_file`, `apply_patch` args for dangerous path patterns (writing to `/etc/`, `/boot/`, etc.) and dangerous content patterns (rm-rf-style embedded in scripts).
- **Files:** `autocode/src/autocode/agent/approval.py`.
- **Tests:** `test_approval.py::test_write_file_blocks_dangerous_paths`.
- **Exit:** Write-tools scanned; blocked patterns documented in config.
- **Status 2026-04-25:** Complete. `ApprovalManager.is_blocked()` now hard-blocks dangerous write targets for `write_file`, `edit_file`, and each `apply_patch` operation before approval prompting or handler execution. It also scans write content (`content` / `new_string`) for destructive script patterns such as `rm -rf`, `mkfs`, `dd if=`, fork bombs, and recursive chmod/chown forms. `apply_patch` is included in read-only mutating-tool blocking. Artifact: `autocode/docs/qa/test-results/20260425-190420-s-blocked-verification.md`.

**S-CKPTMSG — Checkpoint includes message history (P1 #11)**
- **Scope:** `CheckpointStore.save_checkpoint()` currently persists task DAG only. Extend to also persist compressed message history (last N turns + a summary). Restore populates both.
- **Files:** `autocode/src/autocode/session/checkpoint_store.py`, `autocode/src/autocode/backend/services.py` (checkpoint restore path).
- **Tests:** `test_checkpoint_store.py::test_restore_rehydrates_messages`.
- **Exit:** `/checkpoint save` + `/checkpoint restore` preserves both task state and conversational context.
- **Status 2026-04-25:** Complete. Checkpoints now store a bounded message snapshot (`captured`, summary, and recent messages) alongside the task DAG. `SessionStore.snapshot_messages()` attaches assistant tool-call rows, and `SessionStore.restore_messages_snapshot()` replaces durable messages/tool calls during checkpoint restore before injecting the restore marker. The slash-command save path now passes the active `SessionStore`, and transport conformance covers `checkpoint.restore` through both stdio and TCP. Artifact: `autocode/docs/qa/test-results/20260425-193136-s-ckptmsg-verification.md`.

**S-COST — Per-session cost limit (warn+continue) (P2 #16)**
- **Scope:** §5 spec plus Tier B from `docs/research/cost-display-comparative-analysis.md`. Threshold logic lives in `CostDashboard`; `TokenTracker.record()` forwards real provider usage and cached-token metadata; `/cost` reads real dashboard totals instead of estimating from message characters.
- **Files:** `autocode/src/autocode/agent/cost_dashboard.py` (threshold check, cache-aware token/cost accounting, cache savings, provider/model aggregation), `autocode/src/autocode/agent/token_tracker.py` (cached-token passthrough and one-shot warning storage), `autocode/src/autocode/layer4/llm.py` (OpenRouter cached-token capture, Ollama zero-cache usage), `autocode/src/autocode/agent/loop.py` (records `cached_input_tokens`), `autocode/src/autocode/config.py` (`agent.cost_limit_usd: float | None`; default unset), `autocode/src/autocode/backend/chat.py` (emit `on_warning` when threshold first crosses), `autocode/src/autocode/app/commands.py` (`/cost` + `/cost --detail` real-number output), `autocode/src/autocode/tui/app.py` (passes cost limit into shared factory).
- **Tests:** `test_cost_dashboard.py::{test_check_limit_unset_never_fires,test_check_limit_fires_once_until_threshold_raised_and_re_crossed,test_record_with_cached_input_tokens,test_estimated_cache_savings_calculation,test_cache_hit_ratio_zero_when_no_input}`; `test_token_counting.py::test_record_forwards_cached_tokens_to_dashboard`; `test_llm.py::TestProviderUsageCapture`; `test_commands.py::TestHandleCost`; `test_backend_chat.py::{test_cost_warning_emitted_once_per_session,test_cost_warning_includes_total_and_threshold}`; backend live-path regressions in `test_backend_server.py`; provider/model cost grouping in `test_agent_loop.py`.
- **Status 2026-04-25:** Complete from builder side. Final focused/backend regression: `329 passed`; full unit suite: `1955 passed`; touched-file Ruff and `git diff --check` are clean. Live PTY smoke on `uv run autocode --mode inline` passed `/cost`, `/cost --detail`, and a `cost_limit_usd: 0.001` threshold crossing through the current working-tree backend. Repo-wide `make lint` still fails on pre-existing unrelated lint debt. Artifact: `autocode/docs/qa/test-results/20260425-212558-s-cost-verification.md`.
- **Exit:** User sets limit; sees single warning on crossing; execution continues. Second+ crossings in the same session are silent unless threshold is raised and re-crossed. `/cost` and `/cost --detail` display real cache-aware session accounting.

**S-EPISODESUM — Episode summarization mercy rule (P2 #19)**
- **Scope:** Before the `max_episodes_per_session` retention cap purges old SQLite episodes and their `episode_events`, generate a deterministic non-LLM `episode_events.event_type == "summary"` row inside a synthetic summary episode. Hook point is `_enforce_retention()` at `episode_store.py:130`. Avoids total loss of older training/event history on long sessions.
- **Important constraint:** `_enforce_retention()` stays synchronous on the episode-start path. An LLM-based summary here would block the event loop on every retention crossing. **First cut: deterministic non-LLM summary** — event-type counts plus `ts_range` and `n_collapsed`. Cheap, deterministic, no LLM dependency. LLM-based richer summarization is a future follow-up that requires moving retention to an async background worker.
- **Files:** `autocode/src/autocode/session/episode_store.py` (adds `_summarize_tranche(events)`, summary-ratio cap helpers, and summary-before-delete retention flow).
- **Tests:** `test_episode_store.py::TestSummarization::{test_enforce_retention_summarizes_oldest_tranche,test_summary_event_schema,test_recursion_cap_drops_oldest_summary,test_retention_synchronous,test_zero_events_noop,test_retention_below_bound_noop}` plus updated `test_retention_enforcement`.
- **Status 2026-04-25:** Complete from builder side. Focused RED run failed 4 expected summarization/cap tests against old code, then GREEN after implementation. Final focused: `13 passed`; adjacent session/agent loop: `68 passed`; full unit: `1961 passed`; touched-file Ruff and `git diff --check` are clean. Live surface is not exposed yet, so verification used a temp SQLite plumbing smoke through the real `EpisodeStore.start_episode()` path and confirmed one stored summary event with exact payload keys. Artifact: `autocode/docs/qa/test-results/20260425-233457-s-episodesum-verification.md`.
- **Exit:** Long sessions retain summarized episode history beyond the episode cap. Retention path stays synchronous and fast (no LLM dependency).
- **Note:** The summary episode itself counts toward `max_episodes`. To prevent infinite summary nesting, retention skips creating a new summary when more than 50% of remaining events are already summaries and drops the oldest summary episode instead.

### Parallel — Documentation + Decision

**S-L3DOC — Layer 3 opt-in decision record**
- **Scope:** §3 decision, corrected by S-L3DOC pre-read and Claude Entry 1482: Layer 3 is not unreachable; `BackendServer` can select it when `config.layer3.enabled`, the `layer3` optional extra is installed, and the request router classifies a simple edit. Core installs leave it dormant via graceful ImportError fallback. Add an opt-in/experimental docstring to `layer3/provider.py` that states this honestly, and treat any future broadening as a separate tranche requiring architecture docs and provider/route/integration tests.
- **Files:** `autocode/src/autocode/layer3/provider.py`, `modular_migration_todo.md`, `docs/features/features_behavior.md`, `docs_summaries/02_runtime_architecture_and_backend.md`.
- **Tests:** None (doc-only).
- **Status 2026-04-26:** Complete from builder side after Claude Entry 1482 correction. `provider.py` now has an opt-in local constrained-generation docstring, file-local mypy issues were cleaned up, and the runtime inventory / architecture summary / modular todo now describe Layer 3 as optional-extra gated. Validation: provider Ruff clean, provider mypy clean, `test_l3_provider.py` `5 passed`, and `pytest -q -k layer3` deselected all tests as expected. Artifact: `autocode/docs/qa/test-results/20260426-001202-s-l3doc-verification.md`.
- **Exit:** Future readers encounter clear opt-in status + activation contract.

**S-DOCSREFRESH — Stale docs refresh**
- **Scope:** Refresh or mark-historical every stale doc. User said "all docs."
- **Sub-slices:**
  - `S-DOCSREFRESH-A`: `docs/requirements_and_features.md` — full sync to post-modularization reality. Complete as of 2026-04-26.
    - `A.1` Section 2 feature catalog/current launch surface — complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-065412-s-docsrefresh-a1-verification.md`.
    - `A.2` Section 5 Go-TUI decision demotion + Section 7 technology stack refresh — complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-072434-s-docsrefresh-a2-verification.md`.
    - `A.3` Phase-5 naming disambiguation for legacy Universal Orchestrator vs modular Phase 5 — complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-072956-s-docsrefresh-a3-verification.md`.
    - `A.4` cross-reference/link audit after A.1-A.3 — complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-083440-s-docsrefresh-a4-verification.md`.
  - `S-DOCSREFRESH-B`: `docs/architecture.md` — sync current entrypoints (Rust TUI primary, Python `--tui`/`--legacy` fallbacks only, TCP transport documented). Complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-084544-s-docsrefresh-b-verification.md`.
  - `S-DOCSREFRESH-C`: `PLAN.md` — audit for stale sections; mark-historical any superseded phase; add pointer to `backend-feature-improvement-plan.md`. Complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-085127-s-docsrefresh-c-verification.md`.
  - `S-DOCSREFRESH-D`: `EXECUTION_CHECKLIST.md` — align with active tranche; move completed items to a historical-done section. Complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-085516-s-docsrefresh-d-verification.md`.
  - `S-DOCSREFRESH-E`: `current_directives.md` — add "Backend Feature Improvement Tranche" section pointing to this plan; note HR-5 Phase B deferred to post-backend-tranche completion. Complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-085932-s-docsrefresh-e-verification.md`.
  - `S-DOCSREFRESH-F`: `autocode/TESTING.md` — align commands with current state, add backend live-PTY smoke rules, and update stale benchmark/scenario paths. Complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-093101-s-docsrefresh-f-verification.md`.
  - `S-DOCSREFRESH-G`: Archive clearly superseded `docs/plan/*.md` files to `docs/plan/archive/` and retarget live references. Complete as of 2026-04-26. Artifact: `autocode/docs/qa/test-results/20260426-094558-s-docsrefresh-g-verification.md`.
- **Files:** listed per sub-slice.
- **Tests:** Ensure no broken intra-repo links after refresh (`markdown-link-check` or equivalent).
- **Exit:** A reader arriving on any top-level doc gets a current picture, not a 2026-02-17 snapshot.
- **Ordering:** Can run in parallel with Stage 1-4 work. Sub-slice A is the biggest lift; do it first.

---

## 7. Per-Stage Exit Gates

Each stage must pass BOTH:

1. **Regression gate:**
   - `uv run pytest autocode/tests/unit -q` → all green
   - `uv run pytest benchmarks/tests -q` → all green
   - `cargo test --manifest-path autocode/rtui/Cargo.toml -q` → all green
   - `cargo clippy --manifest-path autocode/rtui/Cargo.toml -- -D warnings` → passed
   - `cargo build --release --manifest-path autocode/rtui/Cargo.toml` → passed
   - `python3 autocode/tests/pty/pty_smoke_rust_m1.py` → passed
   - `python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py` → passed
   - 2026-04-26 local deterministic closeout artifact: `autocode/docs/qa/test-results/20260426-095259-backend-tranche-regression-gate.md`

2. **Stage-specific contract coverage:**
   - Stage 1: transport-parametrized test for thinking ordering (ON vs OFF) is green.
   - Stage 2: `on_task_state` with `in_progress` transition is green on both stdio and TCP.
   - Stage 3: transport-parametrized cache-hit + context-with-search + persisted-memory contracts are green.
   - Stage 4: transport-parametrized cost-warning + checkpoint-roundtrip contracts are green.

Per-slice exit: its named test passes AND the per-slice verification artifact is stored under `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<slice-id>-verification.md`.

---

## 8. Overall Tranche Exit Gate

This tranche is complete when:

1. All 17 slices (16 feature + 1 L3 decision) + all 7 doc-refresh sub-slices land with per-slice artifacts.
2. Local deterministic regression gate is green on the current tree (§7.1). Complete as of 2026-04-26 via `autocode/docs/qa/test-results/20260426-095259-backend-tranche-regression-gate.md`.
3. Transport conformance coverage has grown from the current session/command/status seed to cover: chat lifecycle (incl. thinking), task state (incl. in_progress), cache behavior, context assembly, memory persistence, cost warning, checkpoint roundtrip.
4. `docs/requirements_and_features.md` accurately reflects 2026-04-25+ reality (no more 2026-02-17 drift).
5. A live PTY canary run on bare `autocode` with thinking ON + thinking OFF + a long tool sequence + a cost-limit crossing all behave per their specs.
6. HR-5 Phase B (`/cc` real-data binding) can resume with a clean backend handoff. Ready as of the local deterministic gate; run the live PTY canary before broad sweeps.

---

## 9. Delegation Protocol

- **Execution:** Codex (Builder). One slice at a time. Each slice opens with a pre-task intent in `AGENTS_CONVERSATION.MD` and closes with a task handoff + verification artifact.
- **Review:** Claude reviews each slice. Verdict posted in comms.
- **Commit:** User commits after each approved slice OR at stage boundaries — never autonomously.
- **Order:** See §6. Recommended tranche order:
  1. **Slice group A (Stage 1):** S-POSTTOOL → S-TOKENCAL → S-THINK-A → S-THINK-B. (S-POSTTOOL first as the smallest hook-path change; validates the slice pattern before the thinking work.)
  2. **Slice group B (Stage 2):** S-INPROGRESS → S-INTERRUPT.
  3. **Slice group C (Stage 3):** S-CLEAR-RESULTS → S-SEARCHRES → S-MEMPERSIST → S-PRIORITY → S-MEMROBUST → S-TRUNCATE → S-L1L2PREVIEW.
  4. **Slice group D (Stage 4):** S-BLOCKED → S-CKPTMSG → S-COST → S-EPISODESUM.
  5. **Parallel:** S-L3DOC (any time) and S-DOCSREFRESH-A → G (start in parallel with Group A, complete by end of Group D).
- **Parallelism:** within a stage group, slices can potentially be bundled into one slice if they touch the same files AND pass the same test gate without a bigger blast radius. Default is one-at-a-time for reviewability.

---

## 10. Non-Goals / Deferred

- **Subagent deep work** — permission enforcement (P1 #8), scheduler fairness (P1 #13). Re-open after HR-5 Phase B (`/cc`).
- **Cross-session memory promotion** (P2 #15). Post-v1.
- **Hard-abort cost limits.** This tranche ships warn+continue only.
- **L3 Layer wiring.** §3 decision.
- **Tool-call execution memoization.** Original S-CACHE plan (skip execution on `(tool, args_hash)` cache hit) is deferred. Invalidation risk for file-reading tools (mtime check) is nontrivial. Revisit post-tranche with a dedicated design. The in-scope S-CLEAR-RESULTS slice handles prompt-pressure relief via selective clearing, which is what `ToolResultCache` was designed for.
- **Architecture cleanup items that live in `modular_migration_todo.md` "Phase 2-4 Follow-through"**: those are governed by that plan, not this one. Examples: `ChatHost` narrowing, `pty.rs` rename + stderr capture, `ChildGuard` dead scaffolding cleanup.

---

## 11. Open Questions That Emerged During Planning

Questions that may surface during Codex's execution; user answers needed:

1. **Thinking mode default** — default to ON (verbose) or OFF (token-saving)? I recommend **ON by default** since it matches Claude-Code-style UX and the user specifically asked for that visibility.
2. **Cost limit default** — config default unset (no limit) or ship a non-zero safety default (e.g., `$10.00`)? I recommend **unset default**; opt-in only.
3. **Tool result cache TTL** — current 10 minutes. Is that right for sessions that can run for hours? Recommend extend to **session lifetime** (invalidate on `session.resume` / `session.new`) OR keep 10min. User call.
4. **Docs refresh depth** — for `PLAN.md` (a huge doc), full rewrite or section-by-section? Recommend **section-by-section**; full rewrite would lose historical decisions.
5. **L1 preview budget** — how many tokens of symbol preview on iteration-zero? Recommend **max 200 tokens**; bounded cheap injection, not a retrieval replacement.

---

## 12. Risk Register

Risks worth a Codex eye during execution. Each lists the slice(s) it threatens, the failure mode, and a mitigation.

| # | Risk | Slices threatened | Failure mode | Mitigation |
|---|---|---|---|---|
| R1 | Streaming-path regression | S-THINK-B | New state-machine breaks tool-call parsing or splits content awkwardly when `<think>` tags appear in legitimate user-pasted content | Snapshot tests of stream → events; preserve current `_parse_think_tags` as a fallback path behind a kill switch for one release |
| R2 | Provider rate-table drift | S-COST | $-cost computed against stale or missing rate entries → false positives or silent under-counting | Verify rate table in `cost_dashboard.py` covers every provider in active config; warn on first call against an unrated provider |
| R3 | Agent-self-clearing footgun | S-CLEAR-RESULTS | LLM clears its own system prompt or current tool-call results mid-turn → reasoning breakdown | Never expose system messages to the clear primitive; guard against clearing the in-flight tool's result |
| R4 | Frontend-state-machine break | S-INPROGRESS | Rust reducer may have hardcoded `pending`/`completed` enum match → introducing `in_progress` panics or renders wrong | **VERIFIED 2026-04-25, RISK NEUTRALIZED.** `model.rs:75` and `protocol.rs:89-99` use `pub status: String` (opaque). `view.rs:899 status_icon()` already handles `"running" | "active" | "in_progress"` → "⏳". Rust frontend is prepared; S-INPROGRESS is Python-only |
| R5 | First-turn latency regression | S-L1L2PREVIEW | L1 preview leaks past 100ms deadline on cold-cache repos → reintroduces Entry 1377 stall | Make deadline enforcement an outer wrapper (`asyncio.wait_for` or thread-pool timeout); regression test against the Entry 1377 baseline (`3257ms` ceiling on `hello`) |
| R6 | Memory test pollution | S-MEMPERSIST | Tests write to project MemoryStore SQLite; later tests see stale entries → flakes | Use `tmp_path` MemoryStore per test; ensure no test writes to user `~/.autocode/memory.db` |
| R7 | Backward-incompat toggle change | S-THINK-A | Users with scripts toggling `/thinking` expect render-only behavior; new behavior changes model output | Document in `rpc-schema-v1.md`; emit `on_warning` (single per session) noting "thinking now controls model behavior" the first time toggle changes after upgrade |
| R8 | Doc refresh stall | S-DOCSREFRESH-A | 476 stale lines is one big PR; review fatigue → blocks tranche exit | Split into A.1 (Section 2 feature catalog; complete), A.2 (historical Go decision / tech stack; complete), A.3 (Phase-5 disambiguation; complete), A.4 (cross-reference audit; complete) |
| R9 | Streaming + cancel interaction | S-INTERRUPT × S-THINK-B | If S-INTERRUPT lands and a streaming `<think>` block is in flight when user cancels, the parser state machine may leak | Add cancellation reset in S-INTERRUPT spec: when CancelledError fires, parser state must reset to OUTSIDE and pending buffer must be flushed |
| R10 | Checkpoint tool-call loss | S-CKPTMSG | Restoring messages without their `tool_calls` table rows means restored sessions look "complete" but lack tool result history | Use `SessionStore.get_messages_with_tool_calls()` for capture; restore must repopulate both tables |
| R11 | Subagent gap re-opens | (out-of-scope this tranche) | If user reprioritizes mid-tranche, partial subagent work creates a half-baked permission system | Preserve `Phase 2-4 Follow-through` items in `modular_migration_todo.md`; do not partially land |
| R12 | L3 opt-in path drift | S-L3DOC | If new code broadens Layer 3 routing without optional-extra/install and integration proof, users hit an unvalidated local-model path | Opt-in docstring + future architecture/integration-test requirement before broadening routed request types |

## 13. Effort Estimates (rough order-of-magnitude)

S = 1-3 days · M = 4-7 days · L = 1-2 weeks. Builder-time, not wall-time.

| Slice | Size | Notes |
|---|---|---|
| S-POSTTOOL | S | Single call site + a hooks test |
| S-TOKENCAL | S | Two call sites; provider check |
| S-THINK-A | M | 5-layer plumbing + bidirectional flag fix |
| S-THINK-B | M | Ollama-only target (OpenRouter already streams reasoning); shared helper extraction + partial-tag-tail fix (R1, R9) |
| S-INPROGRESS | S | New status value + tool transition. Rust audit complete — no Rust changes needed (R4 neutralized) |
| S-INTERRUPT | M | Cancellation propagation + parser reset (R9) |
| S-CLEAR-RESULTS | S | Expose existing API as 2 tools + prompt guidance |
| S-SEARCHRES | S | Consume already-accepted parameter |
| S-MEMPERSIST | S | Add save() call after gather() (R6) |
| S-PRIORITY | M | Proportional reduction logic + tests |
| S-MEMROBUST | S | Replace string parse with `provider.generate_json` |
| S-TRUNCATE | M | Content-aware truncation per type |
| S-L1L2PREVIEW | M | Deadline enforcement + working-set scope (R5) |
| S-BLOCKED | S | Extend pattern check across write tools |
| S-CKPTMSG | M | Checkpoint serialization + tool_calls restore (R10) |
| S-COST | M | Tier B cache-aware cost accounting + warn emission + `/cost` display |
| S-EPISODESUM | M | Summarize-before-purge in `_enforce_retention` |
| S-L3DOC | S | Doc + architecture-guard test (R12) |
| S-DOCSREFRESH-A | M-L | Complete via A.1/A.2/A.3/A.4 per R8 |
| S-DOCSREFRESH-B | S | architecture.md entrypoint sync |
| S-DOCSREFRESH-C | M | PLAN.md section-by-section audit |
| S-DOCSREFRESH-D | S | EXECUTION_CHECKLIST.md alignment |
| S-DOCSREFRESH-E | S | current_directives.md backend section |
| S-DOCSREFRESH-F | S | TESTING.md commands + backend live PTY smoke rules |
| S-DOCSREFRESH-G | S | Archive superseded plan docs — complete |

**Rough tranche total:** ~9 S + ~11 M + ~1 L ≈ 60-100 builder-days. That's ~3-5 weeks of dedicated work. Parallelism (one builder + one reviewer + one user) compresses wall-time to ~2-3 weeks if the slice cadence is 1-2 per day on small slices, ~3-4 days on medium slices.

If the user wants a faster path: ship a **P0-only minimum tranche** first (S-POSTTOOL, S-TOKENCAL, S-THINK-A, S-THINK-B, S-INPROGRESS, S-CLEAR-RESULTS, S-SEARCHRES, S-MEMPERSIST, S-BLOCKED) ≈ ~30 builder-days ≈ 1.5 weeks. P1 + P2 + docs land in a follow-up tranche.

## 14. References

- `docs/features/backend_features.md` — current backend implementation inventory plus missing/planned feature inventory
- `docs/plan/archive/backend-feature-catalog-brainstorm.md` — source brainstorm for this plan
- `docs/plan/backend-tightening-refinement-plan.md` — Codex's method/TDD plan
- `AGENTS_CONVERSATION.MD` Entries 1415, 1417, 1420, 1421 — planning chain
- `docs/reference/rpc-schema-v1.md` — contract doc to update as features land
- `docs/features/features_behavior.md` — post-modularization inventory
- `modular_migration_todo.md` §"Phase 2-4 Follow-through" — architecture cleanup (separate track)
- `docs/tui-testing/tui_implementation_plan.md` — HR-5 Phase B/C (resumes after this tranche)
