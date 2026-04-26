# Cost Display — Comparative Analysis Across Coding Agents

> **Purpose:** Inform AutoCode's S-COST display design by surveying how peer agents surface cost/usage to users.
> **Method:** Direct knowledge (Claude Code), repo research notes (pi-mono), industry observation + public docs (others). Confidence levels declared per agent.
> **Date:** 2026-04-25.
> **Outcome:** three tiered design proposals (§4) for user choice. **Backend always rich (CostDashboard); display tier governs user-facing surface only.**

---

## 1. Confidence levels

| Agent | Confidence | Source |
|---|---|---|
| **Claude Code** | High | Direct knowledge as the agent currently impersonating |
| **pi-mono / pi coding agent** | Medium | Repo `docs/research/pi-mono-competitive-analysis.md` + upstream README references |
| **Aider** | Medium-High | Well-documented public patterns; widely-used `/tokens` and `/cost` commands |
| **OpenCode (sst.dev)** | Medium | Industry observation; multi-provider tracking is a known strength |
| **Codex CLI (OpenAI)** | Medium | Public docs + observable patterns; status indicator known |
| **Cursor (Composer/agent)** | Medium | Direct UI use, not deep agent-mode telemetry observation |
| **Goose (Block)** | Low-Medium | Public docs only |
| **OpenHands / SWE-agent** | Low | Mostly autonomous — cost intentionally de-emphasized in UX |
| **Continue** | Medium | Open-source; tracks via providers |

What follows is a comparison built from these sources. Where I'm uncertain I label "approximate" or "varies by version" and recommend the user verify before locking design.

---

## 2. Comparison Matrix

### 2.1 Display surfaces (where cost shows up)

| Agent | Status bar (live) | `/cost`-style command | Dedicated dashboard / view |
|---|---|---|---|
| Claude Code | ✓ — `$X.XX · tokens` always visible | ✓ — `/cost` command with breakdown | partial — context-window indicator is a separate surface |
| Codex CLI | ✓ — token + cost in footer | ✓ — `/usage` or similar | — |
| OpenCode | ✓ — token in status; cost when configured | ✓ — `/cost` with multi-provider | ✓ — web UI cost dashboard |
| pi-mono | partial — token counter only | partial — limited breakdown | — |
| Aider | ✓ — turn cost + session cost in prompt prefix | ✓ — `/tokens`, `/cost` | — |
| Goose | ✓ — usage indicator | partial | — |
| Cursor (agent) | partial — context window % | — (subscription-paid; cost not surfaced) | — |
| Continue | ✓ — token counter | partial | — |
| OpenHands | partial — agent runs autonomously, cost de-emphasized | — | partial — admin view only |

**Pattern:** status bar + `/cost` command is the dominant pair across non-autonomous agents. Dedicated dashboards are an OpenCode differentiator.

### 2.2 Detail level (what's shown)

| Agent | Total session $ | Per-turn delta | Per-model breakdown | Cache hit/miss | Per-tool attribution | Context-window % | Limit/threshold |
|---|---|---|---|---|---|---|---|
| Claude Code | ✓ | ✓ | ✓ (when multi-model) | **✓ — prominent** | partial | ✓ | ✓ — Pro/Max plan-aware |
| Codex CLI | ✓ | ✓ | ✓ | partial | — | ✓ | partial |
| OpenCode | ✓ | partial | ✓ — strong | ✓ | partial | ✓ | ✓ — config'd |
| pi-mono | partial — tokens only | — | — | — | — | partial | — |
| Aider | ✓ | ✓ | ✓ | ✓ — calls them out | partial | partial | ✓ — `--max-cost` |
| Goose | partial | partial | ✓ | partial | — | partial | partial |
| Cursor (agent) | — | — | — | — | — | ✓ | — (subscription) |
| Continue | partial | partial | ✓ | partial | — | partial | — |
| OpenHands | partial | — | partial | — | — | — | — |

**Pattern observations:**
- **Total session $** is universal among agents that show cost at all.
- **Cache hit/miss is becoming standard.** Claude Code, OpenCode, and Aider all surface it because cache savings can be 50–90% of cost. Showing the cache ratio educates users about prompt-design impact.
- **Per-model breakdown** matters when an agent uses multiple models per session (which AutoCode does: routing to L4 + occasional external).
- **Per-tool attribution is rare.** OpenCode and some others have it; most agents skip it because it adds noise.
- **Context-window %** is a Claude Code differentiator. Helpful when compaction matters.

### 2.3 Cache awareness — special note

Anthropic prompt caching, OpenAI prefix caching, and Gemini context caching all give 5–10× cost reductions when used correctly. Agents that DON'T surface cache hits leave users in the dark about whether their prompts are cache-hitting.

| Agent | Cache hit display |
|---|---|
| Claude Code | Yes — `cache_creation_input_tokens` and `cache_read_input_tokens` shown explicitly |
| Aider | Yes — separate cost lines for cached vs uncached |
| OpenCode | Yes when provider supports |
| Codex CLI | Partial — depends on version |
| pi-mono | No |
| AutoCode today | **No — `cost_dashboard.py` doesn't track cache hits separately** |

This is an explicit gap in AutoCode's `CostDashboard`. The `record()` method only takes `tokens_in` / `tokens_out`, not `cached_input_tokens`. Adding cache awareness would require:
- Provider integration: `OllamaProvider`/`OpenRouterProvider` need to capture cache fields from API response (Ollama may not support; OpenRouter does for cache-supporting providers).
- `CostEntry` schema: add `cached_input_tokens: int = 0` and a separate cost calc for cached vs uncached.
- Display: show cache hit rate when non-zero.

### 2.4 Format examples (current / approximate; mock-up format)

**Claude Code (status bar):**
```
[ready] claude-sonnet-4-6 · 12.4K↑ 3.2K↓ · $0.0473 · 8% used
```
With cache:
```
[ready] claude-sonnet-4-6 · 12.4K↑ (10.1K cached) 3.2K↓ · $0.0089 · 8% used
```

**Aider (prompt prefix):**
```
> [main!] Tokens: 4.5k sent, 1.2k received. Cost: $0.04 message, $0.42 session.
```
With cache:
```
> Cost: $0.04 message ($0.01 cached), $0.42 session.
```

**pi-mono (status bar — minimalist):**
```
> [coding-agent] tokens: 15623
```

**OpenCode (status bar; web UI also has dashboard):**
```
[gpt-4o-mini] 12.4K · $0.014 · cache 65%
```
Detailed `/cost`:
```
Provider          Model          Tokens       Cost     Cache%
openrouter        coding         15,623       $0.27    65%
ollama            qwen-7b        4,200        $0.00    n/a
                                ────────     ──────
                  Total          19,823       $0.27
```

**AutoCode today (status bar — Rust TUI):**
```
[ready] coding · 12,453 · $0.27
```
Current `/cost` (heuristic — pre-S-COST):
```
**Session Usage:**
- Messages: 8 (3 user, 4 assistant, 1 tool)
- Estimated tokens: ~12,453
- Provider: openrouter / coding
```

---

## 3. Strategic Considerations

### 3.1 What the user actually pays for

For Anthropic-backed sessions: prompt + completion tokens, with cache reads at ~10% of normal rate, cache writes at ~125%. **Without cache surfacing, users can't tell if their setup is efficient.**

For OpenRouter-routed sessions: model-specific rates. Multi-provider users want per-provider attribution.

For local Ollama: zero $ but real time/VRAM cost (which AutoCode currently doesn't surface).

### 3.2 What's worth showing vs hiding

**Always show:**
- Session total $ (or "free" for local-only)
- Token count (input + output)
- Active model

**Worth showing when applicable:**
- Cache hit rate (when non-zero)
- Per-model breakdown (when multi-model session)
- Threshold proximity (when limit set)
- Context-window % (when approaching compaction)

**Skip unless explicitly asked:**
- Per-tool attribution (noise)
- Per-task attribution (noise unless task-tracking is central UX)
- Per-agent attribution (only relevant for multi-agent / subagent setups)
- Cost projection (speculative, user wants real)

### 3.3 AutoCode's actual model

AutoCode routes across 4 layers (L1 deterministic, L2 retrieval, L3 local constrained — currently deferred, L4 LLM). Most cost is L4. The CostDashboard's per-layer/per-agent/per-task breakdown is GOOD INFRASTRUCTURE for future multi-agent debugging, but most users in v1 will only care about: total $, total tokens, current model, threshold.

The OpenCode-style multi-provider breakdown matters when AutoCode genuinely uses multiple providers per session. Today it usually doesn't (single gateway alias). When subagent work resumes post-`/cc`, the multi-agent breakdown becomes more useful.

### 3.4 The `/cost` command as a teaching surface

A well-designed `/cost` command can teach users about:
- Where their tokens go (input vs output)
- Whether they're benefiting from caching
- How close they are to limits
- Which model they're paying for

This argues for slightly more detail than "single-line counter" — closer to Aider's prompt-prefix style with optional `/cost --detail` for the full picture.

---

## 4. Three tiered design proposals

Each tier specifies BACKEND changes (always rich), STATUS BAR (live counter), and `/cost` COMMAND (on-demand detail).

### TIER A — Minimalist (pi-mono / Claude-Code-status-bar style)

**Backend:** no change beyond planned S-COST threshold + check_limit. Existing `CostDashboard` keeps multi-axis structure but isn't surfaced.

**Status bar:** existing Rust TUI display unchanged. Already shows tokens + cost.

**`/cost` command output:**
```
$0.27 · 15,623 tokens · 4 turns · openrouter/coding
```
With limit:
```
$0.27 / $5.00 (5%) · 15,623 tokens · 4 turns · openrouter/coding
```

**Effort:** S — same as Entry 1467 spec. ~30-line `_handle_cost` rewrite + threshold work.

**Best for:** users who want minimal noise; pi-mono/Claude Code crowd.

**Trade-off:** loses cache visibility, multi-model breakdown, and the teaching surface. Underutilizes existing CostDashboard infrastructure.

---

### TIER B — Balanced (Claude-Code-`/cost`-command style)

**Backend:** add cache-hit tracking to `CostDashboard`:
- `CostEntry` gains `cached_input_tokens: int = 0`
- `record()` accepts a `cached_input_tokens` kwarg
- New aggregation `cache_hit_ratio` property

Provider integration:
- `OpenRouterProvider`: capture `usage.prompt_tokens_details.cached_tokens` from API response
- `OllamaProvider`: no-op (Ollama doesn't expose cache info)

**Status bar:** existing display + when cache rate > 0, show: `12.4K (8K cached) · $0.05`

**`/cost` command output (no flag):**
```
Session: $0.27 · 15,623 tokens · 4 turns

Input:  10,234 (8,512 cached, 83% hit) · $0.0312
Output: 5,389 · $0.2388

Provider: openrouter / coding
Limit: $5.00 (5% used)            ← only when limit set
```

**`/cost` command output (with `--detail`):**
```
Session: $0.27 · 15,623 tokens · 4 turns

Per-model:
  openrouter / coding:    14,200 tokens · $0.27
  openrouter / swebench:   1,423 tokens · $0.00 (free tier)

Cache: 8,512 cached / 10,234 input (83% hit) — saved ~$0.16
Context: 28,500 / 200,000 tokens (14%)

Provider: openrouter / coding
Limit: $5.00 (5% used)
```

**Effort:** M — 60–100 lines. Backend cache-tracking + provider capture + 2 `/cost` modes + tests.

**Best for:** users who use Claude Code or Aider; want learning surface + threshold; OK with one extra slash flag for detail.

**Trade-off:** more complexity than tier A but pays off via cache visibility. Cache savings are often the single biggest cost lever.

---

### TIER C — Detailed (OpenCode-style)

**Backend:** tier B PLUS:
- Per-tool cost attribution (track which tool's tokens)
- Cost projection (estimate $ to complete current task based on history)
- Persistent cross-session cost rollup (opt-in, file-backed)

**Status bar:** tier B display + per-minute spend rate when active: `$0.27 · 0.05/min`

**`/cost` command output (default already detailed):**
```
Session: $0.27 · 15,623 tokens · 4 turns · 8 minutes
Spend rate: $0.034 / min

Per-model:
  openrouter / coding:    14,200 tokens · $0.27
  openrouter / swebench:   1,423 tokens · $0.00

Per-layer:
  L1 (deterministic):     2,100 tokens · $0.00
  L2 (retrieval):         1,800 tokens · $0.00
  L4 (LLM):              11,723 tokens · $0.27

Per-tool (top 5):
  search_code:   3,200 tokens · $0.075
  read_file:     2,100 tokens · $0.049
  edit_file:     1,800 tokens · $0.042
  ...

Cache: 8,512 cached / 10,234 input (83% hit) — saved ~$0.16
Context: 28,500 / 200,000 (14%)
Limit: $5.00 (5% used)

Today:    $1.42 across 5 sessions    ← if cross-session enabled
This week: $8.23 across 23 sessions
```

**Optional dedicated dashboard:** `autocode dashboard` command — opens a TUI panel with sortable tables.

**Effort:** L — 200–400 lines. Per-tool tracking, projection logic, cross-session persistence, optional dashboard view.

**Best for:** power users running long sessions, multi-agent setups, cost-sensitive teams.

**Trade-off:** noise for casual users; valuable for power users. Per-tool/per-layer attribution gives debugging info for "why did this turn cost so much?" Cross-session rollup gives accountability.

---

## 5. Recommendation

**For v1: I recommend TIER B (Balanced).**

Reasons:
1. **Cache awareness is the single biggest cost lever.** Without it, users can't tell if they're efficient. Claude Code and Aider both surface it because they've found it pays off in user understanding. AutoCode is leaving money on the table by not displaying it.
2. **Per-model breakdown is one extra line and matters when AutoCode routes to multiple models** (post-subagent-resume, this becomes important).
3. **Tier B's default output (~5 lines) is still readable in a single view.** Not a wall of text like tier C.
4. **Implementation is M (60-100 lines), not L.** Within a single slice budget.
5. **`--detail` flag opens the door to tier C later** without breaking tier B users.

**Backend principle (per user direction):** `CostDashboard` keeps its rich multi-axis structure. We add cache tracking now (small extension) and reserve per-tool/per-layer attribution for tier C if/when needed. Backend always richer than display.

**TIER A** is fine if the user is allergic to any non-essential UI; saves implementation time.

**TIER C** is appropriate post-v1 when multi-agent work resumes — by then `/cost` will need per-agent breakdown anyway, and the rest of tier C lights up naturally.

---

## 6. Open questions for user

1. **Tier choice:** A (minimalist), B (balanced/recommended), or C (detailed)?
2. **Cache tracking:** add to `CostDashboard` now (B/C) or defer (A)? Cache tracking is a small backend change but provider integration requires a per-provider capture path.
3. **Threshold default:** unset (recommended; opt-in only) or ship with a safety default like `$10.00`?
4. **Status-bar live updates:** keep current cadence (per `on_cost_update` notification) or extend to update on each `/cost` call too?
5. **Cross-session rollup (tier C only):** would the user want today/this-week totals, or strictly per-session?

---

## 7. References

- Personal observation of Claude Code behavior (high confidence)
- `docs/research/pi-mono-competitive-analysis.md` — pi-mono philosophy
- `docs/plan/research-components-feature-checklist.md` — T7-3 confirms AutoCode status-bar live cost is DONE
- Aider docs: `/tokens` and `/cost` commands
- OpenCode multi-provider observation
- AutoCode `agent/cost_dashboard.py` (current 134-line implementation)
- AutoCode `app/commands.py:1396` (current `_handle_cost` heuristic implementation)
