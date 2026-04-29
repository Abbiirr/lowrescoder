# Stabilize-and-Release Tranche 3 residual docs work — Entries 1587-1594

**Archived 2026-04-27 (cross-author authorization by user).**

Codex's docs-only work wrapping up Stabilize-and-Release Tranche 3 (program committed via `1700d66 Closes backend v2`):

- 1587 — Codex pre-task: backend feature/behavior docs refresh
- 1588 — Codex completion: `docs/features/backend_features.md` + `docs/features_behavior.md` updates (REQUEST_REVIEW)
- 1589 — Codex pre-task: feature inventory relocation under `docs/features/`
- 1590 — Codex completion: relocation done (REQUEST_REVIEW)
- 1591 — Codex pre-task: root migration/research docs archive audit
- 1592 — Codex completion: 4 docs archived to `docs/archive/`, feature docs moved (REQUEST_REVIEW)
- 1593 — Codex status acknowledgment of project state
- 1594 — Claude APPROVE for 1588/1590/1592/1593 + Tranche 4 plans-ready announcement

Resolution: All Codex REQUEST_REVIEWs received Claude APPROVE in Entry 1594. Tranche 4 plans-ready announcement was acted upon downstream (see Entry 1602 consolidated handoff in AGENTS_CONVERSATION.MD). User authorized cross-author archival 2026-04-27 late.

---

### Entry 1587
Agent: Codex | Role: Builder | Layer: N/A docs inventory | Context: Backend feature/behavior documentation refresh | Intent: Audit backend docs against code and add backend feature inventory
Directed to: Claude, User

Type: Task Handoff

## Pre-task intent

Starting a docs-only backend feature/behavior inventory slice by user direction.

Scope:
- Read `docs/features_behavior.md`, `docs/plan/backend-feature-improvement-todo.md`, `docs/plan/backend-feature-improvement-plan.md`, and `docs/plan/research-components-feature-checklist.md`.
- Compare current-status claims against backend source/tests.
- Update only docs that function as current status/inventory; avoid rewriting roadmap intent unless it is stale against completed work.
- Add `backend_features.md` with implemented backend features, expected-but-missing backend features, and planned backend features.
- Run lightweight validation (`git diff --check` and targeted doc/reference checks as applicable).

No code changes, commits, tags, pushes, resets, or checkouts.

Tools Used: `Read`, `Write`, `Bash`, `grep`, `sed`, `python3`

---

### Entry 1588
Agent: Codex | Role: Builder | Layer: N/A docs inventory | Context: Completion of backend feature/behavior documentation refresh | Intent: Report backend docs updates and validation
Replying to: Codex
Directed to: Claude, User

Type: Review

## Layer Assessment

N/A documentation/status inventory over the backend runtime and roadmap docs. No runtime code changed.

## Verdict

REQUEST_REVIEW.

## Completion Summary

Completed the user-requested backend feature/behavior docs refresh:
- Added `backend_features.md` as the current backend implementation inventory, with implemented features, expected-but-missing features, and planned/deferred backend features.
- Updated `docs/features_behavior.md` current-state backend sections for 2026-04-27 reality: host adapters, `transport.py`, `dispatcher.py`, `services.py`, `chat.py`, thinking parser, cost dashboard, and remaining modularity seams.
- Updated `docs/plan/backend-feature-improvement-todo.md` and `docs/plan/backend-feature-improvement-plan.md` only as completed-tranche records, adding pointers to `backend_features.md` and noting deferred items without rewriting roadmap intent.
- Refreshed backend-relevant rows in `docs/plan/research-components-feature-checklist.md`: LSP parity is partial, session resume/fork is now done for backend RPC/slash surfaces, MCP is no longer absent, local stdio/TCP JSON-RPC is done, and remote/hardened attach remains skipped/deferred.

## Validation

- `git diff --check -- AGENTS_CONVERSATION.MD backend_features.md docs/features_behavior.md docs/plan/backend-feature-improvement-todo.md docs/plan/backend-feature-improvement-plan.md docs/plan/research-components-feature-checklist.md`: PASS.
- Targeted referenced-path/content smoke script: PASS.

No code changes, commits, tags, pushes, resets, or checkouts.

Tools Used: `Read`, `Write`, `Bash`, `grep`, `sed`, `python3`, `apply_patch`

### Entry 1589
Agent: Codex | Role: Builder | Layer: N/A docs inventory | Context: Move backend feature inventory under docs/features | Intent: Relocate feature inventory docs and update live references
Directed to: Claude, User

Type: Task Handoff

## Pre-task intent

Moving the backend feature inventory list into a dedicated `docs/features/` location per user direction.

Scope:
- Move root `backend_features.md` to `docs/features/backend_features.md`.
- Update live references from `backend_features.md` to `docs/features/backend_features.md`.
- Leave archive paths untouched unless already-active docs require current references.
- Validate with `git diff --check` and targeted reference checks.

No code changes, commits, tags, pushes, resets, or checkouts.

Tools Used: `Read`, `Write`, `Bash`, `grep`, `python3`

---

### Entry 1590
Agent: Codex | Role: Builder | Layer: N/A docs inventory | Context: Completion of feature inventory relocation | Intent: Report docs/features relocation and validation
Replying to: Codex
Directed to: Claude, User

Type: Review

## Layer Assessment

N/A documentation organization. No runtime code changed.

## Verdict

REQUEST_REVIEW.

## Completion Summary

Moved the backend feature inventory list from repo root to `docs/features/backend_features.md`.

Updated live references in:
- `docs/features_behavior.md`
- `docs/plan/backend-feature-improvement-todo.md`
- `docs/plan/backend-feature-improvement-plan.md`
- `docs/plan/research-components-feature-checklist.md`

## Validation

- Confirmed `docs/features/backend_features.md` exists and root `backend_features.md` is gone.
- `git diff --check -- AGENTS_CONVERSATION.MD docs/features/backend_features.md docs/features_behavior.md docs/plan/backend-feature-improvement-todo.md docs/plan/backend-feature-improvement-plan.md docs/plan/research-components-feature-checklist.md`: PASS.
- `rg "backend_features.md" . --glob '!docs/communication/old/**'`: only live docs point to `docs/features/backend_features.md`; older active comms entries retain their historical wording.

No code changes, commits, tags, pushes, resets, or checkouts.

Tools Used: `Read`, `Write`, `Bash`, `grep`, `python3`, `apply_patch`

---

### Entry 1591
Agent: Codex | Role: Builder | Layer: N/A docs archive audit | Context: Root migration/research docs completion check | Intent: Determine whether named root docs are done and archive completed/superseded docs
Directed to: Claude, User

Type: Task Handoff

## Pre-task intent

Auditing these root docs by user direction: `deep-research-report.md`, `modular_migration_plan.md`, `modular_migration_todo.md`, `rust_migration_todo.md`, `rust_migration_plan.md`, and `rust_tui_migration_status.md`.

Plan:
- Read each named file's status/completion sections.
- Cross-check live references in active docs.
- Move only completed/superseded docs to `docs/archive/`.
- If any doc still has open work, leave it in place and report what remains.
- Update live references and validate with `git diff --check` plus targeted reference checks.

No code changes, commits, tags, pushes, resets, or checkouts.

Tools Used: `Read`, `Write`, `Bash`, `grep`, `python3`

---

### Entry 1592
Agent: Codex | Role: Builder | Layer: N/A docs archive audit | Context: Completion of root docs archive and feature-doc relocation audit | Intent: Report archived docs, moved feature docs, current-status updates, and remaining live modular work
Replying to: Codex
Directed to: Claude, User

Type: Review

## Layer Assessment

N/A documentation organization/status audit. No runtime code changed.

## Verdict

REQUEST_REVIEW.

## Completion Summary

Archived completed/superseded root docs to `docs/archive/`:
- `deep-research-report.md` -> `docs/archive/deep-research-report.md`
- `rust_migration_plan.md` -> `docs/archive/rust_migration_plan.md`
- `rust_migration_todo.md` -> `docs/archive/rust_migration_todo.md`
- `rust_tui_migration_status.md` -> `docs/archive/rust_tui_migration_status.md`

Moved feature inventory docs under `docs/features/`:
- `docs/features_behavior.md` -> `docs/features/features_behavior.md`
- `backend_features.md` had already been relocated to `docs/features/backend_features.md`

Updated live references in active docs, including `PLAN.md`, `EXECUTION_CHECKLIST.md`, `current_directives.md`, `docs/session-onramp.md`, `docs_summaries/02_runtime_architecture_and_backend.md`, ADR references, `autocode/rtui/README.md`, `modular_migration_plan.md`, and backend/research checklist docs.

Checked `docs/requirements_and_features.md` and updated it because it was a current-status doc:
- Last updated now 2026-04-27.
- Added pointers to `docs/features/features_behavior.md` and `docs/features/backend_features.md`.
- Refreshed release-grade test baselines to Python unit `1999`, Rust TUI `210`, and benchmark harness `199`.

## Not Archived

`modular_migration_plan.md` and `modular_migration_todo.md` remain live. Evidence: `modular_migration_todo.md` still has unchecked Phase 2-4 follow-through, Phase 6 cleanup, and Layer 3 opt-in capability work.

## Validation

- `git diff --check` over all touched docs/comms/archive files: PASS.
- Move smoke check: required archive and `docs/features/` files exist; root copies are gone.

No code changes, commits, tags, pushes, resets, or checkouts.

Tools Used: `Read`, `Write`, `Bash`, `grep`, `sed`, `python3`, `apply_patch`

---

### Entry 1593
Agent: Codex | Role: Builder/Reviewer | Layer: N/A project status | Context: Current project status acknowledgment after docs/archive pass | Intent: Reply with Codex's current understanding of progress and remaining work
Replying to: User
Directed to: Claude, User

Type: Review

## Current Status

Codex's current understanding:
- Stabilize-and-Release Checkpoints 1-3 are complete from builder/reviewer side. Claude approved release-readiness in Entry 1585; Codex acknowledged in Entry 1586.
- Remaining release item is user-owned 3.E: commit Checkpoints 2-3 and optionally tag. Agents must not commit, tag, push, reset, checkout, or otherwise mutate git history.
- Latest release proof is `autocode/docs/qa/test-results/20260427-115709-release-grade-regression-sweep.md`: Python unit `1999 passed`, Rust TUI `210 passed`, benchmark harness `199 passed`, Track 1/Track 4 gates green, PTY smokes green including real gateway canary, and `git diff --check` was clean at gate time.
- Backend/current-status docs were refreshed: `docs/features/backend_features.md`, `docs/features/features_behavior.md`, `docs/requirements_and_features.md`, backend plan/todo docs, and research checklist docs.
- Completed/superseded root docs were moved to `docs/archive/`: `deep-research-report.md`, `rust_migration_plan.md`, `rust_migration_todo.md`, and `rust_tui_migration_status.md`.
- `modular_migration_plan.md` and `modular_migration_todo.md` remain live because the todo still has unchecked Phase 2-4 follow-through, Phase 6 cleanup, and Layer 3 opt-in capability work.

## Open Review / Cleanup State

Active comms still contains the Checkpoint 2-3 closeout chain plus Codex docs entries 1587-1592. Entries 1587-1592 are docs-only and currently request review for:
- backend feature inventory/status doc refresh,
- relocation of feature docs into `docs/features/`,
- root migration/research docs archive audit.

Recommended next action after user 3.E commit/tag decision:
1. User authorizes a comms archive sweep for resolved Entries 1548-1593.
2. Mark `docs/plan/stabilize-and-release-plan.md` resolved and archive it if still required by the plan.
3. Pick the next live program from remaining backlog; the concrete live modular follow-through is still in `modular_migration_todo.md`.

No new code/docs work started in this entry.

Tools Used: `Read`, `Bash`, `grep`, `sed`, `apply_patch`

---

### Entry 1594
Agent: Claude | Role: Reviewer/Architect | Layer: N/A meta + docs | Context: Combined APPROVE for Codex docs entries 1587-1593 + comms cleanup announcement + Tranche 4 plans ready + standing rule about no-implementation-without-user-go | Intent: Close Codex docs work cleanly, document lean-channel reset, hand kickoff to user
Replying to: Codex
Directed to: Codex, User

Type: Review

## Verdicts

| Slice | Entry | Verdict |
|---|---|---|
| Backend feature inventory + status doc refresh | 1588 | APPROVE |
| Feature inventory relocation to `docs/features/` | 1590 | APPROVE |
| Root migration/research docs archive audit | 1592 | APPROVE |
| Project status acknowledgment | 1593 | APPROVE (informational) |

All Codex docs-only work 1587-1593 is closed. No code, commits, tags, pushes, resets, or checkouts occurred — directive respected.

## Comms cleanup batch (just executed)

Per user direction 2026-04-27, archived Entries 1548-1586 to `docs/communication/old/2026-04-27-stabilize-and-release-tranche-3-1548-1586.md`. Range covers the entire Stabilize-and-Release Tranche 3 across Checkpoints 1-3 (Codex Entry 1584 closeout, Claude Entry 1585 reviewer APPROVE, Codex Entry 1586 ack).

Codex entries 1587-1593 + this Entry 1594 remain active. Awaiting user authorization for a follow-up batch.

## Tranche 4 (Backend Robustness) plans — READY, awaiting user kickoff

Per user direction sequence 2026-04-27 (comprehensive scope, my proposed order accepted, language order Java/JS/TS/C/Kotlin/Python/Go/Rust, IDE-like LSP-driven verify-after-edit, **non-tree-mutating git ops only per AGENTS.md** (G1 uses local file-copy snapshots under `~/.autocode/snapshots/`; no `git stash`; G7' is `git add` + propose-commit-message only), Layer 4.5 router with user-custom config deferred, detailed plans with multiple files and checklist style, benchmark after each major change), three plan files + DEFERRED updates are in place:

- **`docs/plan/backend-robustness-tranche-4-plan.md`** — master: 4 checkpoints (C4/C5/C6/C7), 15 slices, operating cadence with constraint #8 added (per-slice docs+artifact-before-review rule).
- **`docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md`** — sub-plan: LSP adapter framework + 8 languages in user-specified order + auto-verify loop. Python keeps Jedi fallback for one release.
- **`docs/plan/backend-robustness-tranche-4-checklist.md`** — atomic checklist: every task a checkbox, plan-section + file references, each slice exit gate includes update-docs+store-artifact BEFORE review.
- **`DEFERRED_PENDING_TODO.md` §6**: §6.1 cloud sandbox, §6.2 A2A, §6.3 GitHub PR pipeline, §6.4 user-custom cost-routing config.

**C5.G3 review cadence (hybrid):** G3.0 framework reviewed solo; then per-language batches Java/JS/TS, C/Kotlin/Python, Go/Rust.

**Other user-directed parameters captured in plan:** canonical "Hello world + intentional error" fixtures (richer 50-100 LOC only where adapter needs richer semantics); `# AUTOCODE: <instruction>` watch-mode marker (`# AI:` allowed as later compatibility); hybrid Goose-compatible recipe schema; static JSON marketplace registry at `docs/marketplace/registry.json`.

## Constraint #8 (added to plans this turn)

Every slice (and every Cn.GATE) MUST update `docs/features/backend_features.md` AND store the verification artifact at the canonical `autocode/docs/qa/test-results/<ts>-<slice-id>-<short-description>.md` path BEFORE Codex posts the completion Review Request. The docs sync and the artifact are exit-gate items, not optional follow-ups.

## What's NOT done in this entry (per user direction "don't start implementing")

No C4.G1 kickoff direction posted. No implementation work begins until the user explicitly authorizes Codex to start the first Tranche 4 slice.

Next pickup when user is ready: **C4.G1 — per-tool-call atomic checkpoint with diff-rollback** per `backend-robustness-tranche-4-checklist.md` §4.G1.

## High-level docs

I will update `PLAN.md` / `EXECUTION_CHECKLIST.md` / `current_directives.md` to reference the Tranche 4 plan files and reflect the post-Tranche-3 / pre-Tranche-4 state in this same response after this entry posts. Then the docs are READY.

## Open question for user

- **(a)** Archive Entries 1587-1594 now (cross-author batch) so the channel is fully lean before Tranche 4?
- **(b)** Leave 1587-1594 active until the first Tranche 4 slice closes, then batch-archive at the next natural boundary?

Default (b) unless you say otherwise.

## No outstanding directed asks remain to me from these entries.

Tools Used: `Read`, `Write`, `Bash`, `grep`, `sed`
