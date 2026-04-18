# Current Directives

> Last updated: 2026-04-17

## Active Phase

**Phase 7 COMPLETE. Phase 8 COMPLETE. Current work is the post-Phase-8 frontier. Immediate active slice: Stable TUI Program (`PLAN.md` Section `1f`). After Stable TUI: large-codebase validation, deeper native external-harness orchestration, and Terminal-Bench improvement.**

## Status

- **Phase 5 (5A0-5D):** COMPLETE — agent teams / delegation substrate
- **Phase 6 (6A-6D):** COMPLETE — packaging, bootstrap, installer, multi-edit, teams
- **Phase 7:** COMPLETE — runtime parity, packaging, UX, verification, benchmark closeout
- **Phase 8 (Internal Orchestration):** COMPLETE — orchestrator substrate plus live frontend switch-over
  - all 3 frontends now use `create_orchestrator()`
  - event schema, message store, task board, policy context, and team eval substrate landed
- **Migration:** COMPLETE — 4 submodules, workspace wiring
- **Installability:** COMPLETE for the plain command contract
  - `autocode` is on PATH on this device
  - `autocode --version` works
  - install smoke artifact exists: `autocode/docs/qa/test-results/20260403-173036-install-smoke.md`
  - note: `autocode doctor` still reports optional dependency gaps on this machine (for example `lancedb`), but the command itself is installed and runnable
- **`/loop` UX:** COMPLETE
  - recurring loop command landed
  - smoke artifact exists: `autocode/docs/qa/test-results/20260403-173500-loop-smoke.md`
- **Stable TUI Program:** Section `1f` is now a research-locked stable-v1 program, not a short closeout slice.
  - **Direction:** Go BubbleTea (`autocode-tui`) remains the default interactive frontend; Python `--inline` remains the explicit fallback until the migration surface is fully closed.
  - **Why:** `deep-research-report.md` concludes that stable replacement value comes from predictable runtime behavior, migration-compatible filesystem/lifecycle contracts, explicit permissions, durable sessions, and verification discipline rather than feature maximalism.
  - **Current verified foundation:**
    - Go TUI default routing is live.
    - BubbleTea v2 / Mode 2026 migration is done.
    - Steering queue, follow-up queue, `/fork`, multiline input, editor launch, frecency history, `/plan`, task dashboard, and status-bar enhancements are landed.
    - Backend parity for `steer`, `session.fork`, and per-turn `on_cost_update` is landed.
    - Focused PTY artifacts are green:
      - `autocode/docs/qa/test-results/20260415-080003-tui-backend-parity-pty-smoke-deterministic-v3-20260415.md`
      - `autocode/docs/qa/test-results/20260415-150741-pty-phase1-fixes.md`
  - **Execution order is fixed unless the user reprioritizes:**
    - **Milestone A:** runtime stability and deterministic TUI loop
      - lock startup, keyboard routing, palette/picker, resize, stream/tool interleave, inline/alt-screen, and crash-recovery acceptance cases
      - required verification: Go unit tests, deterministic mock harness, fresh PTY artifact
      - exit gate: no open runtime regressions; stored PTY runtime artifact proves the matrix
    - **Milestone B:** compatibility and migration contracts
      - finish `CLAUDE.md` / `CLAUDE.local.md` / bounded `@imports`, skill progressive disclosure + reload, hook lifecycle payloads, and migration-friendly export/session behavior
      - required verification: migration fixtures, hook-schema tests, skill reload tests, branch/export tests
      - exit gate: docs explicitly state supported contracts and unsupported edges
    - **Milestone C:** permissions, sandbox, and hook enforcement
      - lock read-only / workspace-write / full-access semantics, allow/ask/deny policy, explainable rule matching, and hook-blocked execution
      - required verification: policy matrix tests, sandbox escape regressions, hook enforcement tests, approval-flow tests
      - exit gate: every tested tool call has a deterministic and explainable permission result
    - **Milestone D:** sessions, compaction, provenance, and recovery
      - lock append-only sessions, branch/export invariants, explicit compaction behavior, provenance preservation, and compaction circuit breakers
      - required verification: crash-injection tests, branch/export invariants, compaction red-team tests, long-session simulations
      - exit gate: forced interruption cannot corrupt history and compaction cannot silently convert tool/file text into instruction text
    - **Milestone E:** context intelligence baseline
      - ensure repo-map path, cheap `@path` completion, deterministic post-edit diagnostics, and bounded-context behavior on larger repos
      - required verification: retrieval regressions, diagnostics-after-edit tests, large-repo validation artifacts, latency/context-growth measurements
      - exit gate: interactive path no longer depends on whole-repo stuffing to stay useful
    - **Milestone F:** verification profiles, release gate, and measurement
      - publish formatter/lint/typecheck/targeted-test profiles, hook-driven verification points, transcript/diff reviewability, and operational metrics
      - required verification: deterministic mock-harness suite, verification-profile suite, transcript/export tests
      - exit gate: stable-v1 release note can cite a complete validation matrix and known limitations
  - **Non-goals while Section 1f is active:**
    - remote-client architecture work
    - broad subagent UX
    - orchestration-first features that increase state complexity
    - parity-only features with no stability, compatibility, or verification value
  - **Status (2026-04-17, late-session):** Stable TUI v1 Slices 0-8 landed. Milestone A CLOSED, B CLOSED, D ~65%, F ~75%. On top of Entries 1114–1123, late-session work (Entry 1124) added: image #9 duplicate-queue-preview removal, system-prompt guardrail against tool-calls on trivial greetings, PTY bugfind binary-path + B5→B6 Esc cleanup, and pi coding agent wired at localhost:4000 (see `~/.pi/agent/models.json`) with 8 gateway aliases exposed for side-by-side TUI comparison. No commit yet.
  - **Immediate next task (ACTIVE SLICE):** TUI Testing Strategy — research + plan a pipeline that spins up multiple TUIs (autocode, pi coding agent, claude-code, opencode, codex CLI, aider, goose), captures their visual state, stores snapshots, and analyzes/compares them. Pi coding agent is already wired at `~/.pi/agent/models.json` with 8 gateway aliases. Detailed plan lands in `PLAN.md` §1g and `EXECUTION_CHECKLIST.md` §"TUI Testing Strategy (Active Slice)". Do NOT pick up Milestone C/D/E/F, benchmarks, or other deferred items during this slice.
  - **All other pending items:** see `DEFERRED_PENDING_TODO.md` at repo root. Walk that file top-to-bottom after the TUI Testing Strategy slice closes. Nothing there is dismissed — just temporarily set aside.
  - **Canonical references:** `PLAN.md` Section `1f`, `EXECUTION_CHECKLIST.md` Section `1f`, `deep-research-report.md`, `docs/tests/tui-testing-strategy.md`, `docs/tests/pty-testing.md`
- **Tests:** 1778 passed, 4 skipped
- **Benchmarks:** 23/23 GREEN (120/120, 100%)
- **B30 Terminal-Bench:** best confirmed score `40% (4/9)` with the `terminal_bench` alias; Harbor adapter baseline recovery is complete, score-improvement work remains open

## Canonical Benchmark State

### Internal benchmark suite

- **B7-B14:** `50/50`
- **B15-B29:** `70/70`
- **Combined:** **`120/120 (100%) — 23/23 GREEN`**

Treat this as the canonical internal quality signal unless a fresh reproducible regression supersedes it.

### B30 external benchmark

- Harbor adapter baseline recovery is complete
- deterministic two-task subset rerun proved the harness is healthier, but remaining limits are now at least partly model/strategy quality rather than just plumbing
- current best confirmed score: **`40% (4/9)`**

## Repository Structure

| Submodule | Contents | Tests |
|-----------|----------|-------|
| `autocode/` | Python backend, Go TUI, Phase 5+6+7 modules | ~1200 |
| `benchmarks/` | Harness, adapters, 77 fixtures, benchmark tests | ~200 |
| `docs/` | All documentation | — |
| `training-data/` | Training data | — |

Total: **1777+ tests, 0 failures in the latest stored full-suite artifact, 4 skipped**

## Key Artifacts

- B28 green: `docs/qa/test-results/20260330-045004-B28-autocode.json`
- B17 green: `docs/qa/test-results/20260330-034741-B17-autocode.json`
- Full pytest: `autocode/docs/qa/test-results/20260402-150707-full-suite-after-fixes.md`
- Install smoke: `autocode/docs/qa/test-results/20260403-173036-install-smoke.md`
- Loop smoke: `autocode/docs/qa/test-results/20260403-173500-loop-smoke.md`
- Phase 7 plan: `docs/plan/phase7-ship-ready.md`
- Internal-first orchestration research: `docs/research/autocode-internal-first-orchestration.md`
- Proposal-v2 adoption memo: `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- Detailed frontier implementation plan: `PLAN.md`

## Where to Look

| What | File |
|------|------|
| Benchmark harness | `benchmarks/benchmark_runner.py` |
| Benchmark adapters | `benchmarks/adapters/` |
| Phase 7 plan | `docs/plan/phase7-ship-ready.md` |
| Execution checklist | `EXECUTION_CHECKLIST.md` |
| Detailed execution plan | `PLAN.md` |
| Sprint index | `docs/plan/sprints/_index.md` |

## Key Policies

1. **Canonical benchmark model:** internal benchmark lanes are green; B30 remains a separate external benchmark track
2. **Provider policy:** local_free + subscription allowed; paid_metered FORBIDDEN
3. **Parity validity:** same harness + same subset + same budgets
4. **Packaged frontend:** Go TUI (`autocode-tui`) is the primary interactive frontend; Python inline REPL is available as an explicit `--inline` fallback; Python backend serves as the JSON-RPC subprocess daemon

## Next Work (Active Frontier — per EXECUTION_CHECKLIST.md)

### 0. Harness Architecture Refinement From Proposal v2 (Status: Landed Foundation)
- [x] Review `docs/research/harness-improvement-proposal-v2-2026-04-08.md`
- [x] Write the adoption memo
  - `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- [x] Formalize the four context planes in AutoCode-native terms
  - design doc: `docs/design/context-plane-model.md`
  - code: `ContextPlane`, `PlaneBudget`, `PlaneState` in `agent/context.py` (15 tests)
- [x] Define durable-memory write / preservation rules
  - code: `DURABLE_WRITE_TRIGGERS`, `TRANSIENT_EXCLUSIONS`, `should_promote_to_durable()` in `session/consolidation.py` (15 tests)
- [x] Normalize canonical runtime state before deeper adapter work
  - code: `RuntimeState` in `agent/context.py` with 12 fields including `working_set`
  - wired into `Orchestrator` as `runtime_state` property (10 tests)
- [x] Expand tool metadata to support scheduling/policy/compaction
  - code: 5 new fields on `ToolDefinition` in `agent/tools.py` (10 tests)
- [x] Improve artifact-first resumability
  - code: `HandoffPacket`, `CompactSummary`, `CheckpointManifest`, `ResumePacket` in `agent/artifact_collector.py` (7 tests)
- [ ] Keep any `.harness/`-style file-tree migration deferred unless explicitly chosen later
  - this is a policy guardrail, not the active implementation queue
### 1. Large Codebase Comprehension (Priority: queued after Section 1f)
- [x] Persistent repo-map / retrieval warmup on the live runtime path
  - iteration-zero bootstrap now warms the shared `CodeIndex` cache and injects a compact repo-map preview
- [x] Research-only comprehension agent/mode
  - live `RESEARCH` mode is now available for read-only repo investigation and concise implementer handoffs
- [x] Structured carry-forward memory (fallback compaction now tool-call-aware)
- [x] First-turn environment bootstrap
- [x] Aggressive output hygiene (caps, truncation markers, stale collapse)
- [x] Cheap file-reference UX (`@path`, line ranges, fuzzy completion, expansion)
- [x] Active working set prioritization for retrieval
  - reads, edits, writes, symbol introspection, and search hits now feed a bounded recent-file set
  - bootstrap surfaces the working set when available
- [ ] Validate this on genuinely large repos
  - measure turns-to-first-relevant-file, context growth, compaction frequency, and long-task recovery
- [x] LanceDB/retrieval dependency contract decided: profile-gated
  - `RetrievalTier` enum: BM25_ONLY / HYBRID_IN_MEMORY / HYBRID_PERSISTENT
  - `check_retrieval_tier()` auto-detects available deps
  - graceful degradation: BM25 always works, hybrid when installed
  - **WIRED INTO `autocode doctor`**: `check_retrieval_tier()` replaces `check_lancedb`
  - 8 tests in `test_retrieval_contract.py`

### 2. Native External-Harness Orchestration (Priority: queued after Section 1)
- [x] Research the command surfaces for Codex / Claude Code / OpenCode / Forge
- [x] Define the canonical `HarnessAdapter` contract and typed event boundary
- [x] Normalize external harness events into the live orchestrator/event model
  - `harness_event_to_orchestrator_dict()` bridges HarnessEvent → OrchestratorEvent
  - `stream_as_orchestrator_events()` chains adapter streams into orchestrator pipeline
  - all 12 HarnessEventTypes mapped to internal EventType
  - session/run context preserved in bridge
  - 14 tests in `test_event_bridge.py`
- [x] Fix adapter process-state bug
  - all 4 adapters now store proc on session.metadata["_process"] in stream_events()
  - snapshot_state() correctly reports active/ended
- [x] Build the first real native adapters on top of the researched CLI surfaces
  - adapters deepened: all 4 emit SESSION_STARTED events, capture git-diff changed files, detect process status
  - code: codex.py, claude_code.py, opencode.py, forge.py in `external/adapters/`
- [x] Keep AutoCode as the control plane; external tools remain worker runtimes, not copied internal clones
  - this architecture decision is already made; the remaining work is implementation depth
### 3. Harness Engineering / Terminal-Bench (Priority: queued after Section 2)
- [x] Non-interactive/autonomous mode (+13 pts estimated)
- [x] Mandatory planning enforcement (+10-15 pts)
- [x] Pre-completion verification middleware (+5-8 pts)
- [x] Progressive reasoning budget (+5-10 pts)
- [x] Doom-loop detection (+3-5 pts)
- [x] Marker-based command sync (+2-5 pts)
- [x] Task-family strategy overlays for Harbor (Section 3.1)
  - `TaskFamily` enum: HTML_OUTPUT, PYTHON_BUILD, GENERAL
  - `classify_task()` auto-detects family from task description
  - `StrategyOverlay` with per-family max retries, preferred/avoid tools, prompt guidance
  - 20 tests in `test_strategy_overlays.py`
  - **WIRED INTO HARBOR ADAPTER**: classify_task + get_overlay called at run start,
    family guidance injected into task prompt, overlay-based doom-loop thresholds,
    StagnationDetector + verifier_aware_retry_guidance active in tool loop
  - 4 integration tests in `test_harbor_adapter.py`
- [x] Verifier-aware retry behavior (Section 3.2)
  - `verifier_aware_retry_guidance()` requires extracting error signal before retry
  - max retry enforcement with stop message
- [x] Stronger stagnation detection (Section 3.3)
  - `StagnationDetector` catches N identical results in a row
  - actionable guidance to change approach
  - Harbor terminal command paths now use explicit completion markers instead of relying purely on fixed timeout behavior
- [x] Terminal-Bench Harbor adapter / first real run artifact
  - stored artifact: `autocode/docs/qa/test-results/20260402-030056-terminal-bench-first-run-artifact-rerun.md`
  - direct `write_file` / `read_file` helpers, planning bootstrap, anti-hallucination prompt guidance,
    doom-loop nudges, and tool-pair-safe compaction are live
  - provider/gateway failures no longer consume the adapter's successful-turn budget
  - focused regressions:
    - `autocode/docs/qa/test-results/20260402-075237-terminal-bench-harbor-adapter-regressions-rerun.md`
    - `autocode/docs/qa/test-results/20260402-075237-terminal-bench-harbor-adapter-ruff-rerun.md`
- [x] Re-run a small deterministic B30 subset after the Harbor fixes
  - first rerun artifact:
    - `autocode/docs/qa/test-results/20260402-082019-terminal-bench-harbor-subset-coding.md`
    - classification: placeholder-task manifest failure, not benchmark quality
  - corrected valid-task rerun artifact:
    - `autocode/docs/qa/test-results/20260402-082147-terminal-bench-harbor-subset-coding-valid-tasks.md`
  - corrected valid-task results:
    - `break-filter-js-from-html`: `0.0`
    - `build-cython-ext`: `0.0`
    - `0` infra / provider errors
  - conclusion: the Harbor adapter is materially healthier, but the remaining B30 limit is not just harness quality anymore
- [x] Terminal-Bench score-improvement pass
  - Adapter v0.3.1: write_file/read_file tools, planning enforcement, verification injection,
    binary file detection, stricter completion signals, post-error recovery, escalating doom-loop
  - Best score: **40% (4/9)** with `terminal_bench` alias (when strong models available)
  - Solved: log-summary-date-ranges, pytorch-model-cli, portfolio-optimization, modernize-scientific-stack
  - Score is model-dependent: 20% without strong models. Accepted 40% as baseline.

### 4. Product UX Acceptance — COMPLETE
- [x] Plain `autocode` command works from PATH after install
- [x] `autocode --version` works
- [x] install smoke artifact stored — `autocode/docs/qa/test-results/20260403-173036-install-smoke.md`
- [x] `/loop` landed with session-scoped recurring jobs
- [x] `/loop` smoke artifact stored — `autocode/docs/qa/test-results/20260403-173500-loop-smoke.md`

### 5. Unified TUI Consolidation — ACTIVE (Immediate Top Queue)
- **Target end state:** one interactive TUI, Go BubbleTea first.
- **Live state:** Go TUI is the default interactive path, but the Python inline fallback still exists behind `--inline`.
- Existing Go TUI work already landed (keep, do not redo):
  - `cmd/autocode-tui/model.go` — stagePalette, verbTicks, currentVerb
  - `cmd/autocode-tui/view.go` — renderPaletteView, renderThinking, spinner verbs
  - `cmd/autocode-tui/update.go` — Ctrl+K palette, handlePaletteKey
  - `cmd/autocode-tui/spinnerverbs.go` — 187 rotating verbs
  - `cmd/autocode-tui/statusbar.go`, `styles.go`, `commands.go`
  - All closeout gates now green — Section 1f is closeable:
    - ✓ PTY artifact: `autocode/docs/qa/test-results/20260415-150741-pty-phase1-fixes.md` (0 bugs, 5/5 scenarios)
    - ✓ CLI contract: `--inline` kept as explicit documented fallback; Go TUI is default; docs agree
    - ✓ Backend parity: `steer`, `session.fork`, `on_cost_update` landed in `server.py` with tests
    - ✓ Ruff: all 12 changed files clean (`20260415-150744-ruff-focused-20260415.md`)
  - Follow-up (not blocking commit): `log.jsonl` / `context.jsonl` split, Phase 7 feature backlog

### 6. External Native-Harness Orchestration — FOUNDATION COMPLETE
- [x] `HarnessAdapter` protocol contract
- [x] Event normalization layer (`external/event_normalizer.py`) with per-harness kind maps
- [x] adapter files exist for Claude Code / Codex / OpenCode / Forge
- [x] baseline adapter tests exist
- [ ] next step is deeper live orchestration integration on top of that substrate, not re-researching the command surfaces again

### 7. Infrastructure — COMPLETE
- [x] L3 constrained generation scaffold (`l3/engine.py`) — graceful fallthrough when unavailable
- [x] Ruff cleanup — 54 auto-fixes applied
- [x] 11 L3 engine tests passing

## Instructions

1. Check `AGENTS_CONVERSATION.MD` for pending messages before starting work
2. Phase 7+8 are complete — immediate next work is Section `1f` TUI parity completion, then resume the broader post-Phase-8 frontier
3. Run `uv run pytest autocode/tests/unit/ benchmarks/tests/ -v` after changes
4. Post progress to `AGENTS_CONVERSATION.MD`
5. See `EXECUTION_CHECKLIST.md` for research-backed frontier items
6. See `PLAN.md` for the detailed implementation plan behind each open checklist item
7. See `docs/research/harness-engineering-competitive-analysis.md` for Terminal-Bench patterns
8. Treat this file, `EXECUTION_CHECKLIST.md`, and `PLAN.md` as the live source-of-truth set; if they drift, sync them before broad new implementation work
