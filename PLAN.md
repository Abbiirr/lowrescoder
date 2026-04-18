# Plan

Last updated: 2026-04-14
Owner: Codex
Purpose: detailed implementation plan for the active post-Phase-8 frontier. `EXECUTION_CHECKLIST.md` is the live status board; this file is the detailed execution map and ordered backlog. For every open checklist item, find the matching section here before implementing.

## How To Use This File

1. Start from `EXECUTION_CHECKLIST.md`.
2. Find the matching numbered section in this file.
3. Use that section’s:
   - goal
   - constraints
   - implementation steps
   - files
   - verification
4. Update both files together when reality changes.

## Ordered Backlog

Follow this order unless the user explicitly redirects:

1. **Section 1g: TUI Testing Strategy (ACTIVE SLICE as of 2026-04-17 late-session)**
2. Section 1f: Unified TUI Consolidation — residual milestones C/D/E/F (deferred, see `DEFERRED_PENDING_TODO.md` §3)
3. Section 1: Large Codebase Comprehension
4. Section 2: Native External-Harness Orchestration
5. Section 3: Terminal-Bench / Harness Engineering
6. Section 5: Documentation Discipline
7. Section 4: Research Corpus Maintenance
8. Section 0: Harness Architecture Refinement From Proposal v2 as a landed foundation / policy reference

Current practical rule:

- **treat Section 1g (TUI Testing Strategy) as the current active slice until user approves move-on**
- keep deferred items visible in `DEFERRED_PENDING_TODO.md`; do NOT dismiss anything
- treat Section 0 as landed foundation unless a new gap is discovered
- treat Section 1f (Unified TUI) residuals as paused, not cancelled
- do not broaden B30 work while the higher-leverage comprehension/adapter items are still moving

---

## 0. Harness Architecture Refinement From Proposal v2

Status:
- landed as foundation
- not the active execution queue
- use this section as a design reference and guardrail source while implementing Sections 1-3

### Goal

Use `harness-improvement-proposal-v2-2026-04-08.md` as a selective improvement source, not as a second parallel architecture.

### Source Inputs

- `harness-improvement-proposal-v2-2026-04-08.md`
- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `docs/research/autocode-internal-first-orchestration.md`
- `docs/research/large-codebase-comprehension-and-external-harness-orchestration.md`

### 0.1 Four-Plane Context Model

#### Goal

Formalize the four context planes in AutoCode-native terms:

- durable instructions
- durable project memory
- live session state
- ephemeral scratch

#### Constraints

- do not introduce a mandatory `.harness/` tree yet
- do not duplicate existing source-of-truth docs
- map the planes onto current modules first

#### Implementation Steps

1. Write a short design doc mapping current modules/files into the four planes.
2. Identify which state is currently mixed across planes.
3. Add a minimal API or model layer that names these planes explicitly.
4. Use that model to guide compaction and handoff behavior.

#### Likely Files

- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `autocode/src/autocode/agent/context.py`
- `autocode/src/autocode/session/consolidation.py`
- `autocode/src/autocode/agent/prompts.py`
- `autocode/src/autocode/agent/orchestrator.py`

#### Verification

- design doc exists and is specific
- no duplicate instruction/memory tree introduced
- compaction/handoff code references the new plane model cleanly

### 0.2 Durable-Memory Write and Preservation Rules

#### Goal

Define what belongs in durable memory, what stays session-local, and what survives compaction by rule.

#### Implementation Steps

1. Create a policy doc for durable-memory writes.
2. Define explicit triggers for durable writes.
3. Define explicit exclusions for transient tool output and dead-end exploration.
4. Update consolidation/memory code to follow those rules.

#### Likely Files

- `docs/research/harness-improvement-proposal-v2-adoption-plan.md`
- `autocode/src/autocode/session/consolidation.py`
- `autocode/src/autocode/agent/memory.py`
- `autocode/tests/unit/test_carry_forward.py`

#### Verification

- tests prove transient noise is not promoted to durable memory
- tests prove key durable facts survive compaction

### 0.3 Canonical Runtime-State Normalization

#### Goal

Stop spreading runtime state ad hoc across loop, frontend, orchestrator, and session objects.

#### Required State

- session id
- task id / active task
- approval mode
- agent mode
- project root / worktree
- working set
- checkpoint stack
- pending approvals
- subagent registry
- current plan pointer
- last compact summary

#### Implementation Steps

1. Define one canonical runtime-state model.
2. Identify duplicated state across frontends/orchestrator/loop.
3. Move all shared state reads/writes to the canonical model.
4. Keep frontend-local UI state separate from orchestration/runtime state.

#### Likely Files

- `autocode/src/autocode/agent/orchestrator.py`
- `autocode/src/autocode/agent/factory.py`
- `autocode/src/autocode/agent/loop.py`
- `autocode/src/autocode/inline/app.py`
- `autocode/src/autocode/backend/server.py`
- `autocode/src/autocode/tui/app.py`

#### Verification

- runtime state has one clear owner
- frontend recreation does not lose orchestration state unexpectedly
- tests cover state propagation and resume behavior

### 0.4 Tool Metadata Expansion

#### Goal

Give tools enough metadata to support compaction, scheduling, policy, and external-adapter compatibility.

#### Additions

- concurrency safety
- interruptability
- output budget hints
- direct-call eligibility
- orchestrated-call eligibility
- maybe: estimated cost / latency class

#### Likely Files

- `autocode/src/autocode/agent/tools.py`
- `autocode/src/autocode/external/harness_adapter.py`
- `autocode/tests/unit/test_tools.py`

#### Verification

- metadata exists on all core tools
- scheduler/policy code uses metadata instead of name-based special cases

### 0.5 Artifact-First Resumability

#### Goal

Make resumed work depend on durable artifacts, not only raw transcript recovery.

#### Outputs to Strengthen

- handoff packet
- compact summary
- checkpoint manifest
- artifact bundle
- resume packet

#### Likely Files

- `autocode/src/autocode/session/checkpoint_store.py`
- `autocode/src/autocode/agent/artifact_collector.py`
- `autocode/src/autocode/session/consolidation.py`
- `autocode/tests/unit/test_consolidation.py`

#### Verification

- resumed sessions recover from artifacts cleanly
- handoffs preserve objective, blockers, and next steps

---

## 1. Large Codebase Comprehension

### Goal

Make AutoCode effective on genuinely large repos without overloading the hot context.

### 1.1 Large-Repo Validation

#### Goal

Validate the already-landed retrieval/comprehension stack on repos where naive whole-context use fails.

#### Metrics

- turns to first relevant file
- context growth rate
- compaction frequency
- recovery quality after long tasks
- working-set usefulness

#### Implementation Steps

1. Pick at least one genuinely large repo.
2. Run a small fixed task set with current retrieval/comprehension behavior.
3. Record metrics and observed failure modes.
4. Feed findings back into retrieval/compaction policy.

#### Verification

- stored artifact with metrics
- specific findings, not just anecdotes

### 1.2 LanceDB and Dependency Contract

#### Goal

Make the retrieval dependency/runtime contract explicit rather than half-optional.

#### Implementation Steps

1. Decide whether LanceDB is required, optional, or profile-gated.
2. Align `doctor`, setup docs, and runtime behavior with that decision.
3. Add tests around missing/available dependency behavior.

---

## 1f. Stable TUI Program

**Last updated: 2026-04-17**

### Goal

Lock a research-backed stable-v1 TUI program for AutoCode.

This section is no longer a short “closeout slice.” It is the source-of-truth execution plan for shipping a stable, migration-friendly coding-agent TUI that:

- is predictable and boring in the best way under real terminal use
- preserves the migration-critical contracts users already expect from Claude Code / Pi style workflows
- remains safe-by-default instead of “YOLO by default”
- treats verification as part of the product, not an optional afterthought

### Primary Research Basis

This plan is locked from these inputs, in priority order:

1. `deep-research-report.md`
2. repo-local implementation and QA evidence under `autocode/docs/qa/test-results/`
3. repo-local comparative audits under `research-components/`
4. `docs/tests/tui-testing-strategy.md` and `docs/tests/pty-testing.md`

If a future implementation decision conflicts with those sources, update the research basis first and only then change the execution plan.

### Locked Decisions

These decisions are now fixed unless the user explicitly redirects:

1. **Go BubbleTea is the default interactive frontend.**
   `autocode chat` continues to route to `autocode/build/autocode-tui` when available.

2. **Python inline remains an explicit fallback, not the default.**
   `--inline` stays supported until the migration surface is fully covered and explicitly retired.

3. **Stable v1 is about compatibility and predictability, not feature maximalism.**
   The target is a strong Levels 1-4 product:
   prompt loop, project memory, skills, hooks, verification, permissions, durable sessions.
   Multi-agent orchestration and remote multi-client expansion are post-v1.

4. **Migration contracts matter more than visual mimicry.**
   `CLAUDE.md`, skills, hooks, session history, queue semantics, and permission gates are the core compatibility surface.

5. **Safe-by-default is the default posture.**
   Read-only / workspace-write / full-access modes and allow/ask/deny policy must be explicit, testable, and explainable.

6. **Verification is a ship gate.**
   PTY evidence, deterministic mock-harness tests, focused unit coverage, and verification-profile execution are mandatory for TUI milestones.

### Research Synthesis

The stable-v1 plan is derived from `deep-research-report.md`, plus the repo-local research components already audited.

Research conclusions that now drive implementation order:

- **Progressive disclosure wins.**
  Do not stuff the entire repo or every skill body into context. Load concise catalogs first, then bodies on demand.
- **Message queue semantics are a first-class usability feature.**
  Mid-stream steering and queued follow-ups must remain deterministic across interactive and headless paths.
- **Filesystem contracts beat cosmetic parity.**
  `CLAUDE.md`, skill folders, hooks, and session trees are the migration-critical surface.
- **Permissions must be both safe and legible.**
  Users need to understand which rule matched, why a tool call was allowed/blocked, and what sandbox mode they are in.
- **Compaction is a correctness and security boundary.**
  Provenance must survive summarization so file/tool text cannot silently become user instruction.
- **Verification needs explicit product support.**
  Hook-driven lint/typecheck/test gates, deterministic mocks, PTY evidence, transcripts, and rollback-friendly diffs are all part of the product.

### Current State Snapshot

Already landed and verified on the current tree:

- Go TUI is the default interactive path.
- `--inline` exists as explicit fallback.
- BubbleTea v2 / Mode 2026 migration is done.
- Steering queue, follow-up queue, session fork RPC, multiline input, editor launch, frecency history, task dashboard, `/plan`, and status-bar additions are landed.
- Backend parity for `steer`, `session.fork`, and per-turn `on_cost_update` is landed.
- PTY regression gates are currently green via:
  - `autocode/docs/qa/test-results/20260415-080003-tui-backend-parity-pty-smoke-deterministic-v3-20260415.md`
  - `autocode/docs/qa/test-results/20260415-150741-pty-phase1-fixes.md`
- Focused validation artifacts are green for:
  - Go TUI tests
  - backend/factory/tools Python tests
  - focused Ruff on touched Python surfaces

What remains open is not “closeout honesty”; it is the stable-v1 roadmap below.

### Stable V1 Definition

For AutoCode, “stable v1 TUI” means all of the following are true at the same time:

- the interactive loop is stable under PTY and real terminal use
- migration-critical artifacts from Claude Code / Pi style setups work predictably
- sessions are durable, branchable, exportable, and crash-recoverable
- permissions and sandboxing are explicit, auditable, and enforced
- verification runs are easy to trigger and hard to skip
- the TUI remains usable on large repos without whole-context stuffing

### Stable V1 Product Surface

The stable-v1 TUI must include these surfaces as first-class product commitments:

- interactive streaming transcript
- multi-line composer
- file references and completion
- explicit approval prompts
- message queue for steering and follow-up
- durable sessions with resume, export, and branching
- project memory loading
- skills discovery and invocation
- hooks lifecycle and verification profiles
- permission / sandbox controls
- repo-map style context index and post-edit diagnostics

### Out Of Scope For Stable V1

These are explicitly post-v1 unless the user reprioritizes:

- multi-client remote attach / server-first TUI model
- generalized subagent orchestration as a default path
- worktree fleets and Level-5 orchestration UX
- broad ecosystem automation beyond narrow, safe integrations
- “parity because another tool has it” features that do not strengthen stability, compatibility, or verification

### 1f.1 Milestone A — Runtime Stability And Deterministic TUI Loop

**Why this milestone exists**

The deep research report is clear that stable v1 starts with a predictable loop: rendering, input routing, queue behavior, and session persistence must be boring and reliable before larger migration features matter.

**Status (2026-04-17)**

Runtime gates are green on 2026-04-17. The deterministic mock harness landed as `autocode/cmd/autocode-tui/milestone_a_test.go` (1109 LOC, 62 tests covering startup, palette, inline/alt-screen, warning/error routing, crash recovery, cost/session/fork, editor, task state, theme, queue priority, resize during overlays, rapid key sequences, tool output, unsolicited-picker prevention). Fresh PTY artifacts `20260417-061442-slice0-pty-phase1.md` (10/10, 0 bugs) and `20260417-061444-slice0-pty-smoke.md` (5/5, 0 bugs) confirm runtime behavior against a real TTY. The only remaining Milestone A gap is the three-picker filter bug (`/model`, `/provider`, `/session` pickers drop non-navigation keystrokes with no filter support despite 40+ model entries). That bug is queued as Slice 1 of the 2026-04-17 implementation plan at `/home/bs01763/.claude/plans/virtual-booping-hoare.md`.

**Work to complete**

1. Keep current landed behaviors stable:
   - startup timeout fallback
   - no unsolicited model picker
   - no queue leakage in visible output
   - warning/error classification
   - steering queue and follow-up queue
   - inline vs alt-screen behavior
2. Harden keyboard routing:
   - rapid Enter / Esc / Ctrl+C sequences
   - slash completion focus retention
   - palette open/close and command routing
   - `/model` and `/provider` picker focus behavior
3. Harden rendering behavior:
   - rapid terminal resize
   - long tool output truncation / expansion policy
   - streaming interleaved with tool cards
   - scrollback stability after flushes
4. Harden crash/recovery expectations:
   - append-only session writes
   - no session corruption on backend death or forced quit
   - resume after interrupted run

**Testing strategy**

- Go unit tests for model/update/view state transitions.
- Deterministic mock-backend tests for queue semantics, picker behavior, warning classification, and done-event routing.
- PTY regression scenarios for:
  - startup
  - normal chat
  - `/model`
  - Ctrl+K
  - warning classification
  - inline mode
  - alt-screen mode
- Narrow manual smoke only when PTY cannot prove a behavior.

**Verification criteria**

- No broken rendering under rapid resize or large outputs.
- Message queue works during streaming and tool execution.
- Slash menus and pickers do not lose focus or appear unsolicited.
- Session transcript remains readable and exportable.
- Forced shutdown does not corrupt the current session.

**Exit gates**

- focused `go test -count=1 ./...` green
- PTY regression artifact shows `0 bugs`
- no open runtime bug reproduced by deterministic mock harness
- updated artifact stored under `autocode/docs/qa/test-results/`

### 1f.2 Milestone B — Compatibility And Migration Contracts

**Why this milestone exists**

The research report identifies migration compatibility as the main reason a stable v1 can replace or sit beside Claude Code / Pi workflows. The goal is filesystem and lifecycle compatibility, not brand mimicry.

**Status**

Partial. `--inline`, queue semantics, and some session behaviors align, but the migration surface is not yet explicitly finished or verified.

**Work to complete**

1. **Project memory contract**
   - support `CLAUDE.md` directory walk
   - support `CLAUDE.local.md`
   - support bounded `@imports`
   - gate external imports behind approval
   - document `AGENTS.md` import guidance so teams avoid duplication
2. **Skills contract**
   - Claude-style skill directories
   - progressive disclosure scan: name/description first, body on demand
   - live skill reload in the current session
   - clear support boundary for frontmatter fields that are honored vs ignored
3. **Hooks contract**
   - SessionStart
   - PreToolUse
   - PostToolUse
   - Stop
   - StopFailure
   - stable payload shape and event names
4. **Session expectations for Pi-style users**
   - branching semantics
   - message queue consistency
   - explicit export/share-ready transcripts

**Testing strategy**

- Fixture repos with synthetic `CLAUDE.md`, `CLAUDE.local.md`, imported files, and skills directories.
- Golden tests for hook event names and payload shapes.
- Skill reload tests that edit a skill mid-session and prove the session observes the update.
- Session branch/export tests with expected file layout and replay behavior.

**Verification criteria**

- A Claude Code style repo can be dropped in without rewriting memory and skill layout.
- Hook event names and payload schemas are deterministic and documented.
- Skill discovery is predictable and does not eagerly flood context.
- Pi-style message queue and branch behavior remain consistent.

**Exit gates**

- migration fixture suite green
- hook schema tests green
- skills reload tests green
- docs explicitly state the supported migration contract and unsupported edge cases

### 1f.3 Milestone C — Permissions, Sandbox, And Hook Enforcement

**Why this milestone exists**

Research strongly favors explicit permission controls and hook-enforced workflow safety over implicit trust. Stable v1 must be safe-by-default but still provide explicit escalation paths.

**Status**

Partial. The product already has some approval surfaces, but the stable-v1 contract for permissions and sandboxing is not yet fully locked and verified.

**Work to complete**

1. Define user-visible sandbox modes:
   - read-only
   - workspace-write
   - full access / danger mode
2. Define per-tool policy surface:
   - allow
   - ask
   - deny
   - wildcard and pattern matching for shell commands
3. Make rule decisions explainable:
   - which rule matched
   - why the call was blocked or approved
   - what escalation would allow it
4. Make hooks part of enforcement:
   - PreToolUse can block
   - PostToolUse can verify
   - Stop / StopFailure can fail the turn or require remediation
5. Add diff-first guardrails for larger multi-file writes unless explicitly escalated.

**Testing strategy**

- Table-driven policy tests covering representative tool calls and shell patterns.
- Negative tests for workspace escape attempts and destructive command paths.
- Hook pass/fail tests proving a blocked tool does not execute.
- Approval-flow tests for escalation from lower-trust to higher-trust modes.

**Verification criteria**

- Given any tool call, the matched permission rule is deterministic and explainable.
- Sandbox modes behave exactly as described.
- Hook enforcement can block or require verification without undefined behavior.
- Large file mutations do not slip through without a review/approval path.

**Exit gates**

- policy matrix tests green
- sandbox escape regression tests green
- hook enforcement tests green
- docs include user-facing permission rules and agent-facing implementation rules

### 1f.4 Milestone D — Sessions, Compaction, Provenance, And Recovery

**Why this milestone exists**

Stable v1 must survive long-running work. Research explicitly calls out append-only sessions, branchable history, transparent compaction, and provenance-aware summarization as both usability and security requirements.

**Status**

Partial. Session features and fork support exist, but stable-v1 requirements around provenance, crash recovery, circuit breakers, and export discipline still need to be locked.

**Work to complete**

1. Keep sessions append-only and replayable.
2. Guarantee branch integrity:
   - valid parent linkage
   - no silent history rewrite
   - export works for branched sessions
3. Make compaction transparent:
   - explicit summaries
   - manual compact path
   - auto-compact path
   - visible provenance labels
4. Add compaction safety features:
   - instruction provenance preservation
   - retry circuit breakers
   - metrics/logging for repeated compaction failure
5. Decide whether `log.jsonl` / `context.jsonl` split is needed now or intentionally deferred post-v1.

**Testing strategy**

- Crash-injection tests during write, flush, and compact flows.
- Branch/replay/export invariant tests.
- Red-team tests where tool/file output attempts to become instruction text across compaction.
- Long-session simulations with repeated tool output and compact/recover cycles.

**Verification criteria**

- Session files are recoverable after forced interruption.
- Branching never corrupts history.
- Compaction is explicit and reversible via session tree navigation.
- Provenance survives summarization and prevents instruction smuggling.

**Exit gates**

- crash/recovery tests green
- branch/export invariants green
- compaction provenance tests green
- explicit documented policy for compaction retry/circuit-break behavior

### 1f.5 Milestone E — Context Intelligence Baseline

**Why this milestone exists**

The research plan is explicit that stable v1 must avoid naive whole-repo stuffing. A bounded repo map and diagnostics-after-edit path are the baseline, with deeper LSP features later.

**Status**

Partially landed in the broader product. For the stable TUI program, this milestone is about wiring those capabilities into a trustworthy interactive contract.

**Work to complete**

1. Ensure repo-map style context selection is available on the interactive path.
2. Ensure `@path` and file completion remain cheap and predictable.
3. Run post-edit diagnostics through LSP or equivalent deterministic diagnostics.
4. Surface diagnostics in a way that helps the user verify changes without overwhelming the stream.
5. Validate behavior on large repos where whole-context loading is obviously non-viable.

**Testing strategy**

- Retrieval/repo-map regressions on representative medium and large repos.
- Completion tests for `@path` and shell/file contexts.
- Diagnostics-after-edit tests using deterministic fixture repos with known errors.
- Measurement runs for latency, context growth, and compaction frequency.

**Verification criteria**

- The first relevant file/symbol is found quickly on large repos.
- Diagnostics appear after edits without disrupting the main loop.
- Context growth stays bounded under long sessions.
- The TUI does not regress into whole-repo context stuffing.

**Exit gates**

- large-repo validation artifact stored
- diagnostics-after-edit tests green
- retrieval/working-set regressions green
- explicit latency and context-growth measurements recorded

### 1f.6 Milestone F — Verification Profiles, Release Gate, And Measurement

**Why this milestone exists**

Stable v1 is only stable if the product makes verification easy and skipping it difficult. The research report treats “verification of verification” as part of readiness, not just one more test run.

**Status**

Open as a formalized release gate, even though several focused artifacts already exist.

**Work to complete**

1. Publish verification profiles:
   - formatter profile
   - lint profile
   - typecheck profile
   - targeted-test profile
2. Ensure hooks can trigger those profiles at PostToolUse / Stop / StopFailure.
3. Track operational metrics:
   - skill trigger accuracy
   - hook success/failure rate
   - retry counts / loop counts
   - compaction failure counts
4. Make transcript and rollback discipline explicit:
   - every tool action is transcripted
   - diffs are reviewable
   - exported history is inspectable
5. Keep a separate-review step available for code review style workflows.

**Testing strategy**

- Deterministic mock-provider harness for tool calling, queue semantics, and hook decisions.
- Verification-profile tests using fixture repos with expected formatter/lint/typecheck/test outcomes.
- Transcript/export tests proving actions remain reviewable.
- Reviewer-mode or second-pass tests where available.

**Verification criteria**

- Verification profiles are reproducible and documented.
- Hook-triggered verification can fail a turn deterministically.
- Retry loops and skipped checks are visible in metrics/artifacts.
- The product makes independent verification easier, not harder.

**Exit gates**

- deterministic mock-harness suite green
- verification-profile suite green
- transcript/export checks green
- release note includes stable-v1 validation matrix and current known limitations

### Cross-Cutting Testing Matrix For Stable V1

Every stable-v1 milestone must specify which rows of this matrix it exercises:

| Test Layer | Purpose | Minimum Requirement |
|---|---|---|
| Go unit tests | model/update/view correctness | green on every TUI behavior change |
| Python unit tests | backend parity, loaders, policies, hooks | green on every backend or contract change |
| Deterministic mock harness | queue semantics, tool routing, hook decisions | required for all stateful loop changes |
| PTY regression | real terminal behavior | required for all interactive TUI changes |
| Migration fixtures | `CLAUDE.md`, skills, hooks, sessions | required for compatibility milestones |
| Security/policy tests | sandbox and allow/ask/deny correctness | required for permission milestones |
| Crash/replay tests | session durability and compaction safety | required for session milestone |
| Large-repo validation | context growth, retrieval latency, recovery | required for context milestone |

### Stable V1 Acceptance Criteria

AutoCode should not declare “stable TUI v1” until all of these are true:

- UI stability:
  - no broken rendering on resize
  - no broken keyboard routing under queue/picker/palette use
  - large outputs degrade gracefully
- Session integrity:
  - append-only, replayable, crash-recoverable session files
  - branch/export invariants hold
  - compaction is explicit and provenance-preserving
- Security and permissions:
  - permission rules are deterministic and explainable
  - sandbox modes behave as promised
  - large writes and destructive actions follow explicit approval rules
- Migration correctness:
  - Claude-style memory/skills/hooks load predictably
  - Pi-style queue/session expectations hold
- Verification discipline:
  - deterministic mock harness is green
  - PTY evidence is green
  - verification profiles run and fail correctly
  - transcripts and diffs are inspectable

### Explicit Non-Goals During Stable V1 Work

While this program is active, do not derail into:

- remote-client architecture work
- broad subagent UX
- orchestration-first features that multiply state complexity
- parity-only features with no stability, compatibility, or verification value

### Next Starting Point

The next implementation work for Section 1f starts at **Milestone A**:

1. lock the runtime stability matrix
2. enumerate missing runtime acceptance cases
3. convert those into deterministic mock tests and PTY checks before adding new TUI surface area

After Milestone A, move in order:

1. Milestone B — migration contracts
2. Milestone C — permissions and hooks
3. Milestone D — sessions and compaction
4. Milestone E — context intelligence
5. Milestone F — release gate and measurement

---

## 1g. TUI Testing Strategy (Active Slice)

**Last updated:** 2026-04-18 (Phase 1 Track 1 substrate landed).
**Status:** Architecture APPROVED by Codex Entry 1141 + doc-polish
delta APPROVED by Codex Entry 1144. Phase 1 Track 1 substrate
implemented under `autocode/tests/tui-comparison/` with positive +
negative control tests green and end-to-end `make tui-regression`
target producing the 5 artifacts per scenario. Track 2 + Track 3
remain open for follow-up slices per the three-track architecture
below.

### Post-Codex-1138 Three-Track Architecture (AUTHORITATIVE)

Codex Entry 1138 correctly flagged that the earlier §1g conflated three
separate jobs into one pipeline. Split cleanly:

#### Track 1 — `tui-regression` (autocode-only, deterministic, CI-eligible)

- Scope: autocode only. **Backend model: deterministic mock by default**
  (`autocode/tests/pty/mock_backend.py` via `AUTOCODE_PYTHON_CMD`).
  CI-eligible lane MUST use the mock — no external gateway dependency,
  no rate-limit exposure, no LLM-quality variance in the regression
  signal. Live-gateway / real-backend coverage is the responsibility
  of the existing `autocode/tests/pty/` suites
  (`pty_phase1_fixes_test.py`, `pty_smoke_backend_parity.py`, etc.),
  not Track 1. Updated per Codex Entry 1151 Suggested Change #1.
- Substrate: `autocode/tests/vhs/` extended with minimal DSR shim.
- Scenarios: the full 16-scenario catalog (§Scenario Catalog below).
- Predicates: only **hard-invariant** predicates (see
  §"Predicate Classification" below). Soft-style predicates are NOT
  gating in this track.
- Artifacts per run: `.raw` (raw ANSI bytes), `.txt` (stripped),
  `.png` (rendered), `.profile.yaml` (terminal profile: TERM,
  COLORTERM, rows, cols, boot_budget_s, dsr_shim_version,
  dsr_responses_served).
- CI hook: `make tui-regression` runs Track 1 only.
- Exit gate (for this slice's DoD):
  - Track 1 produces truthful hard-invariant verdicts for autocode.
  - No false passes (i.e., the test doesn't claim green when autocode
    is visibly broken).
  - No false failures on the known-good autocode startup scenario.

#### Track 2 — `tui-reference-capture` (manual, non-CI, ad hoc)

- Scope: reference TUIs (claude, codex, opencode, goose, forge, pi)
  for visual comparison only.
- Substrate: same capture driver as Track 1, but the **isolation
  contract is weaker** because these tools write state on
  startup/exit. Run under strong tmpdir isolation where feasible; for
  tools that refuse to run isolated, mark as "reference capture only
  from user's real `$HOME`".
- Scenarios: **5-scenario portable subset only** — see §"Portable
  Reference Scenarios" below. The 16-scenario autocode catalog is NOT
  used here; those scenarios are not portable.
- Predicates: none applied. Track 2 produces artifacts (PNG + text +
  profile) that Track 3 consumes; it does not itself assert
  correctness.
- Invocation: `make tui-reference-capture` — never runs in CI. User
  triggers manually when baselines need refreshing (e.g., reference
  tool version bump).
- Isolation tiers:
  - Tier A (CI-safe): autocode (Track 1 only; not Track 2).
  - Tier B (strong-isolated, acceptable for Track 2): pi with
    read-only copy of `~/.pi/agent/models.json`, snapshot-before and
    diff-after to verify no writes escaped.
  - Tier C (manual-only, user's real `$HOME`): claude, codex,
    opencode, goose, forge — explicitly allowed to write state,
    captured once per reference-version bump.
- **Tier C "documented N/A on blocker" policy** (per Codex Entry 1141
  Suggested Change #4): if a Tier C tool is blocked on the capture day
  by auth churn, forced updater behavior, rate-limit, or other
  environmental issue, the capture run MUST document the blocker in
  the run's `_index.md` as `status: N/A — <reason>` and move on. No
  unbounded waits, no retry loops. A blocked Tier C tool does NOT
  fail Track 2; Track 2 only requires ≥2 reference TUIs captured total
  (pi at Tier B + any one Tier C). If more Tier C tools capture
  cleanly, great; if they don't on that day, they go on the next
  attempt.

#### Track 3 — `tui-style-gap-backlog` (non-slice)

- Scope: the downstream UX work of making autocode look/feel more
  like Claude Code.
- Inputs: Entry 1136's 11-item gap list + predicates labeled as
  "soft-style target" (see §"Predicate Classification").
- Output: a prioritized backlog in
  `docs/plan/tui-style-gap-backlog.md` (new file, to be created
  during implementation). Each item gets HIGH/MED/LOW with
  before/after PNG references.
- **Not part of this slice's DoD.** This track is produced BY the
  slice, not required to close the slice.

### Predicate Classification

Codex 1138 Concern #3 and Suggested Change #8 require predicates to
be labeled. Resolving the earlier contradictions:

**Hard invariants (autocode correctness — Track 1 gates)**

Per Codex Entry 1151 Suggested Change #2, the hard-invariant list is
split into two tiers: a **Phase 1 enforced subset** (the 6 gates
currently enforced by `make tui-regression` for the `startup` +
`first-prompt-text` scenarios) and a **full Track 1 target set** that
will be filled in across Phase 2+ as more scenarios come online.

**Phase 1 + Phase 2 (so far) enforced subset (11 — currently gating `make tui-regression`)**

1. `no_crash_during_capture` — raw buffer ≥ 32 bytes (more than just
   terminal queries)
2. `composer_present` — composer-specific markers only (`Ask AutoCode`,
   `❯ Ask`, `> Ask`, `│ > `, `│ ❯ `) visible in rendered frame. Bare
   `>` / `❯` are **not** sufficient (they collide with picker selection
   rows). Returns PASS with `N/A` detail on scenarios that intentionally
   replace the composer: `{model-picker, provider-picker,
   session-picker}` and `{ask-user-prompt}`.
3. `no_queue_debug_leak` — no `<<STEER`, `steering_queue`,
   `queue_debug`, `[queue]` markers in scrollback
4. `basic_turn_returns_to_usable_input` — scenario-aware; for turn
   scenarios, composer must still be visible after the turn; for
   non-turn scenarios (e.g. `startup`), returns PASS with
   `detail="N/A — scenario has no turn"`. Aligns with
   `docs/tests/tui-testing-strategy.md` "Basic Chat Turn" requirement.
5. `spinner_observed_during_turn` — scenario-aware; for turn
   scenarios, at least one braille spinner char
   (`⠙⠹⠸⠼⠴⠦⠧⠇⠏⠋⠛⠓`) OR a verb marker (`Thinking`, `Pondering`,
   `Working`, `Creating`, `Reasoning`, `Connecting`, `Synthesizing`,
   `Processing`) must appear in captured stream; else PASS with N/A.
6. `response_followed_user_prompt` — scenario-aware; for turn
   scenarios, substantive non-chrome content must follow the user
   prompt line; else PASS with N/A.
7. **`picker_filter_accepts_input`** — Phase 2 Scenario 1 unlock;
   scenario-aware over `{model-picker, provider-picker, session-picker}`;
   verifies picker header visible AND `[filter:` token present after
   user types filter chars; else PASS with N/A.
8. **`approval_prompt_keyboard_interactive`** — Phase 2 Scenario 2
   unlock; scenario-aware over `{ask-user-prompt}`; verifies the modal
   renders a question line AND option markers (`❯`/`●`/`○` or a
   ``^\s*\d+\.\s+\S`` enumerated list — bare option words in prose are
   NOT sufficient) AND a keyboard hint (`Enter`, `Esc`, …); else PASS
   with N/A. Also flips `composer_present` to N/A for ask-user
   scenarios, since the modal replaces the composer.
9. **`warnings_render_dim_not_red_banner`** — Phase 2 Scenario 3
   unlock; scenario-aware over `{error-state}`; verifies backend
   WARNINGs render as a dim ``⚠`` scrollback line AND do NOT end up
   wrapped inside the red ``Error:`` banner; else PASS with N/A.
10. **`startup_timeout_fires_when_backend_absent`** — Phase 2 Scenario
    4 unlock; scenario-aware over `{orphaned-startup}`; runs against
    `tests/pty/silent_backend.py` (never emits `on_status`); verifies
    the 15s ``startupTimeoutDuration`` path surfaces the canonical
    ``Backend not connected (startup timeout)`` banner; else PASS with
    N/A.
11. **`spinner_frame_updates_over_time`** — Phase 2 Scenario 5 unlock;
    scenario-aware over `{spinner-cadence}`; scans the full raw ANSI
    byte stream (not just the final pyte frame) for ≥2 distinct
    braille glyphs, proving the spinner actually rotates over time;
    else PASS with N/A.

**Full Track 1 target set (deferred to Phase 2+)** — each comes online
as the matching scenario lands in the runnable catalog:

- `cursor_visible` — pyte cursor row/col within screen bounds in
  rendered frame

Rule: the full target set is the stable-v1 Track 1 contract. The
Phase 1 enforced subset is what `make tui-regression` actually runs
today. Every phase bump must document which target predicate became
enforced in that phase's completion report.

**Soft style targets (Track 3 backlog — NOT Track 1 gates)**

- composer has rounded Unicode border
- status bar is BELOW composer (current autocode has it ABOVE — this
  is the contradiction Codex flagged; resolving: current ordering is
  NOT a hard invariant; the target is BELOW but moving there is
  Track 3 work, not Track 1 failure)
- spinner includes `esc to interrupt` hint
- welcome box spans ≥3 rows and ≥40 cols
- version displayed inline in top border
- composer prefix character (`>` vs `❯`)
- 16-color vs 256-color palette choices
- mode hint text content (`/help for help...` vs
  `! for bash · / for commands · esc to undo`)

### Portable Reference Scenarios (Track 2, 5 items)

Codex 1138 Suggested Change #4. The 16-scenario catalog is too broad
for cross-tool. Portable subset:

1. `startup` — empty state after launch
2. `command-discovery` — typing `/` or `?` (each tool's equivalent)
3. `simple-prompt` — send "hello", capture response rendering
4. `narrow-terminal` — cols=60 rendering
5. `error-state` — induced gateway 429 OR manual 401-style error
   (only where safely inducible per tool)

Full 16-scenario catalog stays in Track 1 (autocode-only) — see
existing §"Scenario Catalog" below for the full list.

### Storage Schema (revised per Codex 1138 Suggested Change #2)

```
autocode/tests/tui-comparison/
  capture.py              # extends tests/vhs/capture.py with DSR shim
  dsr_responder.py        # minimal responder: [6n, [c, [?u, OSC 10;?
  launchers/<tui>.py
  predicates.py           # hard vs soft labeled
  scenarios/              # 16 for Track 1
  portable_scenarios.py   # 5 for Track 2
  profile.py              # terminal-profile YAML emitter

autocode/docs/qa/tui-comparison/
  regression/<run-id>/<scenario>/       # Track 1 artifacts (autocode only)
    autocode.raw          # raw ANSI bytes
    autocode.txt          # stripped text
    autocode.png          # pyte-rendered
    autocode.profile.yaml # TERM, COLORTERM, rows, cols, boot_s, dsr_shim_v, dsr_responses_served
    predicates.json       # {"hard": {pred: pass/fail}, "soft": {pred: pass/fail}}
  reference/<date>-baseline/            # Track 2 artifacts (manual only)
    <tool>/<scenario>/
      {raw,txt,png,profile.yaml}
    _index.md             # tool versions + tier labels + any warnings
```

### Exit Gates (revised per Codex 1138 Suggested Change #6)

This slice closes when:
- [ ] Track 1 substrate exists and runs deterministically against
      autocode
- [ ] Track 1 hard-invariant predicates produce TRUTHFUL verdicts
      (pass on known-good state, fail on injected regression)
- [ ] Track 2 capture pipeline works on the 5 portable scenarios for
      at least 2 reference TUIs (pi as Tier B + one Tier C tool)
- [ ] Gap report is generated truthfully for Track 3 consumption
      (lists observed soft-style deltas without claiming them as
      failures)
- [ ] `make tui-regression` is CI-eligible; `make tui-reference-capture`
      is user-triggered only
- [ ] `docs/plan/tui-style-gap-backlog.md` exists and enumerates
      HIGH/MED/LOW style items from Entry 1136 + predicates-soft

NOT required to close this slice:
- autocode already passing soft-style target predicates (that's Track
  3 work)
- all 6 reference TUIs captured (minimum 2)
- LLM vision narrator running (optional add-on)

### Supporting detail below

The remaining sections below ("Open Design Questions (closed)",
"Scenario Catalog (full 16)", "Look-and-Feel Criteria", "Phases",
"Current vs Target Layout", etc.) remain as the supporting
implementation detail for Track 1 and Track 3. Where those sections
conflict with the three-track architecture above, the three-track
architecture wins.

### Goal

Build a repeatable pipeline that spins up each candidate TUI under
identical prompts on the shared LiteLLM gateway, captures visual state,
stores snapshots alongside reference baselines, and analyzes/compares
them so:

1. fidelity regressions in autocode are caught quickly
2. side-by-side feedback against reference tools (pi, claude-code,
   opencode, codex CLI, aider, goose) is concrete
3. "this does not feel like Claude Code" becomes a testable claim
   instead of a recurring screenshot back-and-forth

### Why Now

The user surfaced three separate rendering issues this session (image
#7, #8, #9) that unit tests and pyte-based PTY tests missed. My prior
"all green" claims were based on state-transition coverage, not visible
end-state. This pipeline replaces opinion with evidence.

### Dependencies Already Satisfied

- Pi coding agent is wired at `http://localhost:4000/v1` via
  `~/.pi/agent/models.json` (8 gateway aliases, LITELLM_MASTER_KEY
  env-persistent). Entry 1124 in AGENTS_CONVERSATION.MD captures the
  wiring.
- VHS-shape pyte + Pillow substrate exists for autocode at
  `autocode/tests/vhs/` — renderer, differ, scenarios,
  run_visual_suite.py, and reference PNGs.
- Mirror of claude-code, pi-mono, opencode, openai-codex, aider,
  claw-code, goose, open-swe exists under `research-components/`.
- Feature-audit checklist exists at
  `docs/plan/research-components-feature-checklist.md`.

### Out Of Scope

- Pixel-perfect parity with claude-code or pi (goal is legible,
  functional equivalence, not byte-for-byte mimicry).
- Building the pipeline on top of a proprietary SaaS — everything
  must run locally.
- Replacing the existing VHS substrate — extend it.

### Closed Design Decisions (as of 2026-04-18)

Each question below has a concrete answer. Implementation proceeds
against these choices.

### 1. Capture strategy per TUI — **pyte + Pillow (Python-native)**

- **Choice:** extend the existing `autocode/tests/vhs/` pipeline
  (pyte + Pillow) to accept any TUI binary as a parameter.
- **Rationale:** no new deps — vhs, asciinema, agg, tmux are all
  absent from the system; adding them adds packaging risk. Pyte
  is already proven for autocode regression and is plenty for
  block/layout/color comparison at the 160x50 or 80x24 grid level.
- **Escape hatch:** if a specific reference TUI uses rendering
  that pyte can't parse (e.g. sixel graphics), fall back to the
  native binary's `--print` / non-TUI mode for that scenario, OR
  add asciinema+agg at that point. Treat as a per-scenario escape,
  not a default.
- **Files that exist and are reused:**
  - `autocode/tests/vhs/capture.py` — PTY spawn + ANSI collect
  - `autocode/tests/vhs/renderer.py` — pyte Screen → PNG via PIL
  - `autocode/tests/vhs/differ.py` — per-cell semantic diff
  - `autocode/tests/vhs/scenarios.py` — scenario DSL

### 2. Driving identical prompts across different TUIs — **per-tool launcher scripts**

- **Choice:** `autocode/tests/tui-comparison/launchers/<tui>.py`
  files, each exposing a `launch(scenario, workdir, env)` callable
  that knows how to spawn that TUI, wait for ready, send prompt,
  drain output, clean-exit.
- **Substrate status (2026-04-18 audit):** `autocode/tests/vhs/capture.py`
  already accepts a generic `binary: Path` via `_spawn(argv=[str(binary)])`.
  Multi-TUI extension is minimal: add `argv_suffix: list[str]` so we can
  pass e.g. `["session"]` for goose, add per-tool `env_extra` patterns,
  extend the ready-marker wait logic. No substrate rewrite needed.
- **Per-TUI invocation (from 2026-04-18 `--help` audit):**

| Tool | argv for interactive | env notes | Ready marker (regex hint) |
|---|---|---|---|
| autocode | `["autocode"]` | `AUTOCODE_PYTHON_CMD` auto-discovered; `LITELLM_MASTER_KEY` passed through | `AutoCode` |
| claude | `["claude"]` | uses `~/.claude/` subscription state; don't mutate | `Claude Code` or `claude>` |
| codex | `["codex"]` | uses `~/.codex/auth.json`; don't mutate | `codex` banner |
| opencode | `["opencode"]` | uses `~/.opencode/` + providers config | ASCII art "OPENCODE" banner |
| goose | `["goose", "session"]` | uses `~/.config/goose/config.yaml` | `goose session` prompt |
| pi | `["pi"]` | uses `~/.pi/agent/models.json` (LiteLLM-wired) + `LITELLM_MASTER_KEY` env var | `pi` prompt |
| forge | `["forge"]` | uses `~/.forge/` if present | `forge` banner |

- **Scenario DSL** reused from existing `autocode/tests/vhs/scenarios.py`:
  each scenario is a list of `(delay_s | bytes_to_send)` steps.
- **`graceful_exit=False` everywhere** — BubbleTea and many other TUIs
  restore the saved primary buffer on Ctrl+D, hiding the running state
  from pyte. Use SIGTERM mid-alt-screen to freeze pyte on live frame
  (pattern already proven in autocode scenarios).

### 3. Storage layout — **scenario-first, date-versioned**

```
autocode/docs/qa/tui-comparison/
  reference/                         # one-time baseline captures
    20260418-baseline/
      _index.md                      # tool versions + scenarios tested
      startup/
        autocode.png
        autocode.txt                 # pyte Screen.display text
        claude.png
        claude.txt
        ...
      first-prompt-text/
        ...
  regression/                        # continuous autocode captures
    20260418-<run-id>/
      _index.md
      _diff.md                       # rule-based + optional vision verdict
      startup/
        autocode.png
        autocode.txt
        diff-vs-reference.png        # if regression caught
```

### 4. Diff layer — **semantic per-cell (intra) + image tolerance (cross)**

- **Intra-autocode regression** (autocode now vs autocode baseline):
  per-cell semantic diff in `tests/vhs/differ.py` with small
  tolerance for color/attr drift. Already works.
- **Cross-TUI comparison** (autocode vs claude-code baseline):
  layouts differ by design; use (a) pyte Screen.display text diff
  for gross layout sanity, (b) image diff with tolerance via PIL
  `ImageChops` for "how different do they look", (c) LLM vision
  narrator for qualitative description.
- **Pixel diff threshold:** 5% default; configurable per scenario.

### 5. Analysis layer — **rules (hard gate) + LLM vision (narrator)**

> **[SUPERSEDED by "Post-Codex-1138 Three-Track Architecture" at the top of §1g.]**
> The predicates listed below were a single undifferentiated bag. The authoritative
> version splits them into **hard invariants** (Track 1 gates) and **soft style
> targets** (Track 3 backlog). See §"Predicate Classification" at the top for the
> canonical list. Preserved here for historical reference only.

- **Rule-based predicates** (Python, operate on pyte Screen + text):
  - `composer_at_bottom(screen)` — cursor or `>`/`❯` in last 2 rows
  - `status_bar_styled(screen)` — row above composer has dim fg
  - `branch_pill_right(screen)` — colored bg cell at status-bar right
  - `welcome_hidden_after_turn(screen, turn_n)` — welcome absent when n≥1
  - `tool_card_bullet(screen)` — ● or ○ at start of tool-call line
  - `spinner_has_elapsed(screen)` — `(Ns)` suffix near "Thinking..."
  - `mode_hint_last_row(screen)` — last row has dim-italic mode hint
  - `picker_filter_header(screen)` — when picker open, shows `[filter: …]`
  - additional predicates as the scenario set grows
- **LLM vision narrator** (optional, uses `vision` gateway alias):
  - Input: 2 PNGs (autocode + reference)
  - Output: 0-100 similarity score + enumerated differences + fix suggestions
  - Called only when rules disagree OR user explicitly requests
  - Budget: ~1 call per scenario at refresh time; not on every regression run
- **Human review surface**: side-by-side stitched PNG written to
  `regression/<run>/<scenario>/side-by-side.png` whenever rule-based
  verdict is WARN or FAIL.

### 6. Environment isolation — **fresh `$HOME`/tmpdir per capture + read-only of user state**

- **Rule:** NEVER mutate the user's real `~/.claude/`, `~/.codex/`,
  `~/.opencode/`, `~/.config/goose/`, `~/.pi/`, or
  `~/.forge/` during a capture.
- **Reference-baseline captures** (one-time, manual): use user's
  existing auth state in read-only mode. Just spawn, capture, exit.
  Don't let the TUI write sessions to disk where possible; if it
  does, clean up after.
- **Continuous regression captures** (autocode only): per-capture
  `tmpdir = mkdtemp("autocode-tui-")`; set `HOME=$tmpdir`,
  `XDG_CONFIG_HOME=$tmpdir/.config`; copy minimal skeleton if the
  launcher needs one; inherit `LITELLM_MASTER_KEY` from parent env.
- **Exit-state check**: after each capture, assert that no files
  were written outside the tmpdir. If any were, flag and fail.

### 7. Failure modes — explicit handling

| Failure | Handling |
|---|---|
| TUI crashes (non-zero exit, SIGSEGV) | capture partial buffer; write `crash.log`; verdict = FAIL |
| TUI hangs waiting for auth | timeout N seconds; capture "auth-required" state as its own scenario; verdict = N/A for auth-gated scenarios |
| Gateway returns 429 | capture the error-rendering; that IS a useful scenario (`error-state` fixture) |
| Empty/black frame | retry once with +2s warmup; if still empty, verdict = FAIL |
| Alt-screen leaves stale buffer after exit | use `graceful_exit=False` + SIGTERM to freeze pyte screen mid-TUI (pattern proven in existing `tests/vhs/`) |
| Scenario not supported by this TUI (e.g. `/model` on a tool without pickers) | scenario produces `skipped.txt` with reason; verdict = N/A |

### 8. Reference-TUI version pinning — captured in `_index.md` header

Every baseline run records the exact binary versions:

```yaml
# _index.md (YAML frontmatter)
run_id: 20260418-baseline-001
captured_at: 2026-04-18T00:00:00Z
tools:
  autocode: "0.1.0"
  claude: "2.1.112 (Claude Code)"
  codex: "codex-cli 0.121.0"
  opencode: "1.4.7"
  goose: "1.30.0"
  pi: "0.67.6"
  forge: "2.9.1"
scenarios_attempted: [startup, first-prompt-text, ...]
terminal: {cols: 160, rows: 50}
```

On version bump of any reference TUI: re-run the baseline scenario
set under a fresh `reference/<date>-baseline/` folder; keep older
baselines for historical comparison.

### Scenario Catalog (canonical set; extensible)

| # | Scenario | Tests |
|---|---|---|
| 1 | `startup` | empty-state layout, header, composer position, status bar chrome |
| 2 | `help` | `/help` or `?` affordance visibility |
| 3 | `first-prompt-text` | "hello" → short text response rendering |
| 4 | `first-prompt-code` | "write fizzbuzz in python" → code-block rendering |
| 5 | `streaming-mid-frame` | snapshot during a deliberately slow response |
| 6 | `thinking-display` | reasoning trace rendering (if tool exposes it) |
| 7 | `tool-call-read` | read-file tool card rendering |
| 8 | `tool-call-bash` | bash/shell tool card rendering |
| 9 | `slash-list` | typing `/` to see command list |
| 10 | `model-picker` | `/model` picker layout + keyboard nav |
| 11 | `queue-mid-stream` | Enter pressed mid-response, queue indicator |
| 12 | `ask-user-prompt` | clarification prompt rendering (if applicable) |
| 13 | `narrow-terminal` | cols=60 rendering |
| 14 | `error-state` | induced 429 or tool-error rendering |
| 15 | `multiline-compose` | Alt+Enter, multi-line composer |
| 16 | `session-resume` | quit + relaunch, history surface |

Tools that don't support a given scenario: skipped with N/A.

### Current vs Target Layout (2026-04-18 observation)

Visual inspection of `autocode/tests/vhs/reference/startup.png` (captured 2026-04-17) shows the current autocode row ordering:

1. Welcome header (orange `AutoCode`)
2. Welcome subtitle (dim)
3. Empty transcript space
4. Status bar (`tools · openrouter · suggest · mock-session-001`)
5. Composer (`> Ask AutoCode…`)
6. Hint row (`/help for help, /model to switch, Ctrl+D to quit`)
7. Mode indicator (`◆ AutoCode`)
8. (In mock captures) backend warning

**Claude-Code target row order:**
1. Welcome (turn 0 only)
2. Transcript
3. Composer (rounded/framed)
4. Status bar (below composer, branch pill right)
5. Mode hint (last row, dim italic)

**Gap:** autocode places the status bar ABOVE the composer and has multiple
chrome rows below. The target is status bar + mode hint BELOW composer, and
the composer itself visually framed.

**Implication for predicates:** Phase 4 hard-gate tests must encode the
target ordering. Running the current tree against those tests should FAIL
on predicates 1, 2, and possibly 3 until the rendering is adjusted. That
is the correct "regression caught" outcome for the current slice — it will
show us exactly what needs to change to achieve Claude-Code-like feel.

**Also observed:** the `◆ AutoCode` row's orange diamond is unexpected —
likely a mode-indicator artifact. Flag as a separate finding in the
regression run.

### Live capture evidence (2026-04-18)

Built `/tmp/tui_probe.py` (100 LOC PTY + select) and captured 7 TUIs. Full
detail in `AGENTS_CONVERSATION.MD` Entry 1136. Headline findings:

- **6 of 7 TUIs capture cleanly** (autocode, pi, claude, opencode, goose, forge).
- **codex blocks** on terminal-query responses (`[6n`, `[c`, `[?u`, `OSC 10;?`).
  Fix: add a DSR responder shim to the capture driver using pyte's own
  terminal state. ~30 LOC addition to Phase 1.
- **Claude Code real specs** extracted from `research-components/claude-code-sourcemap/src/`:
  - `Logo.tsx` — rounded border box, `✻ Welcome`, sub-block with `/help` and `cwd`
  - `Spinner.tsx` — 12-frame sparkle rotation at 120ms, 55 verbs, format `{char} {verb}… ({Ns} · esc to interrupt)`
  - `PromptInput.tsx` + `screens/REPL.tsx` — rounded composer box, `>` prefix in 3-wide gutter, hint row below with `! for bash · / for commands · esc to undo` + right-aligned `shift+⏎ for newline`
- **Spinner-interrupt format is cross-tool** (Claude + forge both use `(Ns · key to interrupt)`). Autocode + pi omit the interrupt hint — gap.
- **Welcome richness gradient**: autocode (2 lines) < pi (3 lines) < forge (cheatsheet box) < opencode (logo+placeholder+mode+keybinds) < claude (full dashboard with recent activity).

### Concrete gap list: autocode vs Claude Code today

| # | Dimension | autocode today | Claude Code | Priority |
|---|---|---|---|---|
| 1 | Composer border | none | rounded dim box | HIGH |
| 2 | Composer prefix | `❯` | `>` | LOW |
| 3 | Bash mode (`!` prefix) | not present | `! for bash mode` | MED |
| 4 | Spinner interrupt hint | missing | `esc to interrupt` | HIGH |
| 5 | Spinner char set | Braille dots | sparkle chars | LOW |
| 6 | Welcome richness | 2 lines | dashboard box | MED |
| 7 | Version in top border | no | yes | LOW |
| 8 | Hint row content | `/help, /model, Ctrl+D` | `! / esc · shift+⏎` | MED |
| 9 | Orange diamond `◆ AutoCode` position | before spinner | n/a | HIGH (remove or relocate) |
| 10 | Mode-below-composer | mode hint pre-composer | n/a pattern | MED |
| 11 | Rounded Unicode border chars usage | not used | used | HIGH |

### Phase 1 additions (capture driver requirements, beyond earlier §1g)

- **DSR responder**: embed a small state machine in the capture driver that watches child output for `ESC[6n`, `ESC[c`, `ESC[?u`, `OSC 10;?` and writes back minimal valid responses so codex + other query-first TUIs render.
- **Longer per-tool timeouts**: goose needs >10s boot for its extension system. Parameterize per-tool `boot_budget_s` in launcher config.
- **Self-updater awareness**: forge auto-updates on every launch. Either cache the binary or skip forge captures on fresh runs. Document in launcher.

### New hard-gate predicates (add to §Look-and-Feel)

- `composer_has_rounded_border(screen)` — composer's top-left corner char in `{╭, ┌, ╒, ╓}`
- `spinner_has_interrupt_hint(screen)` — spinner line contains token `interrupt` or `esc` while loading
- `welcome_scoped_to_init(screen, turn_n)` — when `turn_n == 0`, welcome box spans ≥3 rows and ≥40 cols

### Look-and-Feel Criteria

Encoded as machine-checkable predicates under
`autocode/tests/tui-comparison/predicates.py`:

**Must match Claude-Code baseline (hard gates for autocode):**
1. Composer occupies bottom 1-2 rows with `>` or `❯` prefix
2. Status bar is row above composer, dim foreground
3. Branch pill on right of status bar (when in git repo)
4. Transcript above composer, inline mode preserves scrollback
5. Tool cards start with ● bullet + optional └ continuation
6. Spinner shows elapsed-seconds suffix `(Ns)`
7. Welcome header shown only at `stageInit` (turn 0)
8. Pickers support keyboard nav + type-to-filter + two-stroke Esc
9. Thinking text rendered dim + italic prefix (▸ or ·:)
10. Warnings render dim (⚠), not red banner, unless fatal
11. Queue indicator appears in scrollback + status-bar count, NOT a live panel (per image #9 fix)
12. Mode hint visible on last row, dim italic

**Taking best from research-components/ (non-blocking improvements):**
- From **pi-mono**: theme customizability + skill slots + progressive-disclosure discovery
- From **opencode**: `/sandbox` mode switch + LSP 9-op surface
- From **openai-codex**: `/resume <id>` symmetric session API + `fork` subcommand
- From **claude-code-sourcemap**: sourcemap navigation hint
- From **goose**: plan mode affordance
- From **open-swe**: session branch tree UI (already partially present via `/fork`)
- From **forge**: agent specification via `--agent` and sandbox via `--sandbox`

### Implementation Phases

> **[SUPERSEDED — old 6-phase single-pipeline model.]**
> The canonical phase/gate model is in §"Post-Codex-1138 Three-Track
> Architecture" at the top of §1g. Track 1 Phase 1 corresponds to
> "Phase 1 — substrate" below but with narrower scope (autocode-only,
> 2 scenarios). Preserved below for historical context.

**Phase 1 — substrate (tests/tui-comparison/):** extend existing
pyte pipeline to accept arbitrary binary; add per-tool launchers
for autocode + pi first; define scenario DSL. ~300 LOC.
Exit gate: capture `startup` + `first-prompt-text` for autocode + pi.

**Phase 2 — scenario catalog:** add 14 more scenarios from §Catalog.
Exit gate: all 16 scenarios capturable for autocode; pi skips
scenarios it doesn't support with documented N/A reasons.

**Phase 3 — reference baselines:** run each reference TUI (claude,
codex, opencode, goose, forge) through the scenarios once; commit
PNG+text baselines to `docs/qa/tui-comparison/reference/<date>-baseline/`.
Exit gate: `_index.md` with versions + all captured scenarios.

**Phase 4 — rules + diff:** implement predicates from §Look-and-Feel;
run rules on autocode captures vs claude-code baseline; generate
diff report.
Exit gate: rules pass on current autocode against at least the
hard-gate predicates 1-12.

**Phase 5 — LLM vision narrator (optional):** gate behind
`--with-vision` flag; uses `vision` alias on localhost:4000.
Exit gate: one annotated diff report stored.

**Phase 6 — CI integration:** `make tui-compare` target that runs
Phases 1-4 headlessly; fails on hard-gate predicate failures;
stores artifacts.

### Exit Gates (overall) — SUPERSEDED

> **[SUPERSEDED — see "Exit Gates (revised per Codex 1138 Suggested
> Change #6)" at the top of §1g. The list below contains the
> pre-revision single-pipeline gates that conflict with the three-track
> architecture.]**

- [ ] design review by Codex (this PLAN.md §1g + Entry 1135 in comms)
- [ ] Phase 1 substrate green: autocode + pi baseline captures stored
- [ ] Phase 3 reference baselines stored for ≥ 3 reference TUIs (claude, codex, one more)
- [ ] Phase 4 hard-gate predicates pass for autocode's current state
- [ ] session-isolation test proves no writes to user's real `~/.claude/`, `~/.codex/`, `~/.opencode/`, `~/.config/goose/`, `~/.pi/`, `~/.forge/`
- [ ] `DEFERRED_PENDING_TODO.md` §2 "side-by-side pi ↔ autocode smoke test" replaced by artifact citation
- [ ] Codex APPROVE on the implementation before any commit decision

### Proposed Research + Design Work (Pre-Implementation)

1. Survey the 4 capture-tool candidates against one scenario
   (autocode startup) and record: fidelity score, setup cost,
   per-capture latency, portability, license.
2. Write per-TUI launch scripts as standalone executables that take
   a scenario name + prompt and produce a predictable output file.
3. Define the scenario schema: what does "capture startup" mean
   across 7 different TUIs? Needs a canonical input set.
4. Prototype against autocode + pi (both already wired) before
   extending to claude-code / opencode / codex / aider / goose.

### Implementation Checklist (SUPERSEDED)

> **[SUPERSEDED by Track 1 Phase 1 scope in Entry 1139 / the
> three-track architecture at the top of §1g.]** The list below
> reflects the pre-revision single-pipeline implementation plan.
> Authoritative Phase 1 deliverables: capture.py, dsr_responder.py,
> launchers/autocode.py, predicates.py (hard+soft classified),
> profile.py, scenarios/startup + scenarios/first-prompt-text, and
> `make tui-regression` CI target. See the top section's Track 1.

- [ ] design choices 1-8 closed in this section
- [ ] per-TUI launch script set committed under
      `autocode/tests/tui-comparison/launchers/`
- [ ] capture layer committed under
      `autocode/tests/tui-comparison/capture.py` (or extends
      `autocode/tests/vhs/capture.py`)
- [ ] scenario library under
      `autocode/tests/tui-comparison/scenarios/`
- [ ] analysis layer (rule-based + LLM narrator) under
      `autocode/tests/tui-comparison/analyze.py`
- [ ] one stored comparison run artifact under
      `autocode/docs/qa/tui-comparison/<date>-baseline/`

### Verification (SUPERSEDED)

> **[SUPERSEDED by "Exit Gates (revised per Codex 1138 Suggested
> Change #6)" at the top of §1g.]**

- Pipeline produces comparable captures for at least autocode + pi
  on the "startup" and "first prompt response" scenarios.
- Rule-based analyzer runs clean; LLM narrator produces a compact
  side-by-side description suitable for a comms entry.
- Nothing in `~/.pi/`, `~/.claude/`, `~/.autocode/` is mutated
  during a capture run.

### Exit Gates (SUPERSEDED — see top of §1g)

- [ ] all 8 open design questions answered in this section
- [ ] working prototype on autocode + pi
- [ ] stored artifacts under `autocode/docs/qa/tui-comparison/`
- [ ] `DEFERRED_PENDING_TODO.md` §2 entry for "Side-by-side pi ↔
      autocode smoke test" removed and replaced by an artifact
      citation
- [ ] Codex review verdict on the design (post review request once
      design questions 1-8 are closed)

---

## 2. Native External-Harness Orchestration

### Goal

Let AutoCode orchestrate Codex, Claude Code, OpenCode, and Forge while those tools keep using their own native harnesses.

### Principle

AutoCode is the control plane. External harnesses are worker runtimes.

### 2.1 Event Normalization

#### Goal

Normalize all external harnesses into AutoCode’s event model.

#### Event Types To Support

- session started/resumed
- prompt sent
- tool call started/finished
- approval requested/granted/denied
- message emitted
- task completed/failed
- artifact emitted
- interrupt/shutdown

#### Likely Files

- `autocode/src/autocode/external/event_normalizer.py`
- `autocode/src/autocode/external/harness_adapter.py`
- `autocode/src/autocode/agent/events.py`

#### Verification

- all first-wave adapters emit canonical events
- event consumers do not need harness-specific branching for common flows

### 2.2 First Real Adapters

#### Goal

Move from adapter contract + research into real integrations.

#### Order

1. Codex
2. Claude Code
3. OpenCode
4. Forge

#### For Each Adapter

Implement:

- launch
- prompt input
- structured output capture
- resume/continue/fork if supported
- permission/sandbox shaping
- artifact capture
- failure classification

#### Verification

- targeted contract tests
- one real smoke per adapter
- transcript/artifact capture proof

### 2.3 Worktree and Session Isolation

#### Goal

Run external harnesses in isolated worktrees/sessions where appropriate.

#### Verification

- no shared-workspace corruption
- artifacts clearly tied to worktree/session id

---

## 3. Terminal-Bench / Harness Engineering

### Goal

Move B30 beyond baseline Harbor recovery into strategy-quality improvement.

### Calibration Pair

- `break-filter-js-from-html`
- `build-cython-ext`

### 3.1 Strategy Overlays

#### Goal

Teach the Harbor path to behave differently by task family.

#### Families

- HTML/output cleanup
- Python/Cython build tasks

### 3.2 Verifier-Aware Retry Behavior

#### Goal

Require the agent to use failing output/verifier signal before repeating build or rewrite cycles.

### 3.3 Stronger Stagnation Detection

#### Goal

Catch repeated build/install/test cycles with no meaningful progress.

### 3.4 Re-Measure Before Broadening

#### Goal

Improve the 2-task subset before making broader B30 claims.

---

## 4. Research Corpus Maintenance

### Goal

Keep `research-components/` explicit and reproducible.

### Rules

- clone public references only
- update `research-components/MANIFEST.md` when adding repos
- keep them isolated from product/runtime dependencies

### Recent Additions

- `nodepad`

---

## 5. Documentation Discipline

### Goal

Keep the live docs coherent while this frontier evolves.

### Files That Must Stay Synced

- `EXECUTION_CHECKLIST.md`
- `current_directives.md`
- `PLAN.md`
- `docs/session-onramp.md`

### Rule

If implementation or research changes the true next step, update these in the same session.
