# Deferred & Pending TODO

> Single consolidated store for everything NOT being worked on right now but
> MUST NOT be lost. Keep this file truthful.
>
> **Current active slice:** TUI Testing Strategy (plan in progress — see
> `current_directives.md`, `EXECUTION_CHECKLIST.md` §"TUI Testing Strategy
> (Active Slice)", and `PLAN.md` §1g).
>
> **When the active slice lands:** walk this file top-to-bottom, requeue by
> priority, and empty items as they are finished or formally closed.

Last updated: 2026-04-17 late-session (post Entry 1128 Codex verdicts + Entry 1129 archival)
Owner: Claude (Coder)
Source of truth for item state: always confirm against the current tree
(git status, AGENTS_CONVERSATION.MD, artifact paths) before acting.

**Entry-number disambiguation** (per Codex Entry 1128 concern #2): the
AGENTS_CONVERSATION.MD log historically had duplicate entry numbers (e.g.
1064 vs 1064b, 1065 vs 1065b) when Claude and Codex posted concurrently.
Always identify entries by **author + date + context**, never by raw
number. The `b`-suffix convention is documented in
`reference_comms_conventions.md`.

---

## 1. Comms Backlog (AGENTS_CONVERSATION.MD)

### 1.1 My (Claude) review requests awaiting Codex DIRECT verdict

Codex Entry 1128 (2026-04-17) explicitly rejected a blanket 1102-1123 roll-up
verdict and directed that each of the following needs its own direct review:

| Entry | Context | Directed | Codex 1128 guidance |
|---|---|---|---|
| 1113 | Milestone A — runtime stability report | Codex, User | "still large enough units that they deserve direct verdicts" |
| 1115 | Slice 1 — three-picker filterability | Codex (reply chain) | open for direct review |
| 1116 | Slice 2 — RulesLoader migration contract | Codex (reply chain) | open for direct review |
| 1117 | Slice 3 — SkillCatalog progressive disclosure | Codex (reply chain) | open for direct review |
| 1118 | Slice 4 — Hook lifecycle runtime | Codex (reply chain) | open for direct review |
| 1119 | Slice 5 — Compaction provenance (Milestone D minimal) | Codex (reply chain) | open for direct review |
| 1120 | Slice 6 — Verification profiles (Milestone F) | Codex (reply chain) | open for direct review |
| 1121 | Slices 0–7 session close-out | Codex (reply chain) | explicit "cleanest next review unit" per 1128 |
| 1122 | Slice 8 — VHS visual snapshot pipeline | Codex (reply chain) | explicit "cleanest next review unit" per 1128 |
| 1123 | TUI fidelity pass + research-components audit | Codex, User | explicit "cleanest next review unit" per 1128 |
| 1124 | Image #9 fix + prompts.py guardrail + pi wiring | Codex, User | Codex 1125 NEEDS_WORK → my 1126 fix-reply pending re-verdict |
| 1126 | Reply to Codex 1125 with HIGH + MEDIUM fixes | Codex, User | pending Codex re-verdict |
| 1127 | Older-backlog freshness walk with group proposals | Codex, User | verdicted in Codex 1128 (A,B APPROVE; C-F NEEDS_WORK; blanket REJECT) |

**Resolved via Codex Entry 1128 (archived on 2026-04-17):** 1102, 1103, 1104, 1106
→ `docs/communication/old/2026-04-17-unified-tui-phases-3-6.md`

**Action when resumed:** pick the cleanest next unit (Codex suggests 1113, 1121,
1122, 1123) and either request Codex direct review or proceed without verdict
per user judgment.

### 1.2 Codex-directed entries to me — RESOLVED STATUS UPDATE

**Archived on 2026-04-17 (Codex Entry 1128 Group B APPROVE):**
- 1107, 1108, 1109, 1110, 1111 → `docs/communication/old/2026-04-17-codex-planning-reset-and-test-policy.md`

**Still active, awaiting Codex to archive its own entry:**
- **1105** — Codex stderr WARNING misclassification bug. Resolved in Entry 1106 (Claude's fix) and implicitly accepted by Codex Entry 1108 Go-side re-review per Codex 1128. Still physically in the active log because only Codex can archive Codex-authored entries. No action needed from Claude.

### 1.3 My pre-task intents — ARCHIVED

Both pre-task intents archived on 2026-04-17 per user authorization ("we need to properly resolve and archive /comms entries before moving ahead"):

- **1101** → `docs/communication/old/2026-04-17-unified-tui-phases-3-6.md`
- **1114** → `docs/communication/old/2026-04-17-claude-pretask-stable-tui-v1-slices.md`

Also archived:
- **1125b** (my meta-listing, superseded by Entry 1127) → `docs/communication/old/2026-04-17-claude-backlog-listing-superseded.md`

---

## 1.4 New finding from Codex 1125 NEEDS_WORK and bugfind rerun

| Item | Source | Status |
|---|---|---|
| Conversational guardrail is only model-side nudge, not enforced | Codex Entry 1125 Medium #3 | Open design decision: either add a deterministic backend gate that blocks tool-calls on first turn for short identity-style messages, or accept best-effort with a visible doc note. Not landing in this active slice (TUI Testing Strategy). |
| B7_todo_write MEDIUM — stale `Thinking…` text leaks into rendered output when the `todo_write` scenario's stream is very short | `pty_tui_bugfind.py` 2026-04-17 rerun (0→1 bug Medium) | Verb rotation in `autocode/cmd/autocode-tui/update.go`/`model.go` may not kick in before the stream closes; need to either guarantee a rotation tick within the first frame or suppress the placeholder verb entirely. Not fixed in this slice. |

## 2. Technical Pending Items From Current Session (Entry 1124)

| Item | Reason deferred | Acceptance |
|---|---|---|
| B7-B30 benchmark sweep paused at lane B7 | User directive "drop everything first" | Resume via `BENCHMARK_RUN_ID=20260417-150835-1469316 bash benchmarks/run_b7_b30_sweep.sh`; all 23 lanes green per `feedback_full_benchmark_runs.md` |
| VHS re-run against current binary after image #9 fix | Queue-preview removal invalidates baselines | `uv run python autocode/tests/vhs/run_visual_suite.py --update` then commit fresh references |
| Stale `autocode/cmd/autocode-tui/autocode-tui` binary deletion | Caused at least one false-positive regression report (Entry 1124) | `rm` and add `.gitignore` rule if not already present; confirm `build/autocode-tui` is the sole canonical build target |
| Image #7 residuals user couldn't reproduce | Need fresh repro from user | If user sees again: `/memoryns` rendering glitch, composer echo in dropdown, `Ask AutoCode…llo` session title corruption |
| Side-by-side pi ↔ autocode smoke test | TUI testing strategy is the parent slice | Pi is wired at `~/.pi/agent/models.json`; use after TUI testing pipeline lands |
| Live streaming regression artifact (real gateway, not mock) | Mock backend doesn't exercise end-to-end token flow | Capture a PTY run with gateway-backed response, store under `autocode/docs/qa/test-results/` |
| Narrow-terminal (<80 col) behavior fresh capture | Not a regression yet, not prioritized | PTY run at cols=60 rows=20; store artifact |
| Commit of current session's edits | Per `feedback_no_auto_commit.md` | User to review + approve commit scope |

### 2.1 Modified but uncommitted files (as of git status at session end)

```
AGENTS.md
AGENTS_CONVERSATION.MD
CLAUDE.md
EXECUTION_CHECKLIST.md
PLAN.md
autocode/cmd/autocode-tui/askuser.go
autocode/cmd/autocode-tui/composer.go
autocode/cmd/autocode-tui/main.go
autocode/cmd/autocode-tui/model.go
autocode/cmd/autocode-tui/model_picker.go
autocode/cmd/autocode-tui/model_picker_test.go
autocode/cmd/autocode-tui/provider_picker.go
autocode/cmd/autocode-tui/provider_picker_test.go
autocode/cmd/autocode-tui/session_picker.go
autocode/cmd/autocode-tui/session_picker_test.go
autocode/cmd/autocode-tui/statusbar.go
autocode/cmd/autocode-tui/styles.go
autocode/cmd/autocode-tui/update.go
autocode/cmd/autocode-tui/view.go
autocode/cmd/autocode-tui/view_test.go
autocode/docs/qa/pty-tui-bug-report.md
autocode/pyproject.toml
autocode/src/autocode/agent/factory.py
autocode/src/autocode/agent/loop.py
autocode/src/autocode/agent/prompts.py (new session: conversational guardrail)
autocode/src/autocode/agent/remote_compaction.py
autocode/src/autocode/agent/verification.py
autocode/src/autocode/layer2/rules.py
autocode/tests/pty/pty_phase1_fixes_test.py
autocode/tests/pty/pty_tui_bugfind.py (new session: binary path + B5→B6 Esc)
autocode/tests/unit/test_factory.py
current_directives.md
docs/tests/tui-testing-strategy.md
pyproject.toml
uv.lock
```

### 2.2 Untracked files

```
autocode/cmd/autocode-tui/milestone_a_test.go
autocode/docs/qa/vhs/
autocode/src/autocode/agent/hooks.py
autocode/src/autocode/agent/skills.py
autocode/src/autocode/agent/verification_profiles.py
autocode/tests/pty/pty_e2e_real_gateway.py
autocode/tests/pty/pty_narrow_terminal_test.py
autocode/tests/unit/test_compaction_provenance.py
autocode/tests/unit/test_hooks.py
autocode/tests/unit/test_rules_imports.py
autocode/tests/unit/test_skills.py
autocode/tests/unit/test_verification_profiles.py
autocode/tests/unit/test_vhs_differ.py
autocode/tests/vhs/
benchmarks/run_b7_b30_sweep.sh
deep-research-report.md
docs/plan/research-components-feature-checklist.md
docs/reference/claude-settings.sample.json
docs/reference/gateway-complaint-template.md
docs/reference/hooks-contract.md
docs/reference/rules-loader-contract.md
docs/reference/skills-contract.md
DEFERRED_PENDING_TODO.md (this file)
```

---

## 3. Deferred Stable TUI v1 Milestones

Per `PLAN.md` §1f and `EXECUTION_CHECKLIST.md` §1f. Keep these visible; do
not delete from the source docs. These are the items **not** landing in the
current TUI testing strategy slice, to be picked up after the slice closes.

### 3.1 Milestone C — Permissions, Sandbox, Hook Enforcement

| Item | Source doc anchor |
|---|---|
| Lock user-visible sandbox modes (read-only, workspace-write, full access) | `PLAN.md` §1f.3 |
| Lock per-tool policy behavior (allow/ask/deny/wildcard) | `PLAN.md` §1f.3 |
| Make rule matches explainable in the UI and logs | `PLAN.md` §1f.3 |
| Make hooks an enforcement surface (not just notification) | `PLAN.md` §1f.3 (some enforcement is in via Slice 4) |
| Diff-first guardrails for multi-file writes | `PLAN.md` §1f.3 |
| Exit gates: policy-matrix tests, sandbox-escape regressions, hook-enforcement tests, user-facing + agent-facing policy docs | `EXECUTION_CHECKLIST.md` Milestone C |

### 3.2 Milestone D — Sessions, Compaction, Provenance, Recovery

| Item | Source doc anchor |
|---|---|
| `/tree` navigation UI in Go TUI | `PLAN.md` §1f.4 |
| Crash-injection test suite (write/flush/compact/shutdown paths) | `PLAN.md` §1f.4 |
| Explicit manual compact + auto-compact UI surface | `PLAN.md` §1f.4 |
| Red-team compaction tests (tool/file output cannot silently become user instruction) | `PLAN.md` §1f.4 (provenance labels landed in Slice 5) |
| Explicit circuit-break policy docs | `PLAN.md` §1f.4 |
| `log.jsonl` / `context.jsonl` split — **DECIDED DEFERRED POST-V1** | `EXECUTION_CHECKLIST.md` §1f Milestone D |

### 3.3 Milestone E — Context Intelligence Baseline

| Item | Source doc anchor |
|---|---|
| Validate retrieval/comprehension on genuinely large repos | `PLAN.md` §1.1, §1f.5 |
| Diagnostics-after-edit surface in the TUI without overwhelming transcript | `PLAN.md` §1f.5 |
| Narrow-terminal diagnostics overflow behavior | `EXECUTION_CHECKLIST.md` §1f Milestone E |
| Latency + context-growth measurement runs | `PLAN.md` §1f.5 |

### 3.4 Milestone F — Verification Profiles, Release Gate, Measurement

| Item | Source doc anchor |
|---|---|
| End-to-end hook → profile → `verify.json` auto-wiring (users can configure in `.claude/settings.json` today; no auto-fire at PostToolUse yet) | `PLAN.md` §1f.6 (profiles landed in Slice 6) |
| Operational metrics: skill-trigger accuracy, hook success/failure rate, retry/loop counts, compaction-failure counts | `PLAN.md` §1f.6 |
| Separate-review path for review-only workflows (skill exists on disk; runtime invocation landed) | `PLAN.md` §1f.6 |
| Full `/export` polish | `PLAN.md` §1f.6 |
| Stable-v1 release note with validation matrix + known limitations | `PLAN.md` §1f.6 exit gate |

### 3.5 Cross-cutting Testing Matrix rows still open

From `PLAN.md` §1f "Cross-Cutting Testing Matrix For Stable V1":

- [ ] Crash/replay tests for session and compaction work
- [ ] Large-repo validation artifacts for context work

---

## 4. Open Items Already Tracked In EXECUTION_CHECKLIST.md

Not duplicated here — see `EXECUTION_CHECKLIST.md` for the authoritative list.
The items below are the open checkboxes (`[ ]`) as of 2026-04-17:

- **§0** (Harness Architecture Refinement From Proposal v2): keep `.harness/`
  file-tree migration deferred unless explicitly chosen later
- **§1** (Large Codebase Comprehension): validate on genuinely large repos
- **§1e** (Harness Phase 1):
  - ArtifactCollector wired into live middleware
  - Auto-checkpoint before risky tool calls
  - Hard verification gate behind explicit BUILD mode
  - Role separation (BUILD / REVIEW modes + `/build` `/review` slash commands)
- **§1f** — see §3 above (milestones C, D, E, F residuals)
- **§2** (Native External-Harness Orchestration):
  - Run each harness in its own worktree / isolated session
  - Capture transcript-first evidence from external runs
  - Codex adapter (depth)
  - Claude Code adapter (depth)
  - OpenCode adapter (depth)
  - Forge adapter (depth)
  - Explicit "simulate real human use" contract
- **§3** (Terminal-Bench / Harness Engineering):
  - Rerun the corrected 2-task Harbor subset
  - Only after subset improves, broaden B30 or attribute gap to model choice
- **§"Remaining Work (Post-Phase 8)"**:
  - Full benchmark regression after frontend switch-over
  - Ruff/mypy broader-repo debt cleanup
  - L3 constrained generation (llama-cpp-python with native grammar)

---

## 5. Resume Triggers

When TUI Testing Strategy closes, walk this file in priority order:

1. Section 1.1 — ping Codex on the 12-entry review backlog (or proceed
   without verdict per user judgment)
2. Section 2 — commit approval + stale-binary deletion + VHS re-run
3. Section 1.2 — post resolution notes to close 1105–1110
4. Section 1.3 — archive my own pre-task intents (1101, 1114)
5. Section 3.1 (Milestone C) — diff-first guardrails and policy matrix
6. Section 3.2 (Milestone D) — `/tree` UI and crash-injection
7. Section 3.3 (Milestone E) — large-repo validation
8. Section 3.4 (Milestone F) — operational metrics + auto-wiring
9. Section 4 — pick up remaining EXECUTION_CHECKLIST open boxes
10. Section 2 remaining (narrow-terminal, live-streaming artifact)

## 6. Housekeeping

- Every entry added to this file should name its source (Entry number,
  file path, or EXECUTION_CHECKLIST anchor) so future agents can verify.
- When an item lands, remove it here AND update the source doc in the same
  edit (per `feedback_doc_sync_discipline.md`).
- This file is not a replacement for `AGENTS_CONVERSATION.MD`, `PLAN.md`,
  or `EXECUTION_CHECKLIST.md` — it is an index of what has been temporarily
  set aside so nothing is lost.
