# Backend Robustness Tranche 4 — Master Plan

> **Status:** ACTIVE.
> **Date:** 2026-04-27.
> **Authors:** Claude (Reviewer/Architect) drafted, User approved scope (comprehensive Tier 1 + Tier 2; 15 slices) on 2026-04-27.
> **Companion plans:**
> - `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md` — detailed sub-plan for the multi-language LSP slice (Checkpoint 5)
> - `docs/plan/backend-robustness-tranche-4-checklist.md` — master atomic checklist with per-task checkboxes
> - `docs/plan/stabilize-and-release-plan.md` — predecessor program (closed)
> - `DEFERRED_PENDING_TODO.md` §6 — items explicitly deferred from this tranche

This plan organises the path from the **fully closed Stabilize-and-Release Program** (Codex Entry 1584 closeout, Claude Entry 1585 reviewer APPROVE, Codex Entry 1586 ack, user 3.E commit `1700d66 Closes backend v2` 2026-04-27 — optional release tag at user discretion) to a release-ready, robust backend that closes most of the 2026-frontier-product feature gap. After Tranche 4 closes, archive this file alongside the other completed plans and update `PLAN.md` Ordered Backlog item 1.

---

## Status Snapshot (2026-04-27)

**Predecessor program:** `docs/plan/stabilize-and-release-plan.md` is fully closed. User 3.E commit `1700d66 Closes backend v2` landed 2026-04-27. Optional release tag at user discretion. Tranche 3 comms cleanup batch (Entries 1548-1586) was archived 2026-04-27 to `docs/communication/old/2026-04-27-stabilize-and-release-tranche-3-1548-1586.md`.

**Current backend baseline** (from `docs/features/backend_features.md`):
- 38 tools (16 core + 22 deferred via `tool_search`)
- 4 approval modes + sandbox policy
- 4 hook types (PreToolUse / PostToolUse / Stop / SessionStart)
- MCP server with audit-log JSONL + lifecycle + doctor + concurrent-client (shipped Tranche 3)
- Cost dashboard with per-model rates + threshold (shipped Tranche 3)
- Skills with progressive disclosure
- Episode summarization, session checkpoints with restore RPC, episode store, blob store
- Verification profiles (python/go/js/rust)
- LSP-style tools (Jedi-backed, Python only — 4 of 9 ops)
- Sub-agents via task tools

**Tranche 4 scope:** comprehensive (Tier 1 + Tier 2 = 15 slices) per user direction. All Tier 3 items (cloud sandbox, A2A, GitHub PR pipeline) explicitly deferred to `DEFERRED_PENDING_TODO.md` §6 except multi-language LSP which is in scope.

**Operating cadence (same as Tranche 3, with new constraint #8 added 2026-04-27):**
1. Codex does not block on review — kickoff → work → completion review request → continue to next slice immediately.
2. Claude reviews each completion and queues the next slice instruction.
3. **Agents must not run any tree-mutating git command** per `AGENTS.md` and `CLAUDE.md`. Commit / tag / push gates remain user-owned.
4. **Permitted agent git operations** (read-only or additive index-only, all comply with AGENTS.md "no tree-mutating git commands"):
   - `git status`, `git diff`, `git log`, `git show` — read-only
   - `git fetch` — updates remote-tracking refs only; does NOT modify working tree (this replaces the earlier "git pull fetch only" wording, which was technically incorrect — `git pull` always fetches AND merges, so it is forbidden)
   - `git stash list`, `git stash show` — read-only inspection only (NOT `stash push` / `stash pop` / `stash apply`, which mutate the working tree)
   - `git add` — index-only staging; does NOT modify the working tree
   - `git worktree add`, `git worktree list`, `git worktree remove` — creates/lists/removes a SEPARATE working tree (does NOT modify the current tree); used by 7.G13 for sub-agent isolation
5. **Forbidden agent git operations** (any of these requires user execution):
   - `git commit`, `git push`, `git tag`, `git reset` (any form), `git rebase`, `git merge`, `git pull` (because it merges), `git checkout` (any form, file or branch — mutates working tree), `git restore` (mutates working tree), `git stash push`, `git stash pop`, `git stash apply`, `git apply`, `git clean`
6. **Snapshot policy for G1 per-tool-call rollback:** local file copies under `~/.autocode/snapshots/<session_id>/<tool_call_id>/`. NO `git stash`. This eliminates the AGENTS.md tree-mutation conflict and removes the G1↔G7' ordering dependency (G1 can land before G7').
7. **Rollback execution:** the agent proposes the rollback diff and the user confirms. The agent then applies the rollback by overwriting working-tree files from the local snapshot directory (no `git checkout` / `git restore`). User may alternatively run `git restore <file>` themselves; the agent does not run it.
8. Benchmark sweep runs at every Checkpoint regression gate (per user direction).
9. Per-batch user authorization for any comms archive moves.
10. **Per-slice docs+artifact rule (user constraint 2026-04-27):** every slice (and every checkpoint gate) MUST update `docs/features/backend_features.md` AND store the verification artifact at the canonical path BEFORE Codex posts the completion Review Request. No "I'll sync docs after the review" deferrals — the docs sync and the artifact are part of the slice's exit gate, not optional follow-up. This applies to all 15 high-level slices and to every Cn.GATE.
11. **C5.G3 review cadence (user direction 2026-04-27):** hybrid — review G3.0 framework solo, then review per-language work in three batches: **Java/JS/TS** (G3.1+G3.2+G3.3), **C/Kotlin/Python** (G3.4+G3.5+G3.6), **Go/Rust** (G3.7+G3.8). Each batch is reviewed in a single combined entry once all three of the batch's slices are completion-posted. Codex still ships them serially; the review just batches.

**Codex-specific cadence rules adopted from user answers (2026-04-27):**
- 5.G3.6 Python migration: keep Jedi as fallback for one release window. Do NOT remove the load-bearing Jedi path in the same slice. Add explicit fallback tests and mark Jedi removal as a later cleanup slice (post-Tranche 4).
- LSP fixtures: start with canonical "Hello world + intentional error" fixtures for every language. Add one realistic 50-100 LOC fixture per language only where the adapter needs richer semantic surface (e.g. Kotlin extension functions, TS generics). Determinism wins.
- 7.G14 Watch mode marker syntax: canonical is `# AUTOCODE: <instruction>`. Aider-compatible `# AI:` is allowed as compatibility but is NOT the primary syntax for this iteration.
- 7.G12 Recipe schema: hybrid Goose-compatible base + AutoCode extensions. The base shape mirrors Goose recipes; AutoCode-specific extensions cover task tools, sub-agents, skills, permissions, and routing metadata.
- 7.G15 Marketplace registry: static JSON in repo at `docs/marketplace/registry.json` for this iteration. No remote fetch; GitHub Pages distribution layer is a later slice.

---

## Checkpoint structure (4 checkpoints, 15 high-level slices → 23 execution sub-slices, 4 gates)

| Checkpoint | Theme | High-level slices | Execution sub-slices | Gate |
|---|---|---|---|---|
| **C4** | Foundation & safety | G1, G2, G7' (3) | 3 (one-to-one) | C4.GATE: regression + benchmark |
| **C5** | Multi-language code intelligence | G3, G4 (2) | 10 (G3 expands into G3.0 framework + G3.1-G3.8 per-language = 9; plus G4 = 10) | C5.GATE: regression + benchmark + LSP smoke |
| **C6** | Headless & cost-aware routing | G5, G6 (2) | 2 (one-to-one) | C6.GATE: regression + benchmark + cost-routing canary |
| **C7** | Polish & nice-to-have | G8, G9, G10, G11, G12, G13, G14, G15 (8) | 8 (one-to-one) | C7.GATE: final release-grade regression + benchmark + closeout |

**Totals:**
- High-level slices: **15** (G1 through G15; G3 and G4 are each one high-level slice).
- Execution sub-slices: **23** (3 + 10 + 2 + 8 = 23; G3 alone expands into 9 sub-slices = framework + 8 languages).
- Checkpoint gates: **4** (C4.GATE, C5.GATE, C6.GATE, C7.GATE).
- Total work units (sub-slices + gates): **27**.

After each checkpoint gate is green: user reviews, optionally commits (commits are user-only), and authorises the next checkpoint to start.

---

## Checkpoint 4 — Foundation & safety

**Goal:** the working tree gets per-tool-call rollback, the agent gets a much better repo-map, and git-aware staging lands without violating the no-commit rule.

**Order:** sequential. Each substage exit-gates the next.

### 4.G1 — Per-tool-call atomic checkpoint with diff-rollback

**Why:** Cline/Cursor/Roo/opencode all ship per-tool-call snapshots; we have only session-level S-CKPTMSG checkpoints. Per-tool snapshots make "undo last tool call" possible without rewinding the whole turn.

**Surface:**
- New reducer state in `autocode/src/autocode/agent/loop.py` and `autocode/src/autocode/session/checkpoint_store.py`: snapshot working-tree-relevant files before each `mutates_fs=True` tool call.
- **Snapshot mechanism: local file copies under `~/.autocode/snapshots/<session_id>/<tool_call_id>/`.** No `git stash` (per AGENTS.md "no tree-mutating git commands"). G1 has no dependency on G7'.
- New slash command `/rollback` (alias `/rb`): list recent per-tool checkpoints, preview by ID or `--last`, and restore only via explicit `/rollback restore <id>`.
- Reuse existing `CheckpointStore` schema; add a `parent_tool_call_id` field plus a per-tool-checkpoint type.
- Rollback execution: agent overwrites working-tree files from local snapshot directory after user confirms; agent does NOT run `git checkout`/`git restore`.

**TDD:**
- RED unit test: agent loop snapshots before each `write_file` / `edit_file` / `apply_patch` / `run_command` call.
- RED reducer test: `/rollback` lists per-tool checkpoints with file diffs.
- RED reducer test: `/rollback <id>` previews without restoring; confirming with `/rollback restore <id>` reverses changes from the snapshot.

**Validation:** focused unit tests + Rust render test + PTY smoke that runs an edit, triggers `/rollback`, and asserts the file returns to pre-edit state.

**Artifact:** `autocode/docs/qa/test-results/<ts>-c4-g1-per-tool-checkpoint-rollback.md`.

**Detailed atomic checklist:** see `backend-robustness-tranche-4-checklist.md` §4.G1.

### 4.G2 — Tree-sitter repo-map upgrade

**Why:** `layer2/repomap.py` is basic; aider's pattern is the gold standard (token-budget ranked, dependency-graph aware, diskcache-invalidated, 20+ language tree-sitter extractors). Direct quality lift on every L2 retrieval.

**Surface:**
- Replace or wrap `autocode/src/autocode/layer2/repomap.py` with a token-aware ranked builder.
- Use existing tree-sitter 0.25.2 dependency.
- Diskcache-backed; invalidate by file mtime + content hash.
- Token budget enforced (suggest default 1000 tokens, configurable).
- Output is a markdown-formatted symbol tree consumable by `prompts.py` system-prompt builder.

**TDD:**
- RED unit test: ranking respects dependency graph (file imported by N others outranks file imported by N-1 others when token budget is tight).
- RED unit test: diskcache invalidation when file mtime changes.
- RED unit test: token budget enforcement.

**Validation:** focused unit tests + integration test that asserts repomap shrinks under budget pressure + manual verification of output quality on `autocode/` itself.

**Artifact:** `autocode/docs/qa/test-results/<ts>-c4-g2-repomap-upgrade.md`.

**Detailed atomic checklist:** see `backend-robustness-tranche-4-checklist.md` §4.G2.

### 4.G7' — Git-aware staging + working-tree snapshot (no commits)

**Why:** aider auto-commits; AutoCode cannot commit. Reframed: the agent stages changes (`git add` only — index-only, AGENTS.md compliant) for the user to commit later. Working-tree snapshot is owned by G1 (local file copies, not `git stash`). G7' is purely about staging discipline + proposing commit messages.

**Surface:**
- New `autocode/src/autocode/agent/git_aware_staging.py` module.
- After a successful edit (PostToolUse on `mutates_fs=True` tools that returned ok):
  - `git add <changed-files>` — index-only operation, AGENTS.md compliant
  - Display "Suggested commit message: ..." in the transcript via `on_token` event
- After failed verification (G4 once landed): no automatic git action; instead the verify failure surfaces via `on_warning` and the user can invoke `/rollback` (G1's local-file-snapshot path).

**Hard rules (per AGENTS.md):**
- **Permitted:** `git status`, `git diff`, `git log`, `git fetch`, `git add`, `git stash list/show` (read-only), `git worktree add/list/remove`.
- **Forbidden:** `git commit`, `git push`, `git tag`, `git reset` (any), `git rebase`, `git merge`, `git pull` (always merges → forbidden), `git checkout` (any form — mutates working tree), `git restore` (mutates working tree), `git stash push/pop/apply`, `git apply`, `git clean`.
- "Propose, don't execute": for any forbidden op the agent shows the user the exact command they could run; the agent never runs it.

**TDD:**
- RED unit test: post-edit successful path stages changed files via `git add`, displays proposed commit message, never invokes any forbidden op.
- RED unit test: forbidden git commands are blocked at the wrapper layer (a unit test scans `git_aware_staging.py` for forbidden subprocess invocations).
- RED unit test: failed-verification path emits `on_warning` and offers `/rollback` (does NOT auto-revert without user confirm; uses G1's local snapshot path).
- RED unit test: in non-git repos, `git add` is skipped; staging is a no-op without crashing.

**Validation:** focused unit tests + PTY smoke that exercises edit → stage → propose-commit-message round-trip.

**Artifact:** `autocode/docs/qa/test-results/<ts>-c4-g7-git-aware-staging.md`.

**Detailed atomic checklist:** see `backend-robustness-tranche-4-checklist.md` §4.G7.

### C4.GATE — Checkpoint 4 regression + benchmark

**Commands:**
- `uv run pytest autocode/tests/unit/ -q`
- `uv run pytest benchmarks/tests -q`
- `cd autocode/rtui && cargo fmt -- --check && cargo test && cargo clippy -- -D warnings && cargo build --release`
- `make tui-regression`
- `make tui-references` (xfail-ratchet check)
- PTY smoke set: comprehensive + checkpoint2 canary + new G1/G7' rollback PTY
- **Benchmark sweep**: `bash benchmarks/run_b7_b30_sweep.sh` (B7-B29 lanes) — first benchmark gate, captures pre-tranche baseline
- `git diff --check`

**Artifact:** `autocode/docs/qa/test-results/<ts>-c4-gate-regression-and-benchmark.md`.

---

## Checkpoint 5 — Multi-language code intelligence

**Goal:** AutoCode is no longer Python-only. LSP support for Java, JavaScript, TypeScript, C, Kotlin, Python (upgrade), Go, Rust. Auto-verify loop wires LSP diagnostics into the agent.

**Order:** Adapter framework first (5.G3.0), then per-language sub-slices in user-specified order, then G4 auto-verify last (depends on G3 being functional).

**Detailed sub-plan:** `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md`. Read that file before kickoff.

**Sub-slices:**
- 5.G3.0 — LSP adapter framework + lifecycle (subprocess management, stdio JSON-RPC, capability negotiation, doctor checks)
- 5.G3.1 — Java via `jdtls` (Eclipse JDT Language Server)
- 5.G3.2 — JavaScript via `typescript-language-server`
- 5.G3.3 — TypeScript via `typescript-language-server` (shares server with JS)
- 5.G3.4 — C via `clangd`
- 5.G3.5 — Kotlin via `kotlin-language-server`
- 5.G3.6 — Python via `pylsp` or `pyright` (upgrade from Jedi-only)
- 5.G3.7 — Go via `gopls`
- 5.G3.8 — Rust via `rust-analyzer`
- 5.G4 — Auto-verify loop using LSP diagnostics

Each language sub-slice ships:
- An adapter under `autocode/src/autocode/layer2/lsp_servers/<lang>.py`
- 9 LSP ops minimum: goto-definition, find-references, hover, document-symbol, workspace-symbol, implementations, call-hierarchy, type-definition, diagnostics
- A doctor check for the language server availability
- A focused PTY smoke that opens a fixture file in that language and exercises the 9 ops
- Documentation update in `autocode/TESTING.md` and `docs/architecture.md`

### C5.GATE — Checkpoint 5 regression + benchmark + LSP smoke

**Commands:** Checkpoint 4 gate commands + per-language LSP smoke artifacts + new auto-verify-loop unit/integration tests + benchmark sweep.

**Artifact:** `autocode/docs/qa/test-results/<ts>-c5-gate-regression-and-benchmark.md`.

---

## Checkpoint 6 — Headless & cost-aware routing

**Goal:** AutoCode supports programmatic / CI / dashboard integration via `--json` mode, and routes per-task to the right cost-tier model within Layer 4.

### 6.G5 — Headless `--json` / `--output-schema` mode

**Why:** Claude Code `-p --output-format stream-json` and Codex `exec --json` both ship NDJSON event streams for CI/audit/external dashboards. AutoCode's JSON-RPC is for the TUI; we need a separate programmatic surface.

**Surface:**
- New CLI subcommand: `autocode exec [PROMPT] --json` (or extend `autocode ask`).
- Output: NDJSON event stream covering `request_ack`, `status`, `token`, `thinking`, `tool_call`, `tool_result`, `cost_update`, `warning`, `error`, `done` events.
- Optional `--output-schema PATH` for typed-output mode (returns a single JSON object matching the schema; reuses the existing structured output path from `layer4/llm.py::generate_json`).

**TDD:**
- RED unit test: `autocode exec "what is 2+2" --json` emits NDJSON with at least the request_ack/token/done events.
- RED unit test: `--output-schema` returns a single JSON object matching the schema.
- RED unit test: error path emits a final `error` event then exits non-zero.

**Validation:** focused unit tests + integration test that pipes the output through `jq` and asserts well-formed NDJSON + benchmark of "headless turn against real gateway" added to canary.

**Artifact:** `autocode/docs/qa/test-results/<ts>-c6-g5-headless-json-mode.md`.

**Detailed atomic checklist:** see `backend-robustness-tranche-4-checklist.md` §6.G5.

### 6.G6 — Layer 4.5 cost-aware multi-provider router

**Why:** OI-MAS research shows ~80% cost reduction with confidence-aware routing; opencode/Goose/Continue all ship cost tiering. Our 4-layer architecture (L1-L4) is task-class routing; this adds intra-layer model tiering within L4.

**Per user direction 2026-04-27:** Layer 4.5 router with auto-selection. **User-custom config (e.g. `/route lint=haiku refactor=sonnet plan=opus`) is DEFERRED** to `DEFERRED_PENDING_TODO.md` §6.4.

**Surface:**
- New `autocode/src/autocode/layer4_5/router.py`: takes the routing decision before L4 invocation.
- Inputs: task class (from existing router), provider/model rate table (from `agent/cost_dashboard.py` shipped 2.F.3), confidence signal from L1 router or task complexity heuristic.
- Outputs: `ProviderSelection(provider, model)` with deterministic fallback if confidence is low.
- Default mappings (auto):
  - lint/format/typecheck-driven small edits → cheapest tier (Haiku-equivalent)
  - bug-fix on small file → mid tier (Sonnet-equivalent)
  - refactor / multi-file edit / architecture / planning → frontier tier (Opus-equivalent)
- Configurable via `~/.autocode/config.yaml` `routing.default_tier_map`.

**TDD:**
- RED unit test: small edit → cheapest tier; refactor → frontier tier; ambiguous → default tier per config.
- RED unit test: fallback when confidence is low.
- RED integration test: cost dashboard shows per-tier breakdown after a multi-tier turn.

**Validation:** focused unit tests + benchmark of "cost-routing canary" (B-style benchmark that measures cost reduction) added to canary.

**Artifact:** `autocode/docs/qa/test-results/<ts>-c6-g6-cost-aware-router.md`.

**Detailed atomic checklist:** see `backend-robustness-tranche-4-checklist.md` §6.G6.

### C6.GATE — Checkpoint 6 regression + benchmark + cost-routing canary

**Commands:** standard regression set + cost-routing canary lane (compare cost on B7-B14 lanes vs C5 baseline; expect 20-40% reduction on simple tasks).

**Artifact:** `autocode/docs/qa/test-results/<ts>-c6-gate-regression-and-benchmark.md`.

---

## Checkpoint 7 — Polish & nice-to-have

**Goal:** ship the Tier 2 polish features that lift AutoCode to frontier parity. Each is a small focused slice; total budget is roughly the same as one larger slice.

| # | Slice | Source pattern | Notes |
|---|---|---|---|
| 7.G8 | Plan/Architect ↔ Editor model split | aider, Cline Plan/Act, Cursor | Composes with 6.G6; uses cheap planner + strong editor (or vice-versa) |
| 7.G9 | AGENTS.md nestable per-directory memory | Codex AGENTS.md, Cursor Memories | Walk parents, merge per-dir rules into context |
| 7.G10 | Session fork/branch with rollout replay | Codex resumeThread(id) | Requires `parent_session_id` schema field; existing `session.fork` RPC already exists per `docs/features/backend_features.md` §"Slash Commands And Backend RPC Surface" |
| 7.G11 | Prompt cache keepalive | aider, Anthropic best practice | 5-min TTL pings on long-running sessions; pairs with cost dashboard cache-savings tracking |
| 7.G12 | Recipe/workflow YAML packaging | Goose recipes, Continue Hub blocks | Layered on top of skills; recipes call sub-tools/sub-skills |
| 7.G13 | Parallel sub-agents in isolated git worktrees | Claude Code subagents, Cursor BG Agents | `git worktree add` is permitted (creates a separate working tree, does NOT mutate the current one). Sub-agent works in worktree; **results merged back via `git diff` + `apply_patch` tool with explicit user confirmation** (NOT `git pull`, NOT `git merge` — both are forbidden tree-mutating operations). |
| 7.G14 | Watch mode (file-save trigger) | aider `# AI: refactor this` | Inotify/fswatch + comment-marker parser |
| 7.G15 | Plugin/marketplace registry pointer | Claude marketplace, Continue Hub, Codex plugin marketplaces | Read-only static JSON registry at `docs/marketplace/registry.json` per user direction. **No remote fetch this iteration.** `/marketplace install` is local-only / mock — it records intent and copies bundled items into `~/.autocode/skills/` or `~/.autocode/recipes/` from items that are already in-repo. Remote-fetch + GitHub Pages distribution is a later slice. |

**Detailed atomic checklist:** see `backend-robustness-tranche-4-checklist.md` §7.G8-G15.

### C7.GATE — Final release-grade regression + benchmark + closeout

**Commands:** Checkpoint 6 gate + final benchmark sweep with cost comparison + closeout entry posted to comms.

**Artifact:** `autocode/docs/qa/test-results/<ts>-c7-gate-final-release-and-benchmark.md`.

---

## Operating cadence reminders

1. **Each slice posts a kickoff Task Handoff entry, then a completion Review Request entry.** Codex continues to next slice after posting completion.
2. **Each slice's verification artifact path** matches `autocode/docs/qa/test-results/<ts>-<slice-id>-<short-description>.md`.
3. **Each slice's docs sync:** update `docs/features/backend_features.md` "Implemented Backend Features" with the new capability and remove from "Expected Backend Features Not Fully Implemented" / "Planned Or Deferred Backend Features" if listed there.
4. **Each Checkpoint gate:** stale-term audit, full regression set, benchmark sweep (B7-B29 minimum, optionally B30 if Harbor adapter is reachable), `git diff --check`, closeout artifact.
5. **No agent commits.** End-of-checkpoint commit decision is user-owned.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Multi-language LSP servers not always available on user machines | Medium | Graceful degradation: doctor reports missing servers; tools that need them return "language not supported" rather than crashing. Per-language slice ships a `setup` doctor check. |
| Auto-verify loop infinite-loops if AI fix introduces new errors | Medium | Hard iteration cap (suggest 3); halt-on-cost-cap; user-explicit `/verify off`. |
| Repo-map upgrade slows large-repo cold start | Low-Medium | Diskcache + lazy invalidation; benchmark gate measures startup time as part of C4.GATE. |
| Cost-routing canary triggers unexpected provider rate limits during gate | Low | Limit canary scope to B7-B14 (14 lanes), use OpenRouter's per-key rate ceiling. |
| Per-tool checkpoints (G1) bloat session DB | Medium | Configurable retention (default: keep last 50 per session); pair with episode store summarization. |
| LSP adapter framework breaks Python Jedi behavior | High during G3.0 | Existing Jedi `lsp_*` tools must keep working. Add migration test: `lsp_goto_definition` on a Python file works the same before and after G3.0 / G3.6. |
| Local snapshot directory grows large on long sessions | Low | G1's `~/.autocode/snapshots/<session_id>/` retention is bounded by `agent.checkpoints.per_tool_retention` (default 50). Older snapshots are pruned automatically. (`git stash` is NOT used per AGENTS.md "no tree-mutating git commands"; G7' is `git add` + propose-commit-message only; rollback overwrites working-tree files from the local snapshot directory.) |

---

## References

- Closed predecessor: `docs/plan/stabilize-and-release-plan.md`
- Backend feature inventory: `docs/features/backend_features.md`
- Frontend feature catalog: `docs/requirements_and_features.md`
- Research components: `research-components/MANIFEST.md` and `docs/plan/research-components-feature-checklist.md`
- Multi-agent landscape: `docs/research/multi-agent-landscape-2026.md`
- Deferrals tracker: `DEFERRED_PENDING_TODO.md` §6
- HR-5 program (closed): `docs/tui-testing/tui_implementation_plan.md`
- Sub-plans:
  - `docs/plan/backend-robustness-tranche-4-G3-multi-language-lsp.md`
  - `docs/plan/backend-robustness-tranche-4-checklist.md`
