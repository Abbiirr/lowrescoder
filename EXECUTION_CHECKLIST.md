# Execution Checklist

Last updated: 2026-04-17 (Stable TUI v1 Slices 0-8 complete + late-session fidelity fixes. Slice 8 = VHS-shape visual snapshot pipeline (pyte + Pillow). Milestone A CLOSED, B CLOSED, C ~85%, D ~65% (provenance in), E ~70%, F ~75% (profiles in). Late-session deltas (Entry 1124): image #9 duplicate-queue-preview removal in view.go/composer.go, prompts.py conversational-guardrail for tool-call-on-hello, pty_tui_bugfind binary-path corrected to build/autocode-tui + B5→B6 Esc cleanup, pi coding agent wired at localhost:4000 via ~/.pi/agent/models.json for side-by-side TUI comparison. Next slice: screenshot-comparison pipeline (multi-TUI spin-up, capture, analyze). See close-out Entries 1121 + 1122 + 1123 + 1124 in AGENTS_CONVERSATION.MD. Plan: /home/bs01763/.claude/plans/virtual-booping-hoare.md.)
Owner: Codex
Purpose: live status checklist for source-of-truth work, active next-frontier research-to-implementation items, and any benchmark/harness follow-up. Re-check this file every 10 minutes during active work.

Detailed implementation map:
- `PLAN.md`
- For every open item below, find the matching numbered section in `PLAN.md` before implementing.
- `DEFERRED_PENDING_TODO.md` — consolidated store of everything NOT in the current active slice. Do not lose these items; walk that file after the active slice closes.

Execution order (2026-04-17 late-session, TUI Testing Strategy priority):
1. **Section 1g TUI Testing Strategy (ACTIVE SLICE)** — research + design the multi-TUI capture/compare pipeline (autocode, pi, claude-code, opencode, codex, aider, goose). User directive to prioritize this before picking up anything else. See `PLAN.md` §1g and `DEFERRED_PENDING_TODO.md`.
2. Section 1f Milestone C/D/E/F residuals (deferred — see DEFERRED_PENDING_TODO.md §3)
3. Section 1 large-repo validation / retrieval contract
4. Section 2 external-harness event normalization + deeper adapters
5. Section 3 Terminal-Bench score improvement
6. Section 5 documentation discipline

## TUI Testing Strategy (Active Slice)

> Status: plan in progress as of 2026-04-17 late-session. No code yet.
> Source of truth for the plan detail: `PLAN.md` §1g.
>
> Goal: a repeatable pipeline that spins up each candidate TUI (autocode +
> pi coding agent + claude-code + opencode + codex CLI + aider + goose)
> under identical prompts on the shared LiteLLM gateway, captures their
> visual state, stores snapshots alongside reference baselines, and
> analyzes/compares them so fidelity regressions in autocode are caught
> quickly and side-by-side feedback against reference tools is concrete.
>
> Dependencies already satisfied:
> - Pi coding agent wired at `http://localhost:4000/v1` via
>   `~/.pi/agent/models.json` (8 aliases, LITELLM_MASTER_KEY env-persistent)
> - VHS-shape pyte + Pillow substrate already exists for autocode at
>   `autocode/tests/vhs/` (renderer, differ, scenarios, run_visual_suite.py)
> - Research-components mirror of claude-code / pi / opencode / codex /
>   aider / goose / etc. under `research-components/`
>
> Open design questions (to close in `PLAN.md` §1g):
> - Capture strategy per TUI: pyte-based ANSI parse vs real PTY + tmux
>   capture-pane vs t-rec vs asciinema-agg vs VHS (charmbracelet)
> - Storage layout: one folder per TUI per scenario, or scenario-first
> - Diff layer: byte diff, ANSI-text diff, per-cell semantic diff, or
>   image diff
> - Analysis layer: visual inspection by human, LLM vision comparison,
>   or rule-based (e.g. "composer present on bottom two rows")
> - How to keep each TUI's environment isolated (auth state, history,
>   DB files, config) so one capture doesn't poison the next
> - How to drive identical prompts across TUIs given wildly different
>   keybindings and startup flows
>
> Exit gates:
> - [ ] plan section in `PLAN.md` §1g closed with concrete design choices
> - [ ] minimal working prototype captures autocode + at least one
>   reference TUI for one scenario
> - [ ] stored snapshots under `autocode/docs/qa/tui-comparison/` or an
>   equivalent path
> - [ ] documented analysis step that produces a compare artifact

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

### 1f. Stable TUI Program

**Purpose:** lock the TUI roadmap around a research-backed stable-v1 program, not a vague “closeout” phase.

**Source of truth:** `PLAN.md` Section `1f` plus `deep-research-report.md`

**Locked product decisions:**
- [x] Go BubbleTea is the default interactive frontend.
- [x] Python `--inline` remains an explicit fallback, not the default.
- [x] Stable v1 is compatibility-first and verification-first, not feature-maximal.
- [x] Migration-critical contracts are `CLAUDE.md`, skills, hooks, sessions, permission gates, and queue semantics.
- [x] Verification is a ship gate, not a polish item.

**Current verified foundation (do not redo, preserve while moving the program forward):**
- [x] Go TUI default routing and explicit `--inline` fallback are in place.
- [x] BubbleTea v2 / Mode 2026 migration is complete.
- [x] Steering queue, follow-up queue, session fork RPC, multiline input, editor launch, frecency history, task dashboard, `/plan`, and status-bar upgrades are landed.
- [x] Backend parity for `steer`, `session.fork`, and `on_cost_update` is landed.
- [x] Focused PTY evidence is green (refreshed 2026-04-17):
  - `autocode/docs/qa/test-results/20260415-080003-tui-backend-parity-pty-smoke-deterministic-v3-20260415.md`
  - `autocode/docs/qa/test-results/20260415-150741-pty-phase1-fixes.md`
  - `autocode/docs/qa/test-results/20260417-061442-slice0-pty-phase1.md` (fresh 2026-04-17, 0 bugs, 10/10)
  - `autocode/docs/qa/test-results/20260417-061444-slice0-pty-smoke.md` (fresh 2026-04-17, 0 bugs, 5/5)
  - `autocode/docs/qa/test-results/20260417-053901-milestone-a-go-tests.md` (Go 417 PASS)
  - `autocode/docs/qa/test-results/20260417-061438-slice0-go-tests.md` (Go 417 PASS)
- [x] Focused Go / Python / Ruff artifacts are green for the touched TUI-supporting surfaces.

#### Milestone A — Runtime Stability And Deterministic TUI Loop

**Status (2026-04-17):** Runtime gates green on 2026-04-17. Open gap is the three-picker filter bug (`/model`, `/provider`, `/session` pickers silently drop non-nav keystrokes) which enters this session as Slice 1. Deterministic mock harness landed at `cmd/autocode-tui/milestone_a_test.go` (1109 LOC, 62 tests). PTY gates green per artifacts listed in Current Verified Foundation above.

**Implementation checklist**
- [x] Lock the runtime acceptance matrix for startup, input, palette, picker, streaming, resize, inline mode, and alt-screen mode — `milestone_a_test.go` covers 62 deterministic scenarios; PTY bugfind exercises runtime paths.
- [ ] Harden rapid key-sequence behavior: `Enter`, `Esc`, `Ctrl+C`, palette open/close, slash completion focus retention, picker focus return.
- [ ] Harden rendering behavior under long tool output, mixed stream/tool cards, and resize churn.
- [ ] Lock crash/recovery expectations for interrupted runs and backend death.

**Testing strategy**
- Go unit tests for `model`, `update`, `view`, and keyboard-routing transitions.
- Deterministic mock-backend tests for queue semantics, unsolicited picker prevention, and warning/error routing.
- PTY scenarios for startup, normal chat, `/model`, Ctrl+K, warning classification, inline mode, and alt-screen mode.
- Manual smoke only when PTY cannot prove the behavior.

**Verification criteria**
- No unsolicited pickers.
- No queue/debug text leaks into visible output.
- No broken rendering on resize or large outputs.
- Queue semantics remain correct while streaming or running tools.
- Forced shutdown does not corrupt the active session.

**Exit gates**
- [x] `cd autocode/cmd/autocode-tui && go test -count=1 ./...` green — 453+ PASS at `20260417-071747-slice7-final-go-tests.md`.
- [x] deterministic runtime mock harness green — `milestone_a_test.go` 62 PASS.
- [x] fresh PTY runtime artifact stored under `autocode/docs/qa/test-results/` — `20260417-071752-slice7-final-pty-phase1.md` (0 bugs) + `20260417-071754-slice7-final-pty-smoke.md` (0 bugs) + `20260417-071732-slice7-pty-narrow-final.md` (0 bugs).
- [x] zero known open runtime regressions in the tracked milestone matrix — three-picker filter bug (BUG-1/2/3) CLOSED in Slice 1 with 36 new Go tests; see `20260417-062303-slice1-go-tests.md`.

**Slice 1 (2026-04-17) — Milestone A closeout:** three-picker filterability landed. `model_picker.go` / `provider_picker.go` / `session_picker.go` now accept type-to-filter with case-insensitive substring match; two-stroke Escape (clear filter → exit); Ctrl+C always exits. `runeForFilter()` helper at `cmd/autocode-tui/model_picker.go:217`. `pty_tui_bugfind.py::check()` gained `expect_{model,provider}_picker` flags to suppress false-positive alerts when tests intentionally invoke `/model`. 36 new Go tests; PTY bugfind went from 3 bugs → 0 for Go TUI path (1 MEDIUM Python-inline-only finding remains, unrelated).

#### Milestone B — Compatibility And Migration Contracts

**Status (2026-04-17):** Core migration surface landed via Slices 2–4. Project memory contract, skills discovery with progressive disclosure, and hook lifecycle runtime all in place. Deferred from this session: session/export file-format expectations for full Pi-style migration.

**Implementation checklist**
- [x] Finish `CLAUDE.md` directory walk support, `CLAUDE.local.md`, bounded `@imports`, and approval-gated external imports — `layer2/rules.py` rewritten in Slice 2 with 23 tests at `20260417-062623-slice2-rules-imports.md`; doc at `docs/reference/rules-loader-contract.md`.
- [x] Finish the skills contract: directory compatibility, progressive disclosure, reload behavior, and supported metadata boundary — `agent/skills.py` landed in Slice 3 with 20 tests; doc at `docs/reference/skills-contract.md`.
- [x] Lock hook lifecycle support: `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, `StopFailure` — `agent/hooks.py` + 4 call-sites in `agent/loop.py` landed in Slice 4 with 22 tests; doc at `docs/reference/hooks-contract.md`; sample at `docs/reference/claude-settings.sample.json`.
- [ ] Lock session/export expectations for Claude Code and Pi-style migrations — deferred; `/fork` works today but `/tree` navigation + JSONL export format are post-session work.

**Testing strategy**
- Fixture repos with synthetic `CLAUDE.md`, `CLAUDE.local.md`, imports, skills, and hooks.
- Golden tests for hook event names and payload shapes.
- Skill reload tests that prove an updated skill is observed by the current session.
- Branch/export tests for migration-style session flows.

**Verification criteria**
- Claude-style repo memory and skills work without repo rewrites.
- Hook names and payloads are deterministic and documented.
- Skills are discovered cheaply and loaded on demand.
- Queue, session, and branch behaviors remain migration-friendly.

**Exit gates**
- [x] migration fixture suite green — Slice 2 `test_rules_imports.py` 23 PASS with synthetic CLAUDE.md/CLAUDE.local.md/@imports/AGENTS.md trees.
- [x] hook schema tests green — Slice 4 `test_hooks.py` 22 PASS; settings.json schema + payload shape + matcher + blocking protocol covered.
- [x] skill reload tests green — Slice 3 `test_skills.py::test_reload_if_changed_detects_mtime` PASS.
- [x] docs explicitly list supported migration contracts and unsupported edge cases — `docs/reference/{rules-loader-contract,skills-contract,hooks-contract}.md`.

#### Milestone C — Permissions, Sandbox, And Hook Enforcement

**Implementation checklist**
- [ ] Lock user-visible sandbox modes: read-only, workspace-write, full access.
- [ ] Lock per-tool policy behavior: allow, ask, deny, wildcard/pattern matching.
- [ ] Make rule matches explainable in the UI and logs.
- [ ] Make hooks an enforcement surface, not just a notification surface.
- [ ] Add diff-first guardrails for larger multi-file writes unless explicitly escalated.

**Testing strategy**
- Table-driven policy tests for representative tool calls and shell patterns.
- Negative tests for workspace escape and destructive command attempts.
- Hook pass/fail tests proving blocked tools do not execute.
- Approval-flow tests proving deterministic escalation between trust levels.

**Verification criteria**
- The matched permission rule is deterministic and explainable for every tested tool call.
- Sandbox modes behave exactly as documented.
- Hook enforcement can block or require verification without undefined behavior.
- Large writes and destructive actions do not bypass explicit approval rules.

**Exit gates**
- [ ] policy matrix tests green.
- [ ] sandbox escape regressions green.
- [ ] hook enforcement tests green.
- [ ] docs include user-facing permission rules and agent-facing implementation rules.

#### Milestone D — Sessions, Compaction, Provenance, And Recovery

**Status (2026-04-17):** Partial. Provenance labels landed in Slice 5 (additive, no schema migration). Crash-injection suite, `/tree` UI, and log.jsonl split remain deferred.

**Implementation checklist**
- [x] Keep sessions append-only and replayable — existing `session/store.py` SQLite+WAL.
- [x] Lock branch integrity, export integrity, and parent linkage invariants — existing `/fork` backend parity (landed pre-session).
- [ ] Make manual and automatic compaction explicit in both storage and UI — partial; `/compact` exists, UI surface minimal.
- [x] Preserve provenance through summaries and compaction — Slice 5 added `Provenance` StrEnum + `classify_message_provenance()` + `CompactionResult.provenance` field + `format_messages_for_compaction(include_provenance=True)`; 18 tests at `20260417-071217-slice5-compaction-provenance.md`.
- [x] Decide explicitly whether `log.jsonl` / `context.jsonl` split is in-v1 or deferred post-v1 — **DEFERRED** post-v1; SQLite+WAL already satisfies append-only/replayable requirements.

**Testing strategy**
- Crash-injection tests during write, flush, compact, and shutdown flows.
- Branch/replay/export invariant tests.
- Red-team compaction tests where tool/file output attempts instruction smuggling.
- Long-session simulations with repeated tool output, compact, and recover cycles.

**Verification criteria**
- Session files remain recoverable after interruption.
- Branching never rewrites or corrupts prior history.
- Compaction is explicit and provenance-preserving.
- Retry / compaction circuit-break behavior is observable and documented.

**Exit gates**
- [ ] crash/recovery tests green.
- [ ] branch/export invariants green.
- [ ] compaction provenance tests green.
- [ ] explicit compaction and circuit-break policy documented.

#### Milestone E — Context Intelligence Baseline

**Implementation checklist**
- [ ] Ensure repo-map style context selection is on the interactive path.
- [ ] Keep `@path` and file completion cheap and predictable.
- [ ] Run deterministic diagnostics after edits.
- [ ] Surface diagnostics in the TUI without overwhelming the transcript.
- [ ] Validate bounded context behavior on medium and large repos.

**Testing strategy**
- Retrieval/repo-map regressions on representative repos.
- Completion tests for file and shell contexts.
- Diagnostics-after-edit tests with deterministic fixture repos.
- Measurement runs for latency, context growth, and compaction frequency.

**Verification criteria**
- The first relevant file/symbol is found quickly on larger repos.
- Diagnostics appear after edits without disrupting the main loop.
- Context growth stays bounded over long sessions.
- The TUI does not regress into naive whole-repo stuffing.

**Exit gates**
- [ ] large-repo validation artifact stored.
- [ ] diagnostics-after-edit tests green.
- [ ] retrieval/working-set regressions green.
- [ ] latency and context-growth measurements recorded.

#### Milestone F — Verification Profiles, Release Gate, And Measurement

**Status (2026-04-17):** Profiles landed in Slice 6. Hook wiring is available via Slice 4 bus; end-to-end auto-fire at PostToolUse is deferred to a follow-up integration session. Operational metrics (skill-trigger accuracy, hook-failure rates, retry counters) remain deferred.

**Implementation checklist**
- [x] Publish formatter, lint, typecheck, and targeted-test verification profiles — `agent/verification_profiles.py` with built-in `python`/`go`/`js`/`rust` bundles landed in Slice 6; 19 tests at `20260417-071400-slice6-verification-profiles.md`.
- [x] Wire hooks so verification can run at `PostToolUse`, `Stop`, and `StopFailure` — hook bus in place (Slice 4); profile-as-hook available for users to configure in `.claude/settings.json`; auto-wiring of profile-on-edit deferred to follow-up.
- [ ] Track operational metrics: skill trigger accuracy, hook outcomes, retries, loops, compaction failures — deferred post-session.
- [x] Make transcript/export/diff reviewability explicit — existing `agent/artifact_collector.py` covers baseline; full `/export` polish deferred.
- [ ] Keep a separate-review path available for review-only workflows — `.claude/skills/review-and-close/SKILL.md` exists on disk; skill-runtime invocation landed in Slice 3.

**Testing strategy**
- Deterministic mock-provider harness for tool calling, queue semantics, and hook decisions.
- Verification-profile tests using fixture repos with expected formatter/lint/typecheck/test outcomes.
- Transcript/export tests proving actions remain reviewable.
- Reviewer-mode or second-pass tests where available.

**Verification criteria**
- Verification profiles are reproducible and documented.
- Hook-triggered verification can fail a turn deterministically.
- Skipped checks and retries are visible in artifacts and metrics.
- Independent verification remains easy for humans and agents.

**Exit gates**
- [ ] deterministic mock-harness suite green.
- [ ] verification-profile suite green.
- [ ] transcript/export checks green.
- [ ] release note includes the stable-v1 validation matrix and known limitations.

#### Cross-Cutting Stable-V1 Testing Matrix

Every milestone above must explicitly exercise the required rows below before it can be closed:

- [ ] Go unit tests for TUI state/model/view/update changes.
- [ ] Python unit tests for backend, loader, policy, hook, and contract changes.
- [ ] Deterministic mock-harness coverage for all stateful loop changes.
- [ ] PTY evidence for all interactive TUI changes.
- [ ] Migration fixtures for compatibility work.
- [ ] Security/policy tests for permission work.
- [ ] Crash/replay tests for session and compaction work.
- [ ] Large-repo validation artifacts for context work.

#### Stable-V1 Program Exit Rule

Do **not** declare the TUI “stable v1” until all of the following are true at once:

- [ ] UI stability gates are green.
- [ ] session integrity gates are green.
- [ ] permission and sandbox gates are green.
- [ ] migration contract gates are green.
- [ ] verification-profile and transcript-review gates are green.
- [ ] docs, help text, and stored artifacts all describe the same current reality.

#### Explicit Non-Goals While Section 1f Is Active

- remote-client architecture work
- broad subagent UX work
- orchestration-first features that multiply state complexity
- parity-only features that do not improve stability, compatibility, or verification

#### Next Starting Point

- [ ] Start with **Milestone A**.
- [ ] Enumerate the missing runtime acceptance cases.
- [ ] Convert those gaps into deterministic mock tests and PTY checks before adding new TUI surface area.
- [ ] After Milestone A, proceed strictly in order: B, C, D, E, F.

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
