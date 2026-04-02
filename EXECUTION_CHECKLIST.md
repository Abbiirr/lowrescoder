# Execution Checklist

Last updated: 2026-04-02 (research mode and canonical HarnessAdapter contract landed)
Owner: Codex
Purpose: live status checklist for source-of-truth work, active next-frontier research-to-implementation items, and any benchmark/harness follow-up. Re-check this file every 10 minutes during active work.

## Active Frontier Work (Research-Backed)

Research note:
- `docs/research/large-codebase-comprehension-and-external-harness-orchestration.md`
- `docs/research/external-harness-adapter-command-matrix.md`

Current public competitive context used for these items:
- Terminal-Bench 2.0 public snapshot on 2026-04-01: Forge Code `78.4%`, Droid `77.3%`, Simple Codex `75.1%`
- The strongest public patterns are:
  - retrieval/indexing instead of whole-repo context stuffing
  - research/planning/execution context separation
  - structured compaction and output hygiene
  - native CLI / headless harness execution rather than bypassing the harness

### 1. Large Codebase and File Comprehension

- [x] Build a persistent repo-map / retrieval layer
  - live runtime now warms the shared `CodeIndex` cache during iteration-zero workspace bootstrap
  - the bootstrap snapshot now includes retrieval-index stats plus a compact repo-map preview
  - cache is keyed by project root and reused across the live session path
- [x] Add a research-only comprehension mode / agent
  - dedicated `RESEARCH` mode now exists on the live runtime path
  - persisted across loop recreation in inline, backend, and Textual frontends
  - slash-command UX:
    - `/research on`
    - `/research off`
    - `/research status`
    - `/comprehend` alias
  - prompt/handoff contract now explicitly asks for:
    - candidate files and symbols
    - active working set
    - repo-local command hints
    - open questions / uncertainty list
    - compact implementation handoff note
  - focused regression artifacts:
    - `autocode/docs/qa/test-results/20260402-054603-frontier-research-mode-regressions.md`
    - `autocode/docs/qa/test-results/20260402-054733-frontier-research-mode-ruff.md`
- [x] Replace generic compaction with structured carry-forward memory
  - fallback compaction now uses a tool-call-aware session snapshot from SQLite
  - carry-forward summary preserves objective, files read, files modified, plan progress, blockers, and next actions
- [x] Add first-turn environment bootstrap
  - iteration-zero middleware now injects a compact workspace snapshot
  - current snapshot includes project root, top-level repo shape, git branch/change count when available, and available tool preview
- [x] Add aggressive output hygiene
  - after-tool middleware now caps oversized payloads with explicit truncation markers
  - identical repeated tool payloads collapse to a short marker instead of bloating context
  - existing context-engine truncation remains the secondary guardrail
- [x] Add cheap file-reference UX
  - inline + TUI already support `@path` references, line ranges, fuzzy completion, and expansion through `tui/file_completer.py`
- [ ] Validate this work on genuinely large repos
  - measure turns-to-first-relevant-file, context growth, compaction frequency, and recovery after long tasks
  - include at least one repo where naive whole-context loading is obviously non-viable

### 1b. LanceDB + Retrieval Wiring (L2 Layer)

- [ ] Install LanceDB + sentence-transformers (`uv pip install lancedb sentence-transformers`)
  - best-effort code already exists; live warmup now uses the in-memory/shared cache path
  - the remaining work is making the dependency/runtime contract explicit
- [x] Wire jina-v2-base-code embeddings into agent loop for semantic code search
  - `layer2/embeddings.py` + `search_code` / `semantic_search` now expose the path on the live tool surface
- [x] Build project indexer: index all files at session start, incremental re-index on change
  - eager warmup now runs on the live runtime path during iteration-zero bootstrap
  - subsequent `search_code` / `semantic_search` calls reuse the same cache object and run incremental `CodeIndex.build()` refreshes against changed files
- [x] Add `semantic_search` tool to ToolRegistry (L2 query → ranked file/function results)
- [x] Hybrid search: BM25 keyword + vector similarity (config `hybrid_weight` already exists)
- [x] Active working set: track which files the agent is currently working with, prioritize in retrieval
  - reads, edits, writes, symbol introspection, and search hits now feed a bounded recent-file working set
  - workspace bootstrap now surfaces the working set when available
  - `search_code` now applies a small bias toward hot files instead of treating every retrieval turn as cold-start

### 1c. Harness Engineering Middleware (Terminal-Bench Patterns)

Research: `docs/research/harness-engineering-competitive-analysis.md`

- [x] Non-interactive / autonomous mode (+13 pts est.)
  - `ApprovalMode.AUTONOMOUS` landed in config/runtime
  - prompt guidance now explicitly prohibits user questions in autonomous mode
  - `ask_user` is blocked in autonomous mode
  - shell commands fail closed in autonomous mode when shell is not pre-enabled
- [x] Mandatory planning enforcement (+10-15 pts est.)
  - live middleware now detects likely multi-step requests and requires task-board use before non-planning tools
  - shared factory now bootstraps `TaskStore` + task tools on the live runtime path so planning is actually available
- [x] Pre-completion verification (+5-8 pts est.)
  - live middleware now retries text completion after file mutation until a verification-style tool runs
- [x] Progressive reasoning budget (+5-10 pts est.)
  - `ReasoningBudgetMiddleware` now applies a high/low/high sandwich across iterations
  - high on iteration zero, low during the execution band, high again during recovery / repeated-failure pressure
- [x] Doom-loop detection (+3-5 pts est.)
  - repeated same-file edits and repeated tool failures now inject recovery / doom-loop warnings
- [x] Marker-based command sync (+2-5 pts est.)
  - Harbor terminal command paths now wrap commands with a unique completion marker and strip it back out of stdout/stderr
  - this keeps completion detection explicit instead of relying only on fixed timeouts / shell flush behavior
- [x] Terminal-Bench Harbor adapter
  - external agent adapter wrapping AgentLoop for tbench submission
  - first real run artifact now stored:
    - `autocode/docs/qa/test-results/20260402-030056-terminal-bench-first-run-artifact-rerun.md`
  - direct `write_file` / `read_file` helpers, planning bootstrap, anti-hallucination prompt guidance,
    pre-completion verification, doom-loop nudges, and tool-pair-safe compaction are now live
  - provider/gateway failures no longer consume the adapter's successful-turn budget
  - focused regression artifacts:
    - `autocode/docs/qa/test-results/20260402-075237-terminal-bench-harbor-adapter-regressions-rerun.md`
    - `autocode/docs/qa/test-results/20260402-075237-terminal-bench-harbor-adapter-ruff-rerun.md`
- [x] Re-run a small deterministic B30 subset after the Harbor fixes
  - first rerun artifact:
    - `autocode/docs/qa/test-results/20260402-082019-terminal-bench-harbor-subset-coding.md`
    - classification: manifest / placeholder-task failure, not task quality
  - corrected valid-task rerun artifact:
    - `autocode/docs/qa/test-results/20260402-082147-terminal-bench-harbor-subset-coding-valid-tasks.md`
  - corrected valid-task results:
    - `break-filter-js-from-html`: `0.0`
    - `build-cython-ext`: `0.0`
    - `0` infra / provider errors
  - conclusion: Harbor execution is materially healthier now, but the remaining B30 limiter is no longer just harness quality

### 1d. Product Installability + Loop UX

- [ ] Make `autocode` runnable as a simple device command after install
  - goal: after supported installation on this device, `autocode` works from any shell like `codex` or `claude`
  - **do not** treat `uv run autocode ...` as success for this item
  - current substrate already exists:
    - `autocode/pyproject.toml` has `[project.scripts] autocode = "autocode.cli:app"`
    - `autocode doctor` exists
    - `autocode setup` exists
    - `autocode/src/autocode/packaging/installer.py` and `bootstrap.py` exist
  - missing contract is end-to-end installability + PATH visibility + fresh-shell verification
  - implement in this order:
    1. choose and document the canonical device install path
       - short-term dev/install target: `uv tool install --from . autocode`
       - packaged/binary path may coexist, but one canonical path must be declared first
    2. ensure install flow leaves a real `autocode` executable on PATH
       - verify `~/.local/bin` / platform bin dir handling
       - if PATH is wrong, fail with explicit remediation
    3. extend `autocode setup` / bootstrap to detect command-not-on-PATH situations
    4. extend `autocode doctor` to check device-level invocation health
       - `command -v autocode`
       - config path consistency
       - frontend/help/version readiness
    5. update user-facing docs to use the real installed command, not only `uv run`
  - minimum acceptance criteria:
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
  - required tests / artifacts:
    - packaging + bootstrap + doctor regressions
    - one stored fresh-shell install smoke artifact proving plain `autocode` works

- [ ] Add Claude-style `/loop` command
  - parity target from the local Claude Code research clone:
    - `research-components/claude-code/CHANGELOG.md` (`2.1.71`: “Added /loop command to run a prompt or slash command on a recurring interval”)
  - **do not** implement this as just an alias for `/mode autonomous`
  - command contract:
    - `/loop <interval> <prompt-or-slash-command>`
    - `/loop list`
    - `/loop cancel <id>` (or `/loop stop <id>`; pick one and document it)
  - required semantics:
    1. if payload starts with `/`, dispatch through the existing `CommandRouter`
    2. otherwise submit it as a normal chat prompt through the live frontend/orchestrator path
    3. loops are session-scoped and visible to the user
    4. no overlapping executions for the same loop entry
    5. loop executions inherit current session/model/approval mode
    6. mutating recurring loops must not silently escalate permissions
    7. inline, backend, and Textual paths must share the same behavior
  - implementation recommendation:
    - add a small recurring scheduler/service for session-level loop jobs
    - do **not** overload `LLMScheduler`; that queue is for LLM call priority, not user-facing recurring jobs
    - persist loop definitions if session resume support is added; otherwise explicitly document session-lifetime-only scope
  - likely files:
    - `autocode/src/autocode/tui/commands.py`
    - `autocode/src/autocode/inline/app.py`
    - `autocode/src/autocode/backend/server.py`
    - `autocode/src/autocode/tui/app.py`
    - new scheduler/store module as needed
  - required tests / artifacts:
    - slash parser + interval parsing
    - prompt loop execution
    - slash-command loop execution
    - list/cancel behavior
    - no-overlap guard
    - approval/mode inheritance
    - one stored interactive/manual smoke artifact
  - acceptance criteria:
    - user can create, inspect, and cancel recurring loops
    - recurring prompt execution is observable in the session
    - recurring slash-command execution works without special frontend-specific code paths

- [ ] Post-implementation Codex review gate for installability + `/loop`
  - after both features land, Codex reviews:
    - completeness against the acceptance criteria above
    - install-path quality and PATH/remediation behavior
    - `/loop` semantics parity, scheduler correctness, and frontend parity
    - bugs/regressions with fresh stored artifacts before approval

Validation artifacts for the completed 1c slice:
- `autocode/docs/qa/test-results/20260401-180039-harness-middleware-planning-verification-final.md`
- `autocode/docs/qa/test-results/20260401-180039-harness-middleware-planning-verification-ruff-final.md`
- `autocode/docs/qa/test-results/20260401-180438-harness-middleware-autonomous-regressions.md`
- `autocode/docs/qa/test-results/20260401-180449-harness-middleware-autonomous-ruff.md`
- `autocode/docs/qa/test-results/20260401-180726-harness-middleware-bootstrap-regressions.md`
- `autocode/docs/qa/test-results/20260401-180734-harness-middleware-bootstrap-ruff.md`
- `autocode/docs/qa/test-results/20260401-180923-harness-output-hygiene-regressions.md`
- `autocode/docs/qa/test-results/20260401-180931-harness-output-hygiene-ruff.md`
- `autocode/docs/qa/test-results/20260401-182039-frontier-carry-forward-reasoning-regressions-rerun.md`
- `autocode/docs/qa/test-results/20260401-182136-frontier-carry-forward-reasoning-ruff-pass.md`
- `autocode/docs/qa/test-results/20260401-182249-frontier-semantic-search-alias-regressions.md`
- `autocode/docs/qa/test-results/20260401-182307-frontier-semantic-search-alias-ruff-pass.md`
- `autocode/docs/qa/test-results/20260402-025702-frontier-retrieval-warmup-regressions.md`
- `autocode/docs/qa/test-results/20260402-025814-frontier-retrieval-warmup-ruff-pass.md`
- `autocode/docs/qa/test-results/20260402-030248-frontier-marker-sync-regressions-rerun.md`
- `autocode/docs/qa/test-results/20260402-030426-frontier-marker-sync-ruff-final.md`

### 2. External Native-Harness Orchestration

- [ ] Keep AutoCode as the control plane and external tools as worker runtimes
  - do not clone Codex / Claude Code / OpenCode / Forge behavior inside AutoCode
- [x] Exhaustive command-surface research pass completed for the first four native harness targets
  - Codex: `codex exec`, `exec resume`, `--json`, `--output-schema`, sandbox/approval flags
  - Claude Code: `claude -p`, `--output-format`, `--resume`, `--continue`, `--permission-mode`, `--worktree`, `--bare`
  - OpenCode: `opencode run`, `serve`, `attach`, `export`, `--format json`, `--continue`, `--session`, `--fork`, built-in `build`/`plan`
  - Forge: `forge --prompt`, `--conversation-id`, `--sandbox`, `--agent`, `conversation dump/resume/clone/info/stats`
  - see `docs/research/external-harness-adapter-command-matrix.md`
- [x] Adapter design now explicitly accounts for:
  - launch
  - stdin/prompt input
  - resume / continue / fork
  - permissions / sandbox
  - plan/read-only modes
  - worktree / isolation
  - transcript / export / JSON event capture
  - interrupt / shutdown / failure boundaries
- [x] Define a canonical `HarnessAdapter` contract
  - live code now exists at:
    - `autocode/src/autocode/external/harness_adapter.py`
  - contract includes:
    - `probe`
    - `start`
    - `send`
    - `resume`
    - `interrupt`
    - `shutdown`
    - `stream_events`
    - `capture_artifacts`
    - `snapshot_state`
  - typed request/handle/event/artifact/snapshot models now exist for the first-wave external harness adapters
- [x] Align runtime tool discovery with the researched first-wave harness set
  - `ExternalToolTracker` now includes:
    - Claude Code
    - Codex
    - OpenCode
    - Forge
    - Gemini
  - discovery can now emit canonical `HarnessProbe` objects with capability flags
- [ ] Normalize every harness into AutoCode’s event model
  - task/session/message/tool/approval/result/artifact lifecycle
- [ ] Run each harness in its own worktree / isolated session
  - preserve real-human behavior while avoiding shared-workspace corruption
- [ ] Capture transcript-first evidence from external runs
  - stdout/stderr, session ids, changed files, executed commands, final diff/commit, exit reason
- [ ] Codex adapter
  - target `codex exec`, `exec resume`, stdin prompts, `--ephemeral`, `--json`, sandbox modes, output-schema/final-message capture, optional MCP-server path
- [ ] Claude Code adapter
  - target `claude -p`, `--output-format stream-json`, `--resume`, `--continue`, `--fork-session`, `--permission-mode`, hook-aware scripting, worktree-aware continuation
- [ ] OpenCode adapter
  - target `opencode run`, `--format json`, `--continue`, `--session`, `--fork`, `--attach`, `opencode serve`, `export`, permission-aware sessions
- [ ] Forge adapter
  - start transcript-first via native CLI (`-p`, `--conversation-id`, `--sandbox`, `--agent`, `--event`, `conversation dump/resume/info/stats`) and only add richer integration if the public surfaces support it cleanly
- [ ] Explicit “simulate real human use” contract
  - drive native CLIs through cwd/worktree/env/stdin/stdout, not raw provider APIs
- [ ] Sequence this after internal comprehension/runtime improvements
  - large-codebase comprehension first
  - external adapters second
  - cross-harness team UX after adapters are trustworthy

## Current Status

- [x] Phase 7A0 runtime/config contract closed
- [x] Phase 7A runtime parity landed
- [x] Phase 7B PyInstaller build + basic smoke verified
- [x] Phase 7C edit preview/apply-reject and observed-mtime conflict blocking landed
- [x] Phase 7D profiler wiring landed
- [x] Shell completion smoke verified
- [x] Routing benchmark verified
- [x] Canonical Phase 7 verification artifact set exists
  - Full pytest: `1528 passed, 4 skipped`
  - Canonical benchmark closeout: all 23 lanes green, `110/110`
  - B28 closeout artifact: `docs/qa/test-results/20260330-045004-B28-autocode.json` => `5/5`
- [x] Final Phase 7 benchmark closeout summary posted in comms
  - Entry 904 + Entry 911
- [x] Phase 8 live frontend switch-over completed
  - All 3 frontends switched to `create_orchestrator()` (Entry 946, 2026-04-01)
  - Orchestrator delegates `run()`, `cancel()`, `set_mode()`, `get_mode()`, `session_id` to inner AgentLoop
- [x] Active post-closeout benchmark rerun fully classified
  - 23/23 green (115/115) confirmed 2026-04-01 — all failures were infra/provider, no capability regressions
  - B21 `add-feature-keep-tests` was a harness bug (protected-path restoring test_app.py), fixed with `allow_test_file_edits`
  - B22 `corrupted-virtualenv` was a fixture bug (dist-info not removed), fixed with setup.sh + force_host
- [x] Final docs/count sync after the rerun state settles

## Immediate Work Queue

### 1. Phase 8 Live Wiring — COMPLETE

- [x] Switch inline app to `create_orchestrator()`
- [x] Switch backend server to `create_orchestrator()`
- [x] Switch Textual TUI to `create_orchestrator()`
- [x] Re-run focused frontend/orchestrator tests after the switch (1407 passed, 0 failed)
- [ ] Run one live smoke of the primary frontend path after the switch

### 2. Benchmark Rerun Monitoring — COMPLETE

- [x] Benchmark rerun completed: 23/23 green (115/115, 100%)
- [x] All failures classified: infra/provider (gateway timeouts, rate limiting) + 2 harness bugs (B21, B22) — fixed
- [x] No capability regressions found
- [x] Fresh artifacts for B7, B8, B15, B20, B21, B22 stored alongside canonical closeout

### 3. Docs / Status Sync — IN PROGRESS

- [x] Checklist aligned with true remaining work (this update)
- [x] Update `current_directives.md` with latest frontier implementations
- [x] Store focused frontier artifacts for the landed research-mode slice

### 4. Post-Phase-8 Carry-Forward

- [ ] External harness adapters (Claude Code / Codex / OpenCode) on top of the internal control plane
- [ ] Full benchmark regression after the frontend switch-over
- [ ] L3 constrained generation (`llama-cpp-python` with native grammar)
- [ ] Broader repo `ruff` / `mypy` debt cleanup (still deferred, not a current blocker)

## 10-Minute Review Loop

Every 10 minutes, do this in order:

1. Check whether any benchmark command is still running.
2. Check `AGENTS_CONVERSATION.MD` tail for new directed work.
3. Check whether a fresh artifact landed in `docs/qa/test-results/`.
4. If a run failed, classify it immediately:
   - infra
   - harness
   - prompt/agent behavior
   - real capability miss
5. Update this checklist after any major state change.
6. Do not start a new broad task until the current rerun result is understood.
7. Keep “historical closeout green” separate from “active rerun still running” in all notes and comms.

## Fresh Evidence Already Available

- Full pytest:
  - `autocode/docs/qa/test-results/20260329-133352-phase7-full-pytest-final.md`
- Docker grading regression tests:
  - `autocode/docs/qa/test-results/20260329-135158-benchmark-docker-safe-directory-tests-rerun.md`
- Loop termination regression tests:
  - `autocode/docs/qa/test-results/20260329-140719-benchmark-loop-termination-regressions-rerun.md`
- Host-mode grading termination regressions:
  - `autocode/docs/qa/test-results/20260329-145040-benchmark-b29-run-command-termination-regressions-rerun.md`
- B29 fixture contract regressions:
  - `autocode/docs/qa/test-results/20260329-145331-benchmark-b29-fixture-contract-regressions.md`
- Routing benchmark:
  - `autocode/docs/qa/test-results/20260329-133352-phase7-routing-benchmark.md`
- Shell completion smoke:
  - `autocode/docs/qa/test-results/20260329-133352-phase7-shell-completion-smoke.md`
- PyInstaller build:
  - `autocode/docs/qa/test-results/20260329-131744-phase7-pyinstaller-build.md`
- Packaged setup smoke:
  - `autocode/docs/qa/test-results/20260329-132046-phase7-pyinstaller-setup-smoke.md`

## Phase 7 Completion Summary

**Phase 7 is COMPLETE as of 2026-03-30.**

- All sprints (7A0, 7A, 7B, 7C, 7D, 7E) done
- All 23 benchmark lanes green: 110/110 (100%)
- Code review: APPROVE (~1,500 lines across 3 submodules, Entry 904)
- Final comms entry: Entry 911

## Phase 8 Status

**Phase 8 substrate and live frontend switch-over are landed. Current work is the post-Phase-8 frontier.**

- 8A0-8F2 substrate modules/tests are real
- `create_orchestrator()` exists in `agent/factory.py`
- inline/backend/TUI now use `create_orchestrator()`
- targeted Phase 8 verification cited in Entry 915: `98 passed`
- broader repo `ruff` / `mypy` debt remains deferred and is not a current blocker

## Remaining Work (Post-Phase 8)

- [ ] Validate the new frontier work on genuinely large repos
- [ ] Research-only comprehension agent / mode
- [ ] Harbor / Terminal-Bench score-improvement pass
  - replace the stale placeholder Harbor task ids in `benchmarks/e2e/external/b30-terminal-bench-subset.json`
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
- [ ] External harness adapters (Claude Code / Codex / OpenCode)
- [ ] Full benchmark regression after frontend switch-over
- [ ] Ruff/mypy broader repo debt cleanup
- [ ] L3 constrained generation (llama-cpp-python with native grammar)
