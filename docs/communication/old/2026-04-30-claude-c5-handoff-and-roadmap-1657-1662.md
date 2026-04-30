# Claude C5 Handoff + Forward-Roadmap Synthesis (Entries 1657 + 1662)

> **SUPERSEDED — see `docs/communication/old/2026-04-30-c5-c6-builder-handoff-prep-1657-1665.md` for the authoritative unified archive of the full pre-builder thread (Entries 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1665).**
>
> This file was a partial draft created by Claude during the cross-author cleanup turn. Codex's unified archive (linked above) was created in the same minute and covers all 9 entries with proper bilateral context. Per AGENT_COMMUNICATION_RULES.md "NEVER delete archived files", this file is preserved as a permanent record but is not referenced by `AGENTS_CONVERSATION.MD`.
>
> **Original archive note:** Archived 2026-04-30 by Claude per user authorization (cross-author cleanup approved in user message after Codex Entry 1665 acceptance).
>
> **Resolution status:** Both entries fully consumed by Entry 1664 (Claude consolidated review + plan + answers) and Entry 1665 (Codex acceptance + final TODO). Authoritative post-commit reference doc spawned at `docs/plan/post-c7-stable-commit-roadmap.md`.

---

### Entry 1657
Agent: Claude | Role: Reviewer/Architect | Layer: cross-cutting program coordination | Context: User-directed momentum push to stable commit ("lets finish the work so we can commit a stable version to git") + interim archive of Entries 1616-1656 (41 entries, full Tranche 4 progress through 8/8 LSP language matrix) | Intent: Lean-channel reset; embed C5.G4 active handoff; compact remaining-work roadmap to C7.GATE stable commit
Replying to: User
Directed to: Codex, OpenCode, User

Type: Task Handoff (C5.G4 active) + Status Roadmap (compact, post-archive)

## Archive executed

Entries 1616-1656 (41 entries) archived to `docs/communication/old/2026-04-29-tranche-4-c4-c5-language-matrix-1616-1656.md` per Entry 1656 recommendation + user direction. Channel reset to lean state for the final stretch.

**Archive contents (one-line summary):** C4.G2 ranked repo-map → C4.G7' git-aware staging + repo-wide forbidden-git enforcement → C4.GATE substrate-pass (COMPLETE_WITH_FAILURES, deferred clean rerun in §6.6) → C5.G3.0 LSP framework → C5.G3.1 Java → C5.G3.2-3 JS+TS → C5.G3.4-6 C+Kotlin+Python → C5.G3.7-8 Go+Rust → **8/8 language matrix complete.**

## Done since `1700d66 Closes backend v2` (uncommitted)

| Slice | Verification artifact |
|---|---|
| Packet 3 — 16 feature contracts + index + cross-link sync | `20260427-121130-packet3-feature-contracts.md` |
| C4.G1 — atomic checkpoint + `/rollback` (initial + fix slice) | `20260428-04xxxx-c4-g1-*` |
| C4.G2 — ranked repo-map + `/repomap` | `20260428-062004-c4-g2-repomap-upgrade.md` |
| C4.G7' — git-aware staging + repo-wide forbidden-git scan | `20260428-064617-c4-g7-git-aware-staging.md` |
| C4.GATE — substrate-pass | `20260428-103751-c4-gate-*` + `20260428-202255-b7-b30-full-sweep-summary.md` |
| C5.G3.0 — LSP framework | `20260429-130737-c5-g3-0-*` |
| C5.G3.1 — Java | `20260429-072748-c5-g3-1-lsp-java-jdtls.md` |
| C5.G3.2-3 — JS + TS | `20260429-075602-c5-g3-{2,3}-*.md` |
| C5.G3.4-6 — C + Kotlin + Python | `20260429-083000-c5-g3-{4,5,6}-*.md` |
| C5.G3.7-8 — Go + Rust | `20260429-095412-c5-g3-{7,8}-*.md` |

**Test surface:** `2071 passed, 12 skipped` full unit suite (gained ~80 tests since `1700d66`); `212 passed` Rust TUI cargo; `199 passed` benchmark harness tests; 6+ self-skipping LSP PTY smokes; repo-wide forbidden-git scan green; `git diff --check` clean.

## ACTIVE NOW — C5.G4 auto-verify-after-edit loop

Auto-flow per Entry 1604 sequencing rule. Final C5 substantive slice. The consumption layer for the LSP substrate: edit → diagnostics catch → agent self-corrects → diagnostics clean.

### Atomic task list (~17 tasks)

**Module:**
- [ ] `autocode/src/autocode/agent/auto_verify.py` — `verify_after_edit(edited_files: list[Path]) → VerifyResult` running LSP diagnostics; returns errors/warnings with file/line/severity
- [ ] Result feeds back into agent loop as system message on failure

**Loop integration:**
- [ ] PostToolUse hook in `autocode/src/autocode/agent/loop.py` for `mutates_fs=True` tools (sibling to G1 atomic checkpoint + G7' staging hooks)
- [ ] After successful edit, call `verify_after_edit` on touched files; on error, feed `Verification failed: <diagnostics>` back as system message
- [ ] Iterate up to N=3 (configurable); on still-failing after N: emit `on_warning`, **NO auto-rollback** (rollback is user-confirmable per G1 contract)

**Configuration:**
- [ ] `AgentConfig.verify` block in `autocode/src/autocode/config.py`: `enabled` (default true), `max_iterations` (default 3), `on_failure` (default `surface_to_user`; alternatives `rollback`, `continue`), `languages` (default all enabled)
- [ ] `/verify on|off|status` slash command

**TDD evidence:**
- [ ] RED: edit introduces syntax error → diagnostics catch → agent fixes → diagnostics clean
- [ ] RED: persistent error after 3 iterations → surface warning, NO auto-rollback
- [ ] RED: edit on language without LSP adapter → no-op, no error
- [ ] RED: `/verify off` → loop bypassed
- [ ] RED: cost-cap halts iteration mid-cycle
- [ ] GREEN: all RED pass

**Validation + Constraint #8:**
- [ ] `uv run pytest autocode/tests/unit/test_auto_verify.py -v` passes
- [ ] PTY smoke `pty_smoke_auto_verify.py` exercising edit → verify → fix loop end-to-end (Python adapter as test driver)
- [ ] Full unit suite still green: target ~`2090+ passed`
- [ ] `git diff --check` clean
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-c5-g4-auto-verify.md`
- [ ] Update `docs/features/backend_features.md` + `docs/features/validation-output.md` (Packet 3 contract reflects actual G4 implementation) + `docs/architecture.md`
- [ ] Post Review Request comms entry directed to Claude

### Hard constraints

- **No auto-rollback.** Verify failure surfaces warning + offers `/rollback`; user-confirmable per G1 contract.
- **First-turn latency invariant** preserved (verify is PostToolUse, not session bootstrap).
- **No tree-mutating git ops** — repo-wide source scan from C4.G7' enforces mechanically.
- **Constraint #8** docs+artifact-before-review.

### Builder routing

Default — OpenCode primary, Codex fallback. Codex has been carrying through C5; user can keep momentum or redirect.

## Remaining slices to stable commit (compact)

| # | Slice | Notes |
|---|---|---|
| 1 | **C5.G4** auto-verify | ACTIVE — handoff above |
| 2 | C5.GATE | cumulative regression + LSP smoke |
| 3 | C6.G5 | headless `--json` mode |
| 4 | C6.G6 | Layer 4.5 cost-aware router (auto-only; user-custom config DEFERRED §6.4) |
| 5 | C6.GATE | cumulative + cost-routing canary |
| 6 | C7.G8 | watch mode (`# AUTOCODE: <instruction>` marker) |
| 7 | C7.G9 | hybrid Goose-compatible recipe schema |
| 8 | C7.G10 | ambient observability |
| 9 | C7.G11 | perf budget enforcement |
| 10 | C7.G12 | graceful degradation |
| 11 | C7.G13 | sub-agent isolation via `git worktree add` (uses `subagents-tasks.md` shape) |
| 12 | C7.G14 | enhanced doctor diagnostics |
| 13 | C7.G15 | static JSON marketplace registry (local-only) |
| 14 | **C7.GATE** | final release-grade regression + benchmark + closeout — user commits here |

**Estimated remaining: ~10-12 sessions.** C7 super-batches available if user wants acceleration (G8+G9+G10 / G11+G12 / G13+G14+G15).

## Deferred items (non-blocking for stable commit)

- §6.1-6.3: Cloud sandbox / A2A / GitHub-PR (Tier 3, no expected revive)
- §6.4: User-custom cost-routing config (partial-deferred from C6.G6)
- §6.5: Repo-map prompt-builder injection (partial-deferred from C4.G2)
- §6.6: Clean B7-B30 rerun (C4.GATE carryover; gateway-gated)

## Pre-commit checklist (executed at C7.GATE close)

- [ ] All slices C5.G4 → C7.GATE bilateral APPROVE
- [ ] Final C7.GATE regression sweep green: full unit + benchmark + cargo + Track 1 + Track 4 + PTY smokes
- [ ] Top-level state docs synced: `current_directives.md` + `EXECUTION_CHECKLIST.md` + `PLAN.md` + `docs/features/backend_features.md`
- [ ] `DEFERRED_PENDING_TODO.md` reflects final state
- [ ] Comms log archived: 1657-onwards into final archive at C7.GATE
- [ ] User runs `git commit` (agents do not commit)

## Out of scope (per "only backend" direction)

- New TUI kickoff Packets 1, 2, 4, 5 — stay PARKED
- Rust TUI consumption of new backend features — future post-Tranche-4 work

## Standing reminders

- Repo-wide forbidden-git scan from C4.G7' enforces mechanically — any new slice introducing forbidden git ops will fail this gate
- First-turn latency invariant — preserve in C5.G4 + all C6 + C7 work
- Project-local symbol determinism — applies to all language adapters and any LSP-consuming code
- Optional-doctor semantics — carry forward
- `docs/architecture.md` doc sync — include in initial Review Request batch artifact

Tools Used: `Read`, `Edit`, `Bash`, `Grep`

---

### Entry 1662
Agent: Claude | Role: Reviewer/Architect | Layer: cross-cutting program coordination | Context: forward-roadmap synthesis from `00-INDEX.md`, `01-tier1-prompt-cache.md`, `02-tier2-app-server-protocol.md`, `03-tier3-memory-architecture.md`, `04-tier4-future-tracks.md`, `05-cross-cutting-concerns.md` (drafted 2026-04-30) vs the active C7.GATE stable-commit path | Intent: propose prioritized sequencing for the new 4-tier roadmap, deconflict with in-flight Tranche 4 slices, surface 3 user decisions before any post-commit work begins
Replying to: User
Directed to: User, Codex

Type: General (strategic recommendation; not a review verdict)

## TL;DR

**Do not interrupt Tranche 4.** Finish C5.G4 → C5.GATE → C6 → C7.GATE per Entry 1657, user commits stable. The new 4-tier roadmap is a **post-stable-commit program**. Three small contract updates align Tranche 4 with the new roadmap so we don't ship work that needs immediate re-do. The remaining ~5 weeks of new work sits behind the commit. C5.G4 + C5.GATE review verdicts will land in a follow-up entry, separate from this strategic post.

## Active state (no change requested)

- C5.G4 awaiting Claude review (Codex Entry 1659; 8/8 unit, full suite `2079 passed, 12 skipped`, PTY smoke green, artifact stored)
- C5.GATE awaiting Claude review (Codex Entry 1661; 8/8 LSP language smokes + auto-verify smoke green; full suite + 77 benchmark + clean diff)
- Per Entry 1657 remaining queue: C5.GATE close → C6.G5 → C6.G6 → C6.GATE → C7.G8…C7.G15 → C7.GATE → user commits

## Cross-check: new roadmap vs Tranche 4

| New tier | Maps to Tranche 4? | Action |
|---|---|---|
| Tier 1.1 — cache breakpoint injection (`layer4/llm.py`) | No — net new | Post-commit; never ship without 1.2 (cross-cutting §"Sequencing risks") |
| Tier 1.2 — stable/dynamic boundary in `agent/prompts.py` | No — net new | Atomic with 1.1 |
| Tier 1.3 — `/cost` cache breakdown + reasoning tokens | **Extends shipped S-COST** (archived Entries 1469-1475) | Additive; ships with 1.1+1.2 |
| Tier 2.1 — Item/Turn/Thread refactor (44 RPC structs → 3 primitives) | No — would replace `rtui/src/rpc/protocol.rs` + Python dispatcher | **DEFER** — needs concrete 2nd client surface to justify |
| Tier 2.2 — Unix socket + WebSocket transports | Partial overlap with shipped Phase-3 stdio + TCP host adapters | Defer; depends on 2.1 |
| Tier 2.3 — `turn/steer` mid-flight input | No | Defer; depends on 2.1 |
| Tier 3.1 — file-system 3-layer memory (replaces SQLite `MemoryStore`) | No — but consumes existing `consolidation.py` autoDream | Post-commit; biggest user-perceived value |
| Tier 3.2 — Session Notes / compaction Path A | No | Stacks on 3.1 |
| Tier 3.3 — verify-before-use prompt section (~50 LOC) | No | Bundle with 1.2 (touches `prompts.py`) |
| Tier 4.1 — KAIROS proactive mode | No | Strict feature flag; ≥ 4 weeks Tier-1.3 telemetry first |
| Tier 4.2 — ephemeral fork | No | Depends on 2.1 |
| Tier 4.3 — sticky environments | No | Depends on 2.1 |
| Tier 4.4 — headless `--json --output-schema` | **Already C6.G5** | **Adopt Tier 4.4 NDJSON spec as the C6.G5 contract** — see Update 1 below |

## Three Tranche-4 contract updates I'm proposing

### Update 1 — adopt Tier 4.4 NDJSON spec for C6.G5 headless mode

The new roadmap's Tier 4.4 specifies one JSON object per line with a `type` discriminator (`thread_started`, `turn_started`, `item_started`, `item_delta`, `item_completed`, `turn_completed`), reasoning tokens in `turn_completed.usage`, and an `autocode generate-schema` subcommand for typed clients. Ratifying this shape now means downstream Tier 4.4 is **already shipped** when we close Tranche 4 — no later re-cut.

Caveat: the `item.kind` enum in Tier 4.4 references the Item/Turn/Thread primitives from Tier 2.1 (which we're deferring). For C6.G5, define a forward-compatible **subset** of `kind` values that map cleanly onto today's RPC events (`agent_message`, `tool_execution`, `plan_update`, `approval`). Document the unused values (`reasoning`, `subagent_delegation`, `diff`) as a documented extension surface so when Tier 2.1 eventually lands, no breaking version bump is forced.

### Update 2 — make C6.G6 cost-aware router cache-pricing-aware in shape

C6.G6 (Layer 4.5 cost-aware auto-router) is the natural consumer of Tier 1.3's `billable_input_cost_factor` (weighted multiplier accounting for cache reads at 0.10x, writes at 1.25x). Build the router's cost-comparison primitive to **accept a cache-multiplier hook now**, even if the cache flag is dark. When Tier 1.1+1.2 ship post-commit, no router refactor is needed.

Today: `effective_cost = provider × model × prompt_tokens × input_price`
Post-Tier-1: same comparison × `billable_input_cost_factor` (=1.0 today, drops post-cache-warmup).

### Update 3 — fold Tier 3.3 verify-before-use into Phase 1 post-commit (NOT inside Tranche 4)

50 lines of `STABLE_INSTRUCTIONS` addition stating "memory is a hint, not truth; verify with `read_file`/`list_files` before acting." Zero risk in isolation, but it touches `prompts.py`. **Bundle it with Tier 1.2's stable/dynamic boundary refactor** so `prompts.py` is touched once, not twice. Don't slip it into a C7 polish slice — keep Tranche 4 substrate stable.

## Post-commit program (proposed sequencing)

This deviates from the roadmap's own "best-bang-for-buck" order (`1.1 → 1.2 → 1.3 → 3.3 → 2.1 → 2.3 → 2.2 → 3.1 → 3.2 → 4.4 → 4.2 → 4.3 → 4.1`) on one axis: **Tier 3 before Tier 2.** The roadmap acknowledges this in §"Things I'd do differently": "Memory before App Server. Tier 3 doesn't depend on Tier 2 and the 3-layer memory delivers immediately visible quality." Given no concrete 2nd-client surface signal from User, the speculative Tier 2.1 ROI doesn't compete with concrete Tier 3 user-perceived value.

### Phase 1 — Prompt Cache + verify-before-use (1 week, ~270 LOC)

| Slice | Action | Acceptance |
|---|---|---|
| Tier 1.1 | Inject `cache_control: ephemeral 1h` on stable prefix in `OpenRouterProvider`; capture `cache_creation_input_tokens` + `cache_read_input_tokens` | first call: write_tokens > 0; second call within 5min: read_tokens ≥ 1024 |
| Tier 1.2 | Refactor `agent/prompts.py` into `STABLE_INSTRUCTIONS` + `build_stable_prefix` + `build_dynamic_tail` with `CACHE_BOUNDARY_MARKER`; deterministic tool-def serialization (`sort_keys=True, separators=(",",":")`) | `tests/unit/test_prompt_cache_boundary.py` proves no time/path/git/todo strings leak above the marker |
| Tier 1.3 | Extend `TokenTracker` with `cache_creation_tokens` + `reasoning_tokens` + `billable_input_cost_factor`; persist on session pause/resume; `/cost` shows cache breakdown | `/cost` displays effective multiplier < 1.0 after warmup |
| Tier 3.3 | (folded in) Append verify-before-use section to `STABLE_INSTRUCTIONS` | LLM-eval: model re-reads file before relying on stale memory |

**Atomic constraint:** PR includes 1.1 + 1.2 together. Shipping 1.1 alone would bust cache every turn (current date / git status / cwd in stable region) → user sees 25% cache-write premium with zero read benefit.

### Phase 2 — File-system Memory (3 weeks, ~1100 LOC)

| Slice | Action | Acceptance |
|---|---|---|
| Tier 3.1 | New `src/autocode/session/memory_fs.py` (~600 LOC) — 3-layer `MEMORY.md` (≤200 lines) + `memory/<topic>.md` + `logs/YYYY/MM/YYYY-MM-DD.md`; new tools `memory_read_topic`, `memory_write_topic`, `memory_grep_logs`, `memory_index_show`; one-shot SQLite `MemoryStore` → topic-files migration script; deprecate (don't drop) `agent/memory.py` | `MEMORY.md ≤ 200 lines` after 50 sessions; topic files load on demand; daily logs append-only |
| Tier 3.2 | New `session/session_notes.py` (~250 LOC); compaction Path A integration in `agent/context.py` | Path A chosen ≥ 80% of compaction events once 10k tokens consumed |

**Risk:** cross-cutting §"Risk: Tier 3.1 migrates SQLite memories to files but agent still references old SQLite" — re-implement `memory_list` against `MemoryFS` or remove with a deprecation cycle. Don't leave the agent calling a stale tool.

### Phase 3 — DEFERRED: Item/Turn/Thread (conditional)

Per cross-cutting §"Things I'd do differently" #3: "If no second client is on the horizon, you're paying ~2 weeks of refactor for purely speculative future value. Defer if no concrete client surface is planned within 6 months."

**Hold-release trigger** — ship Tier 2.x only when ≥ 1 of:
- A concrete Tauri / Electron / web / IDE plugin / programmatic third-party consumer is being kicked off
- `rtui/src/rpc/protocol.rs` has accumulated > 60 ad-hoc structs (currently 44; growth driver = TUI parity work resuming)
- Two human or AI agents need to consume the backend concurrently from different surfaces

If none hold ~3 months post-commit, re-evaluate against the AI verification harness (`docs/plan/ai-verification-harness-plan.md`, untracked in `git status`) — that may be the better Phase-3 candidate.

### Phase 4 — Feature-flag tier (non-blocking, default-off)

| Slice | Default | Promotion criterion |
|---|---|---|
| Tier 4.1 KAIROS | `AUTOCODE_FEATURE_KAIROS=false` | ≥ 4 weeks Tier-1.3 telemetry baseline + observability story; cross-cutting §"KAIROS won't ship cleanly without a strong observability story first" |
| Tier 4.2 ephemeral fork | gated | Requires Tier 2.1 |
| Tier 4.3 sticky env | gated | Requires Tier 2.1 |

## Three open questions for User

1. **Tier-1 timing:** strictly post-C7.GATE, or interleave between C5.GATE close and C6.G5? Interleave gives Tranche 4 itself the cost cut, but adds a `prompts.py` substrate change mid-tranche. **My recommendation: strictly post-commit.** Tranche 4 substrate stays stable.
2. **2nd client surface:** any concrete Tauri / Electron / web / IDE plugin / programmatic consumer planned within 6 months? Decides whether Tier 2.1 belongs in Phase 2 or stays deferred.
3. **AI verification harness vs new roadmap:** `docs/plan/ai-verification-harness-plan.md` is staged untracked in `git status` (7 milestones, scenario generator + sandbox + agent runner + grader). Does it slot before, after, or inside Phase 2? Both compete for the same post-commit attention window. The memory in `project_ai_verification_harness.md` flags this as PROPOSED, post-Tranche-4.

## Cross-cutting concerns I'm carrying forward unchanged

Everything in `05-cross-cutting-concerns.md` — testing strategy, telemetry, migration safety, rollback paths, performance budgets, sequencing risks, documentation deliverables — applies as written when each tier ships. No deviations proposed.

## Standing Tranche-4 reminders (unchanged)

- Repo-wide forbidden-git scan from C4.G7' enforces mechanically
- First-turn latency invariant preserved across all C6/C7
- Constraint #8: every slice updates `docs/features/backend_features.md` + stores QA artifact BEFORE Review Request
- Per-author archive duty — I'll archive Entry 1657 chain on user direction once C7.GATE stable commit lands

## Next concrete actions (no work begins on this plan without user signoff)

1. **Claude (me) — next entry:** deliver C5.G4 + C5.GATE review verdicts so the active queue continues to advance toward C7.GATE.
2. **User:** answer the 3 open questions above, OR redirect priorities entirely. No post-commit work starts until that signal lands.
3. **Codex (after Claude C5 verdicts):** if Updates 1+2+3 are ratified, the C6.G5 + C6.G6 contracts in `docs/plan/backend-robustness-tranche-4-checklist.md` get updated atomically with the kickoff slice. Otherwise C6.G5 ships as currently specified and Phase 1 post-commit owns full Tier 4.4 conformance work.

Tools Used: `Read`
