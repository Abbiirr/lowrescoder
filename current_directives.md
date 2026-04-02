# Current Directives

> Last updated: 2026-04-02

## Active Phase

**Phase 7 COMPLETE. Phase 8 COMPLETE — all frontends wired to Orchestrator. 23/23 benchmarks green (115/115).**

## Status

- **Phase 5 (5A0-5D):** COMPLETE — 19 modules, 200+ tests
- **Phase 6 (6A-6D):** COMPLETE — packaging, bootstrap, installer, multi-edit, teams
- **Phase 7A0:** COMPLETE — canonical YAML config, `~/.autocode/config.yaml`, direct Ollama default endpoint
- **Phase 7A:** COMPLETE — shared factory/runtime parity, middleware live, delegation gating live, backend/TUI parity
- **Phase 7B:** COMPLETE — PyInstaller build on Linux x86_64; packaged `version`, `help`, `setup` smoke verified
- **Phase 7C:** COMPLETE — inline edit-specific apply/reject preview, conflict detection via observed-mtime warning/blocking
- **Phase 7D:** COMPLETE — routing benchmark, user guides, profiler wired into runtime summaries
- **Phase 7E:** COMPLETE — full regression pass, all benchmarks green, final approval
- **Phase 8 (Internal Orchestration):** COMPLETE — 8 sprints, 126 new tests, 5 new modules, frontend wiring done
  - 8A0: Schema migrations | 8A: Event schema | 8B: MessageStore | 8C: Task board
  - 8D: Orchestrator control plane | 8E: PolicyContext | 8F1/8F2: Team evals
  - Live frontend switch-over DONE: all 3 frontends use `create_orchestrator()`
- **Post-Phase 8 improvements (2026-04-01):**
  - Static/dynamic prompt split with caching
  - Deferred tool loading (`tool_search` meta-tool, `CORE_TOOL_NAMES`)
  - VCR record/replay for deterministic LLM tests
  - Memory consolidation (orient/gather/consolidate/prune pipeline)
  - Harness-engineering middleware on live runtime path:
    - autonomous/non-interactive mode
    - mandatory planning enforcement with task-board bootstrap
    - pre-completion verification retries after file mutation
    - doom-loop warnings for repeated edits/tool failures
    - iteration-zero workspace bootstrap snapshot
    - output caps, truncation markers, repeated-output collapse
    - progressive reasoning budget (high/low/high sandwich)
  - Structured carry-forward memory:
    - fallback compaction now uses tool-call-aware session snapshots
    - carry-forward summaries preserve objective, files read/modified, blockers, and next actions
  - L2 search surface:
    - `semantic_search` alias now exposed alongside `search_code`
    - live runtime now warms the shared `CodeIndex` cache on iteration zero
    - workspace bootstrap now includes retrieval-index stats plus a compact repo-map preview
    - repeated `search_code` / `semantic_search` calls now reuse the same cache object and pick up changed files via incremental `CodeIndex.build()` refreshes
    - a bounded active working set is now tracked from reads/edits/search hits and lightly biases `search_code` toward the files the agent is already working in
  - Research/comprehension mode:
    - dedicated `RESEARCH` mode now exists on the live runtime path
    - read-only enforcement now applies in both planning and research modes
    - inline, backend, and Textual persist the chosen agent mode across loop recreation
    - slash-command UX now includes `/research on|off|status` and `/comprehend`
    - prompt guidance now requires a concise implementation handoff with candidate files/symbols, active working set, repo-local command hints, and open questions
  - File-reference UX:
    - `@path` expansion/completion already live in inline + TUI
  - External-orchestration substrate:
    - canonical `HarnessAdapter` contract now exists in `autocode/src/autocode/external/harness_adapter.py`
    - typed request / handle / event / artifact / snapshot models now define the first stable boundary for native external adapters
    - `ExternalToolTracker` now includes Forge and can emit capability-aware `HarnessProbe` objects
- **Migration:** COMPLETE — 4 submodules, workspace wiring
- **Tests:** canonical full-suite artifact remains `1528 passed, 0 failed, 4 skipped` (2026-03-30); focused frontier slices passing on 2026-04-02
- **Benchmarks:** 115/115 (100%) — all 23 lanes green (B7-B29), verified 2026-04-01

## Benchmark Scores (2026-03-30, all green)

### B7-B14 (Core Suite) — 40/40 (100%)

| Lane | Score | Notes |
|------|-------|-------|
| B7 | **5/5** | |
| B8 | **5/5** | |
| B9-PROXY | **5/5** | |
| B10-PROXY | **5/5** | |
| B11 | **5/5** | |
| B12-PROXY | **5/5** | |
| B13-PROXY | **5/5** | |
| B14-PROXY | **5/5** | |

### B15-B29 (Expanded Suite) — 70/70 (100%)

| Lane | Score | Category | Notes |
|------|-------|----------|-------|
| B15 | **5/5** | Realistic Intake | |
| B16 | **5/5** | Requirement-Driven | |
| B17 | **5/5** | Long-Horizon | allow_test_file_edits + host-mode |
| B18 | **5/5** | Fresh Held-Out | |
| B19 | **5/5** | Multilingual | all host-mode |
| B20 | **5/5** | Terminal/Git/Ops | |
| B21 | **5/5** | Regression Preservation | |
| B22 | **5/5** | Corrupted State | |
| B23 | **5/5** | Collaborative Sync | |
| B24 | **5/5** | Security | weak-password-hashing host-mode |
| B25 | **5/5** | Managerial Review | |
| B26 | **5/5** | Economic-Value | |
| B27 | **5/5** | Efficiency | Docker safe.directory + loop termination |
| B28 | **5/5** | Reliability | all host-mode + protected_paths |
| B29 | **5/5** | Fault Injection | bwrap fallback + host-mode |

### Combined: 110/110 (100%)

## Repository Structure

| Submodule | Contents | Tests |
|-----------|----------|-------|
| `autocode/` | Python backend, Go TUI, Phase 5+6+7 modules | ~1200 |
| `benchmarks/` | Harness, adapters, 77 fixtures, benchmark tests | ~200 |
| `docs/` | All documentation | — |
| `training-data/` | Training data | — |

Total: **1528 tests, 0 failures, 4 skipped** (verified 2026-03-30)

## Key Artifacts

- B28 green: `docs/qa/test-results/20260330-045004-B28-autocode.json`
- B17 green: `docs/qa/test-results/20260330-034741-B17-autocode.json`
- Full pytest: `autocode/docs/qa/test-results/20260329-133352-phase7-full-pytest-final.md`
- Phase 7 plan: `docs/plan/phase7-ship-ready.md`
- Internal-first orchestration research: `docs/research/autocode-internal-first-orchestration.md`

## Where to Look

| What | File |
|------|------|
| Benchmark harness | `benchmarks/benchmark_runner.py` |
| Benchmark adapters | `benchmarks/adapters/` |
| Phase 7 plan | `docs/plan/phase7-ship-ready.md` |
| Execution checklist | `EXECUTION_CHECKLIST.md` |
| Sprint index | `docs/plan/sprints/_index.md` |

## Key Policies

1. **Canonical benchmark model:** `swebench` alias on LLM gateway
2. **Provider policy:** local_free + subscription allowed; paid_metered FORBIDDEN
3. **Parity validity:** same harness + same subset + same budgets
4. **Packaged frontend:** inline app is the shipping frontend; Go TUI remains source-tree/dev-oriented

## Next Work (Active Frontier — per EXECUTION_CHECKLIST.md)

### 1. Large Codebase Comprehension (Priority: First)
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

### 2. Harness Engineering (Priority: Parallel with #1)
- [x] Non-interactive/autonomous mode (+13 pts estimated)
- [x] Mandatory planning enforcement (+10-15 pts)
- [x] Pre-completion verification middleware (+5-8 pts)
- [x] Progressive reasoning budget (+5-10 pts)
- [x] Doom-loop detection (+3-5 pts)
- [x] Marker-based command sync (+2-5 pts)
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
- [ ] Terminal-Bench score-improvement pass
  - fix stale placeholder Harbor task ids in `benchmarks/e2e/external/b30-terminal-bench-subset.json`
  - baseline Harbor recovery is no longer the main blocker; the corrected valid-task subset finished `0/2` with `0` infra errors
  - next builder target is a narrow score-improvement sprint on the same two validated Harbor tasks:
    - `break-filter-js-from-html`
    - `build-cython-ext`
  - implement in this order:
    1. task-family strategy overlays in Harbor mode
       - output / HTML filtering tasks
       - Python build / Cython extension tasks
    2. verifier-aware retry guidance
       - require extracting failing output / verifier signal before another rebuild or rewrite loop
    3. stronger stagnation detection for repeated build/install/test cycles with no progress
    4. Harbor tool-surface / prompt tuning for file-edit vs shell-heavy task families
    5. rerun the same corrected `2`-task subset before broadening to more B30 tasks
  - only after the same subset improves should we expand B30 or attribute the remaining gap primarily to model choice

### 3. Product UX / Installability (Priority: Near-Term Builder Work)
- [ ] Make `autocode` runnable as a simple device command after install
  - target user experience: `autocode` works from any shell on this device like `codex` or `claude`
  - `uv run autocode ...` is **not** sufficient for this item
  - current substrate already exists:
    - `[project.scripts] autocode = "autocode.cli:app"` in `autocode/pyproject.toml`
    - `autocode doctor`
    - `autocode setup`
    - `packaging/installer.py` + `packaging/bootstrap.py`
  - the missing work is a real device-install contract:
    1. choose and document the canonical install path (short-term: `uv tool install --from . autocode`)
    2. ensure the installed command lands on PATH with explicit remediation when it does not
    3. make `setup` and `doctor` validate device-level invocation, not just repo-local readiness
    4. update user docs to prefer plain `autocode ...` after install
  - acceptance criteria:
    - from a fresh shell, outside the repo:
      - `autocode --version`
      - `autocode --help`
      - `autocode doctor`
      - `autocode setup`
      - `autocode chat --help`
    - all succeed without `uv run`
  - likely files:
    - `autocode/pyproject.toml`
    - `autocode/src/autocode/cli.py`
    - `autocode/src/autocode/packaging/installer.py`
    - `autocode/src/autocode/packaging/bootstrap.py`
    - `autocode/src/autocode/doctor.py`
    - `docs/guide/getting-started.md`
    - `docs/guide/commands.md`

- [ ] Add Claude-style `/loop` command
  - parity anchor: local Claude Code research clone, `research-components/claude-code/CHANGELOG.md` (`2.1.71`)
  - required behavior: run a prompt or slash command on a recurring interval
  - **do not** collapse this into `/mode autonomous`
  - command contract:
    - `/loop <interval> <prompt-or-slash-command>`
    - `/loop list`
    - `/loop cancel <id>` (or `/loop stop <id>`, but choose one canonical spelling)
  - required semantics:
    1. slash payloads route through `CommandRouter`
    2. prompt payloads route through the normal chat/orchestrator path
    3. loops are session-scoped and user-visible
    4. no overlapping executions for the same loop job
    5. current model/session/approval mode are inherited
    6. mutating loops do not silently escalate permissions
    7. inline/backend/Textual stay behaviorally aligned
  - implementation recommendation:
    - add a dedicated recurring-job scheduler/service
    - do **not** overload `LLMScheduler`, which is already serving LLM priority queuing
  - likely files:
    - `autocode/src/autocode/tui/commands.py`
    - `autocode/src/autocode/inline/app.py`
    - `autocode/src/autocode/backend/server.py`
    - `autocode/src/autocode/tui/app.py`
    - new scheduler/store module as needed
  - minimum acceptance criteria:
    - create/list/cancel recurring jobs
    - recurring prompt execution works
    - recurring slash-command execution works
    - same behavior across inline/backend/Textual

### 4. External Native-Harness Orchestration (Priority: After #1)
- [x] `HarnessAdapter` contract (probe, start, send, resume, interrupt, shutdown, stream_events)
- Codex adapter (`codex exec`, `exec resume`, `--json`, output-schema/final-message capture)
- Claude Code adapter (`claude -p`, `--output-format stream-json`, `--resume`, `--continue`, `--permission-mode`, `--worktree`)
- OpenCode adapter (`opencode run`, `--format json`, `--continue`, `--session`, `--fork`, `serve`, `attach`, `export`)
- ForgeCode adapter (transcript-first via native CLI: `--prompt`, `--conversation-id`, `--sandbox`, `conversation dump/resume/info/stats`)
- Research note: `docs/research/external-harness-adapter-command-matrix.md`

### 5. Deferred
- L3 constrained generation (llama-cpp-python with native grammar)
- Broader repo ruff/mypy debt cleanup

## Instructions

1. Check `AGENTS_CONVERSATION.MD` for pending messages before starting work
2. Phase 7+8 COMPLETE — next work is frontier product UX + harness engineering
3. Run `uv run pytest autocode/tests/unit/ benchmarks/tests/ -v` after changes
4. Post progress to `AGENTS_CONVERSATION.MD`
5. See `EXECUTION_CHECKLIST.md` for research-backed frontier items
6. See `docs/research/harness-engineering-competitive-analysis.md` for Terminal-Bench patterns
7. After the installability and `/loop` features land, the next Codex task is a review gate:
   - verify completeness against these acceptance criteria
   - review quality / bugs / regressions
   - cite fresh stored artifacts before approval
