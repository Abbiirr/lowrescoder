# Execution Checklist

Last updated: 2026-04-15 (all 1f Tasks A-E complete; PTY 0 bugs; focused gates green; commit-scope cleanup still required)
Owner: Codex
Purpose: live status checklist for source-of-truth work, active next-frontier research-to-implementation items, and any benchmark/harness follow-up. Re-check this file every 10 minutes during active work.

Detailed implementation map:
- `PLAN.md`
- For every open item below, find the matching numbered section in `PLAN.md` before implementing.

Execution order:
1. Section 1f Unified TUI Consolidation (replaces "Claude Code primary TUI parity")
2. Section 1 large-repo validation / retrieval contract
3. Section 2 external-harness event normalization + deeper adapters
4. Section 3 Terminal-Bench score improvement
5. Section 5 documentation discipline

## Active Frontier Work (Research-Backed)

Research note:
- `docs/research/large-codebase-comprehension-and-external-harness-orchestration.md`
- `docs/research/external-harness-adapter-command-matrix.md`
- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `docs/research/deep-research-report.md`

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
- `docs/research/harness-improvement-proposal-v2-2026-04-08.md`
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

Research: `docs/research/harness_starter_prompt_v2.md`

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

### 1f. Unified TUI Consolidation

**Architecture direction (2026-04-13):** One TUI remains the target end state. Go BubbleTea (`autocode-tui`) is the default interactive frontend today. Python inline still exists as an explicit `--inline` fallback in `cli.py`, so removal is not complete yet. Python backend remains the subprocess daemon.

**Research sources used:**
- `research-components/pi-mono` — differential rendering, steering queues, JSONL branching, log/context split
- `research-components/claude-code` — Ink renderer, inline mode, status bar, Ctrl+K palette
- `research-components/aider` — sliding window streaming, token-aware summarization, multiline input
- `research-components/opencode` — frecency history, timeline fork, background theme detection
- `research-components/goose` — task dashboard emojis, thinking randomization, `/plan` mode
- `research-components/gastown` — charmbracelet stack, agent-mode awareness, adaptive colors
- BubbleTea v2 — `tea.EnableMode2026()` for synchronized output (Mode 2026), native support

**Already landed (keep, do not redo):**
- [x] `stagePalette` + Ctrl+K palette (`cmd/autocode-tui/update.go`, `view.go`)
- [x] 187 rotating spinner verbs (`spinnerverbs.go`)
- [x] `❯` prompt, branded header, braille thinking spinner
- [x] footer-first status bar
- [x] `/undo`, `/diff`, `/cost`, `/export` commands (`tui/commands.py`)
- [x] `todo_write`, `todo_read`, `glob_files`, `grep_content` tools
- [x] Go palette entries for all new commands (`update.go`)
- [x] `todo_write`/`todo_read` in CORE_TOOL_NAMES
- [x] Always-on RulesLoader via `load_project_memory_content()` in `agent/factory.py`

**Phase 1 — Fix Critical Bugs: code-fixed, PTY closure done**
- [x] C3: Go TUI PTY startup — `startupTimeoutMsg` 15s fallback added; `stageInit` now shows spinner and unblocks after timeout (`messages.go`, `model.go`, `update.go`, `view.go`)
- [x] C1: Model picker after every chat — regression tests added in `model_picker_test.go`; no unsolicited `requestModelListCmd` trigger found; tests guard against future regressions
- [x] C2: “(queued N pending)” text leak — root cause was CLAUDE.md context pollution; `_RULES_MAX_CHARS = 3000` cap added in `agent/factory.py`
- [ ] H4/M3: Python inline session recovery after gateway timeout — reset `_current_agent` on cancellation in `handle_chat` (deferred; inline REPL being removed)
- [x] Store a fresh PTY artifact for the current tree
  - startup, normal chat, `/model`, Ctrl+K, and warning classification covered in:
    - `autocode/docs/qa/test-results/20260415-080003-tui-backend-parity-pty-smoke-deterministic-v3-20260415.md`
    - `autocode/docs/qa/test-results/20260415-150741-pty-phase1-fixes.md`

**Phase 2 — Consolidation (one TUI): default routing done, contract not closed**
- [x] Wire `autocode chat` → launches `autocode-tui` binary — `_find_go_tui_binary()` in `cli.py` already does this; binary at `autocode/build/autocode-tui`; `--inline` flag is explicit opt-in fallback
- [x] Decide the inline fallback contract in `autocode/src/autocode/cli.py`
  - DECIDED: `--inline` is kept as an explicit documented fallback
  - docs updated in `current_directives.md` to accurately describe the contract
  - help text in `cli.py` updated to say "explicit fallback"
- [ ] Rename `autocode-tui` binary to be the primary `autocode` interactive entrypoint
- [ ] Ensure `autocode serve` remains the standalone backend daemon
- [ ] Update install scripts and `autocode/cmd/` accordingly
- [ ] Run full test suite; update all tests that reference inline TUI

**Phase 3 — Mode 2026 + Differential Rendering (Go side):**
- [x] BubbleTea v2 migration (v1.3.4 → v2.0.2, charm.land vanity imports, tea.KeyPressMsg, tea.View struct)
- [x] Mode 2026 enabled by default in BubbleTea v2 (no manual ANSI sequences needed)
- [x] Sliding window for stream: stable completed lines → scrollback via tea.Println, last N lines → live panel
- [x] ~~Implement differential renderer: cache lastRenderedLines~~ CORRECTED: BubbleTea v2 handles terminal-level diffing natively via Mode 2026; dead scaffolding (`lastRenderedLines`, `renderGeneration`) removed
- [x] `--inline` flag wired: default = alt-screen; `--inline` opts out (no `tea.WithAltScreen()`), preserving scrollback — NEEDS_WORK → FIXED
- [x] Verify: focused `go test ./...` green

**Phase 4 — Pi-mono Features (Go side complete, backend parity landed):**
- [x] Steering queue: `Ctrl+C` during streaming → steer input mode → `steer` RPC to backend; Esc cancels; second Ctrl+C force-quits
- [x] Follow-up queue: `/followup <msg>` queues a message — CORRECTED: was routing via steer RPC (wrong); fixed to drain via `followupDrainMsg` → `sendChat` path
- [x] JSONL session branching: `/fork` command creates branch, `session.fork` RPC to backend; `ForkSessionParams`/`ForkSessionResult` protocol types
- [ ] log.jsonl + context.jsonl split: Python backend change (deferred)
- [x] Backend RPC handlers in `autocode/src/autocode/backend/server.py`
  - `steer` request handling added — cancels active run and injects steer message
  - `session.fork` request handling added — creates forked session with copied messages, does not switch
  - 29 new tests in `test_backend_server.py`

**Phase 5 — Best-of-All Features (Go side):**
- [x] Multiline input: `Alt+Enter` / `Ctrl+J` inserts newline, `Enter` submits — already in composer via `textarea.KeyMap`
- [x] External editor: `Ctrl+E` opens `$EDITOR` with current input buffer; `editorDoneMsg` loads result back into composer
- [x] Frecency-based prompt history: `historyEntry` type with `frecencyScore()`, `sortByFrecency()`, `historyAddFrecency()`; `loadFrecencyHistory()`/`saveFrecencyHistory()` for JSONL persistence
- [x] Task dashboard: `renderTaskDashboard()` shows pending/running/done/failed counts (Goose pattern)
- [x] `/plan` mode: `/plan` command toggles `planMode`; `planModeStyle` renders `[PLAN MODE]` indicator in view
- [x] Background theme detection: `detectThemeCmd()` reads `COLORFGBG` env var; `bgColorMsg` sets `themeDetected`

**Phase 6 — Status Bar Enhancements (Go side complete, backend producer landed):**
- [x] Live cost display: `totalCost` updated by `backendCostMsg`; displayed in status bar — CORRECTED: `on_cost_update` notification routing added to `dispatchNotification`; was missing, now wired
- [x] Live token count: `totalTokensIn`+`totalTokensOut` accumulated in `handleDone`; displayed in status bar
- [x] Provider/model display: always visible via `backendStatusMsg`
- [x] Session ID display: shown in status bar
- [x] Background task indicator: `backgroundTasks` count + "⏳ N bg" in status bar
- [x] Python backend `on_cost_update` producer
  - Go-side notification parsing is wired
  - backend now emits `on_cost_update` after each chat turn (L4 and L2 paths)
  - documented as per-turn snapshot, not live-streaming cost

**Stderr classification fix (from live-use bug, Entry 1105):**
- [x] `drainStderr` now classifies log lines by severity: WARNING/WARN → dim yellow, DEBUG/INFO → suppress, ERROR/CRITICAL/unknown → red error banner

**Immediate next slice (start here):**
- [x] Task A: backend `steer` RPC in `autocode/src/autocode/backend/server.py`
  - testing strategy: targeted Python tests for dispatch, happy path, and no-active-run failure
  - exit gate: backend no longer rejects `steer`; no hang/traceback; Go tests still green
- [x] Task B: backend `session.fork` RPC in `autocode/src/autocode/backend/server.py`
  - testing strategy: targeted Python tests for new session id, session/log setup, and documented switch behavior
  - exit gate: returns a usable `new_session_id`; docs/comms match actual behavior
- [x] Task C: backend `on_cost_update` producer
  - testing strategy: targeted Python notification tests, plus focused Go regression run
  - exit gate: emit real `on_cost_update` payloads; documented as per-turn only
- [x] Task D: CLI contract cleanup in `autocode/src/autocode/cli.py`
  - DECIDED: `--inline` kept as explicit documented fallback
  - testing strategy: targeted CLI tests plus a minimal smoke on the chosen path
  - exit gate: code, help text, and docs all agree on whether `--inline` is supported
- [x] Task E: PTY validation artifact refresh
  - artifact: `autocode/docs/qa/test-results/20260415-150741-pty-phase1-fixes.md` (10/10 checks, 0 bugs — 2026-04-15)
  - focused smoke companion: `autocode/docs/qa/test-results/20260415-080003-tui-backend-parity-pty-smoke-deterministic-v3-20260415.md`
  - exit gate met: stored artifact shows no unsolicited picker, queue leak, panic, traceback, or fatal warning rendering

**Completion Gates (Section 1f closeout):**
- `cd autocode/cmd/autocode-tui && go test -count=1 ./...` green
- targeted backend tests for new JSON-RPC handlers and cost-update emission green
- stored PTY artifact for the live Go TUI path shows:
  - startup reaches a usable prompt or timeout fallback
  - normal chat does not open unsolicited model/provider pickers
  - queue/debug text does not leak into the visible stream
  - backend warnings do not render as fatal red error banners
- docs and CLI contract agree on whether `--inline` remains supported
- `uv run pytest autocode/tests/unit/ -v` green (≥1778 pass, 0 fail)
- Manual smoke: PTY artifact from `pty_tui_bugfind.py` with no model-picker-after-chat, no queue leak
- `autocode chat` launches Go TUI (not Python inline REPL)

**Phase 7 — Feature Completeness Backlog (unlock after Section 1f closeout):**

Feature audit completed 2026-04-13: 35 DONE (51%), 8 PARTIAL (12%), 26 MISSING (38%) out of 69 features surveyed across research-components. Full detail in `PLAN.md §1f.8`. Implement in priority order:

*Tier 1 — Quick Wins (1-2h each):*
- [ ] QW1: Double-press Ctrl+C quit guard — show "Press Ctrl+C again to quit" hint at `stageInput` on first press; quit only on second press within 3s window
- [ ] QW2: Turn duration timer — track turn-start time, show elapsed in status bar while streaming; final duration shown after `on_done`
- [ ] QW3: Pager for long outputs — `/help`, `/config`, `/memory` open `stagePager` (j/k scroll, q/Esc exit) instead of dumping to stream area

*Tier 2 — Medium Effort (half-day each):*
- [ ] ME1: Collapsible tool output — tool rows with output > 8 lines show `[+N more]`; Tab/Enter expands
- [ ] ME2: Tool timeline summary — after `on_done`, emit a one-line summary "bash → ✓ | read_file → ✓ (3 tools, 2.1s)" via `tea.Println`
- [ ] ME3: Colored diff display — for `edit_file` tool results containing a unified diff, render `+` lines green and `-` lines red/dim
- [ ] ME4: File path tab completion — extend `completion.go` to complete file paths after `@` or in `/shell <partial>`
- [ ] ME5: Live markdown rendering in main stream — apply `glamour.Render()` to `streamBuf` content at tick time (line-by-line to handle partial code blocks)
- [ ] ME6: External editor ($EDITOR) wiring — `Ctrl+E` at `stageInput`; `editorDoneMsg`/`openEditorCmd()` already exist in `messages.go` and `update.go`; verify they are actually wired

*Tier 3 — Larger Changes (multi-session):*
- [ ] L1: `/export` command rendering — write scrollback + tool calls to `~/.autocode/exports/<session>-<ts>.md`; show confirmation in status bar
- [ ] L2: Session fork/branch TUI — after 1f.7 Task B lands, show new session ID and "branch `<id>`" status bar indicator on successful fork
- [ ] L3: Help overlay — `?` at non-streaming stage shows scrollable keybinding overlay; close with Esc/q
- [ ] L4: Dark/light theme variants — use `themeDetected` field to switch between two lipgloss palettes; env var `AUTOCODE_THEME=light` as initial toggle
- [ ] L5: Syntax highlighting for code blocks — `alecthomas/chroma` for triple-backtick blocks; opt-in via `AUTOCODE_SYNTAX=1`

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
