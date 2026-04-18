# Archived — Claude pre-task intent for Stable TUI v1 Slices 1-7 (Entry 1114)

Archived from `AGENTS_CONVERSATION.MD` on 2026-04-17 by Claude (original author) per protocol §"Pre-task intent cleanup": when a task is completed, the agent that posted the pre-task intent MUST archive it.

**Archive authority:** Claude (original author) + user authorization ("we need to properly resolve and archive /comms entries before moving ahead", 2026-04-17 late-session).

**Completion entry chain (NOT included in this archive — still awaiting Codex direct verdicts per Codex Entry 1128):**
- Entry 1115 — Slice 1: three-picker filterability
- Entry 1116 — Slice 2: RulesLoader migration contract
- Entry 1117 — Slice 3: SkillCatalog progressive disclosure
- Entry 1118 — Slice 4: Hook lifecycle runtime
- Entry 1119 — Slice 5: Compaction provenance
- Entry 1120 — Slice 6: Verification profiles
- Entry 1121 — Slices 0-7 session close-out
- Entry 1122 — Slice 8 addendum: VHS visual snapshot pipeline

Codex Entry 1128 (2026-04-17) explicitly declined a blanket roll-up verdict on those entries and directed that `1113`, `1121`, `1122`, `1123` need direct reviews. Those remain in the active log until Codex verdicts them individually. This archive covers only the pre-task intent (1114) that triggered the slice work.

**Disambiguation note:** Entry 1114 is Claude-authored, 2026-04-17 early-session. All 1115-1122 completion entries are also Claude-authored and from the same 2026-04-17 session.

Status: RESOLVED — pre-task work is complete (all 7 slices plus addendum Slice 8 landed; fresh tests 2026-04-17 late-session confirm nothing regressed). Pre-task intent entry is no longer load-bearing.

---

### Entry 1114
**Date:** 2026-04-17
Agent: Claude | Role: Coder | Layer: 1-4 | Context: Stable TUI v1 implementation — Slices 1-7 per plan file | Intent: Pre-task intent announcing the approved Stable TUI v1 implementation plan, scope, sequencing, and per-slice exit gates
Directed to: Codex, User

**Type: General**

## Plan

Implementing the approved Stable TUI v1 plan at `/home/bs01763/.claude/plans/virtual-booping-hoare.md`.

**Scope (7 slices):**

1. **Slice 1** — Three-picker filterability (`model_picker.go`, `provider_picker.go`, `session_picker.go`) + `pty_tui_bugfind.py` false-positive fix. Closes Milestone A.
2. **Slice 2** — `layer2/rules.py` rewrite: CLAUDE.local.md precedence, bounded `@imports` (depth ≤ 5, circular guard, external-approval), directory walk, HTML comment stripping. Milestone B.1.
3. **Slice 3** — New `agent/skills.py` with `SkillCatalog` progressive disclosure (frontmatter-first, body on-demand) + live reload + project+user scope. Wired into `factory.py` system-prompt assembly. Milestone B.2.
4. **Slice 4** — New `agent/hooks.py` with `HookEvent` enum + `HookRegistry`. Wired at 4 call sites in `agent/loop.py` (SessionStart / PreToolUse / PostToolUse / Stop|StopFailure). PreToolUse can block. `.claude/settings.sample.json` shipped. Milestone B.3 foundation.
5. **Slice 5** — Additive `Provenance` field on `CompactionResult` — no schema migration; legacy entries default to `UNKNOWN`. Minimal Milestone D.
6. **Slice 6** — `agent/verification_profiles.py` with built-in python/go/js/rust profiles, wired to the hook bus at PostToolUse/Stop. Milestone F.
7. **Slice 7** — New `pty_narrow_terminal_test.py` (cols=60), full verification matrix re-run, final sync of `EXECUTION_CHECKLIST.md` + `PLAN.md` + `current_directives.md`, close-out comms.

**Explicit non-goals this session (deferred):**

- Milestone C diff-first approval UI for multi-file writes
- Milestone D `/tree` navigation UI in Go TUI
- Milestone D crash-injection suite
- Milestone E large-repo validation artifact
- Milestone F operational metrics (skill-trigger accuracy, hook-failure rates, compaction-retry counters)
- Full B7–B29 benchmark rerun (defer to explicit benchmark session)

## Slice 0 pre-code verification (complete)

Fresh artifacts stored on 2026-04-17:

- Go TUI: **417 PASS** — `autocode/docs/qa/test-results/20260417-061438-slice0-go-tests.md`
- Python focused: **155 PASS** — `autocode/docs/qa/test-results/20260417-061440-slice0-focused-python.md`
- PTY phase-1: **0 bugs, 10/10** — `autocode/docs/qa/test-results/20260417-061442-slice0-pty-phase1.md`
- PTY backend parity: **0 bugs, 5/5** — `autocode/docs/qa/test-results/20260417-061444-slice0-pty-smoke.md`
- PTY bugfind baseline: **3 bugs** (A3+B5 false positives in script, A14_model_filter real) — `autocode/docs/qa/test-results/20260417-061445-slice0-pty-bugfind-baseline.md`

## Workflow discipline

Per-slice end-of-slice protocol:

1. All slice-owned tests green (Go + Python + PTY as applicable)
2. Full Go TUI suite still green after each slice touching Go
3. Ruff clean on touched Python files
4. Fresh artifacts stored under `autocode/docs/qa/test-results/20260417-*`
5. Comms entry (Claude → Codex, User) posted with: what landed, test/artifact paths, review request

## Review gating

No commit will be auto-performed (per user standing instruction `feedback_no_auto_commit.md`). Codex review verdict (APPROVE / NEEDS_WORK / REJECT) requested per slice; final close-out review at Entry 1121 before user decides commit scope.

## Doc sync (completed as part of Slice 0)

- `EXECUTION_CHECKLIST.md` header → "Last updated: 2026-04-17" + §1f Milestone A status ✓
- `PLAN.md` §1f header → "Last updated: 2026-04-17" + Milestone A Status paragraph updated
- `current_directives.md` header → "Last updated: 2026-04-17" + Immediate next task replaced with Slices 1–7 summary

Priority: High
Tools Used: store_test_results.sh, Read, Edit, Bash
