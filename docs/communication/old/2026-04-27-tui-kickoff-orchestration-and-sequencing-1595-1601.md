# AutoCode Backend-First + Minimal Rust TUI Kickoff — orchestration + sequencing — Entries 1595-1601

**Archived 2026-04-27 (superseded by Codex Entry 1602 consolidated review/handoff + Claude Entry 1603 APPROVE in AGENTS_CONVERSATION.MD).**

These entries scattered the new TUI kickoff direction across an orchestration entry (1595), 5 per-packet Task Handoffs (1596-1600), and a sequencing-decision ratification (1601). User direction 2026-04-27 late: archive the scattered set; the consolidated active direction lives in Codex Entry 1602 + Claude Entry 1603.

Trail:

- 1595 — Claude orchestration: 5 work packets, OPEN QUESTION on Tranche 4 reconciliation, OPEN QUESTION on Builder identity (both resolved this turn)
- 1596 — Claude Packet 1 handoff (repo audit) — PARKED for after Tranche 4
- 1597 — Claude Packet 2 handoff (current architecture doc) — PARKED
- 1598 — Claude Packet 3 handoff (16 feature contracts) — **PROMOTED to active prep slice; full Packet 3 spec + atomic sub-task list lives in this archive file**
- 1599 — Claude Packet 4 handoff (20 fixtures) — PARKED
- 1600 — Claude Packet 5 handoff (Rust TUI plan) — PARKED
- 1601 — Claude sequencing ratification: Tranche 4 first with Packet 3 prep slice; Packets 1/2/4/5 parked; Builder=OpenCode primary, Codex fallback

**Resolution path for Codex Entry 1602's references** to "Entry 1598" and "Entry 1601": both live in this archive file below. Builder picking up Packet 3 should read the Entry 1598 section here for the full atomic sub-task list (structure spec, typed contract models, exit gate, hard constraints).

**Source-of-truth program brief remains at** `docs/plan/backend-first-tui-kickoff-2026-04-27.md`.

---

### Entry 1595
Agent: Claude | Role: Reviewer/Architect | Layer: N/A program kickoff | Context: New user-supplied program brief — "AutoCode Backend-First + Minimal Rust TUI Kickoff" (5 work packets) | Intent: Announce the new program, raise the Tranche 4 reconciliation question, lay out 5 packet handoffs (Entries 1596-1600), and request user authorization to kick off Packet 1
Directed to: User, OpenCode

Type: Task Handoff (program kickoff) + Concern (open question)

## Pre-task intent (this orchestration)

Saved verbatim user-supplied kickoff prompt to `docs/plan/backend-first-tui-kickoff-2026-04-27.md` as the program-brief source-of-truth. No other code/doc changes, no commits, no tags, no resets, no checkouts.

## Program at a glance

User's directive (verbatim text in the saved doc): start the next AutoCode implementation phase by establishing **backend/TUI contracts, audit current implementation, remove Go/BubbleTea-era ambiguity, create deterministic fixtures for the new Rust TUI** — explicitly **not** by jumping into visual TUI coding. Five work packets:

| # | Packet | Deliverable | Entry |
|---|---|---|---|
| 1 | Repo audit + architecture freeze | `docs/audits/tui_backend_readiness.md` | 1596 |
| 2 | Current architecture document | `docs/tui/current-architecture.md` | 1597 |
| 3 | Normalize 16 feature contracts | `docs/features/<feature>.md` × 16 | 1598 |
| 4 | 20 deterministic backend-event JSONL fixtures | `fixtures/tui/<scene>.jsonl` × 20 | 1599 |
| 5 | Minimal Rust TUI plan (no implementation) | `docs/tui/minimal-rust-tui-implementation-plan.md` | 1600 |

## OPEN QUESTION (Directed to: User) — Tranche 4 reconciliation

`docs/plan/backend-robustness-tranche-4-plan.md` is READY awaiting C4.G1 kickoff (per `current_directives.md`). It targets backend robustness (multi-language LSP, atomic snapshots, headless, cost-aware routing, watch mode, recipes, marketplace). The new kickoff targets TUI shell + backend contracts.

**Surface overlap:** agent events / permissions / risk / checkpoints+restore (Tranche 4 G1) / recovery / validation streams / subagents+tasks / sandbox+policy (Tranche 4 G2).

**Three possible reconciliations** — please pick one:

- **(a) Supersede Tranche 4.** New kickoff replaces it; Tranche 4 plan moves to `docs/archive/` until further notice.
- **(b) Run in parallel.** OpenCode does this kickoff (audit-only, no impl); Codex (or whoever you redirect to Builder) starts Tranche 4 C4.G1 in parallel. No surface conflict because this kickoff is audit/contracts only.
- **(c) Sequence.** Run this kickoff first (Packets 1-5, no impl). Tranche 4 plan gets refreshed against the new contracts before C4.G1 starts.

Default if you don't pick: **(c)**, because this kickoff is contracts-first and Packets 3+5 will firm up exactly the surfaces Tranche 4 G1+G2 will touch.

## OPEN QUESTION (Directed to: User) — Builder identity

Defaulting to **OpenCode** (per role table in `AGENT_COMMUNICATION_RULES.md`). For Tranche 4 you redirected Codex to Builder. If you want the same here, say so and I'll reroute Entries 1596-1600.

## Operating rules carried into Entries 1596-1600

1. **No implementation kicks off until you authorize Packet 1.**
2. **Per-packet exit gate (Tranche 4 Constraint #8):** every packet updates an inventory doc AND stores a verification artifact at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<packet-id>-<short>.md` BEFORE the Builder posts a Review Request.
3. **Strict no-tree-mutating-git policy per `AGENTS.md`.** Permitted: `status/diff/log/show/fetch/stash list|show/worktree add|list|remove/config (read)/add`. Forbidden: `commit/push/tag/reset/rebase/merge/pull/checkout (any)/restore/stash push|pop|apply/apply/clean`. Even within Packet 1 audit commands (`git log`, `git show`) — read-only.
4. **Reuse existing assets, don't reinvent.** `autocode/tests/tui-references/` already has 14 named scenes (`ready, active, multi, plan, review, cc, recovery, restore, sessions, palette, diff, grep, escalation, narrow`) live as PTY gates with deterministic triggers (manifest auto-generated from `tui-references/AutoCode TUI _standalone_.html`). Packet 4's 20 fixtures must map to these (overlap on 14, 6 are net-new: `queue-drawer, plan-inline, live-drawer, protected-path, slash-picker, file-picker, symbol-picker, search-focus = grep, transcript-review, command-center = cc, multitasking = multi, restore-focus = restore, session-browser = sessions, command-palette-focus = palette, diff-focus = diff` — Builder will reconcile final overlap in Packet 4).
5. **Hard constraints from prompt** echoed in every packet: forbidden = centered overlays, dimmed modal backdrops, default-state side rail, default-state queue drawer, hidden-while-streaming composer, human-text parsing for backend state, old Go/BubbleTea as target architecture, decorative spinner verbs, dashboard/card UI, command center as default. Required = typed events over string parsing, fixtures before live integration, minimal default TUI, explicit keyboard controls, contract+fixture tests.
6. **User-locked render contract (2026-04-22)** is a hard constraint for Packet 5: full-screen render, terminal resizing works, multiple sizes validated, native scrollback preserved. Codified in `autocode/docs/qa/test-results/20260422-131037-tui-fullscreen-hard-requirements-pass.md`.

## What's NOT done in this entry

- No code or test changes.
- No commits, tags, pushes, resets, or checkouts.
- No implementation work begun on any packet.
- The Tranche 4 plan files were NOT modified — their disposition depends on the user's reconciliation answer above.

## Sequencing recommendation

- Packet 1 first (audit unblocks the others).
- Packets 2 and 3 may parallelize after Packet 1.
- Packet 4 depends on Packet 3.
- Packet 5 depends on Packets 1-4.

## Files involved (Reviewer-side this entry)

- Created: `docs/plan/backend-first-tui-kickoff-2026-04-27.md`
- Read-only: `current_directives.md`, `EXECUTION_CHECKLIST.md`, `PLAN.md` (top), `autocode/tests/tui-references/README.md` + `manifest.yaml` + `scene_presets.py`, `AGENT_COMMUNICATION_RULES.md`.

Tools Used: `Read`, `Write`, `Edit`, `Bash`, `grep`

---

### Entry 1596
Agent: Claude | Role: Reviewer/Architect | Layer: N/A program kickoff | Context: AutoCode Backend-First + Minimal Rust TUI — Work Packet 1 (repo audit + architecture freeze) | Intent: Hand off Packet 1 to Builder once user authorizes kickoff
Directed to: OpenCode

Type: Task Handoff

## Action requested

Produce `docs/audits/tui_backend_readiness.md` per the schema in `docs/plan/backend-first-tui-kickoff-2026-04-27.md` (Work packet 1 section). This is **audit-only** — no code changes, no commits, no test edits.

## Required commands (READ-ONLY)

Run from repo root. Strict no-tree-mutating policy — these commands are all read-only:

```bash
git log --oneline --decorate -n 3
git show --stat --name-status HEAD
git show --stat --name-status HEAD~1
git show --stat --name-status HEAD~2

find docs -maxdepth 3 -type f | sort
find autocode -maxdepth 4 -type f | sort | sed -n '1,250p'

rg "overlay|modal|popup|backdrop|dim|centered|dialog" autocode docs -n || true
rg "queue|queued|followup|draft|submitted|steer|pending" autocode docs -n || true
rg "restore|checkpoint|rewind|diff|review|escalation|approval|permission|protected" autocode docs -n || true
rg "tui|rtui|fullscreen|renderer|drawer|composer|slash|palette|focus|transcript" autocode docs -n || true
rg "subagent|task|delegate|agent" autocode docs -n || true
rg "stdout|stderr|validation|command stream|tool result|result_payload" autocode docs -n || true
```

## Atomic sub-tasks

- [ ] Run all required commands (read-only) and capture output for the audit doc
- [ ] Section 1 — Last 3 commits summary
- [ ] Section 2 — Current architecture summary (must reflect Rust TUI is sole frontend; Go BubbleTea + Python inline deleted 2026-04-19)
- [ ] Section 3 — Rust TUI vs old Go/BubbleTea status (status: deleted; reference any vestigial doc/test artifacts that still mention them)
- [ ] Section 4 — Backend feature inventory table (18 rows minimum per the prompt's feature list) using status vocabulary `ready | partial | missing | blocked | historical | demo-only`. For each row, fill columns: docs exist? / types or events exist? / reducer or state exists? / persistence exists? / tests exist? / TUI-ready? / issues
- [ ] Section 5 — TUI feature inventory table (same row set + columns; the question is whether the Rust TUI surfaces each feature)
- [ ] Section 6 — P0 blockers (must include any feature where contracts are missing or surface depends on an undefined event)
- [ ] Section 7 — P1 follow-ups
- [ ] Section 8 — Files inspected (full list)
- [ ] Section 9 — Tests discovered (with counts and locations)
- [ ] Section 10 — Recommended first implementation sequence (numbered ordering of next steps; should align with Packets 2-5 sequencing)
- [ ] Cross-reference existing 14-scene Track 4 ratchet (`autocode/tests/tui-references/`) under "fixtures/tests" feature row — those are READY for the overlapping 14 surfaces
- [ ] Cross-reference `docs/reference/rust-tui-architecture.md`, `docs/reference/rust-tui-rpc-contract.md`, `docs/reference/rpc-schema-v1.md` for current contracts
- [ ] Cross-reference `docs/features/backend_features.md` and `docs/features/features_behavior.md` for current backend inventory
- [ ] Note any "centered overlay" / "modal backdrop" / "dim" residue from older eras as historical findings (must NOT be carried into the new TUI plan)

## Files Builder will create

- `docs/audits/tui_backend_readiness.md` (new)

## Files Builder may read (non-exhaustive)

- `current_directives.md`, `PLAN.md`, `EXECUTION_CHECKLIST.md`
- `autocode/rtui/src/**`, `autocode/src/autocode/backend/**`
- `docs/reference/**`, `docs/features/**`, `docs/architecture.md`
- `autocode/tests/tui-references/**`, `autocode/tests/tui-comparison/**`, `autocode/tests/vhs/**`, `autocode/tests/pty/**`
- `bugs/codex-tui-issue-inventory.md`

## Exit gate (Constraint #8 inherited from Tranche 4 cadence)

Before posting a Review Request:

- [ ] `docs/audits/tui_backend_readiness.md` is the canonical inventory doc updated for this packet (no separate inventory doc required)
- [ ] Verification artifact stored at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-packet1-tui-backend-readiness-audit.md` capturing: list of commands run, file paths inspected, doc table-of-contents, and explicit confirmation that no tree-mutating git op was used
- [ ] No code changes, no commits, no test edits

## Hard constraints (echoed)

- No centered overlays / dimmed backdrops / default-state side rail / default-state queue drawer / hidden-while-streaming composer / human-text parsing for backend state / old Go/BubbleTea as target architecture / decorative spinner verbs / dashboard-card UI / command-center as default UI in any audit recommendation.
- Strict no-tree-mutating-git policy: only `status/diff/log/show/fetch/stash list|show/worktree add|list|remove/config (read)/add` permitted.
- Audit-only — no code, tests, fixtures, contracts, or plan files edited in this packet.

## Priority

P0 — blocks all other packets. Begin only after user authorizes program kickoff (per Entry 1595 OPEN QUESTIONS).

Tools Used: `Read`, `Edit`

---

### Entry 1597
Agent: Claude | Role: Reviewer/Architect | Layer: N/A program kickoff | Context: AutoCode Backend-First + Minimal Rust TUI — Work Packet 2 (current architecture document) | Intent: Hand off Packet 2 to Builder; depends on Packet 1 close
Directed to: OpenCode

Type: Task Handoff

## Action requested

Produce `docs/tui/current-architecture.md` per the schema in `docs/plan/backend-first-tui-kickoff-2026-04-27.md` (Work packet 2 section). Goal: remove ambiguity about old Go/BubbleTea TUI vs current Rust TUI by freezing the current state explicitly.

## Atomic sub-tasks

- [ ] Open the doc with the verbatim "must explicitly say" block from the program brief (Rust is current interactive TUI; Python JSON-RPC backend; old Go/BubbleTea = historical migration reference; new minimal shell targets Rust only; product TUI must not use centered overlays or demo switchers)
- [ ] Section: Current TUI entrypoint(s) — list `autocode/rtui/src/main.rs`, the launcher CLI command path, alt-screen vs inline mode handling
- [ ] Section: Backend server / transport entrypoint(s) — list `autocode/src/autocode/backend/server.py`, stdio + TCP host adapters, spawn-managed vs attach modes
- [ ] Section: JSON-RPC protocol files — `autocode/src/autocode/backend/schema.py`, `autocode/rtui/src/rpc/schema.rs`, `docs/reference/rpc-schema-v1.md`
- [ ] Section: Current test commands — exact Make targets and `uv run pytest` invocations from `autocode/TESTING.md`
- [ ] Section: Current PTY/snapshot commands — `make tui-references`, `make tui-regression`, `make tui-reference-gap`, `make tui-scene-matrix`, frame-sequence helper
- [ ] Section: Known historical directories/docs that should NOT be used for new work — anything Go/BubbleTea, anything in `docs/archive/`, demo-only HTML mockups not bound to live data, centered-overlay-era code paths
- [ ] Cross-reference `docs/reference/rust-tui-architecture.md`, `docs/reference/rust-tui-rpc-contract.md`, ADR-001/002/003 in `docs/decisions/`
- [ ] Capture the user-locked fullscreen render contract (2026-04-22) as a current-state invariant

## Files Builder will create

- `docs/tui/current-architecture.md` (new)
- May add a small index file linking pre-existing Rust-TUI docs if appropriate

## Files Builder may read (non-exhaustive)

- `autocode/rtui/Cargo.toml`, `autocode/rtui/src/**`
- `autocode/src/autocode/backend/**`
- `autocode/TESTING.md`
- `docs/reference/rust-tui-{architecture,rpc-contract}.md`, `docs/reference/rpc-schema-v1.md`
- `docs/decisions/ADR-00{1,2,3}-*.md`
- `Makefile`

## Exit gate

- [ ] `docs/tui/current-architecture.md` written
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-packet2-current-architecture-doc.md`
- [ ] Cross-references resolved (no broken links)

## Hard constraints (echoed)

- No new architecture proposals — this packet is **descriptive of current state only**.
- No code changes; no test edits; no commits; no tree-mutating git ops.

## Priority

P1 — depends on Packet 1 close. May parallelize with Packet 3 after Packet 1.

Tools Used: `Read`, `Edit`

---

### Entry 1598
Agent: Claude | Role: Reviewer/Architect | Layer: N/A program kickoff | Context: AutoCode Backend-First + Minimal Rust TUI — Work Packet 3 (16 feature contracts) | Intent: Hand off Packet 3 to Builder; depends on Packet 1 close
Directed to: OpenCode

Type: Task Handoff

## Action requested

Ensure these 16 feature-contract files exist under `docs/features/`. Extend existing good docs; do NOT duplicate. Where existing docs match a packet name partially, integrate via a "## Open questions" / "## Acceptance criteria" extension and add a small index file linking them.

```
docs/features/agent-events.md
docs/features/session-lifecycle.md
docs/features/transcript.md
docs/features/composer.md
docs/features/queue.md
docs/features/commands.md
docs/features/permissions.md
docs/features/protected-paths.md
docs/features/diff-review.md
docs/features/checkpoints-restore.md
docs/features/recovery.md
docs/features/validation-output.md
docs/features/subagents-tasks.md
docs/features/search-file-symbol.md
docs/features/tui-rendering.md
docs/features/terminal-compat.md
```

Each file uses the contract structure: Purpose / User-visible TUI surfaces / Backend contract / Event types / State+reducer / Persistence / Commands+keybindings / Failure+recovery / Tests+fixtures / Acceptance criteria / Open questions.

## Typed contract models to embed (from program brief)

- `AgentEvent` discriminated union + `BaseEvent` interface
- `QueueItem` + `QueueItemState` + queue behavior text (Alt+Enter, editable-until-submitted, collapsed = 1 row, expanded = bottom drawer not overlay)
- `CommandDefinition` interface + same-registry rule (slash picker, Ctrl+Shift+P focus mode, keybindings, custom commands all share one registry)
- `PermissionMode` + `RiskFacts`
- `FileDiff` + `DiffHunk` + `DiffLine`
- `Checkpoint`
- `RecoveryState` (with `preservedDraft` field — composer state preservation across recovery is non-negotiable)
- `CommandStream` (validation stream model)

## Atomic sub-tasks

- [ ] Audit `docs/features/` for existing files first (Codex consolidated some via Entries 1588 + 1590); reconcile names before creating duplicates
- [ ] For each of the 16 contracts: confirm file exists or create; ensure all 11 sections present; embed the relevant typed model from program brief
- [ ] Create `docs/features/_index.md` cross-linking the 16 contracts + `backend_features.md` + `features_behavior.md` (so the inventory remains discoverable)
- [ ] In `commands.md`: explicitly cite the same-registry rule and list current Rust TUI command surface (slash, Ctrl+K palette) as canonical
- [ ] In `queue.md`: explicit "expanded queue is bottom drawer, not overlay" — no centered modal
- [ ] In `tui-rendering.md`: codify the user-locked fullscreen render contract; cite `20260422-131037-tui-fullscreen-hard-requirements-pass.md`
- [ ] In `terminal-compat.md`: cite tmux compatibility, scrollback preservation, resize handling, no-flicker requirements
- [ ] In `protected-paths.md`: define rail mode `ProtectedPath` as the only acceptable surface for protected-path escalation (NOT a centered modal)
- [ ] In `recovery.md`: explicitly include `preservedDraft` semantics — composer text must survive a halt/error
- [ ] In `subagents-tasks.md`: cross-reference existing orchestrator/team-eval substrate (Phase 8) and external-harness adapters (Phase 6)

## Files Builder will create or edit

- 16 files under `docs/features/` (some new, some extended)
- `docs/features/_index.md` (new)

## Files Builder may read (non-exhaustive)

- `docs/features/backend_features.md`, `docs/features/features_behavior.md` (recently consolidated)
- `docs/audits/tui_backend_readiness.md` (output of Packet 1)
- `docs/reference/rpc-schema-v1.md` and current schema files
- `autocode/src/autocode/backend/**`, `autocode/rtui/src/**`

## Exit gate

- [ ] All 16 contract files present; index file present
- [ ] No duplicate content across contracts (cross-references instead)
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-packet3-feature-contracts.md`
- [ ] `docs/features/backend_features.md` updated with cross-links to the new contract files (Constraint #8 inventory sync)

## Hard constraints (echoed)

- No code changes, no test edits.
- Contracts MUST forbid: centered overlays, dimmed backdrops, default-state side rail, default-state queue drawer, hidden-while-streaming composer, human-text parsing for backend state.
- Contracts MUST require: typed events over string parsing, deterministic fixtures, explicit keyboard controls, same-registry command discovery.

## Priority

P1 — depends on Packet 1 close. May parallelize with Packet 2.

Tools Used: `Read`, `Edit`

---

### Entry 1599
Agent: Claude | Role: Reviewer/Architect | Layer: N/A program kickoff | Context: AutoCode Backend-First + Minimal Rust TUI — Work Packet 4 (20 deterministic JSONL fixtures) | Intent: Hand off Packet 4 to Builder; depends on Packet 3 close
Directed to: OpenCode

Type: Task Handoff

## Action requested

Create 20 deterministic JSONL fixtures under `fixtures/tui/`. Each fixture is a sequence of typed backend events (NOT raw terminal text), small enough for PTY/snapshot tests, renderable into the canonical UI shell (HUD / Transcript or focus region / Optional drawer / Optional queue strip / Composer / Hint line).

```
fixtures/tui/ready.jsonl
fixtures/tui/active.jsonl
fixtures/tui/multitasking.jsonl
fixtures/tui/queue-drawer.jsonl
fixtures/tui/plan-inline.jsonl
fixtures/tui/live-drawer.jsonl
fixtures/tui/review.jsonl
fixtures/tui/diff-focus.jsonl
fixtures/tui/protected-path.jsonl
fixtures/tui/recovery.jsonl
fixtures/tui/restore-focus.jsonl
fixtures/tui/session-browser.jsonl
fixtures/tui/command-palette-focus.jsonl
fixtures/tui/slash-picker.jsonl
fixtures/tui/file-picker.jsonl
fixtures/tui/symbol-picker.jsonl
fixtures/tui/search-focus.jsonl
fixtures/tui/transcript-review.jsonl
fixtures/tui/command-center.jsonl
fixtures/tui/narrow.jsonl
```

## Mapping vs existing 14-scene Track 4 ratchet

`autocode/tests/tui-references/` already has 14 named scenes with deterministic triggers (`scene_presets.py`) and predicates (`predicates.py`). Map Packet 4 fixtures to those scenes; net-new surfaces are the ones with NO existing match:

| Packet 4 fixture | Track 4 scene equivalent | Status |
|---|---|---|
| `ready` | `ready` | overlap |
| `active` | `active` | overlap |
| `multitasking` | `multi` | overlap |
| `queue-drawer` | — | NET-NEW |
| `plan-inline` | `plan` (partial — Track 4 is full focus mode) | overlap if same surface, else split |
| `live-drawer` | — | NET-NEW |
| `review` | `review` | overlap |
| `diff-focus` | `diff` | overlap |
| `protected-path` | `escalation` (partial — protected path is a sub-case) | reconcile in Builder review |
| `recovery` | `recovery` | overlap |
| `restore-focus` | `restore` | overlap |
| `session-browser` | `sessions` | overlap |
| `command-palette-focus` | `palette` | overlap |
| `slash-picker` | — | NET-NEW |
| `file-picker` | — | NET-NEW |
| `symbol-picker` | — | NET-NEW |
| `search-focus` | `grep` | overlap (rename in fixtures) |
| `transcript-review` | — | NET-NEW |
| `command-center` | `cc` | overlap |
| `narrow` | `narrow` | overlap |

Net-new = 6 (queue-drawer, live-drawer, slash-picker, file-picker, symbol-picker, transcript-review). Builder reconciles partial overlaps (`plan-inline` vs `plan`, `protected-path` vs `escalation`) during fixture authoring and documents the decision in the verification artifact.

## Atomic sub-tasks

- [ ] Confirm canonical event schema location (Packet 3 contracts) — every fixture event MUST conform to a typed contract
- [ ] For each fixture: write a sequence of typed backend events sufficient to drive the named UI surface
- [ ] Ensure `narrow.jsonl` exercises the 30-row × 68-col footprint per `scene_presets.py` precedent
- [ ] Ensure `recovery.jsonl` includes `preservedDraft` payload to validate composer-state survival
- [ ] Ensure `queue-drawer.jsonl` includes multiple `QueueItem` records in mixed states (`draft`, `queued`, `next`, `blocked`, `prioritized`)
- [ ] Ensure `protected-path.jsonl` triggers `RailMode::ProtectedPath` (rail surface, NOT centered modal)
- [ ] Ensure `command-center.jsonl` is opt-in via explicit power-mode entry (NOT default UI)
- [ ] Ensure `slash-picker.jsonl` filters in real time as the user types (composer-attached picker, not focus mode)
- [ ] Ensure `transcript-review.jsonl` exercises read-only history navigation with search highlighting
- [ ] Add a fixture-loading helper / golden-test harness reference in the verification artifact (the Rust TUI / Python tests will consume these)
- [ ] Write a `fixtures/tui/README.md` documenting the schema, the 20 surfaces, the existing Track 4 mapping table, and how each fixture is loaded

## Files Builder will create

- 20 `.jsonl` files under `fixtures/tui/`
- `fixtures/tui/README.md` (new)
- May add fixture-validation pytest if Builder judges it cheap (otherwise queue for a later slice)

## Files Builder may read

- All Packet 3 contracts under `docs/features/`
- `autocode/tests/tui-references/scene_presets.py`, `predicates.py`, `manifest.yaml`, `README.md`
- `autocode/tests/pty/fixtures/rpc-schema-v1/` for prior fixture-corpus precedent
- `autocode/src/autocode/backend/schema.py`

## Exit gate

- [ ] 20 fixtures present + README
- [ ] Each fixture validates against the typed contracts from Packet 3
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-packet4-tui-fixtures.md` with the overlap-vs-net-new table filled in
- [ ] Cross-link added in `docs/audits/tui_backend_readiness.md` Section "fixtures/tests" row (status flips appropriately)

## Hard constraints (echoed)

- Fixtures are typed backend events, not terminal text.
- No fixture exceeds what fits in a snapshot test cleanly.
- No fixture asserts a centered overlay or dimmed modal — those are forbidden by product doctrine.
- No code changes outside `fixtures/tui/`. No commits. No tree-mutating git ops.

## Priority

P1 — depends on Packet 3 close.

Tools Used: `Read`, `Edit`, `Write`

---

### Entry 1600
Agent: Claude | Role: Reviewer/Architect | Layer: N/A program kickoff | Context: AutoCode Backend-First + Minimal Rust TUI — Work Packet 5 (Rust TUI plan, no implementation) | Intent: Hand off Packet 5 to Builder; depends on Packets 1-4 close
Directed to: OpenCode

Type: Task Handoff

## Action requested

Produce `docs/tui/minimal-rust-tui-implementation-plan.md` per the schema in `docs/plan/backend-first-tui-kickoff-2026-04-27.md` (Work packet 5 section). **No implementation code in this packet** — this is the plan that the next program (after audit + contracts + fixtures land) will execute.

## Required content (verbatim from program brief)

### TUI mode enums (Rust)

```rust
enum FocusMode {
    None, Diff, Restore, Sessions, CommandPalette, Search, TranscriptReview,
}
enum DrawerMode {
    None, Stdout, Stderr, Validation, Queue, Grep,
}
enum RailMode {
    None, Review, ProtectedPath, CommandCenter,
}
enum ComposerPicker {
    None, Slash, File, Symbol, Model,
}
```

### Components

`Hud`, `Rule`, `TranscriptOrFocusRegion`, `Drawer`, `QueueStrip`, `Composer`, `HintLine`, `TmuxStrip`.

### Rendering constraints

- fixed composer allocation
- bounded drawer allocation
- stable queue strip height
- no full clear per token
- synchronized output if supported
- ANSI-safe wrapping
- terminal-width-aware truncation
- resize handling
- fake composer cursor
- real cursor restored on crash
- no scroll jumps

### Default visual grammar

```text
model · effort · cwd · branch · permission · context · cost · state
sandbox · Δ/files · tasks · agents · q · checkpoint
```

### Canonical tool-call grammar

```text
⏺ Read(path)
⏺ Search("pattern" scope)
⏺ Edit(path)
⏺ Run(command)
```

## Atomic sub-tasks

- [ ] Open the doc with explicit dependency: "Implementation does not begin until Packets 1-4 are closed and Reviewer approves this plan"
- [ ] Section: TUI mode enums — embed the four enums verbatim with one-paragraph rationale per variant
- [ ] Section: Components — describe each component's responsibility and which mode/drawer/rail it owns
- [ ] Section: Rendering constraints — codify each as an acceptance criterion with the precise check the test harness will run
- [ ] Section: Default visual grammar — show how each token maps to a backend event source (no human-text parsing)
- [ ] Section: Tool-call grammar — show how each tool-start event renders to one of the four canonical lines
- [ ] Section: Mapping to existing infrastructure — reuse Track 4 ratchet (`autocode/tests/tui-references/`), Track 1 substrate (`autocode/tests/tui-comparison/`), VHS PNG regression, PTY smokes
- [ ] Section: Mapping to feature contracts — every component cites the relevant Packet 3 contract
- [ ] Section: Mapping to fixtures — every mode/drawer/rail cites the Packet 4 fixture(s) that drive it
- [ ] Section: Migration plan — staged rollout that preserves current backend work and Rust TUI sessions; explicit "do not rewrite from scratch unless audit proves contracts and fixtures are absent"
- [ ] Section: Risk register — flicker, scroll jumps, cursor leaks on crash, sync output incompatibility on legacy terminals, narrow-width rendering, alt-screen vs inline parity
- [ ] Section: Open questions for user

## Files Builder will create

- `docs/tui/minimal-rust-tui-implementation-plan.md` (new)

## Files Builder may read

- All outputs of Packets 1-4
- `autocode/rtui/src/**` (current implementation as starting point — preserve, do not rewrite blind)
- `docs/reference/rust-tui-architecture.md`, `docs/reference/rust-tui-rpc-contract.md`
- `autocode/tests/tui-references/**` (Track 4)

## Hard constraints (echoed)

- No code or test changes — plan only.
- Plan must explicitly forbid: centered overlays, dimmed backdrops, default-state side rail, default-state queue drawer, hidden-while-streaming composer, human-text parsing for backend state, old Go/BubbleTea as architectural target, dashboard/card UI, command center as default.
- Plan must explicitly require: full-screen render, terminal-resize works, multiple-size validated, scrollback preserved (user-locked render contract 2026-04-22).
- Side rail allowed only for: review approval, protected-path escalation, explicit command-center power mode.

## Exit gate

- [ ] Plan doc complete with all required sections
- [ ] Verification artifact at `autocode/docs/qa/test-results/<ts>-packet5-rust-tui-plan.md`
- [ ] Cross-links into Packets 1-4 outputs all resolve

## Priority

P2 — depends on Packets 1-4 close.

Tools Used: `Read`, `Edit`

---

### Entry 1601
Agent: Claude | Role: Reviewer/Architect | Layer: N/A program coordination | Context: User decision on program sequencing — Tranche 4 first with Packet 3 (16 feature contracts) as prep slice; Packets 1/2/4/5 parked; Builder=OpenCode primary, Codex fallback | Intent: Ratify the user's chosen sequence in the active log, route Builder, ask for Packet 3 prep kickoff
Replying to: User
Directed to: User, OpenCode, Codex

Type: Task Handoff (sequencing decision)

## User decision (2026-04-27 late)

- **Tranche 4 first.** Backend Robustness Tranche 4 (`docs/plan/backend-robustness-tranche-4-plan.md`) is the active program.
- **Packet 3 (16 feature contracts) is promoted to active prep slice** — runs before C4.G1 to give Tranche 4 named typed shapes (Checkpoint, RiskFacts, CommandStream, SubagentEvent) instead of inventing them ad-hoc during implementation.
- **Packets 1, 2, 4, 5 are PARKED** for after Tranche 4 closes.
- **Builder routing:** OpenCode primary; Codex fallback when OpenCode is unavailable for the slice.

## New active sequence

1. **Packet 3 prep slice** (Entry 1598; ~3-5 days; doc-only; OpenCode primary / Codex fallback) — 16 feature-contract files under `docs/features/` per the structure in Entry 1598. Exit gate per Constraint #8.
2. **C4.G1** — per-tool-call atomic checkpoint with diff-rollback, per `docs/plan/backend-robustness-tranche-4-checklist.md` §4.G1.
3. **Tranche 4 remainder** — G1-G15, 23 sub-slices, 4 gates per the existing master plan + checklist.
4. **Eventually after Tranche 4 closes:** Packets 1, 2, 4, 5 (audit, current-architecture doc, fixtures, Rust TUI plan).

## Status flips on prior entries

| Entry | Packet | Old status | New status |
|---|---|---|---|
| 1596 | P1 — repo audit | Pending kickoff | **PARKED** until Tranche 4 closes |
| 1597 | P2 — current architecture doc | Pending kickoff | **PARKED** until Tranche 4 closes |
| 1598 | P3 — 16 feature contracts | Pending kickoff | **ACTIVE PREP SLICE** — kickoff pending user go |
| 1599 | P4 — 20 fixtures | Pending kickoff | **PARKED** until Tranche 4 closes |
| 1600 | P5 — Rust TUI plan | Pending kickoff | **PARKED** until Tranche 4 closes |

## Coordination note for OpenCode (Packet 3 prep)

When you take Packet 3, design each contract so its event/state shape can absorb whatever Tranche 4's implementation slices will emit. The four highest-overlap contracts:

- `docs/features/checkpoints-restore.md` — for Tranche 4 G1 atomic-checkpoint events
- `docs/features/permissions.md` + `docs/features/protected-paths.md` — for Tranche 4 G2 sandbox/policy
- `docs/features/validation-output.md` — for Tranche 4 G4 auto-verify-after-edit streams
- `docs/features/subagents-tasks.md` — for Tranche 4 G13 worktree-isolated subagents

If a contract shape blocks a Tranche 4 slice mid-implementation, raise a Concern entry; the contract gets updated. The contracts are descriptive of intent, not frozen.

## Open asks (Directed to: User)

1. **Authorize OpenCode to start Packet 3 prep slice now?** (Codex fallback if OpenCode is unavailable for this slice.)
2. **C4.G1 follows immediately after Packet 3 closes**, or do you want a separate go-ahead?
3. **Top-level state docs** (`PLAN.md`, `EXECUTION_CHECKLIST.md`, `current_directives.md`) currently describe Tranche 4 as the active phase but don't mention the Packet 3 prep slice or the parked packets. Want me to refresh them now, or leave for later?

## Hard constraints (carry forward to Packet 3)

- No tree-mutating git ops. Strict per `AGENTS.md`.
- Per-slice Constraint #8 exit gate: update `docs/features/backend_features.md` AND store verification artifact at `autocode/docs/qa/test-results/<ts>-packet3-feature-contracts.md` BEFORE Review Request.
- Contracts MUST forbid: centered overlays, dimmed modal backdrops, default-state side rail, default-state queue drawer, hidden-while-streaming composer, human-text parsing for backend state, old Go/BubbleTea as architectural target, dashboard/card UI, command center as default UI.
- Contracts MUST require: typed events over string parsing, deterministic fixtures (Packet 4 will realize them later), explicit keyboard controls, same-registry command discovery, full-screen render contract preserved (per user-locked render contract 2026-04-22).

## What's NOT done in this entry

- No code changes.
- No commits, tags, pushes, resets, or checkouts.
- No top-level state-doc edits (pending user OK).
- No kickoff authorization given to OpenCode yet — that's the open ask above.

Tools Used: `Read`, `Edit`
