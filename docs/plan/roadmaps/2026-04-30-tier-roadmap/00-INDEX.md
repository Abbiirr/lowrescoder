# AutoCode Forward Roadmap — Index

**Status:** drafted 2026-04-30 from research dive on Claude Code source leak (KAIROS, AutoDream, MEMORY.md), Codex App Server (Item/Turn/Thread), OpenRouter prompt-caching, and arXiv 2601.06007 (Don't Break the Cache).

**Goal:** ship the minimum changes that (a) cut OpenRouter free-tier cost ≥ 40% on long agent runs, (b) give AutoCode a Codex-style multi-surface harness so a Tauri/Electron/web client can reuse the backend, and (c) bring memory and compaction up to Claude Code parity.

---

## Document map

| File | Topic | Read first if you care about… |
|---|---|---|
| `00-INDEX.md` | this file | overall sequencing |
| `01-tier1-prompt-cache.md` | breakpoint injection, stable/dynamic boundary, reasoning-token capture | cutting LLM bill this week |
| `02-tier2-app-server-protocol.md` | Item/Turn/Thread refactor, transports, `turn/steer` | enabling desktop/web clients |
| `03-tier3-memory-architecture.md` | 3-layer memory, Session Notes, verify-before-use | matching Claude Code memory |
| `04-tier4-future-tracks.md` | KAIROS, ephemeral forks, sticky envs, headless | longer-term optionality |
| `05-cross-cutting-concerns.md` | testing, telemetry, migration, rollback safety | engineering quality |

---

## Execution order

```
Week 1     Tier 1 — prompt cache plumbing (1.1 + 1.2 + 1.3)
Week 2-3   Tier 2.1 — Item/Turn/Thread refactor
Week 4     Tier 2.2 + 2.3 — transports + turn/steer
Week 5-7   Tier 3.1 — file-system 3-layer memory
Week 8     Tier 3.2 + 3.3 — Session Notes + verify-before-use
Week 9+    Tier 4.x — proactive, ephemeral, sticky envs (each behind feature flag)
```

Tier 1 is independent of everything else — ship it standalone. Tier 2 unlocks all future client surfaces. Tier 3 depends on the existing `consolidation.py` autoDream code path (no Tier 2 dependency).

---

## Success criteria per tier

### Tier 1 — measurable in production
- `prompt_tokens_details.cached_tokens > 0` on second consecutive turn
- `cache_creation_input_tokens` reported once per stable-prefix change
- `/cost` slash command shows cache hit ratio
- Test: send identical 2k-token system prompt twice within 5 min → second call's `cached_tokens` ≥ 1024

### Tier 2 — externally observable
- A separate Rust binary (`autocode-app-client`) using only public RPC can list threads, start a turn, stream items, send approval response
- `thread/fork ephemeral=true` returns `path: null`
- Server returns `-32001 "Server overloaded; retry later"` when WebSocket queue full
- Tests pass for `initialize` handshake → `thread/start` → `turn/start` → multiple `item/*` notifications → `turn/completed`

### Tier 3 — qualitative + measurable
- `~/.autocode/<project-hash>/MEMORY.md` exists and is ≤ 200 lines after 50 sessions
- Topic files present: `architecture.md`, `debugging.md`, `decisions.md`
- Daily logs append-only — agent cannot delete (filesystem ACL or just convention enforced via tool refusal)
- Compaction Path A (Session Notes) chosen ≥ 80% of compaction events once 10k tokens consumed

### Tier 4 — feature-flag gated
- `AUTOCODE_FEATURE_KAIROS=true` enables `<tick>` injection
- KAIROS calls SleepTool when no work queued (verified by log)
- Default off; can be promoted to default-on after 4 weeks of clean telemetry

---

## What this roadmap deliberately omits

- **5-tier compaction parity** — current 3-tier covers ~90% of value; the marginal Claude Code tiers (per-tool budgets, edit-block pinning) are addressable later
- **Anti-distillation tooling** — irrelevant for a non-distilled product
- **Undercover mode** — Anthropic-employee-specific
- **Buddy/Tamagotchi** — pure entertainment
- **Voice mode** — no clear path to implementation without Realtime API budget
- **Multi-agent Coordinator** — interesting but scope creep relative to current goals

---

## Dependencies and prerequisites

| Tier | Depends on | Blocks |
|---|---|---|
| 1.1 | nothing | 1.3 (cache token reporting needs cache enabled) |
| 1.2 | nothing | 1.1 to be effective (uncached dynamic content invalidates cache) |
| 1.3 | 1.1 | none |
| 2.1 | nothing | 2.2, 2.3, 4.2 |
| 2.2 | 2.1 | none |
| 2.3 | 2.1 | none |
| 3.1 | nothing | 3.2 (Session Notes referenced from MEMORY.md) |
| 3.2 | 3.1 | improved compaction quality |
| 3.3 | nothing | reduces hallucination cost |
| 4.1 | 3.1 (daily logs), 1.1 (cache-aware sleep tradeoff) | none |
| 4.2 | 2.1 | none |
| 4.3 | 2.1 | none |
| 4.4 | 2.1 (json schema generation) | none |

---

## Glossary

- **Tier** — priority bucket; lower number = higher priority
- **TI ID** — `<tier>.<sequence>`, e.g. `1.2` = Tier 1, second item
- **stable prefix** — content that doesn't change between turns (system prompt, tool defs, RulesLoader output) — eligible for prompt cache
- **dynamic tail** — content that changes per turn (current date, git status, tool results) — must NOT be in cache region
- **breakpoint** — `cache_control: {type: "ephemeral", ttl: "1h"}` marker placed on the last block of cached content
- **Item/Turn/Thread** — Codex App Server's three primitives; see `02-tier2-app-server-protocol.md`
- **MEMORY.md** — Claude Code's 200-line index file in `~/.claude/projects/<git-root-hash>/memory/`
- **Topic file** — sibling markdown file referenced by MEMORY.md, loaded on demand
- **Daily log** — `logs/YYYY/MM/YYYY-MM-DD.md`, append-only, never auto-loaded
- **Session Notes** — living document updated every 5k tokens after 10k activation, used in compaction Path A
- **KAIROS** — Anthropic's unreleased proactive-mode daemon; `<tick>` injection between user turns
- **AutoDream** — Claude Code's background memory consolidation; same module name as your `consolidation.py`
- **Path A vs Path B** — compaction strategies. A=use Session Notes as summary; B=fresh API summary call

---

## Quick reference — what each track changes

```
Tier 1.1  src/autocode/layer4/llm.py             +120 LOC
Tier 1.2  src/autocode/agent/prompts.py          refactor + sentinel
Tier 1.3  src/autocode/agent/token_tracker.py    +40 LOC + persistence
Tier 2.1  rtui/src/rpc/protocol.rs               replace 44 structs with 3 primitives
          src/autocode/backend/server.py         add thread/turn/item dispatch
          docs/reference/rpc-schema-v2.md        new schema doc
Tier 2.2  rtui/src/main.rs + new transport mods  Unix socket + WebSocket
Tier 2.3  src/autocode/agent/loop.py             message-queue insertion mid-turn
Tier 3.1  src/autocode/session/memory_fs.py      NEW file ~600 LOC
          src/autocode/agent/tools.py            add memory_read_topic, memory_grep_logs, memory_write_topic
          drop src/autocode/agent/memory.py      migrate then delete
Tier 3.2  src/autocode/session/session_notes.py  NEW file ~250 LOC
          src/autocode/agent/context.py          compaction Path A integration
Tier 3.3  src/autocode/agent/prompts.py          add verify-before-use section
Tier 4.1  src/autocode/agent/proactive.py        NEW file ~400 LOC, behind AUTOCODE_FEATURE_KAIROS
Tier 4.2  rtui/src/state/model.rs + reducer.rs   ephemeral fork support
Tier 4.3  src/autocode/agent/sandbox.py          per-thread environment binding
Tier 4.4  src/autocode/cli.py                    autocode exec --json --output-schema
```
