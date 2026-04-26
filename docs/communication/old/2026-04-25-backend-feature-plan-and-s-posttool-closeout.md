# Backend Feature Improvement Plan + S-POSTTOOL Closeout (Entries 1420, 1421, 1422, 1423, 1424, 1426, 1429)

**Archived:** 2026-04-25
**Archival authorization:** user-directed selective archive (option "3" — keep most recent for traceability, archive resolved planning chain).
**Resolution record:**
- Plan + todo + drift-map: `docs/plan/backend-feature-improvement-plan.md`, `docs/plan/backend-feature-improvement-todo.md`, `docs/plan/docsrefresh-A-drift-map.md`.
- Brainstorm source: `docs/plan/backend-feature-catalog-brainstorm.md`.
- S-POSTTOOL implementation artifact: `autocode/docs/qa/test-results/20260425-110630-s-posttool-verification.md`.

## Thread scope

Entries 1420-1429 cover the backend feature improvement program from brainstorm → formal plan → corrections → bilateral acceptance → first slice (S-POSTTOOL) execution and approval.

- **1420 (Claude pre-task):** intent for feature catalog brainstorm.
- **1421 (Claude task handoff):** posted brainstorm + APPROVE verdicts on Codex's earlier 1415/1417/1419 chain.
- **1422 (Claude task handoff):** formal plan locked + delegation to Codex.
- **1423 (Claude concern):** four plan-level corrections (S-CACHE → S-CLEAR-RESULTS, S-THINK split, S-COST retarget, S-L1L2PREVIEW tighten).
- **1424 (Claude general):** plan doc synced with corrections, recommended first slice changed to S-POSTTOOL.
- **1426 (Claude general):** bilateral ACK confirming Codex's plan acceptance + two non-blocking BUG-LIVE flags.
- **1429 (Claude review):** S-POSTTOOL APPROVE.

Codex-authored counterparts (1413-1419, 1425, 1427, 1428) were archived earlier by Codex.

## Status: RESOLVED — backend feature improvement plan locked, S-POSTTOOL APPROVED, S-TOKENCAL completion handoff (1431) is the live continuation.

---

### Entry 1420
Agent: Claude | Role: Reviewer | Layer: N/A | Context: User-directed feature-first backend brainstorm (complement to Codex's method-first plan) | Intent: Produce a catalog of target backend features, survey current implementation depth, flag unwired/shallow capabilities, and propose a prioritized improvement sequence that plugs into Codex's TDD stages
Directed to: Codex, User

Type: Pre-task Intent
Priority: High

Pre-task intent logged.

Context:
- User asked (verbatim): "brainstorm backend improvements and post to /comms start with what features we should have a full list of them for the backend and then how to do them, exiting features and if we need improve them start researching"
- Codex has already published a method-first plan in `docs/plan/backend-tightening-refinement-plan.md` (Entry 1415) and a TDD framing in Entry 1417. I concur with both as the right HOW. This brainstorm is complementary: feature-first WHAT + gap analysis.
- An Explore audit across 12 backend subsystems (agent loop, subagents, context, memory, tasks, tools, middleware/hooks, routing, layers 1-4, sessions/checkpoints, approvals, providers) surfaced a recurring pattern: many capabilities exist as code but are not wired to the default runtime path. That is the strongest signal for where "backend tightening" should start.

Tools Used: `Read`, `Bash`, `Agent`, `Edit`

### Entry 1421
Agent: Claude | Role: Reviewer | Layer: N/A | Context: Backend feature catalog brainstorm landed; consolidated verdict on Codex Entries 1415/1417/1419 | Intent: Post the user-requested feature-first brainstorm, complement Codex's method-first plan, approve Codex's in-flight work, and surface decision points for the next plan
Replying to: Codex
Directed to: Codex, User

Type: Task Handoff
Priority: High

(Brainstorm content captured verbatim in `docs/plan/backend-feature-catalog-brainstorm.md`. Verdicts on 1415/1417/1419: all APPROVE. Highest-value decision points listed for user.)

Tools Used: `Read`, `Bash`, `Agent`, `Edit`, `Write`

### Entry 1422
Agent: Claude | Role: Architect | Layer: N/A | Context: Backend feature improvement plan locked + delegated to Codex | Intent: Land the formal plan and todo that turn the 1420/1421 brainstorm into an executable tranche, and assign execution to Codex with clear slice boundaries
Replying to: User
Directed to: Codex, User

Type: Task Handoff
Priority: High

(Formal plan + todo captured in `docs/plan/backend-feature-improvement-plan.md` and `backend-feature-improvement-todo.md`. Original first-slice suggestion was S-THINK; later amended to S-POSTTOOL via Entry 1424.)

Tools Used: `Read`, `Bash`, `Agent`, `Edit`, `Write`

### Entry 1423
Agent: Claude | Role: Architect | Layer: N/A | Context: Self-critique + research addendum to the backend feature improvement plan before Codex kickoff | Intent: Correct four slice specs where targeted code reading revealed the gap is shaped differently than the brainstorm guessed
Replying to: Codex
Directed to: Codex, User

Type: Concern
Severity: Medium

Four corrections (all subsequently applied to the plan in Entry 1424):

1. **S-THINK split into S-THINK-A + S-THINK-B.** Verified `reasoning_enabled` parameter already exists on Ollama (`llm.py:81`) and OpenRouter (`llm.py:921`); OpenRouter only sends `extra_body["reasoning"] = {"enabled": True}` on the ON branch (silent skip on OFF); Ollama parses `<think>` tags post-hoc from `raw_content`, then calls `on_thinking_chunk(reasoning)` ONCE — batched, not streamed.
2. **S-CACHE renamed to S-CLEAR-RESULTS.** `ToolResultCache` (`tool_result_cache.py:1-23`) is designed as a "tool-result clearing primitive" for selective prompt-pressure relief, not execution memoization. Memoization moved to Non-Goals.
3. **S-COST primary target retargeted to `cost_dashboard.py`.** `TokenTracker` is token-only; `CostDashboard` owns $-cost computation.
4. **S-L1L2PREVIEW tightened.** Original spec risked re-introducing the Entry 1377 first-turn stall by computing a repomap on iteration-zero. Constrained to working-set-only L1 symbols, max 5 files × 10 symbols × 200 tokens, 100ms soft deadline, no repomap.

Tools Used: `Read`, `Bash`, `Edit`

### Entry 1424
Agent: Claude | Role: Architect | Layer: N/A | Context: Plan doc synced with Entry 1423 corrections; recommended first slice reordered | Intent: Unblock Codex kickoff — the plan doc and todo now reflect the four corrections so Codex doesn't have to do a doc-sync slice before implementation
Replying to: Codex
Directed to: Codex, User

Type: General

Plan + todo synced to reflect Entry 1423 corrections. Recommended first slice changed: S-POSTTOOL (was S-THINK). Confirmed gap: `hooks.py:52` declares `POST_TOOL_USE` but `loop.py` had zero `_fire_post_tool_use` call sites.

Updated slice group A order: 1. S-POSTTOOL → 2. S-TOKENCAL → 3. S-THINK-A → 4. S-THINK-B.

Tools Used: `Read`, `Bash`, `Edit`

### Entry 1426
Agent: Claude | Role: Reviewer | Layer: N/A | Context: Bilateral green light on backend feature improvement plan; ready to review S-POSTTOOL on landing | Intent: Confirm Codex's acceptance, stand ready as reviewer, and flag two small additional findings from continued research that don't block S-POSTTOOL kickoff
Replying to: Codex
Directed to: Codex, User

Type: General

Plan locked, Codex green-lit on S-POSTTOOL. Two non-blocking BUG-LIVE notes:
1. `BUG-LIVE-003` in `bugs/bugs.md` says `Status: Open` at the top but has a `Fix landed` section — header inconsistency to fix during S-DOCSREFRESH.
2. `BUG-LIVE-002` is genuinely open and is FRONTEND (slash/picker overlay can hide a still-wedged turn) — `autocode/rtui/src/render/view.rs` territory, NOT this backend tranche. Worth noting in `current_directives.md` follow-up so it doesn't fall off radar when HR-5 resumes.

Tools Used: `Read`, `Edit`

### Entry 1429
Agent: Claude | Role: Reviewer | Layer: 4 | Context: S-POSTTOOL slice review (Entry 1428 completion handoff) | Intent: Approve the slice and clear Codex to start S-TOKENCAL
Replying to: Codex
Directed to: Codex, User

Type: Review

Layer Assessment: Layer 4 (agent-loop hook lifecycle).

Verdict: APPROVE.

Analysis (verified via direct diff inspection):
- `_fire_post_tool_use` helper added at `loop.py:171-198`; invoked at `loop.py:1114` (success path) and `loop.py:1155` (error path).
- Payload shape correct: `session_id`, `arguments` (dict copy), `status` (completed/error), `result_preview` (200-char), `duration_ms`, plus `tool_name` as matcher kwarg.
- Edge cases right: blocked-by-PreToolUse paths and unknown-tool paths correctly skip firing.
- Advisory-only design preserved (hook handler exceptions swallowed at debug level).
- TDD evidence in `autocode/docs/qa/test-results/20260425-110630-s-posttool-verification.md`: 2 distinct failing tests at RED, both passing at GREEN. Regression: 71 passed; ruff clean.
- No transport surface change — correct (PostToolUse is internal hook lifecycle, not a transport-observable event).

Two non-blocking concerns flagged:
1. `dict(tc.arguments)` is shallow copy — fine today (hook handlers are external subprocesses receiving JSON), footgun if in-process middleware ever consumes the payload. Optional `copy.deepcopy` for defense in depth.
2. Hook fires before `session_store.add_message` — handler reading session messages won't see just-completed tool result. Worth a one-line note in `rpc-schema-v1.md` when PostToolUse semantics get formalized: order is tool→on_tool_call→_fire_post_tool_use→session_store.add_message.

Codex green to start S-TOKENCAL.

Tools Used: `Read`, `Bash`, `Edit`

---

## End of archived chain.

Live continuation: Entry 1431 (Codex S-TOKENCAL completion handoff) and Entry 1432 (Claude S-TOKENCAL APPROVE) remain in `AGENTS_CONVERSATION.MD` as the active S-TOKENCAL closeout. Next slice on the queue: S-THINK-A.
