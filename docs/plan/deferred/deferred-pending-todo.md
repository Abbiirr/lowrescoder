# Deferred & Pending TODO

> Single consolidated store for everything NOT being worked on right now but
> MUST NOT be lost. Keep this file truthful.
>
> **Current active program:** Backend Robustness Tranche 4 (plan files at
> `docs/plan/backend-robustness-tranche-4-plan.md`,
> `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md`,
> `docs/plan/backend-robustness-tranche-4-checklist.md`).
> Predecessor Stabilize-and-Release Tranche 3 is reviewer-side closed; user
> 3.E commit + tag is pending; tranche-3 plan archive cut covered Entries
> 1548-1586 in `docs/communication/old/2026-04-27-stabilize-and-release-tranche-3-1548-1586.md`.
>
> Sections 1-5 below are HISTORICAL (TUI Testing Strategy era, 2026-04-17).
> They are preserved for reference; treat as superseded unless explicitly
> referenced by a current slice. Sections 6-8 are CURRENT and authoritative
> for items deferred from Tranche 4.

Last updated: 2026-04-28 (C4.G2 repo-map prompt injection deferral added as §6.5).
Original sections 1-5 last updated: 2026-04-17 late-session.
Owner: Claude (Reviewer/Architect) for sections 6-8; original Coder ownership
preserved on legacy sections.
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
docs/archive/deep-research-report.md
docs/plan/research-components-feature-checklist.md
docs/reference/claude-settings.sample.json
docs/reference/gateway-complaint-template.md
docs/reference/hooks-contract.md
docs/reference/rules-loader-contract.md
docs/reference/skills-contract.md
docs/plan/deferred/deferred-pending-todo.md (this file)
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

## 6. Backend Robustness Tranche 4 — Items Explicitly Deferred (User Direction 2026-04-27)

Per user direction after the post-Stabilize-and-Release gap analysis (Entry 1585 review of Codex Entry 1584 closeout), the following backend robustness candidates from the 2026 frontier-product survey are deferred. They are NOT in scope for the upcoming backend-robustness tranche. Tracked here so they are not lost.

### 7.1 Cloud sandbox backends

- **Source products:** Open SWE (Daytona/Modal/Runloop/LangSmith), Cursor 2.0 Background Agents, Replit Agent 3
- **What it would add:** isolated VM/container per session for safe arbitrary-code execution; multi-tenant scaling; protection against destructive operations beyond what local OS sandboxing provides
- **Why deferred:** out of scope for AutoCode's local-first delivery; would require external infrastructure (Modal, Daytona, etc.) and a hosted offering shape we are not pursuing now
- **Revive trigger:** AutoCode ships a hosted offering, OR a stepping-stone single-machine sandbox (`nsjail`/`firejail`/`bubblewrap`) is wanted as a hardening pass on `FULL_ISOLATION`
- **Already in place:** `agent/sandbox.py` `SandboxPolicy` (NONE/READ_ONLY/WRITABLE_PROJECT/FULL_ISOLATION); approval modes; per-tool block coverage from S-BLOCKED

### 7.2 A2A (Agent-to-Agent) protocol support

- **Source:** Linux Foundation A2A v0.3 (donated by Google Cloud 2025-06-23); used by CrewAI, Google ADK, gastown
- **What it would add:** standardized AgentCard discovery; cross-org agent collaboration; multi-vendor agent orchestration via JSON-RPC over HTTPS + SSE
- **Why deferred:** AutoCode is a local-first single-agent today; no current cross-org agent-network requirement. Multi-agent orchestration happens via internal subagents (`agent/subagent_tools.py` + `task_tools.py`), not network protocol
- **Revive trigger:** AutoCode ships a multi-org coordination feature, integrates with vendor-managed agents (SAP, Salesforce, Microsoft Agent Framework), or wants to participate in an A2A-compliant marketplace
- **Coverage of the adjacent need (MCP — agent-to-tool, vertical):** SHIPPED via 2.F.1 (`autocode mcp-serve`) + 2.F.2 (audit log + lifecycle + doctor + concurrent-client). MCP is the agent-to-tool standard; A2A is the agent-to-agent standard. Both are governed under Linux Foundation but they solve different problems

### 7.3 GitHub-native asynchronous PR pipeline

- **Source products:** Open SWE (issue → plan → PR), Roo Cloud (autonomous cloud-runner), Cursor Background Agents, Devin
- **What it would add:** GitHub-issue / PR–triggered agent invocation; long-horizon autonomous loops; cloud-side execution decoupled from local IDE; in-thread status updates via GitHub comments
- **Why deferred:** AutoCode is a local terminal agent; this shape is a different deployment model (cloud runner + GitHub App + webhook handlers + auth surface)
- **Revive trigger:** AutoCode ships a hosted offering with a GitHub App integration; OR benchmark sweeps need autonomous-loop execution outside the user's local machine
- **Partial alternative already in place:** local benchmark harness (`benchmarks/run_b7_b30_sweep.sh`) runs autonomous loops locally; CI hooks could be added incrementally without committing to GitHub-native PR pipeline

---

### 6.4 User-custom cost-routing configuration (G6 Tranche 4 — partial-deferred)

- **Source products:** opencode (`/model` per-task), Continue Hub blocks, Goose multi-model recipes
- **What it would add:** user-controllable slash command surface like `/route lint=haiku refactor=sonnet plan=opus`; per-project `.autocode/route.yaml` overrides; runtime "force this turn to use model X" mode
- **What's in Tranche 4 G6 by default:** Layer 4.5 cost-aware multi-provider router with auto-selection based on task complexity + the per-model rate tables shipped in 2.F.3 (`agent/cost_dashboard.py`). Sensible defaults; no user-facing override surface
- **Why deferred:** auto-routing needs to prove itself before exposing knobs; user-custom config adds CLI/slash-command surface area that's not load-bearing for the first release
- **Revive trigger:** auto-routing is shipped and stable, AND a real user reports they want to override the default per-task model selection
- **Related items already shipped:** per-model rate tables (2.F.3), `/cost --detail` (S-COST), `provider_model` deprecation warning (2.F.4)

---

### 6.5 Repo-map system-prompt auto-injection (C4.G2 partial-deferred)

- **Source:** Claude Entry 1618 review of Codex Entry 1617; `docs/plan/backend-robustness-tranche-4-checklist.md` §4.G2 "Integration"
- **What it would add:** automatic insertion of the upgraded ranked repo map into the agent system prompt through the existing prompt `context` parameter
- **What shipped in C4.G2 instead:** ranked, token-budgeted repo-map generator; persistent mtime+sha cache; dependency fan-in ranking; Python tree-sitter extraction; conservative Go extraction; explicit `/repomap` and `/map` command surface
- **Why deferred:** automatic first-turn repo-map generation violates the existing bootstrap latency invariant enforced by `test_first_turn_includes_environment_bootstrap_snapshot`; repo-map generation must stay explicit or be composed by a later context-assembly path that can budget latency intentionally
- **Revive trigger:** a context-assembly slice intentionally decides when repo-map text belongs in prompt context, or C5 LSP integration adds a cheap incremental repo-map path that preserves first-turn latency

---

### 6.6 Clean B7-B30 rerun after gateway/provider stabilization (C4.GATE carryover)

- **Source:** Claude Entry 1639 review of Codex Entry 1637; full sweep artifact `autocode/docs/qa/test-results/20260428-202255-b7-b30-full-sweep-summary.md`
- **What it would add:** a clean post-fix B7-B30 benchmark verdict after gateway aliases and provider availability are stable.
- **Current sweep verdict:** `COMPLETE_WITH_FAILURES` from run id `20260428-122348-742618`: 24/24 lanes completed, 120/120 tasks recorded, 84/120 resolved, 31/120 infra failures, 0 lane process failures.
- **Pre-tranche baseline:** `120/120 (100%)` and `23/23 GREEN` per `current_directives.md` canonical benchmark state.
- **Why deferred:** the completed sweep exposed external gateway/provider instability, including unavailable `terminal_bench`, provider 403/429/404 paths, and intermittent gateway connectivity. The harness path itself now completes and records artifacts.
- **Revive trigger:** gateway/provider stabilization, specifically `terminal_bench` alias availability on the gateway plus a clean post-fix re-run path for B7/B8 lane processes.
- **Post-stabilization action:** run the full B7-B30 sweep with the current task-timeout harness and compare against the pre-tranche baseline. Strong-lane signal from the completed sweep suggests near-baseline recovery is expected once aliases/providers are stable.

---

## 7. Items Out of Scope for AutoCode's Shape (no revive trigger expected)

Different agent shape entirely; not on roadmap unless product direction changes:
- Voice-to-code (Aider): accessibility win, requires audio capture/transcription pipeline
- Browser / Computer Use mode (Replit Agent 3 reflection loop, Codex desktop): different agent shape (UI-driving)
- Real-time collaboration / agent sharing: requires multi-tenant backend + auth layer

---

## 8. Housekeeping

- Every entry added to this file should name its source (Entry number,
  file path, or EXECUTION_CHECKLIST anchor) so future agents can verify.
- When an item lands, remove it here AND update the source doc in the same
  edit (per `feedback_doc_sync_discipline.md`).
- This file is not a replacement for `AGENTS_CONVERSATION.MD`, `PLAN.md`,
  or `EXECUTION_CHECKLIST.md` — it is an index of what has been temporarily
  set aside so nothing is lost.
