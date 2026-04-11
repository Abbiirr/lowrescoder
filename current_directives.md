# Current Directives

> Last updated: 2026-04-11

## Active Phase

**Phase 7 COMPLETE. Phase 8 COMPLETE. Current work is the post-Phase-8 frontier. Immediate active slice: Claude Code primary TUI parity (`Section 1f`). After that: large-codebase validation, deeper native external-harness orchestration, and Terminal-Bench improvement.**

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
- **Claude Code primary TUI parity:** IN PROGRESS
  - partial Go TUI parity slice is already landed in the worktree
  - landed so far:
    - `❯` prompt
    - compact branded header
    - braille thinking spinner
    - simplified footer-first status bar
    - initial compact tool-row styling
  - still open:
    - compact approval prompt parity
    - completion/scrollback consistency with the live view
    - task-panel demotion when it adds dashboard noise
    - narrow-terminal hardening
    - focused Go TUI render/interaction coverage
    - manual smoke artifacts
    - slash-command discovery parity for bare `/`
    - arrow-key slash-menu navigation and Enter-to-select behavior
    - an on-screen `/model` picker instead of text-only model dumping
    - gateway-authenticated `/model` listing against `http://localhost:4000/v1`
    - clearer provider visibility and an intentional provider-switching UX
    - prompt/tool-schema consistency around `list_files` vs the live callable tool surface
  - codebase-specific findings from the current audit:
    - `http://localhost:4000/v1/models` returns `401` unauthenticated and `200` with `Authorization: Bearer $LITELLM_API_KEY`
    - shared gateway header logic already exists in `autocode/src/autocode/gateway_auth.py`
    - Python already exposes `/provider` and `/model`; the remaining gap is cross-surface parity and status/control visibility
    - `go version` is available on this machine, `cd autocode/cmd/autocode-tui && go test ./...` now passes, and Go-side testing is an active gate rather than an environment blocker
  - use `docs/qa/manual-ai-bug-testing-playbook.md` for live AI-behavior sweeps; render tests alone are not enough
  - every manual sweep must produce a filled artifact based on `docs/qa/manual-ai-bug-test-report-template.md`
  - apply the deep research selectively here:
    - prefer typed first-class provider/model/tool flows over shell-style fallback behavior
    - keep deferred-tool discovery explicit when the core tool set is intentionally narrow
    - treat prompt/tool-surface consistency as a product contract, not just a prompt-writing issue
- **Tests:** 1630+ passed, 4 skipped
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

Total: **1630+ tests, 0 failures in the latest stored full-suite artifact, 4 skipped**

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
4. **Packaged frontend:** inline app is the shipping frontend; Go TUI remains source-tree/dev-oriented

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

### 5. Claude Code Primary TUI Parity — ACTIVE (Immediate Top Queue)
- existing parity scaffolding is real:
  - `docs/design/claude-code-visual-parity.md`
  - `claude_like` profile in config / inline / Textual
  - parity-oriented inline snapshot coverage
- partial Go TUI parity work is already landed in the active worktree:
  - `cmd/autocode-tui/model.go`
  - `cmd/autocode-tui/view.go`
  - `cmd/autocode-tui/statusbar.go`
  - `cmd/autocode-tui/styles.go`
  - `cmd/autocode-tui/update.go`
  - matching test updates in `model_test.go`, `view_test.go`, `statusbar_test.go`, `update_test.go`
- do **not** restart this work from scratch; continue from the current Go TUI diff
- do **not** treat that scaffolding as end-state completion
- next work is to make the primary full-screen TUI feel structurally and behaviorally close to Claude Code
- the unfinished high-value items are:
  - compact approval prompt parity
  - compact completion/scrollback tool summaries
  - task-panel demotion when the screen should stay chat-first
  - narrow-terminal / truncation hardening
  - focused Go TUI render tests and manual smokes
  - bare `/` slash discovery parity with the Python router
  - gateway-authenticated `/model` behavior using the shared gateway auth helper
  - clear provider visibility and `/provider` UX
  - prompt/tool-surface consistency around `list_files` and `tool_search`
- completion requires:
  - refreshed parity contract from current Claude Code behavior signals
  - single-column chat-first TUI layout
  - footer-first status hierarchy
  - fixed-width braille/shimmer thinking spinner
  - compact tool rows and stable approval prompts
  - narrow-terminal hardening
  - focused render/snapshot tests
  - manual smoke artifacts
  - live Go validation on the actual module path
  - gated rollout until review says every zone is `Close` or better

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
