# Backend Vision and Usability Spec

> **Status:** ACTIVE companion to `docs/plan/backend-feature-improvement-plan.md`.
> **Purpose:** the existing plan answers WHAT/HOW per slice; this doc answers WHY/UX. Pain points with reproductions, observability targets, per-stage user-visible deltas, new-feature brainstorm, and per-slice keystroke-level acceptance scenarios.
> **Author:** Claude (Reviewer/Architect).
> **Date:** 2026-04-25.
> **Aligns with user direction:** "we need to brainstorm more and have a very concrete and usable backend."

---

## 1. Vision: What a "Complete" AutoCode Backend Feels Like

AutoCode's product peers are Claude Code, Cursor's agent mode, Aider, OpenHands, and Codex CLI. A complete backend should feel **at least as honest, steerable, and observable** as those, while keeping AutoCode's local-first / deterministic-first edge.

The user does four things in this product, in roughly this order of frequency:

1. **Ask + answer** — "what does this code do?" / "where is X used?" / "how do I…"
2. **Edit + verify** — "fix the bug" / "add a test for Y" / "rename X across the repo"
3. **Explore + learn** — "show me how this module is structured" / "what changed since last week?"
4. **Long-form work** — "implement feature Z over the next hour with my supervision"

For each, the backend has a moment-of-truth where it either delights or disappoints.

### 1.1 Ask + answer

- **Should feel:** instant ack ("working…"), thinking visible if model reasons, tokens stream, citations show which files informed the answer.
- **Today:** ack works (Entry 1408); thinking is parsed but not streamed for Ollama (S-THINK-B target); no citations; first-token latency on cold-start is fine post-Entry 1377 fix.

### 1.2 Edit + verify

- **Should feel:** agent says what it'll do, shows a diff, runs tests, shows pass/fail, asks for approval to keep going.
- **Today:** approval works for write tools; diff shown via `git_diff` tool but not auto-shown before write; verification runs tests if asked; no auto-loop of "edit → test → fix → re-test" without user nudge.

### 1.3 Explore + learn

- **Should feel:** L1/L2 retrieval makes the agent feel like it knows the repo; cheap structural answers (find_definition, find_references) are sub-second; semantic search returns relevant files.
- **Today:** L1/L2 are built but **not auto-injected into prompts** — agent has to call `search_code` manually. S-SEARCHRES + S-L1L2PREVIEW address part of this.

### 1.4 Long-form work

- **Should feel:** session can run for hours, memory accumulates, context never fills up unexpectedly, tasks are tracked, checkpoints work, cost stays predictable.
- **Today:** sessions persist; memory accumulates within session (S-MEMPERSIST will close the gather→save gap); compaction at 75% works but loses summary detail; checkpoints save tasks but not messages (S-CKPTMSG target); cost is tracked but no budget cap surfaces (S-COST target).

### 1.5 Where AutoCode could leapfrog

- **Local-first determinism for L1/L2:** Claude Code/Cursor are LLM-only; AutoCode has a deterministic layer they don't. Maximize this.
- **Modular backend:** users can run backend over TCP and connect from any frontend. None of the peers have this.
- **Honest observability:** today the user sees status icons; tomorrow they could see a real cost dashboard, retry rate, layer-routing decisions, memory hit rate. Build the surface.

---

## 2. Current Pain Points (concrete reproductions)

Pain points users hit today. Each lists repro + which slice (if any) addresses it.

### P-1: First-turn stall on cold gateway alias
**Repro:** `OPENROUTER_MODEL=this_alias_does_not_exist autocode`, type `hello`, wait 30s.
**Today:** Fixed by Entry 1408 (BUG-LIVE-003). On_warning fires; visible failure.
**Plan slice:** none needed. Done.

### P-2: Thinking tokens hidden for Ollama reasoning models
**Repro:** Switch to a DeepSeek-R1 / Qwen-reasoning Ollama model, ask a hard question. Thinking arrives all-at-once at end, not streamed.
**Today:** Ollama path batches thinking via post-hoc `<think>` tag parse (`llm.py:721-749`).
**Plan slice:** **S-THINK-B** (in progress).

### P-3: Toggle `/thinking off` doesn't actually disable model thinking
**Repro:** `/thinking off`, ask hard question. Model still reasons (and bills for reasoning tokens) — toggle was render-only.
**Today:** `_show_thinking` controls frontend display only.
**Plan slice:** **S-THINK-A**.

### P-4: Slash menu hides a wedged turn
**Repro:** Submit `hello` against a misconfigured gateway → turn hangs → press `/` → palette opens → original failure invisible.
**Today:** `BUG-LIVE-002` open. **Frontend bug** — `view.rs` overlay-vs-status precedence.
**Plan slice:** OUT OF BACKEND TRANCHE — flagged in Entry 1426 for HR-5 Phase B/C.

### P-5: Tool-result clutter dominates context
**Repro:** Run agent through 10 file-reads + 5 searches in one turn. Next turn's prompt is mostly stale tool output. Compaction kicks in late.
**Today:** `ToolResultCache` has clearing primitive but agent doesn't know to use it.
**Plan slice:** **S-CLEAR-RESULTS** + **S-PRIORITY** + **S-TRUNCATE**.

### P-6: Search results don't auto-feed prompt
**Repro:** Agent runs `search_code("auth flow")`. Result shown to agent in tool result, but `ContextAssembler.search_results` parameter is unused.
**Today:** `core/context.py:84` accepts `search_results` arg, never builds a section from it.
**Plan slice:** **S-SEARCHRES**.

### P-7: Memories extracted but never saved
**Repro:** End a long session, start a new one in same project, reference learned-from-the-old-session conventions. Agent has forgotten.
**Today:** `SessionConsolidator.gather()` returns learnings; no caller writes them to MemoryStore.
**Plan slice:** **S-MEMPERSIST**.

### P-8: Tasks have no `in_progress` state
**Repro:** Create a task with `create_task`. Set status to "in_progress" via `update_task`. Status string doesn't change in any visible way; treated as `pending` until "completed".
**Today:** Tools transition pending→completed; `in_progress` value is allowed but no tool sets it.
**Plan slice:** **S-INPROGRESS**.

### P-9: Cost surprise at end of long session
**Repro:** Long session, agent burns 100K+ tokens. User sees cost only when they `/cost`. No mid-session warning.
**Today:** `token_tracker` accumulates; `cost_dashboard` computes $; no threshold-crossing event.
**Plan slice:** **S-COST**.

### P-10: Backend stderr crashes vanish
**Repro:** Backend Python module fails on import (e.g., bad config). `autocode` shows nothing.
**Today:** `autocode/rtui/src/backend/pty.rs:19` sets `cmd.stderr(Stdio::null())`.
**Plan slice:** OUT — docs/plan/deferred/modular_migration_todo.md "Phase 2-4 Follow-through" item ("preserve backend stderr on the live user path"). NOT in backend feature tranche.

### P-11: Checkpoint restores tasks but not conversation
**Repro:** `/checkpoint save before-experiment` → do experimental work → `/checkpoint restore before-experiment`. Tasks restored. Messages lost.
**Today:** `CheckpointStore.save_checkpoint()` persists task DAG only.
**Plan slice:** **S-CKPTMSG**.

### P-12: PostToolUse hooks declared in settings.json but never run
**Repro:** Add a `PostToolUse` hook to `~/.claude/settings.json`. Run a tool. Hook never fires.
**Today:** Fixed by S-POSTTOOL ✓ (Stage 1, complete).

### P-13: Agent reads same file 5 times in a turn
**Repro:** Agent processes a long task. Re-reads `pyproject.toml` (no changes between reads).
**Today:** `ToolResultCache` exists but doesn't memoize; tool runs each time.
**Plan slice:** **DEFERRED** (memoization → post-tranche per Entry 1423 §10).

### P-14: Long session episodes purge silently
**Repro:** Session > 200 events. Oldest episodes deleted with no trace. User can't reconstruct early decisions.
**Today:** `episode_store.py:130 _enforce_retention()` deletes hard.
**Plan slice:** **S-EPISODESUM**.

### P-15: Token counts are wrong
**Repro:** `provider.count_tokens(text)` returns 7 for a 100-char input on a real tokenizer. Heuristic returns 25. Compaction triggers at wrong time.
**Today:** Fixed by S-TOKENCAL ✓ (Stage 1, complete).

### P-16: Dangerous write through write_file
**Repro:** Agent calls `write_file(path="/etc/passwd", content="…")`. `is_blocked` only scans `run_command`; write goes through approval but not pattern-block.
**Today:** `approval.py:43` only checks `tool_name == "run_command"`.
**Plan slice:** **S-BLOCKED**.

### P-17: Agent hits provider rate limit, fails turn
**Repro:** Burst rapid requests. OpenRouter returns 429. Agent retries with backoff but eventually fails, no fallback.
**Today:** Retry loop in `_is_openrouter_retryable_error` works; no provider failover.
**Plan slice:** **NEW — surfaced in §5 backlog** (provider failover).

### P-18: User updates AGENTS.md mid-session, agent doesn't see change
**Repro:** Edit `AGENTS.md` while session is running. Continue conversation. Agent uses old instructions.
**Today:** `_memory_content` loaded once at session start.
**Plan slice:** **NEW — surfaced in §5 backlog** (memory live-reload).

### P-19: Tool failure doesn't tell user WHY
**Repro:** Tool fails with exception. Output is "Error: …" — no suggestion of what went wrong or how to fix.
**Today:** Exception message is the result; no error classification.
**Plan slice:** **NEW — surfaced in §5 backlog** (error classification).

### P-20: Long thinking blocks responsive cancel
**Repro:** Submit complex task → model thinks for 60s → press Ctrl-C. Cancel takes effect after thinking ends, not mid-stream.
**Today:** `S-INTERRUPT` (P2 #17) targets this for tool execution. For thinking tokens, cancellation flows through provider streaming — verify.
**Plan slice:** **S-INTERRUPT** (cancellation for tool exec). Thinking-stream cancel needs separate verification.

---

## 3. Observability Targets (definition of "fixed")

The backend isn't "fixed" until we can MEASURE it. These targets define done.

### 3.1 Latency targets

| Metric | Today | Target | Plan slice |
|---|---|---|---|
| First `on_chat_ack` after `chat` request | <100ms | <100ms (preserve) | — |
| First `on_token` for trivial query (e.g., `hello`) | ~3-7s on remote gateway | <2s on `coding` alias | S-THINK-A (no thinking overhead when off) |
| First `on_token` for cold-cache `search_code` | ~30s+ | <5s | DEFER — needs background indexing |
| Tool execution overhead (excl. handler work) | ~5-20ms | <5ms | S-CACHE wiring (P3 deferred) |
| Cancellation latency from Ctrl-C → state-clear | ~1-3s | <500ms | S-INTERRUPT |

### 3.2 Reliability targets

| Metric | Today | Target | Plan slice |
|---|---|---|---|
| Retry rate per turn (OpenRouter 429/5xx) | unmeasured | <5% over 7-day window | New: surface metric via `cost_dashboard` extension |
| Tool failure rate (excl. user errors) | unmeasured | <1% | New: telemetry slice |
| Session resume succeeds (full state restored) | partial — tasks only | 100% — messages + tasks + memories | S-CKPTMSG |
| Backend crash → frontend visible message | NEVER (stderr→null) | always | OUT — modular Follow-through |
| `on_warning` emitted on long retry | yes (Entry 1408) | preserve + classify | New: error classification |

### 3.3 Cost targets

| Metric | Today | Target | Plan slice |
|---|---|---|---|
| User can see live cost during turn | only via `/cost` | always visible in status bar | S-COST + new status-bar binding |
| Cost limit warning before crossing | none | once per session | S-COST |
| Cost projection before turn execution | none | rough estimate from prompt size | New: cost projection P3 |
| Token-budget breakdown by section | none | available via `/cost --breakdown` | New: P3 |

### 3.4 Context efficiency targets

| Metric | Today | Target | Plan slice |
|---|---|---|---|
| Compaction frequency (per N turns) | unmeasured | <1 per 50 turns on typical session | S-PRIORITY + S-TRUNCATE |
| Tool-result token share of prompt | can hit 80% | <40% | S-CLEAR-RESULTS + S-TRUNCATE |
| Search-result reuse (same search within session) | 0% (no memo) | 70%+ when params identical | DEFER (memoization) |
| Memory-hit rate (learned memories surfaced) | 0% (no surfacing) | 30%+ when relevant | New: memory surfacing P3 |

### 3.5 What "complete" means

Backend tranche is complete when:
1. All 16 in-tranche slices land (per existing plan §8).
2. **A live PTY canary** exercising P-2, P-3, P-5, P-7, P-8, P-9, P-11, P-14, P-16 reproduces the BEFORE state pre-fix and the AFTER state post-fix.
3. Latency table 3.1 measurements collected on a 100-turn synthetic workload; numbers are within target.
4. Cost table 3.3 visible UI surface confirmed.

---

## 4. Per-Stage User-Visible Delta

What the user SEES change after each stage. Concrete enough to be testable.

### After Stage 1 (S-POSTTOOL ✓ + S-TOKENCAL ✓ + S-THINK-A + S-THINK-B)

**User experience delta:**
- `~/.claude/settings.json` `PostToolUse` hooks now actually run after each tool. (Already shipped.)
- Compaction triggers based on real provider token counts, not chars-÷-4 heuristic. Less surprising. (Already shipped.)
- `/thinking off` actually saves tokens. Cost goes down measurably for reasoning models.
- `/thinking on` shows tokens streaming in real time, like Claude Code. Distinct visual treatment.

**Acceptance scenario:**
```
$ autocode
[ready, coding alias]
> /thinking
Thinking: ON
> Solve: what's the largest prime under 100?
[Thinking: I need to find primes < 100. Start with 97...] (streamed in muted text)
[Answer: 97]
> /thinking
Thinking: OFF
> Solve: what's the largest prime under 100?
[Answer: 97]                                              (no thinking shown)
```

**Provable via:** Layer B parametrized contract test that asserts `on_thinking` event count = 0 when toggle off, > 0 (and ordered before `on_done`) when toggle on.

### After Stage 2 (S-INPROGRESS + S-INTERRUPT)

**User experience delta:**
- `/tasks` panel shows three states (pending → in_progress → completed). Tasks visibly transition while agent works on them.
- Pressing Ctrl-C during a long `run_command` cancels cleanly within 500ms.

**Acceptance scenario:**
```
> Create a task to refactor the auth module.
[Task created: refactor_auth (pending)]
> Start working on it.
[Task: refactor_auth (in_progress)]    ← visible in /tasks
[reads files…]
[Task: refactor_auth (completed)]
```

```
> run_command "sleep 30"
[run_command running…]
^C
[Cancelled. Tool exited cleanly in 320ms.]
```

### After Stage 3 (S-CLEAR-RESULTS + S-SEARCHRES + S-MEMPERSIST + S-PRIORITY + S-MEMROBUST + S-TRUNCATE + S-L1L2PREVIEW)

**User experience delta:**
- Long sessions don't bog down with stale tool output — agent proactively clears results it no longer needs.
- Search results auto-feed the prompt — no need to repeat "search for X" multiple times.
- Memories accumulate visibly (`/memory list` shows entries growing over a session).
- Iteration-zero shows a brief symbol summary for files in the working set, when cheap.

**Acceptance scenario:**
```
> /memory list
[3 memories]
1. tool_pattern: prefer ripgrep over grep (relevance: 0.95)
2. project_fact: auth lives in src/auth/ (0.88)
3. user_preference: explain in 2-3 sentences (0.81)

> [agent runs 20 file reads]
> [agent decides via prompt to clear stale results]
[ToolResultCache.clear: dropped 14 file_read results > 5 minutes old]

> /search code "rate limiting"
[3 results found]
> Where do we rate-limit?
[Answer pulls from search results without re-running search]
```

### After Stage 4 (S-BLOCKED + S-CKPTMSG + S-COST + S-EPISODESUM)

**User experience delta:**
- Dangerous paths in write_file/edit_file/apply_patch are blocked, not just run_command.
- `/checkpoint save X` + `/checkpoint restore X` round-trips the conversation, not just tasks.
- A cost limit hit emits exactly one warning per session.
- Long sessions retain a summarized history beyond the 200-event cap.

**Acceptance scenario:**
```
> /checkpoint save before-refactor
[Checkpoint saved: 14 messages, 3 tasks, 2 memories]
> [do experimental work for 30 minutes]
> /checkpoint restore before-refactor
[Checkpoint restored: 14 messages, 3 tasks, 2 memories]
> What were we discussing?
[Agent has full context from before the experiment]
```

```
[200th event in long session]
[Episode store: summarized oldest 50 events into 1 summary event before purge]
> /memory list
[memories preserved]
[summary event also accessible via debug log]
```

```
[config: agent.cost_limit_usd: 5.00]
[after $5.00 crossed]
[Warning] Session cost limit reached: $5.07 / $5.00 threshold. Continuing; use /cost to view.
[no further warnings; turn continues]
```

### After Parallel Doc Refresh

User-experience neutral. But:
- `requirements_and_features.md` reflects current reality (Rust TUI primary, ~60 tools, ~27 commands).
- `architecture.md` shows TCP transport + attach mode.
- `current_directives.md` records this tranche's status.
- A new reader can navigate from `docs_summaries/` to the right doc on first try.

---

## 5. New Feature Backlog (post-tranche P3 ideas)

Brainstormed during this ultrathink — features the existing plan doesn't address. Each lists rough size + UX value + recommendation.

| # | Feature | UX value | Size | Recommendation |
|---|---|---|---|---|
| F1 | **Provider failover** — config'd fallback chain; on persistent 429/5xx, swap provider+model | High (P-17 reliability) | M | **Promote to P2** |
| F2 | **Memory live-reload** — re-read AGENTS.md / .autocode/memory.md on tool use | Med (P-18) | S | Promote to P2 |
| F3 | **Error classification** — categorize tool failures (NETWORK/PERMISSION/SYNTAX/etc.) + suggest fix | High (P-19) | M | Promote to P2 |
| F4 | **Cost projection** — estimate $ before turn from prompt size + history | Med | M | P3 |
| F5 | **Background indexing** — index repo continuously in a worker; never block on warmup | High (3.1 latency) | L | **Promote to P2 — high leverage** |
| F6 | **Status-bar cost ticker** — live $ in status bar, not just `/cost` | Med | S | P3 (add when S-COST lands) |
| F7 | **Diff preview before write** — auto-show diff before write_file/edit_file even in AUTO mode | High | S | Consider replacing/extending S-BLOCKED scope |
| F8 | **Citation/source tracking** — when LLM uses retrieved code, cite the source files | High (trust) | M | P3 |
| F9 | **`@symbol` mentions** — extend `@file` to `@MyClass.foo` | Med | S | P3 |
| F10 | **Multi-step undo** — `/undo 3` to roll back N tool calls | High | M-L | P3 |
| F11 | **Conversation export** — `/export markdown` saves to file | Med | S | Easy win — add as S-DOCSREFRESH-style sub-slice |
| F12 | **Tool failure analytics** — track success/failure rate per tool, surface via `/stats` | Med | M | P3 |
| F13 | **Inference-time budgets** — `agent.max_turn_seconds` config to abort long thinking | High | S | Promote to P2 — pairs with S-COST |
| F14 | **Smart compaction** — semantic similarity dedup of redundant messages | Med | M-L | P3 |
| F15 | **Replay** — re-execute a tool sequence from a previous session | Med (debug aid) | M | P3 |
| F16 | **Speculative file reads** — pre-fetch files mentioned in prompt | Low | M | Skip — minor |
| F17 | **Workspace bookmarks** — `/bookmark add` / `/bookmark goto` | Low | S | Skip |
| F18 | **Tool composition** — meta-tool that chains tool calls atomically | Med | L | P3 |
| F19 | **Plan-mode artifact** — `/plan` produces a markdown export | Med | S | Consider adding to S-DOCSREFRESH-like sub-slice |
| F20 | **Multi-language Layer 1** — TS, Go, Rust tree-sitter handlers | Very high | XL | **Roadmap item** — separate tranche |
| F21 | **Code review subagent** — dedicated review pass before commit | High | M | Defer to post-`/cc` (subagent track) |
| F22 | **Auto test generation** — generate tests for changed code | High | L | P3 |
| F23 | **Documentation auto-update** — flag docs likely affected by code change | Med | M | P3 |
| F24 | **Tool sandbox** — risky tools in isolated container | High (security) | XL | Roadmap |
| F25 | **Confidence scoring** — model self-estimate of answer correctness | Med | S (just propagate) | P3 |
| F26 | **Persistent learning across users** — opt-in shared memory pool | Med | XL | Skip for v1 |

**Recommended promotions to backend tranche P2 (4 items):**

- **F1 Provider failover** — concrete reliability improvement that pairs with Entry 1408's fail-fast classification.
- **F2 Memory live-reload** — small slice, big "feels right" UX win.
- **F3 Error classification** — extends `_format_openrouter_error` pattern from Entry 1408.
- **F5 Background indexing** — addresses cold-cache latency without re-introducing the Entry 1377 first-turn stall risk that S-L1L2PREVIEW had to thread carefully.
- **F13 Inference-time budgets** — pairs naturally with S-COST (cost is one budget; time is another).

If user agrees, these become 5 new in-tranche slices (S-FAILOVER, S-MEMRELOAD, S-ERRCLASS, S-BGINDEX, S-TIMEBUDGET) bringing the in-tranche feature count from 16 to 21. Effort impact: ~+15-25 builder-days. The fast-path P0-only minimum (~30 days) doesn't change.

**Easy wins to add as doc-refresh-style mini-slices (not full slices):**
- **F6 Status-bar cost ticker** — frontend status binding after S-COST lands.
- **F11 Conversation export** — `/export` slash command, simple.
- **F19 Plan-mode artifact export** — `/plan export`, simple.

**Roadmap items beyond v1:** F20 Multi-language L1, F24 Tool sandbox.

---

## 6. Per-Slice Acceptance Scenarios (concrete keystroke→screen)

For each in-tranche slice, the SHIPPED criterion as a user-observable test.

### S-POSTTOOL ✓
Already shipped. Acceptance proven via test:
```
[settings.json: PostToolUse hook prints "TOOL DONE" to stderr]
> read_file path=/etc/hostname
[tool runs]
[stderr: TOOL DONE]
```

### S-TOKENCAL ✓
Already shipped. Acceptance:
```
[provider.count_tokens("a"*100) returns 7]
> [internal: ContextEngine.count_tokens("a"*100) returns 7, not 25]
```

### S-THINK-A
```
> /thinking off
> [hard task]
[provider request includes "reasoning":{"enabled":false} for OpenRouter]
[provider request includes "think":false for Ollama 0.3.14+]
[no on_thinking notifications observed]
[token usage measurably lower vs ON]
```

### S-THINK-B
```
> /thinking on
> [hard task using DeepSeek-R1 via Ollama]
[stream: <think> opens]
[stream: thinking text streams chunk-by-chunk into the dimmed thinking area]
[stream: </think> closes]
[stream: regular content begins streaming]
[partial-tag-tail edge case: <thi|nk> across chunk boundary detected and routed correctly]
```

### S-INPROGRESS
```
> create_task title="refactor auth"
[Task: refactor_auth (pending)]
> Start working on it
[Task transitions: pending → in_progress, on_task_state notification fires]
[Rust TUI shows ⏳ icon (already supported per view.rs:899)]
[work completes]
[Task: refactor_auth (completed) → ✓ icon]
```

### S-INTERRUPT
```
> run_command "sleep 30"
[Tool: run_command (running)]
^C
[CancelledError propagates]
[interruptible=True tool exits cooperatively within 500ms]
[on_tool_call status="cancelled" notification fires]
> [agent loop continues with next user input]
```

### S-CLEAR-RESULTS
```
> [agent runs 10 file_reads in one turn]
[ToolResultCache: 10 entries recorded]
> [agent reaches context pressure threshold]
[agent calls clear_tool_result(age="5m") — exposed as a tool]
[14 entries cleared]
> [next turn's prompt is leaner]
```

### S-SEARCHRES
```
> search_code "rate limiting"
[3 results: src/auth.py, src/rate.py, tests/test_rate.py]
[ContextAssembler.assemble(search_results=...) builds a "Search Results" section]
> Where do we rate limit?
[answer references the search results from the assembled context, no re-search]
```

### S-MEMPERSIST
```
> [long session, agent learns: "user prefers ripgrep"]
> /exit
[end-of-session: SessionConsolidator.gather() → list of learnings]
[NEW: each learning routed through MemoryStore.save() with Jaccard dedup]
> autocode  # new session
> /memory list
[entry: tool_pattern: prefer ripgrep over grep (relevance: 0.95)]
```

### S-PRIORITY
```
> [context section "rules" hits 600 tokens but budget is 300]
[BEFORE: 600 tokens included; total prompt over budget]
[AFTER: rules truncated to 300 tokens; total prompt within budget]
[CompactionResult logged: rules section reduced from 600→300]
```

### S-MEMROBUST
```
[LLM response: "Here are some learnings: [{"category": "...", "content": "..."}]"]
[BEFORE: regex-based [...] match fails on preamble; learnings dropped]
[AFTER: provider.generate_json(schema=...) returns structured list; all learnings parsed]
```

### S-TRUNCATE
```
[tool returns 5000-token code listing with function signatures throughout]
[BEFORE: head 60% + tail 40% = middle signatures lost]
[AFTER: signatures preserved; bodies elided; "..." markers]
[Per-tool output_budget_tokens honored: file_read=2000, search_text=500, etc.]
```

### S-L1L2PREVIEW
```
> autocode  # cold start
[iteration-0 system prompt includes:]
[Workspace Bootstrap:]
[Project root: /home/user/repo]
[Git branch: main (3 changes)]
[Retrieval index: cold; deferred]
[Active working set: src/auth.py, src/main.py]
[L1 preview (cached): src/auth.py: def login(), def logout(), class AuthError]
[deadline check: parse completed in 47ms (under 100ms soft cap)]
> hello
[first turn streams as fast as before Entry 1377 fix; no regression]
```

### S-BLOCKED
```
> [agent calls write_file path=/etc/passwd]
[ApprovalManager.is_blocked(tool="write_file", args=...) → True]
[blocked: "/etc/" is a system path]
[tool not executed; agent receives error result]
> [agent retries with safe path]
```

### S-CKPTMSG
```
> /checkpoint save before-experiment
[Checkpoint: 14 messages + 3 tasks + 2 memories saved]
> [do work]
> /checkpoint restore before-experiment
[Checkpoint restored: 14 messages, 3 tasks, 2 memories]
> What were we discussing?
[agent has full context]
```

### S-COST
```
[config: agent.cost_limit_usd: 5.00]
> [run heavy task]
[cost crosses $5.00 mid-turn]
[on_warning emitted: "Session cost limit reached: $5.07 / $5.00 threshold. Continuing; use /cost to view."]
> [more work — no further warnings unless threshold raised]
```

### S-EPISODESUM
```
[200th event in session]
[BEFORE retention purge]
[NEW: _summarize_oldest_episodes(50) → "summary: tool_call×42, error×2, ts=…"]
[delete the 50 originals]
[summary event remains in episode_events]
[recursive cap: if >50% of remaining events are summaries, skip new summary]
```

### S-L3DOC
```
> [code reader opens layer3/provider.py]
[file header docstring:]
"""DEFERRED: Layer 3 local constrained generation.

This module is intentionally not wired into the default runtime path.
See docs/plan/backend-feature-improvement-plan.md §3 for the rationale
and revisit triggers (a) airgapped deployment requirement, (b) L4 cost
threshold consistently exceeded.

DO NOT IMPORT from non-test code without re-evaluating §3 first.
"""
```

### S-DOCSREFRESH-A through G
```
> [open docs/requirements_and_features.md]
[reflects 2026-04-25 state: ~60 tools, ~27 slash commands, Rust TUI primary, modular backend, on_warning surfacing, etc.]
> [open docs/architecture.md]
[shows TCP transport + attach-mode topology]
> [open current_directives.md]
[has Backend Feature Improvement Tranche section pointing to this plan]
> [open autocode/TESTING.md]
[commands match current state: bare autocode preferred over autocode chat]
> [docs/plan/ archive folder]
[clearly superseded plans (Phase 5/6/7/8) moved here, not in main folder]
```

---

## 7. What This Doc Doesn't Cover (deferred to other docs)

- **Tool catalog regeneration:** ~60-tool detailed list. Belongs in `S-DOCSREFRESH-A.1` (the §2.4 rewrite of `requirements_and_features.md`).
- **Slash command map:** ~27-command surface. Belongs in same.
- **Layer-model post-modular diagram:** where L1-L4 live in services/dispatcher/chat/transport/host structure. Belongs in `docs/architecture.md` (S-DOCSREFRESH-B target).
- **Sequence diagrams** for chat / approval / cancel / session-resume flows. Belongs in `docs/reference/rpc-schema-v1.md` extension.

---

## 8. Action for the User

1. **Read this doc** — confirm the vision (§1), pain points (§2), and observability targets (§3) are right.
2. **Decide on §5 promotions:** do F1 + F2 + F3 + F5 + F13 join the tranche as 5 new slices, or stay P3?
3. **Decide on §5 mini-slices:** F6 + F11 + F19 — easy wins, want them in?
4. **Optionally:** ratify §4 user-visible deltas as the acceptance criteria for stage exit gates (not just the per-slice exits).

Once decided, this doc becomes the **acceptance spec** for the tranche. Codex reviews it alongside the plan doc; per-slice acceptance scenarios in §6 become the concrete `expected user-visible behavior` block in each slice's pre-task intent.

---

## 9. References

- `docs/plan/backend-feature-improvement-plan.md` — formal plan (WHAT/HOW)
- `docs/plan/backend-feature-improvement-todo.md` — checklist
- `docs/plan/archive/backend-feature-catalog-brainstorm.md` — original brainstorm (archived)
- `docs/plan/archive/docsrefresh-A-drift-map.md` — `requirements_and_features.md` audit
- `bugs/bugs.md` — BUG-LIVE-001 through BUG-LIVE-004 status
- `AGENTS_CONVERSATION.MD` Entry 1431 — live S-TOKENCAL completion
- `autocode/docs/qa/test-results/20260425-110630-s-posttool-verification.md` — S-POSTTOOL artifact
- `autocode/docs/qa/test-results/20260425-120234-s-tokencal-verification.md` — S-TOKENCAL artifact
