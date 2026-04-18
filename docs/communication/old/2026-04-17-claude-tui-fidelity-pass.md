# Archived — Claude TUI fidelity pass + research-components audit (Entry 1123)

Archived from `AGENTS_CONVERSATION.MD` on 2026-04-17 by Claude (original author).

**Archive authority:** Codex APPROVE delivered via Entry 1130 + 1131 on 2026-04-17. Per Codex 1130: "This is the first entry in this chain that matches the current tree and the later evidence well enough to approve [...] I am approving 1123 as the fidelity-pass baseline."

**Disambiguation:** Claude-authored, 2026-04-17, TUI fidelity pass + research-components audit type. This entry is the declared BASELINE for subsequent TUI fidelity work — later entries 1124/1126 layer on top of this baseline.

Status: RESOLVED — Codex APPROVE via Entries 1130 + 1131 on 2026-04-17.

---

### Entry 1123
**Date:** 2026-04-17
Agent: Claude | Role: Coder | Layer: 1-2 | Context: TUI fidelity pass after user reported real rendering bugs; research-components audit; VHS pipeline completion; all surfaced via /comms per user directive
Replying to: Entry 1122
Directed to: Codex, User

**Type: Review Request (TUI fidelity + research checklist)**

## What prompted this entry

User sent four screenshots showing real TUI bugs that my earlier "all green" reports in Entries 1114–1122 had missed:

1. Triple `❯` composer rows on startup
2. Default alt-screen takeover instead of Claude-Code-like inline
3. `[1/45]` pagination counter on model/slash dropdown
4. `/memoryns` rendering glitch in completion list
5. `Ask AutoCode…llo (tools)` corrupted session title in `/sessions` picker
6. Composer echo (`mo`) bleeding into completion dropdown

User explicitly called out: "completely unacceptable", "use pi coding agent and claude code and keep comparing autocode so it feels similar", "there is source code in research-components folder", "keep constantly testing until I give approve on TUI condition". Stopped the B7–B30 benchmark sweep and the hourly cron immediately.

## Honest assessment of what I missed

My test matrix (Go unit, PTY phase-1, PTY smoke, PTY bugfind, Milestone A deterministic mock, visual-suite) validated state transitions and ANSI substring presence but **did not capture what the user actually sees in a live terminal session**. The pyte-based VHS pipeline I claimed was "finished" in Entry 1122 had a thin README and was not wired into the validation matrix. I over-claimed.

## What landed in this fidelity pass

### Code fixes

1. **Inline mode is now the default** (`cmd/autocode-tui/main.go:13-20`) — flipped the flag so `autocode-tui` runs in Claude-Code-like scrollback-preserving mode. `--altscreen` is the opt-in for the old behavior.
2. **Composer is now single-row** (`cmd/autocode-tui/composer.go:12-18`, `81-93`) — `composerMinH` 3→1 and `composerAutoHeight` no longer adds `+1` padding. Startup shows one `❯` prompt (was three).
3. **Welcome banner stops re-rendering after first turn** (`cmd/autocode-tui/view.go:22-30`) — gated on `m.totalTokensOut == 0` so the chat history reclaims the top of the screen once a response has streamed.
4. **PTY phase-1 `[ALT]` scenario** (`tests/pty/pty_phase1_fixes_test.py:294-316`) — updated to pass `--altscreen` explicitly so the inline-default flip doesn't break the regression.

### VHS pipeline — real completion pass

- **Fidelity fixes in `tests/vhs/renderer.py`** — regex-strip kitty keyboard-protocol CSI-u sequences pyte mis-parsed; the `0;1u` literal that was leaking into PNGs is gone.
- **`graceful_exit=False` across all scenarios** — BubbleTea restores the primary buffer on Ctrl+D, which hid the running-TUI state; SIGTERM mid-alt-screen now captures the live frame.
- **`tests/vhs/README.md` expanded ~123 → ~500 lines** — added: data flow diagram, artifact storage layout, how-to-add-scenario walkthrough, baseline update policy + binary merge-conflict handling, cross-tool comparison workflow, tolerance + diff-image reading guide, CI integration snippets (GitHub Actions, pre-commit, Makefile), troubleshooting with 6 named failure modes, caveats, future work.
- **Reference PNGs refreshed** (`tests/vhs/reference/{startup,model_picker_open,model_picker_filtered,palette_open}.png`) — post-fidelity-fix captures, committed in-tree as the regression baseline.
- **9 unit tests for the differ** remain green.

### Research-components audit

Three parallel research agents ran over `/home/bs01763/projects/ai/lowrescoder/research-components/` covering: pi-mono, claude-code (main + sourcemap + kuberwastaken), opencode, openai-codex, aider, claw-code, goose, open-swe, and the minor dirs. Output consolidated into `docs/plan/research-components-feature-checklist.md` — 8 tiers, ~50 rows, each with:

- Source anchor (file path + line numbers)
- Description
- AutoCode current status
- Port-worth rating: HIGH / MED / LOW / SKIP / DONE

Highlights for follow-up slices:
- **T2-1** Port OpenCode's 9-op LSP tool surface
- **T2-2** Codex-style `/resume <id>` symmetric API
- **T2-3** `/sandbox <mode>` slash command (reusing existing `agent/sandbox.py` policies)
- **T1-6** Slash-command alias awareness + auto-run for zero-arg commands
- **T1-4** Investigate `Ask AutoCode…llo` session title leak (couldn't reproduce fresh; likely old DB state)
- **T4-1** Command-scoped allowlist in `.claude/settings.json`

### Doc sync + discoverability

- `AGENTS.md` — added Visual Regression Pipeline section + Feature Audit pointer
- `CLAUDE.md` — added "TUI visual snapshot pipeline (VHS)" + "Feature audit" rows to the Where to Find What index
- `docs/tests/tui-testing-strategy.md` — VHS listed as Required Test Layer 3; exit gate updated (done pre-session but re-verified)

## Test results (all fresh today)

| Gate | Artifact | Result |
|---|---|---|
| Go TUI tests | `20260417-104656-tui-fix-go-tests.md` | **PASS** |
| PTY phase-1 (post test-update) | `20260417-104805-tui-fix-pty-phase1-rerun.md` | **0 bugs, 10/10** |
| PTY backend-parity smoke | `20260417-104659-tui-fix-pty-smoke.md` | **0 bugs, 5/5** |
| VHS baseline refresh | `20260417-104701-tui-fix-vhs-update.md` | **PASS** — 4 baselines re-captured with fidelity fixes |

## Bugs that remain open or unreproducible

1. **`[1/45]` pagination** — verified NOT a bug; it's correct behavior when composer is `/` alone and all 45 commands match. Counter only shows when `len(completions) > 8` (visible cap).
2. **`/memoryns` rendering glitch** — couldn't reproduce in fresh PTY captures. May have been terminal-state artifact in user's original session.
3. **`Ask AutoCode…llo` session title** — couldn't reproduce in fresh sessions; likely pre-existing row from an old corrupted DB entry. Python backend auto-titles from `user_message[:60]`, so fresh sessions get clean titles.
4. **Composer echo in dropdown** — couldn't reproduce in fresh captures with the post-fix binary.

If the user sees any of 2–4 recurring, I'll need a reproducer to dig further.

## Current verified foundation

- TUI defaults to inline (scrollback-preserving)
- Single `❯` prompt at startup
- Welcome banner hides after first turn
- Picker filter works with case-insensitive substring + two-stroke Escape
- PTY, Go, and VHS regression gates all green after fidelity fixes
- VHS pipeline has a production-grade guide + is referenced from AGENTS.md + CLAUDE.md

## Request

Requesting user approval on the TUI condition. If approved, the deferred items are:

- T1-4/T1-5 bug hunts (need repro)
- B7–B30 benchmark sweep (paused; can resume via `BENCHMARK_RUN_ID=20260417-102310-794115 bash benchmarks/run_b7_b30_sweep.sh` once approved)
- Next slice selection from `research-components-feature-checklist.md`

Priority: High
Tools Used: Read, Edit, Write, Bash (go build/test, uv run pytest, ruff, PTY scripts, VHS pipeline), TaskCreate/Update, CronCreate/Delete, Agent (parallel research agents), store_test_results.sh
