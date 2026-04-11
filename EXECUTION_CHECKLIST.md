# Execution Checklist

Last updated: 2026-04-11 (deep-research + codebase audit integrated; TUI parity queue now reflects real gateway auth, router parity, prompt/tool-surface contract, and live Go validation findings)
Owner: Codex
Purpose: live status checklist for source-of-truth work, active next-frontier research-to-implementation items, and any benchmark/harness follow-up. Re-check this file every 10 minutes during active work.

Detailed implementation map:
- `PLAN.md`
- For every open item below, find the matching numbered section in `PLAN.md` before implementing.

Execution order:
1. Section 1f Claude Code primary TUI parity
2. Section 1 large-repo validation / retrieval contract
3. Section 2 external-harness event normalization + deeper adapters
4. Section 3 Terminal-Bench score improvement
5. Section 5 documentation discipline

## Active Frontier Work (Research-Backed)

Research note:
- `docs/research/large-codebase-comprehension-and-external-harness-orchestration.md`
- `docs/research/external-harness-adapter-command-matrix.md`
- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `deep-research-report.md`

Current public competitive context used for these items:
- Terminal-Bench 2.0 public snapshot on 2026-04-01: Forge Code `78.4%`, Droid `77.3%`, Simple Codex `75.1%`
- The strongest public patterns are:
  - retrieval/indexing instead of whole-repo context stuffing
  - research/planning/execution context separation
  - structured compaction and output hygiene
  - native CLI / headless harness execution rather than bypassing the harness
  - context-plane separation, memory write policy, and artifact-first resumability
  - typed first-class operations should replace bash-style explanations wherever the product already has a typed surface

### 0. Harness Architecture Refinement From Proposal v2

Status:
- foundation landed
- not the active implementation queue anymore
- keep the `.harness/` defer decision in place unless the user explicitly redirects

Research:
- `harness-improvement-proposal-v2-2026-04-08.md`
- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`

- [x] Review proposal v2 and classify what is adopt-now vs defer vs reject
  - adoption memo written in `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
  - core conclusion: use the proposal selectively, do not treat it as a second parallel harness architecture
- [x] Formalize the four-plane context model in AutoCode-native terms
  - durable instructions
  - durable project memory
  - live session state
  - ephemeral scratch
  - design doc: `docs/design/context-plane-model.md`
  - code: `ContextPlane`, `PlaneBudget`, `PlaneState`, `get_plane_for_content()` in `agent/context.py`
  - 15 tests passing in `test_context_planes.py`
- [x] Define durable-memory write and preservation rules
  - what becomes durable memory
  - what stays session-local
  - what survives compaction by rule
  - code: `DURABLE_WRITE_TRIGGERS`, `TRANSIENT_EXCLUSIONS`, `should_promote_to_durable()` in `session/consolidation.py`
  - 15 tests passing in `test_durable_memory.py`
- [x] Normalize canonical runtime state before deeper adapter work
  - session/task/approval/worktree/working-set/checkpoint/subagent/pending-approval state should stop being spread ad hoc across loop/frontend/orchestrator
  - code: `RuntimeState` in `agent/context.py` with all 12 fields including `working_set`
  - wired into `Orchestrator` as `runtime_state` property with session_id sync
  - 10 tests passing in `test_runtime_state.py`
- [x] Expand tool metadata to support the cleaner control plane
  - concurrency safety
  - interruptability
  - output budget hints
  - direct-call vs orchestrated/programmatic-call eligibility
  - code: 5 new fields on `ToolDefinition` in `agent/tools.py`
  - 10 tests passing in `test_tool_metadata.py`
- [x] Strengthen artifact-first resumability
  - resume packet / handoff packet / compact state should be first-class outputs, not only incidental logs
  - code: `HandoffPacket`, `CompactSummary`, `CheckpointManifest`, `ResumePacket` in `agent/artifact_collector.py`
  - 7 tests passing in `test_artifact_resume.py`
- [ ] Keep `.harness/`-style file-tree adoption deferred unless explicitly chosen later
  - current recommendation is **not now**
  - this is a policy/decision guardrail, not a code implementation blocker

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

- [x] Decide LanceDB dependency contract: profile-gated (optional, graceful degradation)
  - `RetrievalTier` enum: BM25_ONLY / HYBRID_IN_MEMORY / HYBRID_PERSISTENT
  - `check_retrieval_tier()` auto-detects available deps
  - `RETRIEVAL_TIER_DESCRIPTIONS` provides install guidance per tier
  - 8 tests in `test_retrieval_contract.py`
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

- [x] Make `autocode` runnable as a simple device command after install
  - DONE: `uv tool install --editable ./autocode` — installs to `~/.local/bin/autocode`
  - `autocode --help`, `autocode version`, `autocode doctor`, `autocode chat --help` all work from any shell
  - editable install: code changes reflected immediately without reinstall
- [x] Fix broken `autocode` CLI experience
  - plain command contract is live
  - `--version` works alongside the `version` subcommand
  - install smoke artifact stored: `autocode/docs/qa/test-results/20260403-173036-install-smoke.md`
  - note: `autocode doctor` still reports optional dependency gaps on machines that do not have everything installed; that is a readiness outcome, not a missing-command failure

- [x] Add Claude-style `/loop` command
  - recurring prompt/slash execution landed
  - loop smoke artifact stored: `autocode/docs/qa/test-results/20260403-173500-loop-smoke.md`
  - command contract exists:
    - `/loop <interval> <prompt-or-slash-command>`
    - `/loop list`
    - `/loop cancel <id>`

- [x] Post-implementation Codex review gate for installability + `/loop`
  - narrow review completed in the active comms cycle
  - remaining work is no longer “implement installability and /loop”, but keeping the status docs truthful

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

- [x] Keep AutoCode as the control plane and external tools as worker runtimes
  - architectural decision made
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
- [x] Normalize every harness into AutoCode's event model
  - `harness_event_to_orchestrator_dict()` bridges HarnessEvent → OrchestratorEvent
  - all 12 HarnessEventTypes mapped to internal EventType
  - session/run context preserved, source metadata tagged
  - `stream_as_orchestrator_events()` chains adapters → bridge → orchestrator pipeline
  - 14 tests in `test_event_bridge.py`
- [x] Adapter process-state bug fixed
  - all 4 adapters now store `session.metadata["_process"] = proc` in `stream_events()`
  - `snapshot_state()` can now correctly report "active" vs "ended"
- [x] Strategy overlays wired into Harbor adapter execution path
  - `classify_task()` + `get_overlay()` called at task start
  - family-specific prompt guidance injected into task prompt
  - overlay-based doom-loop thresholds replace hardcoded values
  - `StagnationDetector` and `verifier_aware_retry_guidance()` active in tool loop
  - 4 new tests in `test_harbor_adapter.py`
- [x] RetrievalTier wired into `autocode doctor`
  - replaces simple `check_lancedb` with tier-aware `check_retrieval_tier`
  - reports BM25_ONLY / HYBRID_IN_MEMORY / HYBRID_PERSISTENT status
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

### 1e. Harness Phase 1 — Skills, Verification, Artifacts, Enforcement

Research: `harness_starter_prompt_v2.md`

- [x] Three core skills (plan-first, build-verified, review-and-close)
  - `.claude/skills/plan-first/SKILL.md` — read-only planning, no edits
  - `.claude/skills/build-verified/SKILL.md` — edits + mandatory verification
  - `.claude/skills/review-and-close/SKILL.md` — diff review, risk summary, go/no-go
- [x] Verification gate + verify.json schema
  - `autocode/src/autocode/agent/verification.py` — VerifyResult, VerificationEvidence, hard gate logic
  - `autocode/tools/verify/verify.sh` — portable verification wrapper (lint/test/typecheck)
  - verify.json schema with checks, exit codes, pass/fail, duration
  - 19 unit tests passing
- [x] Artifact/evidence collection system
  - `autocode/src/autocode/agent/artifact_collector.py` — ArtifactCollector class
  - commands.log: shell commands with timestamps and exit codes
  - diff.patch: unified diff of all changes via git
  - verify.json: structured verification results
  - risk.md: auto-generated risk summary with GO/NO-GO verdict
  - 8 unit tests passing
- [x] Claude Code hooks (optional integration layer)
  - `.claude/hooks/stop_gate.sh` — blocks task completion without verify.json
  - `.claude/hooks/pre_tool_guard.sh` — blocks destructive commands and sensitive file writes
Per Codex Entry 993: these must be scoped behind explicit profiles/modes/config, NOT on the default chat path.
- [ ] ArtifactCollector wired into live middleware (low-risk, high-signal)
  - after_tool middleware logs commands to collector
  - session end saves all artifacts
- [ ] Auto-checkpoint before risky tool calls (low-risk)
  - middleware on before_tool that auto-checkpoints when tool.mutates_fs
  - debouncing: skip if nothing changed since last checkpoint
- [ ] Hard verification gate — behind explicit BUILD mode or harness mode only
  - integrate VerificationEvidence into middleware.py
  - NOT on default chat path — only when BUILD mode or benchmark harness is active
- [ ] Role separation: BUILD and REVIEW modes
  - extend AgentMode enum with BUILD, REVIEW
  - BUILD requires verification before completion
  - REVIEW blocks all edits
  - /build and /review slash commands

### 1f. Claude Code Primary TUI Parity

Existing scaffolding that should be reused, not re-counted as completion:
- [x] parity spec exists at `docs/design/claude-code-visual-parity.md`
- [x] `claude_like` profile exists in config / inline / Textual
- [x] some inline parity-oriented snapshot tests already exist in `test_inline_renderer.py`
- [x] first Go TUI parity slice is already landed in the active worktree
  - `❯` prompt
  - compact branded header
  - braille thinking spinner
  - simplified footer-first status bar
  - initial compact tool-row styling
  - matching first-pass test updates in:
    - `model_test.go`
    - `view_test.go`
    - `statusbar_test.go`
    - `update_test.go`
  - do not restart this work from scratch

Still open:
- [x] Refresh the parity contract from current Claude Code behavior
  - fold in the latest local changelog signals:
    - footer-first status hierarchy
    - fixed-width braille/shimmer spinner
    - compact tool-call grouping/collapse
    - narrow-terminal footer stability
    - reduced layout jitter during streaming
- [x] Make the primary full-screen TUI the first real parity target
  - treat the TUI as the main execution surface for this workstream
  - do not drift into a Pi-style multi-pane orchestrator dashboard
- [ ] Rebuild the core layout contract
  - single-column chat-first hierarchy
  - minimal branded header
  - bottom footer/status line as the main live-status surface
  - prompt kept visually minimal and stable
  - current remaining gaps:
    - task-panel demotion when it creates dashboard noise
    - completion/scrollback consistency with the live view
- [ ] Align the highest-salience interaction visuals
  - thinking spinner/text
  - compact tool rows
  - success/failure markers
  - approval prompt shape
  - prompt/footer hierarchy
  - current remaining gaps:
    - compact approval prompt parity
    - compact tool/result summaries on turn completion
- [ ] Harden narrow-terminal and render-stability behavior
  - 80-column layout must remain readable
  - long model names, file paths, and tool args must truncate cleanly
  - spinner/tool updates must not cause visible layout jitter
  - Unicode/wide-char rendering must stay correct
- [ ] Add focused render/snapshot/string-contract coverage
  - welcome
  - idle prompt
  - streaming
  - thinking
  - compact tool success
  - compact tool failure
  - approval prompt
  - narrow-terminal footer
- [ ] Pass non-regression quality gates on the TUI suite
  - `view_test.go`
  - `statusbar_test.go`
  - `update_test.go`
  - `approval_test.go`
  - `commands_test.go`
  - `e2e_test.go`
- [ ] Record manual smoke artifacts before calling parity complete
  - 80-column terminal
  - 120+ column terminal
  - visible thinking + streaming in same turn
  - long-path / long-command example
  - every manual run must start from `docs/qa/manual-ai-bug-test-report-template.md` and end with a filled PASS/FAIL artifact
- [ ] Run the manual AI bug-testing playbook during each parity pass
  - use `docs/qa/manual-ai-bug-testing-playbook.md`
  - explicitly cover:
    - bare `/` command discovery
    - visible slash menu should show the full relevant command set
    - Up/Down should move the slash-menu selection
    - Enter should accept the highlighted slash command
    - `/help` vs completion parity
    - `/model` against the localhost gateway
    - `/model` should offer an on-screen picker, not just a dumped text list
    - `/provider` visibility and switching
    - provider/model visibility in the live status surface
    - repo-local prompts like `check the files in this repo`
    - live resize behavior while idle and while streaming
    - `autocode ask` when slash/provider/tool-surface behavior changes
- [ ] Fix prompt/tool-surface mismatches before calling parity complete
  - current known bug class:
    - system prompt still teaches `list_files`
    - live core schema may expose only a narrower tool subset plus `tool_search`
    - this can trigger bogus self-diagnosis like “tool list is empty” or “no list_files tool”
- [ ] Fix gateway auth/header parity for model listing and health checks
  - current known bug class:
    - unauthenticated `http://localhost:4000/v1/models` returns `401`
    - authenticated with `Authorization: Bearer $LITELLM_API_KEY` returns the real alias catalog
    - shared helper already exists in `autocode/src/autocode/gateway_auth.py`
    - AutoCode should not mislabel that as generic gateway failure
- [ ] Add a router-parity contract between the Go TUI slash surface and the Python router
  - bare `/` discovery should not rely only on visual snapshots
  - `knownCommands` in `cmd/autocode-tui/commands.go` must stay aligned with `create_default_router()` in `src/autocode/tui/commands.py`
- [ ] Treat provider/model state as typed first-class UI state
  - show current provider/model clearly
  - keep `/provider` as the provider control surface
  - avoid shell-style or generic fallback explanations when the typed route exists
- [x] Run live Go validation on the real module path
  - `go version` is available on this machine
  - `cd autocode/cmd/autocode-tui && go test ./...` now passes in the current tree
  - the old `spinner.MiniDot` fix is verified in live validation
- [ ] Keep rollout gated behind `claude_like` until the completion gates pass
  - only then decide whether to promote `claude_like` to the default profile

## Remaining Work (Post-Phase 8)

- [ ] Validate the new frontier work on genuinely large repos
- [x] Research-only comprehension agent / mode
- [ ] Harbor / Terminal-Bench score-improvement pass
  - replace the stale placeholder Harbor task ids in `benchmarks/e2e/external/b30-terminal-bench-subset.json`
  - baseline Harbor recovery is no longer the main blocker; the corrected valid-task subset finished `0/2` with `0` infra errors
  - next builder target is a narrow score-improvement sprint on the same two validated Harbor tasks:
    - `break-filter-js-from-html`
    - `build-cython-ext`
   - implement in this order:
     1. [x] task-family strategy overlays in Harbor mode
        - `TaskFamily` enum: HTML_OUTPUT, PYTHON_BUILD, GENERAL
        - `classify_task()` + `StrategyOverlay` with per-family params
        - `agent/strategy_overlays.py` — 20 tests in `test_strategy_overlays.py`
     2. [x] verifier-aware retry guidance
        - `verifier_aware_retry_guidance()` requires error signal extraction before retry
        - max retry enforcement
     3. [x] stronger stagnation detection for repeated build/install/test cycles with no progress
        - `StagnationDetector` catches N identical results in a row with actionable guidance
      4. [x] Harbor tool-surface / prompt tuning for file-edit vs shell-heavy task families
         - strategy overlays wired into `harbor_adapter.py` execution loop
         - task-family guidance injected per-overlay, stagnation + verifier-aware retry active
      5. [ ] rerun the same corrected `2`-task subset before broadening to more B30 tasks
  - only after the same subset improves should we expand B30 or attribute the remaining gap primarily to model choice
- [ ] External harness adapters (Claude Code / Codex / OpenCode)
- [ ] Full benchmark regression after frontend switch-over
- [ ] Ruff/mypy broader repo debt cleanup
- [ ] L3 constrained generation (llama-cpp-python with native grammar)

## 10-Minute Review Loop

Every 10 minutes, do this in order:

1. Check `AGENTS_CONVERSATION.MD` for newly directed work.
2. Re-open `EXECUTION_CHECKLIST.md` and confirm the active item is still the top backlog item.
3. Use `PLAN.md` to constrain the current implementation slice before editing.
4. Check for fresh artifacts in `docs/qa/test-results/` and `autocode/docs/qa/test-results/`.
5. Update these docs immediately if reality changed:
   - `current_directives.md`
   - `EXECUTION_CHECKLIST.md`
   - `PLAN.md`
   - `docs/session-onramp.md`
6. Keep historical green evidence separate from exploratory frontier runs in all notes and comms.
