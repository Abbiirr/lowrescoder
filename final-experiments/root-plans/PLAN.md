# Plan — AutoCode Suite (PLAN_01–05 Roll-up)

**Date:** 2026-06-22 · **Reconciled:** 2026-06-23 · **Re-verified:** 2026-06-24
**Mode:** `plan-todo-workflow:research`
**Status:** Ready for `implement`, **Tier-0 correctness/safety first** (see `TODO.md` Tier-0; the 2026-06-23 audit reopened PLAN_04/05's optimistically-closed gates).

## Goal

Drive the AutoCode Suite from "5 plans at MVP, several env-broken test suites" to "every plan's MVP gate green, every cross-cutting test surface green." The output is verified by per-plan closing-gate commands plus the superproject-level `make -C lowrescoder test-all`.

This is a **roll-up**: the canonical, line-anchored analysis lives in two large files (cited below). The root-level `PLAN.md` / `TODO.md` / `TESTING.md` are the plan-todo workflow's contract; the large files are the spec.

## Context And References

- **Canonical plan files (source of truth):**
  - `lowrescoder/new_plans/01-trust-domains.md` — trust-domain architecture referenced by all 5 plans.
  - `lowrescoder/new_plans/PLAN_01_harness-ide.md` (837 lines) — substrate / MCP server.
  - `lowrescoder/new_plans/PLAN_02_video-agent.md` (558 lines) — content pipeline.
  - `lowrescoder/new_plans/PLAN_03_station-ide.md` (654 lines) — egui/wgpu IDE consumer.
  - `lowrescoder/new_plans/PLAN_04_anvil-teacher.md` (618 lines) — root-cause analyst + ACE playbook.
  - `lowrescoder/new_plans/PLAN_05_anvil-copycat.md` (558 lines) — registry + 3-channel copycat.

- **Canonical gap analysis (per-plan, line-anchored):** `lowrescoder/new_plans/NEW_PLANS_GAPS.md` (Jun-23, 65 KB) — verdict matrix (IMPLEMENTED / PARTIAL / MISSING / DEFERRED-DOCUMENTED) per plan section, plus §8 cross-cutting + closing-gate roll-up. *(The repo-root `NEW_PLANS_GAPS.md` is the stale Jun-22 snapshot.)*

- **Canonical remaining-TODO (per-plan checklist with file:line targets):** `lowrescoder/new_plans/NEW_PLANS_REMAINING_TODO.md` (Jun-23, 65 KB) — every checkbox references a plan line + a verification criterion + a closing-gate, plus an **Addendum (A.1–A.6)** and a **Tier-0 correctness/safety** table. *(Root copy is the stale Jun-22 snapshot.)*

- **Source-material + empirical audit:** `lowrescoder/new_plans/NEW_PLANS_REST_AUDIT.md` (Jun-23) — audits the docs the two above never touched (`harness_copy_teacher/` = Anvil, the ClipMind security stack, the autocode-station requirements + the two HTML mockups), corrects stale `❌`s (G5 distiller / `sense` / Channel B are **built**), flags the optimistic PLAN_04/05 closures, and carries the **§9 empirical test-run scoreboard** (suites actually run 2026-06-23).

- **Research artifacts (this pass):**
  - `temp-research/research-log.md` — research process, per-plan verdicts, test environment issues, decisions.
  - `temp-research/assumptions.md` — assumptions, risks, unknowns, open questions.
  - `temp-research/web-searches.md` — references (no external web searches needed; all in-repo).
  - `temp-research/context-summary.md` — compact reload for future agent turns.

- **Operator's prior stability report** (covers all test counts in this roll-up):
  - 112 passed + 1 skipped (video-agent) / 133 passed + 1 skipped (autocode/anvil) / 2305 passed + 12 skipped + 73 failed + 4 collection errors (autode core) / 187 passed + 3 failed (harness-tester) / 15 passed (harness-ide integration) / 26 passed (crates/station headless).

## Approach

### Plan ↔ component ↔ gate mapping

| Plan | Component (where to write) | Closing gate | Status |
|---|---|---|---|
| PLAN_01 | `harness-ide/src/` (Rust) | `cd harness-ide && cargo test --workspace` | Phases 0–3 MVP shipped; 4–5 partial; 6 absent. |
| PLAN_02 | `video-agent/src/video_agent/` (Python) | `cd video-agent && pytest` | Core complete; broll/music_duck parse-only; UI absent. |
| PLAN_03 | `harness-ide/crates/station/src/` (Rust egui/wgpu) | `cd harness-ide && cargo test -p autocode-station` | Trust-domain spine + hunk review + composer + A/B compare + approval card — real. ~80% traditional IDE, ~90% AI-IDE breadth missing. |
| PLAN_04 | `autocode/src/autocode/anvil/teacher/` (Python) | `cd autocode && uv run pytest tests/unit/test_anvil_teacher_*.py` | MVP online path shipped; G5 distiller + edge-cost measurement absent. |
| PLAN_05 | `autocode/src/autocode/anvil/{registry,census,gapdiff,propose,cli}.py` + `autocode/anvil/{patch_bundles,copycat}/` (Python) | `cd autocode && uv run pytest tests/unit/test_anvil_*.py` | Channel A complete; Channel B absent; Channel C-cheap wired (teacher emits); C-weights absent. 5 patch bundles (1 promoted, 4 gated_pass). |
| Cross | (test env fixes) | `cd autocode && uv run pytest tests/unit/ -v` plus `cd harness-tester && uv pip install -e ../autocode && pytest tests/` | 79 env-broken autocode unit + 3 `ModuleNotFoundError: autocode` in harness-tester. |

### Implementation strategy

> **2026-06-23 reconciliation.** PLAN_05 Channel B and PLAN_04 G5/`sense` are now **built** (the Jun-22 ordering below that started with them is superseded). The Jun-23 audit (`…/NEW_PLANS_REST_AUDIT.md`) re-prioritizes around **Tier 0 — correctness/safety false-greens** that cost a few lines because the machinery already exists. Do these before any feature work; full list in `TODO.md` Tier-0 (0a–0f).

0. **Tier 0 first.** (0a) wire the Anvil edge-cost guard into `gate` + make `promote` block on `no_regression`; (0b) egress-gate the ClipMind cloud planner; (0c) Anvil gate-component lockout test; (0d) station Inbox-default + maker/checker enforcement; (0e) `new_plans/INDEX.md` + fix the ClipMind README map; (0f) deterministic teacher-loop test (the only red). Each removes a false-green or a launch blocker.
1. **Then plan-by-plan, in any order.** Each plan's closing-gate command is the local green. Phases within a plan have exit gates; the exit gate is the closing-gate command for that plan in `TESTING.md`.
2. **PLAN_04 G4 (held-out corpus + split + noise band)** — the Phase-1 "do not proceed" measurement substrate the teacher is supposed to rest on; absent today, which is *why* the Gate-A closures are optimistic. Building it makes 0a trustworthy and de-optimisms the PLAN_04/05 closures.
3. **PLAN_01 substrate tool surface** — `git_push`/`open_pr` ✅, §5.1 REPL keybindings ✅, LSP 14/14 ✅ (verified 2026-06-24). The one remaining search tool is `semantic_search` (§2.2.2); then capability/signed-bearer auth + clientId multiplex (§6) and Phase-6 hardening (§7).
4. **Then PLAN_01 Phase 5 (semantic merge) + Phase 6 (git_push/open_pr).** These are the two missing tool scopes. Once they land, the MCP server exposes the full PLAN_01 §2.2.6 surface.
5. **Then PLAN_02 music_duck + broll renders** — these are parse-only today. Render is deterministic; the closing gate is the rendered MP4 SHA matching the snapshot.
6. **Then PLAN_03 carry-overs** — REPL keybindings, search panel, settings dialog, multi-workspace, terminal panel, debug adapter, etc. The MVP is the closing gate; the carry-overs are opt-in.
7. **Finally, fix the cross-cutting test environment** — install Pillow, install/create `evals`, install `autocode` into `harness-tester`, init `.git`, fix `anvil/gate.py::_default_check_runner` to use a configurable runner, mark the model-dependent live E2E advisory.

### Modules / files likely to change (cross-plan)

- `harness-ide/src/tools/mod.rs` (PLAN_01 — add semantic merge + git_push + open_pr)
- `harness-ide/src/git/mod.rs` (PLAN_01 — fill in `git_push`, `open_pr` branches)
- `video-agent/src/video_agent/render/music_duck.py` (PLAN_02 — render, not just parse)
- `video-agent/src/video_agent/render/broll.py` (PLAN_02 — render)
- `harness-ide/crates/station/src/editor/repl.rs` (PLAN_03 — keybindings)
- `harness-ide/crates/station/src/ui/settings.rs` (PLAN_03 — settings dialog)
- `autocode/src/autocode/anvil/teacher/distill.py` (PLAN_04 G5 — new file)
- `autocode/src/autocode/anvil/teacher/cost.py` (PLAN_04 edge-cost — new file)
- `autocode/src/autocode/anvil/copycat/channel_b.py` (PLAN_05 Channel B — new file)
- `autocode/src/autocode/anvil/gate.py:42` (cross-cutting — configurable runner)
- `autocode/src/autocode/app/commands.py:1436` (cross-cutting — `_repo_root` overshoot)
- `harness-tester/pyproject.toml` (cross-cutting — install autocode as editable dep)

### Compatibility requirements

- **Crate split must be preserved.** `harness-ide/Cargo.toml:16-18` declares `crates/station`; `crates/station/Cargo.toml:13` depends on `harness-ide`. PLAN_01 = `harness-ide/`; PLAN_03 = `crates/station/`.
- **Tool registry dispatch must stay source-of-truth.** New tools register in `harness-ide/src/tools/mod.rs:29-80`; do not bypass the dispatcher.
- **Trust-domain scopes must stay in the policy tier.** PLAN_01 §3.3 lists `policy` as PLAN_01's differentiator; do not collapse `Approver::request` to bool.
- **Anvil Mtimes patch-bundle index must stay append-only.** PLAN_05 §6.2; do not retroactively rewrite promoted bundles.
- **ACE playbook must stay append-only.** PLAN_04 §2.3; Curator may compact, not delete.

### Non-goals (this pass)

- No new product features beyond what the 5 plans already specify. (Do not add a 6th trust domain, a 4th copycat channel, etc.)
- No CI/CD pipeline (no GitHub Actions test runs). `autocode/.github/`, `benchmarks/.github/`, `harness-tester/.github/workflows/docs.yml` are docs-only or empty today; that is the current state and is not in scope.
- No GPU / hardware-gated work. PLAN_05 §7 Phase 7 (Channel C-weights) requires RTX 4060 Ti 8–16 GB + per-provider ToS clearance; this is forever-deferred.
- No LiteLLM live E2E in CI. `autocode/tests/integration/test_anvil_teacher_e2e.py:55-103` is marked advisory.
- No replan of the plan structure. The 5-phase build sequence is the operator's chosen order; this pass executes it, not redesigns it.

## Risks And Decisions

### Top risks (in priority order)

1. **PLAN_03 is the most ambitious plan.** 654 lines of spec covering "Codex app + Cursor + Zed + traditional IDE + AI-IDE breadth." The current station is a working prototype/MVP, not the full surface. Risk: treating "PLAN_03 MVP" as "PLAN_03 done." Mitigation: `NEW_PLANS_GAPS.md` §3 enumerates what is missing per §1–§5 + §9 carry-overs; the implement pass works through them in order.
2. **Static-analysis risk.** The verdicts are based on source-reading, not test-execution. Risk: a tool registered in dispatch but raising at runtime would be marked IMPLEMENTED. Mitigation: the operator's prior stability report corroborates — 112 passed (video-agent) and 133 passed (anvil) mean registered tools actually run.
3. **Single-source risk.** All 5 plan files + the operator's stability report come from one operator. No second-author review. Mitigation: every claim in `NEW_PLANS_GAPS.md` is anchored to a `file:line` reference that a second reviewer can re-derive.
4. **Environment-broken tests are not product-logic risks.** 79 autocode failures + 3 harness-tester failures + 1 model-dependent E2E are env artifacts, not bugs. They are tracked as operational hazards in `NEW_PLANS_REMAINING_TODO.md` §X.
5. **The `policy` approval scope is a soft gap.** PLAN_01 §3.3 line 334 calls `policy` "PLAN_01's differentiator." Today `Approver::request` returns just `Approved/Denied`; the four scopes are not modeled as data. Risk: a future builder could treat this as IMPLEMENTED. Mitigation: the gap is called out explicitly in `NEW_PLANS_GAPS.md` §1.3.

### Key decisions (in priority order)

1. **Treat the operator's stability report as a known-good baseline; do not re-derive it.** The user explicitly stated "Saved to memory as suite-split-test-artifacts so this doesn't get re-derived." Re-running the full test suite in this research pass is unnecessary.
2. **`NEW_PLANS_GAPS.md` and `NEW_PLANS_REMAINING_TODO.md` are the canonical analysis and checklist.** The user asked for them explicitly; the plan-todo workflow expects analysis under `PLAN.md` / `TODO.md` / `TESTING.md`. The two large files are the source of truth; the small root-level files are the workflow's contract.
3. **`PLAN.md` at the repo root is a roll-up, not a re-write.** It points at `NEW_PLANS_GAPS.md` for analysis and `NEW_PLANS_REMAINING_TODO.md` for the per-item checklist. Re-rewriting 100 KB of line-anchored analysis into 200 lines of `PLAN.md` would lose the line refs.
4. **`TODO.md` at the repo root is the consolidated next-action list, with one entry per closing gate.** The plan-todo workflow expects a single checkbox list. `NEW_PLANS_REMAINING_TODO.md` has ~150 boxes; the root `TODO.md` has 5 plan-level entries + 1 cross-cutting.
5. **`TESTING.md` at the repo root is the closing-gate command table, with one test command per plan plus the cross-cutting and superproject gates.** The plan-todo workflow expects gates keyed to closing conditions.
6. **Cross-cutting `make -C lowrescoder test-all` is the superproject-level gate.** `lowrescoder/Makefile:12-19` defines `test / test-bench / test-all`; this is the canonical operator command.

### Open questions for the operator (defer to `implement` if not blocking)

- **Q1 — Priority order.** Confirm the Tier-0-first ordering (0a–0f, then PLAN_04 G4 corpus, then the PLAN_01 tool surface, then PLAN_02 renders, then PLAN_03 carry-overs, then cross-cutting test env). The Jun-22 "start with Channel B / G5" order is superseded — both are built.
- **Q2 — Channel C-weights.** Is PLAN_05 §7 Phase 7 (Channel C-weights, requires RTX 4060 Ti 8–16 GB + per-provider ToS clearance) in scope for this pass, or forever-deferred?
- **Q3 — Live E2E.** Should `autocode/tests/integration/test_anvil_teacher_e2e.py:55-103` be marked required (with a model pin) or always-advisory?
- **Q4 — `evals` package.** Is `evals` a public PyPI package (then `uv pip install evals` resolves) or an internal package (then it must be in the workspace)?

#### `[DECIDE]` list (from `…/NEW_PLANS_REST_AUDIT.md` §5 / TODO A.6 — user calls that *bound downstream scope*)

- **Anvil:** tool-vs-research-artifact stopping point (stop ~Phase 4 ≈ 80% of value, or push to 5–7?); autonomy cap + "Anvil may not create new planning docs"; default `reuse_scope`; harness-only vs rented-GPU distillation (RX 480 is not a trainer — ROCm dropped Polaris; the 8 GB 4060 Ti is the only one and QLoRA on 8B is "marginal-to-infeasible"); codename "Anvil" (locked-in-by-default via `autocode anvil …`).
- **ClipMind:** Q1 (cloud mode + its required egress gate — 0b), Q2 (logical-only isolation acceptable?), Q8 (build the injection + redaction corpus?).
- **Station:** v2-vs-v3 mockup target; approve-for-session taxonomy (the spec deliberately *rejects* "approve for session"); Skills-view fate; CRDT depth vs modelled-presence (req-doc §8 vs PLAN_03 §3.3 conflict); web/remote auth architecture; status-model state-machine ownership.

## How to read this roll-up

- For the **gap analysis** (what's done, what's partial, what's missing, what's deferred-and-documented), read `NEW_PLANS_GAPS.md` §1–§5 + §6 (cross-cutting) + §7 (closing-gate roll-up).
- For the **per-item checklist with file:line targets and verification criteria**, read `NEW_PLANS_REMAINING_TODO.md` (the "Code locations (where to write)" table at the top gives the file paths per plan).
- For the **runnable gates**, see `TESTING.md` at this repo root.
- For **decisions, risks, unknowns, open questions**, see this file's "Risks And Decisions" + `temp-research/assumptions.md`.
