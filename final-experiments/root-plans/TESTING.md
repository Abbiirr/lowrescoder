# Testing — AutoCode Suite (PLAN_01–05 closing gates)

**Date:** 2026-06-22 · **Reconciled:** 2026-06-23
**Operator baseline:** see `temp-research/research-log.md` §3 for the prior stability report.

**Empirical baseline — gate-verified after the 2026-06-23 implementation pass** (initial audit numbers in parentheses, `…/NEW_PLANS_REST_AUDIT.md` §9):**

| Component | Command | Result | Δ |
|---|---|---|---|
| harness-ide + station (PLAN_01/03) | `cd harness-ide && cargo test --workspace` | **82 passed, 0 failed** | +1 `semantic_search` test 2026-06-24; station 30 |
| video-agent (PLAN_02) | `cd video-agent && .venv/bin/python -m pytest` | **142 passed, 1 skip, 0 fail** | +30 (was 112) |
| Anvil teacher+copycat (PLAN_04/05) | `cd autocode && .venv/bin/python -m pytest tests/unit/test_anvil_*.py` | **210 passed** | +21 (was 189/194) |
| Anvil teacher loop (0f) | `…/test_anvil_teacher_e2e.py` | **1 passed, 1 skipped** (offline) | was the only red |
| harness-tester | `cd harness-tester && .venv/bin/python -m pytest` | **190 passed** | 3 `ModuleNotFoundError` cleared |

Tier-0's "only red in the repo" (`test_anvil_teacher_e2e.py` local-model flake) is resolved — a deterministic stubbed-gateway test now covers the path offline. (Use `.venv/bin/python -m pytest`, not `uv run`, per the offline-env note.)

Each plan's gate is the local command that proves the MVP is green. **The `tier_0` gate proves the already-built correctness/safety guards are actually *active*** (the audit's central finding: the mechanisms exist but aren't enforced). The cross-cutting gate proves the env is healthy; the superproject gate proves the whole suite is green at once.

## tier_0

**Scope:** activate the already-built guards the 2026-06-23 audit found inert (false-greens). No new features — wiring + enforcement + one test each.

Closing checks:

- **0a Anvil edge-cost guard active.** ✅ **DONE 2026-06-23.** `promote()` refuses a `met: true, no_regression: false` bundle; the gate CLI measures from `--baseline/--candidate-trajectories` and records `edge_cost_measured` honestly. Verified: `.venv/bin/python -m pytest tests/unit/test_anvil_*.py -k "edge_cost or promote"` → **11 passed**; full `test_anvil_*.py` → **194 passed**. (Use `.venv/bin/python -m pytest`, not `uv run`, per the offline-env note.)
- **0b ClipMind egress gate.** ✅ **DONE 2026-06-23.** Deny-by-default (`VIDEO_AGENT_ALLOW_EGRESS=1` or TTY confirm); ungated `--planner llm` refused (exit 3) before the source is read. Verified: `cd video-agent && .venv/bin/python -m pytest -k "egress or approval or planner"` → 8 passed; full suite 142 passed.
- **0c Gate-component lockout.** ✅ **DONE 2026-06-23.** A bundle targeting verifier/eval/metrics/registry/gate/promote/kill-switches is **refused at gate and promote** (word-boundary matched). Verified: `cd autocode && .venv/bin/python -m pytest tests/unit/test_anvil_*.py -k "gate_component or lockout"`; full `test_anvil_*.py` 210 passed.
- **0d Station Inbox-default + maker/checker in the GUI.** Launch view is `View::Inbox` (`app.rs:169`). The engine already enforces `maker ≠ checker` (`tools/run.rs:46-50`, `ui/app.rs:315-348`); the station GUI must expose a checker-set + confirm path (it currently only displays the line, `crates/station/src/app.rs:354-360`). Test: a station approval-card test drives the checker-confirm path and a maker cannot self-approve. `cd harness-ide && cargo test -p autocode-station`.
- **0e Docs.** ✅ **DONE 2026-06-23.** `lowrescoder/new_plans/INDEX.md` lists the 5 PLANs + Anvil + ClipMind + station with dependency edges; `README.md` rewritten to the flat 4-file reality, every link resolves.
- **0f Deterministic teacher loop.** ✅ **DONE 2026-06-23.** `test_anvil_teacher_e2e.py::test_teacher_student_end_to_end_stubbed_gateway` is green offline (no local-model dependency); the live test self-skips. Verified: `cd autocode && .venv/bin/python -m pytest tests/integration/test_anvil_teacher_e2e.py` → 1 passed, 1 skipped.

Manual check: each of 0a–0f has a runnable test that demonstrates the *refusal*/offline path (a guard), not just the happy path — all six verified green 2026-06-23.

## plan_01

**Plan:** PLAN_01 — Harness-IDE substrate.
**Code:** `harness-ide/src/` (Rust).
**Target:** all `cargo test --workspace` invocations pass; no `cfg(test)` regressions; trust-domain scope data-model and the §2.2.6 tool surface are wired.

Closing gate:

```bash
cd /home/bs01763/projects/ai/autocode-full/harness-ide && cargo test --workspace
```

Manual checks:

- All 10 git tools in `harness-ide/src/tools/mod.rs:29-80` dispatch and return without panic.
- `Approver::request` returns one of `{Approved, Denied, Pending}` with a structured reason (post-policy-scope fix).
- Semantic merge (`harness-ide/src/git/merge.rs` or equivalent) returns a 3-way conflict report, not just a bool.
- LSP surface is 14/14: `grep -c '"lsp_' harness-ide/src/tools/mod.rs` and `grep -c 'name: "lsp_' harness-ide/src/tools/lsp.rs` both return `14`. (verified 2026-06-24)
- `semantic_search` (§2.2.2): ✅ built 2026-06-24 — dispatched in `src/tools/mod.rs` and `specs()`-listed in `search.rs`; `cargo test --workspace` includes `semantic_search_ranks_and_respects_gitignore` asserting a free-form query returns ≥1 ranked `file:line: [score N]` result and respects `.gitignore` (walker uses `require_git(false)`).

## plan_02

**Plan:** PLAN_02 — Video-agent content pipeline.
**Code:** `video-agent/src/video_agent/` (Python).
**Target:** `pytest` green at 112 passed + 1 skipped; broll + music_duck tests render (not just parse); intent template fixtures all present.

Closing gate:

```bash
cd /home/bs01763/projects/ai/autocode-full/video-agent && pytest
```

Manual checks:

- `pytest video_agent/render/test_broll.py -v` — render assertion is `mp4_sha == snapshot_sha`.
- `pytest video_agent/render/test_music_duck.py -v` — ducking curve assertion is `np.allclose(curve, snapshot, atol=1e-3)`.
- `pytest video_agent/intent/test_templates.py -v` — every template in the registry has a fixture.

## plan_03

**Plan:** PLAN_03 — Station IDE (egui/wgpu).
**Code:** `harness-ide/crates/station/src/` (Rust).
**Target:** `cargo test -p autocode-station` green at the existing 26 headless tests; carry-over features pass their own per-feature snapshot tests.

Closing gate:

```bash
cd /home/bs01763/projects/ai/autocode-full/harness-ide && cargo test -p autocode-station
```

Manual checks:

- Trust-domain spine, hunk review, composer, A/B compare, approval card all pass their existing snapshot tests.
- REPL keybindings, search panel, settings dialog, terminal panel each have at least one new snapshot test once added.
- LSP-client upgrade keeps `crates/station/src/workspace.rs:234-247` happy (no API breakage on `harness_ide::core::Engine::lsp_symbols`).

## plan_04

**Plan:** PLAN_04 — Anvil teacher.
**Code:** `autocode/src/autocode/anvil/teacher/` (Python).
**Target:** `pytest tests/unit/test_anvil_teacher_*.py` green; G5 (offline distill) test exists and proves teacher replay beats teacher live on a real teacher trajectory corpus.

Closing gate:

```bash
cd /home/bs01763/projects/ai/autocode-full/autocode && uv run pytest tests/unit/test_anvil_teacher_*.py
```

Manual checks:

- Root-cause taxonomy rank = frequency × severity × (1 + is_tool_missing_capability × 2) holds on the existing fixtures.
- ACE playbook deltas are append-only (`autocode/src/autocode/anvil/teacher/curator.py`).
- G5 distill picks the smallest Channel B bundle whose replay score beats the live score on `tests/fixtures/teacher_corpus/*.jsonl`.

## plan_05

**Plan:** PLAN_05 — Anvil copycat (registry + 3 channels).
**Code:** `autocode/src/autocode/anvil/{registry,census,gapdiff,propose,cli}.py` + `autocode/anvil/{patch_bundles,copycat}/` (Python).
**Target:** `pytest tests/unit/test_anvil_*.py` green at 133 passed + 1 skipped; Channel B test exists; promotion of at least one `gated_pass` bundle is tested.

Closing gate:

```bash
cd /home/bs01763/projects/ai/autocode-full/autocode && uv run pytest tests/unit/test_anvil_*.py
```

Manual checks:

- Channel A (structural imitation) renders a sibling patch whose diff hash matches a fixture.
- Channel B (outcome distillation) renders a teacher-replayable form whose hash matches a fixture (new in this pass).
- Channel C-cheap (`reuse_scope = "outcomes"`) is exercised by the teacher output (`autocode/src/autocode/anvil/teacher/`).
- Anvil Mtimes patch-bundle index (`autocode/anvil/patch_bundles/`) is append-only — promoted bundles never get rewritten.

## cross_cutting

**Scope:** test environment (env-broken tests, not product logic).
**Target:** 79 env-broken autocode unit failures resolve to ≤0; 3 `ModuleNotFoundError: autocode` in harness-tester resolve to 0; live E2E is advisory.

Closing gate:

```bash
# 1. Autocode core unit suite
cd /home/bs01763/projects/ai/autocode-full/autocode && uv run pytest tests/unit/ -v

# 2. Harness-tester (after installing autocode as an editable dep)
cd /home/bs01763/projects/ai/autocode-full/harness-tester && uv pip install -e ../autocode && pytest tests/

# 3. (Optional) re-run the anvil teacher live E2E in advisory mode
cd /home/bs01763/projects/ai/autocode-full/autocode && uv run pytest tests/integration/test_anvil_teacher_e2e.py -v --maxfail=1 || echo "advisory: live E2E model-dependent, skip"
```

Manual checks:

- `python -c "from autocode.app.commands import _repo_root; print(_repo_root())"` returns the autocode repo root, not its parent.
- `python -c "import PIL; print(PIL.__version__)"` resolves.
- `python -c "import evals"` resolves (after PyPI install or local-workspace add).
- `cd /home/bs01763/projects/ai/autocode-full/autocode && git rev-parse --is-inside-work-tree` returns `true` (or the doctor git test is pinned).
- `python -c "from autocode.anvil.gate import _default_check_runner; print(_default_check_runner())"` returns a runner that does **not** hardcode `uv run pytest` (i.e., the runner is configurable).

## superproject

**Scope:** the whole suite at once.
**Target:** every component's MVP gate green in one invocation.

Closing gate:

```bash
cd /home/bs01763/projects/ai/autocode-full/lowrescoder && make test-all
```

(Equivalent to running `make test` (autocode + harness-tester + video-agent + benchmarks) and `make test-bench` and per-crate `cargo test`, per `lowrescoder/Makefile:12-19`.)

Manual check:

- Exit code 0.
- No `[skip]` line in the summary that wasn't there in the operator's prior stability report (i.e., the implement pass does not silently skip suites to game the gate).

## benchmarks

**Scope:** cross-cutting perf/eval surface.
**Code:** `benchmarks/`.
**Target:** benchmarks are runnable; their results are deterministic enough to compare across runs (within tolerance).

Closing gate:

```bash
cd /home/bs01763/projects/ai/autocode-full/benchmarks && uv run pytest -v
```

(If benchmarks do not have a pytest surface today, the closing gate degenerates to "the benchmarks directory is runnable via `python -m benchmarks.<entry>`" — record the actual command in the per-plan checklist once verified.)

Manual check:

- No `ModuleNotFoundError` on import.
- Output is comparable to the prior stability report's benchmark numbers.