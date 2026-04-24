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
4. `docs/tui-testing/tui-testing-strategy.md` and `docs/tests/pty-testing.md`

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

**Last updated:** 2026-04-23 (14-scene parity program active; HR-5 Phase A benchmark-latency close-out is recorded and `/cc` real-data binding is now the active next slice).
**Status:** Architecture APPROVED by Codex Entry 1141 + doc-polish
delta APPROVED by Codex Entry 1144. Phase 1 Track 1 substrate
implemented under `autocode/tests/tui-comparison/` with positive +
negative control tests green and end-to-end `make tui-regression`
target producing the 5 artifacts per scenario. Track 2 + Track 3
remain open for follow-up slices per the three-track architecture
below. Track 4 (reference-driven design-target ratchet against the
`tui-references/` mockup bundle) landed Slice 1 on 2026-04-18 with
Codex APPROVE via Entry 1197 — see §Track 4 below.

**Visual Parity Program (2026-04-21, active):** Durable 14-scene staged
execution plan approved Claude Entry 1298. Canonical documents:
- Phase A close-out plan: `docs/plan/hr5-phase-a-benchmark-latency-plan.md`
- Phase A close-out checklist: `docs/plan/hr5-phase-a-benchmark-latency-checklist.md`
- Execution plan: `docs/tui-testing/tui_implementation_plan.md`
- Working checklist: `docs/tui-testing/tui_implementation_todo.md`
- Baseline matrix: `autocode/docs/qa/test-results/20260421-175050-tui-14-scene-capture-matrix.md`
- Fidelity baseline: `autocode/docs/qa/test-results/20260421-172920-tui-reference-gap.md`
- First Stage 4 verification note: `autocode/docs/qa/test-results/20260421-235651-tui-stage4-fidelity-pass.md`

Stage order: 0 (fix `basic_turn_returns_to_usable_input` predicate) →
1 (promote `sessions`, `palette`, `plan`) → 2 (`restore`, `multi`,
`review`, `diff` — user design gate required) → 3 (`grep`,
`escalation`, `cc` — blocked on product features) → 4 (global fidelity
pass). Stages 0-3 are complete. Stage 4 remains open, but HR-5 Phase A
is now closed on the canary lane: the real-gateway Rust TUI PTY path
completed `B13-PROXY` through `--autocode-runner tui` without the
stretched stale-request workaround, recorded in
`docs/qa/test-results/20260423-040320-B13-PROXY-autocode.json` and
`docs/qa/test-results/20260423-100635-tui-benchmark-latency-verification.md`.
`/cc` real-data binding is now the active Phase B slice. The latest
runtime slice is
`autocode/docs/qa/test-results/20260422-114723-tui-runtime-gateway-pass.md`.

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

#### Track 4 — `tui-references` (design-target ratchet, added 2026-04-18)

- **Scope:** Deterministic, structural parity between the live Go TUI
  and the 14-scene mockup bundle under `tui-references/`. Distinct from
  Track 1 (which checks runtime *invariants*) and Track 2 (which
  captures *other* TUIs for visual comparison). Track 4 checks whether
  the live autocode TUI layout matches the product owner's design
  target on a per-scene basis.
- **Substrate:** `autocode/tests/tui-references/` — reuses the Track 1
  PTY capture driver, DSR responder, and pyte render helper; does not
  duplicate process-launch code.
- **Source of truth:** the HTML bundle
  `tui-references/AutoCode TUI _standalone_.html`. The JPG exports are
  human-readable artifacts only; the `<template id="t-<scene>">`
  subtrees are the contract. Extracted into `manifest.yaml` (14 scenes,
  4 populated: `ready`, `active`, `recovery`, `narrow`; 10 stubbed).
- **Contract:** structural predicates on a pyte Screen — HUD presence,
  composer presence, keybind footer, scene-specific markers (recovery
  action cards, narrow-layout fit, active-turn indicator),
  capture-sanity floor. No image metrics, no OCR, no content-anchor
  matching against demo values.
- **Xfail ratchet semantics:** every MVP test is
  `@pytest.mark.xfail(strict=True)`. Tests are expected to FAIL today
  because the UI does not yet render the design-target layout.
  `strict=True` turns any unexpected XPASS (= UI feature landed) into a
  suite failure, forcing the developer to remove the decorator and
  promote the scene to a hard regression gate. Each xfail reason names
  the concrete gap blocking promotion.
- **CI hook:** `make tui-references` runs the extractor + predicate
  unit tests (stdlib only, ~0.12s) plus the live PTY ratchet
  (~16s, all currently XFAIL). Green in CI because XFAIL counts as
  success under `strict=True`.
- **Slice status:**
  - **Slice 1 — LANDED 2026-04-18, APPROVED by Codex Entry 1197.**
    Files: `autocode/tests/tui-references/{__init__.py, extract_scenes.py,
    manifest.yaml, predicates.py, test_reference_scenes.py, README.md}` +
    `autocode/tests/unit/test_tui_reference_{extractor,predicates}.py`.
    43 unit tests + 4 live PTY xfail tests.
  - **Slice 2 — pending user authorization.** Scope: themed parallel
    renderer (Tokyo Night + vendored JetBrains Mono) under Track 4,
    side-by-side HTML artifact report per scene, region-SSIM as
    non-blocking reporting metric, mock-backend `__HALT_FAILURE__`
    trigger for the recovery scene. Adds `scikit-image` + `imagehash`
    dev-deps.
  - **Slice 3 (optional, later):** Headless Chromium + xterm.js
    live-side rendering for defensible pixel-level diff. Opt-in via
    `make tui-references-highfi`.
- **DoD for closing Track 4:** every MVP scene promoted out of xfail.
  That happens one scene at a time as the matching UI feature ships —
  HUD chip row closes `ready`, tool-chain panel + diff hunks close
  `active`, narrow-layout branch closes `narrow`, recovery action cards
  + halt trigger close `recovery`. Track 4 remains "open" until all
  four xfails are flipped off.
- **Review chain:** `AGENTS_CONVERSATION.MD` Entries 1182 → 1200.

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
   `docs/tui-testing/tui-testing-strategy.md` "Basic Chat Turn" requirement.
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


## 6. MVP Acceptance & Targets (absorbed from docs/plan.md)

### 6.1 Success Metrics

| Metric | Target | Verification |
|---|---|---|
| LLM call reduction | 60–80% vs naive approach | Instrumentation logging |
| Edit success rate (first attempt) | >40% | Aider polyglot benchmark subset |
| Edit success rate (with retry) | >75% | Aider polyglot benchmark subset |
| Simple query latency | <500 ms | Automated timing tests |
| Agentic task completion | >50% on custom test suite | Manual + automated |
| Memory usage (idle) | <2 GB RAM (stretch: <500 MB) | System monitoring |
| Memory usage (inference) | <8 GB VRAM | System monitoring |

### 6.2 MVP Acceptance Checklist

All 12 must pass for MVP release.

| # | Criterion | Pass Condition |
|---|---|---|
| 1 | CLI operational | `autocode chat`, `ask`, `edit`, `config`, `--help` all work |
| 2 | Local LLM integration | LLM Gateway streams responses with <2 s to first token |
| 3 | Edit success rate | >40% pass@1 on 50-task Aider benchmark subset |
| 4 | Edit with retry | >75% success after up to 3 retries |
| 5 | No data loss | 0 file corruptions across 100 edit operations |
| 6 | Rollback works | 100% of failed edits restore original file state |
| 7 | Layer 1 accuracy | 100% correct on deterministic query test suite (find refs, go-to-def, list symbols) |
| 8 | Search relevance | >60% precision@3 on custom retrieval test suite |
| 9 | Latency targets | Layer 1 <50 ms; hybrid search <200 ms; simple query <500 ms |
| 10 | Memory limits | Idle <2 GB RAM; inference <8 GB VRAM |
| 11 | Sandbox enforced | Blocked commands rejected; timeout kills long-running processes |
| 12 | Git safety | Every successful edit creates a commit; `/undo` reverts cleanly |

### 6.3 Sandbox Default Policy

Executable in §1f.3 "Permissions, Sandbox, And Hook Enforcement". Concrete baseline:

- **Allowed by default:** `pytest`, `python`, `pip`, `mvn`, `gradle`, `java`, `javac`, `git status`, `git diff`.
- **Blocked by default:** `rm -rf`, `sudo`, `curl`, `wget`, network commands.
- **Working directory:** restricted to project root.
- **Timeout:** 30 s default, 300 s max.
- **User override:** `~/.autocode/config.yaml` → `shell.allowed_commands`, `shell.blocked_commands`, `shell.allow_network`.

### 6.4 Observability Requirements

- Per-request logs: latency, tokens, model, retries.
- Debug log with full prompts and responses (local only, opt-in).

---

## 1h. Rust TUI Migration Program (ACTIVE)

> **Status (2026-04-19):** **ACTIVE** — all 12 decisions in §1h.1 locked by user (Entry 1220). Active implementation slice: **Rust-M1**. Go TUI frozen (maintenance-only). Source research: `deep-research-report (1).md` at repo root (treat as draft; §1h.2 corrections authoritative).
>
> **Scope in one sentence:** Replace the Go BubbleTea frontend (`autocode/cmd/autocode-tui/`, 13,102 LOC across ~30 files) with a Rust inline TUI binary that speaks the **existing** JSON-RPC protocol (`protocol.go`) over PTY to the **unchanged** Python backend at `autocode/src/autocode/backend/server.py`.

### 1h.0 Mission And Strategic Rationale

**Why migrate.** The Go BubbleTea frontend is a working foundation, but Rust delivers three concrete gains:
1. **Richer terminal control depth** — `crossterm` exposes raw-mode, cursor, synchronized-update, and bracketed-paste primitives that BubbleTea v2 abstracts away, making fine-grained rendering and future capability additions easier.
2. **Linux-first PTY with a Windows path later** — `portable-pty` gives us a credible route from Linux now to Windows ConPTY later, without tying the product to BubbleTea long-term.
3. **Smaller long-tail maintenance surface** — a pure-Rust binary with explicit PTY ownership eliminates the Go runtime, CGO concerns, and BubbleTea version-churn as the dependency surface shrinks to `Cargo.lock`.

Note: **inline-by-default mode is NOT a new Rust benefit**. The Go TUI already defaults to inline scrollback-preserving mode (`main.go:13-20`, `--altscreen` is opt-in). The Rust port preserves this behavior, it does not introduce it.

**What stays.**
- Python backend (`autocode/src/autocode/backend/server.py`, agent loop, session store, tool surface, hooks).
- JSON-RPC protocol as defined in `autocode/cmd/autocode-tui/protocol.go` — Rust must be semantically indistinguishable on the wire (same method, id, params/result, event order).
- Four-dimension TUI testing matrix (Track 1 runtime invariants · Track 4 design-target ratchet · VHS self-regression · PTY smoke) — all four retarget the Rust binary via `$AUTOCODE_TUI_BIN`.
- Artifact storage policy (`autocode/docs/qa/test-results/` + per-track subdirs).
- Agent communication protocol, commit policy, role defaults.

**What goes (at Rust-M11 cutover).**
- Go TUI: `autocode/cmd/autocode-tui/` deleted.
- Python `--inline` REPL fallback: `autocode/src/autocode/inline/app.py` + `renderer.py` + `completer.py` deleted.
- No coexistence period. No selector env var. One binary: `autocode-tui`.

### 1h.1 Pre-Implementation Decisions Required (BLOCKING)

No code is written until every item below is answered in writing by the user. These are recorded here for the review pass.

**All 12 decisions LOCKED 2026-04-19 (user, Entry 1220).**

| # | Decision | **Locked Answer** |
|---|---|---|
| a | Strategic go/no-go | **YES — migrate Go → Rust** |
| b | Crate stack — locked baseline | **`crossterm` + `ratatui` + `tokio` + `portable-pty` + `serde_json` + `anyhow` + `tracing`**. M1 spike candidates (not yet locked): `tui-textarea`, `tokio-util::LinesCodec` — see §1h.1 spike table |
| c | PTY vs plain pipe | **PTY via `portable-pty`** |
| d | Stable-V1 timing | **FREEZE** — §1f Go milestone C/D/E/F work stopped; gates absorbed into Rust milestones |
| e | Binary naming | **`autocode-tui`** — single name from day one; Go removed, no coexistence period |
| f | Inline vs alt-screen default | **INLINE by default**; `--altscreen` opt-in flag |
| g | Windows | **Linux only for v1; architecture keeps ConPTY path open for later** |
| h | Selection mechanism | **N/A** — one binary; no selector needed |
| i | Track 4 fidelity | **Permission to improve** — re-baseline xfail decorators at Rust cutover |
| j | Builder agent | **Flexible** — OpenCode or Claude per slice; user decides per milestone |
| k | Python `--inline` fallback | **DELETE** at cutover (git preserves history) |
| l | Research report | **DRAFT** — §1h.2 corrections are authoritative |

**Crate stack — locked baseline (M1+):**

| Layer | Crate | Rationale |
|---|---|---|
| Terminal I/O | `crossterm` | Cross-platform; async `EventStream` (requires `event-stream` feature); ratatui's default backend; ConPTY-capable. **Pin to ratatui's semver range** — mismatched versions create separate raw-mode state |
| Layout + widgets | `ratatui` | Frame/Widget tree; List, Paragraph, Block; used in gitui/bottom; 2–3× less render code vs raw |
| Async runtime | `tokio` | Industry standard; `spawn_blocking` for blocking PTY handles; `mpsc` channels for internal bus |
| PTY spawn | `portable-pty` | WezTerm's crate; blocking `try_clone_reader()`/`take_writer()` — wrap in `spawn_blocking`, not async |
| JSON codec | `serde` + `serde_json` | Standard; struct-per-message mirrors `protocol.go` |
| Errors | `anyhow` | Ergonomic; no perf overhead |
| Logging | `tracing` + `tracing-subscriber` (file only) | **Stdout is RPC channel** — accidental stdout log = protocol corruption |

**M1 spike candidates (prove in Rust-M1 before committing):**

| Crate | Risk | Spike question |
|---|---|---|
| `tui-textarea` | Default bindings collide: `Ctrl+K` (palette), `Ctrl+C` (cancel/steer), `Ctrl+J`, `Ctrl+U`, `Ctrl+R` | Can every key route through app reducer first with all crate defaults suppressed? |
| `tokio-util::LinesCodec` | Silently discards bytes after `max_length` violation until next newline | What is the max RPC message size? Set explicit cap or use manual line-split instead |

### 1h.2 Research Report Integration And Accuracy Audit

**Source of truth:** `deep-research-report (1).md` at repo root (357 lines; executive summary + 14 numbered sections).

**Verified claims (repo-ground-truth confirmed):**
- ✅ Go TUI source tree matches report §1 Table 1 (plus additional files the report omits: `backend_unix.go`, `backend_windows.go`, `detect.go`, `completion.go`, `markdown.go`, `spinnerverbs.go`, `styles.go`, `taskpanel.go`, `milestone_a_test.go`, `palette_test.go`).
- ✅ JSON-RPC message catalog in report §2 Table 2 matches `protocol.go` lines 1-180.
- ✅ `tests/pty/` layout matches report §9 expectations.
- ✅ `crossterm` + `portable-pty` + `serde_json` crate stack is sound per current crate docs.

**Corrections and omissions:**
- ⚠️ Report §1 cites `autocode/server.py`; actual path is `autocode/src/autocode/backend/server.py`.
- ⚠️ Report §2 Table 2 omits `CostUpdateParams` (notification `on_cost_update`, see `protocol.go:181-186`).
- ⚠️ Report §1 Table 1 lists `inline/app.py` + `renderer.py` as "will be replaced by Rust"; **actually** those files are flagged for deletion (memory `feedback_inline_is_shipping_frontend.md`). Migration deletes them, it does not port them.
- ⚠️ Report §8 migration steps ignore the existing 4-dimension testing matrix (Track 1/4, VHS, PTY smoke) — §1h.7 fills that gap.
- ⚠️ Report §6-7 frame "inline-by-default scrollback preservation" as a new Rust capability. **Incorrect** — the Go TUI already defaults to inline mode (`main.go:13-20`, `--altscreen` is opt-in since at least commit `b113adb`). Rust preserves this behavior; it does not introduce it.
- ⚠️ Report §11-12 assumes a coexistence period with `AUTOCODE_FRONTEND=rust|go` selector and a gradual rollout. **Rejected** — user decision: single binary `autocode-tui`, Go removed at M11 cutover, no coexistence period.
- ⚠️ Report §4 does not qualify `tui-textarea` as an unproven spike candidate. It has app-hostile default keybindings (`Ctrl+K`, `Ctrl+C`, `Ctrl+J`, `Ctrl+U`, `Ctrl+R`) that collide with app-owned controls. Treat as M1 spike, not locked foundation.
- ⚠️ Report §11 rollback plan does not account for Claude-Code-style settings (hooks, skills) landed in Slices 3-4 — §1h.9 preserves these via JSON-RPC contract, no Rust-side logic needed.
- ⚠️ Report §12 suggests a separate Git branch/repo; this plan keeps the Rust code in-tree under `autocode/rtui/` for monorepo continuity.

**Citations the report leaves unresolved (non-blocking, track for M1 spike):**
- Tokio vs async-std choice — both viable; tokio is stdlib-adjacent for most teams.
- Ratatui layering — whether we adopt ratatui's layout/widgets or stay closer to raw crossterm for rendering control (report implies raw).

### 1h.3 Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Rust TUI (autocode-tui)                   │
│                                                             │
│  ┌──────────────┐   ┌────────────┐   ┌──────────────────┐   │
│  │ Input Router │──▶│ State / FSM│──▶│ Render Pipeline  │   │
│  │ (crossterm)  │   │ (ReducerFn)│   │ (ratatui/direct) │   │
│  └──────┬───────┘   └─────┬──────┘   └────────┬─────────┘   │
│         │                 │                   │             │
│         ▼                 ▼                   ▼             │
│  ┌────────────────────────────────────────────────────┐     │
│  │              RPC Bus (tokio channels)              │     │
│  └────────┬───────────────────────────┬───────────────┘     │
│           │ outbound                  │ inbound             │
│           ▼                           ▼                     │
│  ┌────────────────┐           ┌────────────────┐            │
│  │ JSON-RPC Codec │           │ JSON-RPC Codec │            │
│  │   (encode)     │           │   (decode)     │            │
│  └────────┬───────┘           └────────▲───────┘            │
│           │                            │                    │
│           ▼                            │                    │
│  ┌───────────────────────────────────────────────────┐      │
│  │         PTY Channel (portable-pty master)         │      │
│  └─────────────────────┬─────────────────────────────┘      │
└────────────────────────┼────────────────────────────────────┘
                         │ framed JSON, 1 msg/line
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Python backend (UNCHANGED): autocode/backend/server.py     │
│  • agent loop  • session store  • tools  • hooks  • skills  │
└─────────────────────────────────────────────────────────────┘
```

**Key architectural invariants:**
1. **The RPC wire format is frozen.** Any Rust-side change that alters a field name, type, or ordering breaks Python. Conformance tests (§1h.7) enforce this.
2. **The Rust process owns stdin/stdout raw mode;** the Python child runs inside a PTY and produces JSON on its stdout.
3. **The state machine is a pure reducer** — `(State, Event) -> (State, Vec<Effect>)` — to make it testable without a terminal.
4. **Rendering is pull-based from state** — no render calls from inside the input router or RPC decoder.
5. **PTY resize events** propagate from the host terminal → Rust → PTY child.

### 1h.4 File And Module Inventory (Go → Rust Port Map)

Current Go TUI: 30 files, 13,102 LOC (measured 2026-04-18). Port map:

| Go source (LOC) | Rust target | Notes |
|---|---|---|
| `main.go` | `src/main.rs` | CLI flags, runtime init |
| `model.go` | `src/state/model.rs` | `AppState` struct, reducer entry |
| `view.go` (450) | `src/render/view.rs` | Ratatui widget tree or direct crossterm |
| `update.go` (913) | `src/event_loop.rs` + `src/state/reducer.rs` | Split: IO loop vs pure reducer |
| `commands.go` | `src/commands/mod.rs` + `src/commands/*.rs` | One slash-command per file |
| `composer.go` | `src/ui/composer.rs` | Multi-line input, Alt+Enter, history |
| `messages.go` | `src/rpc/msg.rs` | `tea.Msg` equivalent — internal event enum |
| `protocol.go` (187) | `src/rpc/protocol.rs` | `serde` structs, semantic/canonical wire parity |
| `backend.go` + `backend_unix.go` + `backend_windows.go` | `src/backend/mod.rs` + `src/backend/pty.rs` | `portable-pty` spawn/monitor |
| `approval.go` + `askuser.go` | `src/ui/prompts/approval.rs` + `src/ui/prompts/askuser.rs` | Blocking modal widgets |
| `history.go` | `src/history.rs` | Frecency scoring (port verbatim) |
| `statusbar.go` (123) | `src/ui/statusbar.rs` | Model · provider · mode · session · tokens · cost · bg |
| `styles.go` (114) | `src/ui/styles.rs` | Color palette (Tokyo Night per memory) |
| `spinnerverbs.go` (202) | `src/ui/spinner.rs` | 187 rotating verbs (literal port) |
| `detect.go` | `src/terminal_detect.rs` | Terminal capability probe |
| `completion.go` | `src/ui/completion.rs` | `@path` expansion + fuzzy match |
| `markdown.go` | `src/render/markdown.rs` | Inline code/bold/italic rendering |
| `taskpanel.go` | `src/ui/taskpanel.rs` | `on_tasks` visualization |
| `model_picker.go` (276) + `provider_picker.go` (185) + `session_picker.go` (162) | `src/ui/pickers/` | Arrow-key + type-to-filter (per memory `feedback_arrow_key_pickers.md`) |
| `milestone_a_test.go` (1109) | `tests/milestone_a/` | Runtime invariant harness — port test scenarios, not Go test framework |
| `*_test.go` (unit) | `tests/unit/` or `#[cfg(test)]` modules | Per-file; some consolidate |
| `palette_test.go` | `tests/palette/` | Ctrl+K palette scenarios |

**Not ported (deleted at cutover):**
- `autocode/src/autocode/inline/app.py` (+ `renderer.py`, `completer.py`, `__init__.py`) — Python REPL fallback.
- `autocode/src/autocode/tui/commands.py` if it exists purely for the inline path (verify before deletion).

**Retained (test harness, retargets at Rust binary):**
- `autocode/tests/pty/*.py` — retargets via `$AUTOCODE_TUI_BIN`.
- `autocode/tests/tui-comparison/` — retargets via `$AUTOCODE_TUI_BIN`.
- `autocode/tests/tui-references/` — retargets via `$AUTOCODE_TUI_BIN`; all 4 `strict=True` xfails re-evaluated at Rust cutover per §1h.1 Decision (i).
- `autocode/tests/vhs/` — retargets via `$AUTOCODE_TUI_BIN`.

### 1h.5 JSON-RPC Contract (Frozen, Verbatim)

**Notifications (Python → Rust).** Rust MUST accept without rejection.

| Method | Params | Source |
|---|---|---|
| `on_token` | `{text: string}` | `protocol.go:43-46` |
| `on_thinking` | `{text: string}` | `protocol.go:48-51` |
| `on_done` | `{tokens_in: int, tokens_out: int, cancelled?: bool, layer_used?: int}` | `protocol.go:53-59` |
| `on_tool_call` | `{name, status, result?, args?}` | `protocol.go:61-67` |
| `on_error` | `{message: string}` | `protocol.go:69-72` |
| `on_status` | `{model, provider, mode, session_id?}` | `protocol.go:74-80` |
| `on_tasks` | `{tasks: [...], subagents: [...]}` | `protocol.go:82-86` |
| `on_cost_update` | `{cost: string, tokens_in: int, tokens_out: int}` | `protocol.go:181-186` — **omitted in research report** |

**Requests (Python → Rust, ID set).** Rust MUST respond with matching ID.

| Method | Params | Response |
|---|---|---|
| `approval` | `{tool: string, args: string}` | `{approved: bool, session_approve?: bool}` |
| `ask_user` | `{question: string, options?: [string], allow_text?: bool}` | `{answer: string}` |

**Requests (Rust → Python, ID set).** Rust MUST await response.

| Method | Params | Result |
|---|---|---|
| `chat` | `{message, session_id?}` | ack |
| `cancel` | `{}` | ack |
| `command` | `{cmd}` | ack |
| `session.new` | `{title?}` | — |
| `session.list` | `{}` | `{sessions: [SessionInfo]}` |
| `session.resume` | `{session_id}` | `{session_id, title, error?}` |
| `session.fork` | `{session_id?}` | `{new_session_id}` |
| `config.set` | `{key, value}` | — |
| `steer` | `{message}` | ack |

**Framing invariants:**
- One JSON object per line, UTF-8, LF-terminated (not CRLF).
- `"jsonrpc": "2.0"` required on every message.
- Response has `id` set and `method` empty.
- Notification has `id` null and `method` set.
- Error responses use standard JSON-RPC `{"error": {code, message}}` shape.

**Conformance suite (§1h.7):** capture Go wire traffic → replay against Rust → **semantic/canonical parity check** (same method, id, params/result/error content, same event order). Raw byte-diff is advisory only — JSON field ordering across serializers is not meaningful. Any semantic divergence fails the gate.

### 1h.6 UI Feature Parity Checklist

Every visible behavior of the current Go TUI must be accounted for before cutover. If a feature is explicitly dropped, it gets a decision row in §1h.1.

- [ ] Composer multi-line input, Alt+Enter newline
- [ ] Frecency history with up/down recall
- [ ] `/` slash command router + typeahead
- [ ] Ctrl+K command palette
- [ ] Model picker (arrow keys + type-to-filter)
- [ ] Provider picker (arrow keys + type-to-filter)
- [ ] Session picker (arrow keys + type-to-filter)
- [ ] Streaming token display with sliding-window flush to scrollback
- [ ] Thinking-token display (dim/separate style)
- [ ] Tool call cards (`on_tool_call` status updates)
- [ ] Status bar: Model · Provider · Mode · Session · Tokens · Cost · bg tasks
- [ ] Spinner with 187 rotating verbs (literal verb list port from `spinnerverbs.go`)
- [ ] Approval modal (blocking, keyboard-accept-only)
- [ ] Ask-user modal (options + free-text)
- [ ] Ctrl+C first-press → steer-mode, second-press → cancel
- [ ] Ctrl+C third-press → hard exit (memory: two-press escape pattern for pickers)
- [ ] `/fork` → session fork with new session ID display
- [ ] `/plan` → plan mode toggle, status-bar indicator
- [ ] `/compact` → manual compaction trigger
- [ ] `/resume` / `/sessions` → picker flow
- [ ] `/model` / `/provider` → picker flow (per memory: MUST be arrow-key, not text dump)
- [ ] `/clear` → scrollback-aware clear
- [ ] `/exit` → graceful shutdown
- [ ] Ctrl+E → `$EDITOR` launch, re-read temp file as composer buffer
- [ ] `@path` file reference completion
- [ ] Markdown inline rendering (code, bold, italic, links)
- [ ] Task dashboard (`on_tasks` → panel)
- [ ] Followup queue (messages queued during streaming auto-send on `on_done`)
- [ ] Resize handling (propagate to PTY child)
- [ ] Inline mode (default; preserves scrollback)
- [ ] `--altscreen` flag (opt-in alt-screen mode)
- [ ] Queue semantics while streaming / tool-calling (no UI events dropped)
- [ ] Warning/error classification routing
- [ ] Unsolicited picker prevention (Track 1 invariant)
- [ ] Debug overlay (if Go TUI has one — verify)
- [ ] Bracketed paste support

### 1h.7 Testing Strategy Integration (Four Dimensions Preserved)

All four existing dimensions retarget the Rust binary via `$AUTOCODE_TUI_BIN`. No harness rewrites; only binary path changes.

| Dimension | Current path | Rust binary retargeting | New Rust-specific additions |
|---|---|---|---|
| **Track 1 — runtime invariants** | `autocode/cmd/autocode-tui/milestone_a_test.go` (Go, 1109 LOC, 62 scenarios) | Port scenarios to Rust `#[test]` fns under `tests/milestone_a/` | Same 62 scenarios; add Rust-only invariants (async task cancellation, tokio channel close-on-error) |
| **Track 4 — design-target ratchet** | `autocode/tests/tui-references/` (Python + live PTY) | `$AUTOCODE_TUI_BIN` → `autocode/rtui/target/release/autocode-tui` | Re-baseline `strict=True` xfails at cutover; document intentional design changes |
| **VHS self-regression** | `autocode/tests/vhs/` (pyte + Pillow) | `$AUTOCODE_TUI_BIN` retarget (already env-driven) | VHS baselines regenerated at cutover (user-gated per memory `feedback_vhs_rebaseline_user_gated.md`) |
| **PTY smoke** | `autocode/tests/pty/` (pty.fork + select + DSR responder) | `$AUTOCODE_TUI_BIN` retarget | Add new scenario: RPC conformance replay (§1h.5) |

**New Rust-native test layers:**
- `cargo test` — unit + integration.
- **JSON-RPC conformance harness** (new): capture Go wire traffic → replay → **semantic/canonical parity check** (same method, id, params/result/error content, same event order). Raw byte-diff is a secondary advisory fixture only — JSON field ordering across serializers is not meaningful. Harness lives at `autocode/rtui/tests/rpc-conformance/`.
- **Crossterm render-function tests** — pure state → render-string tests without a real terminal.
- **Tokio channel stress tests** — backpressure, dropped-message, close-on-error, PTY EOF handling.

**Evidence artifacts** continue to land at `autocode/docs/qa/test-results/<YYYYMMDD-HHMMSS>-<label>.md` per CLAUDE.md discipline.

### 1h.8 Migration Milestones (Rust-M1 → Rust-M10)

Each milestone has: **goal · dependencies · exit gate · stored artifact**. Do not start Milestone N+1 until Milestone N artifact is green.

#### Rust-M1 — Scaffolding, PTY launch, minimal RPC echo, spike validation
- **Goal:** `autocode-tui` Rust binary (at `autocode/rtui/`) spawns `autocode backend` via `portable-pty`, reads `on_status` line, prints it raw, exits on Ctrl+C. Also: **spike `tui-textarea` keybinding override** and **spike `tokio-util::LinesCodec` size policy** — verdict on whether both are promoted to locked stack or replaced.
- **Dependencies:** All §1h.1 decisions locked (done). Codex architecture APPROVE (Entry 1223 NEEDS_WORK resolved by this remediation — re-review gated).
- **Exit gate:** PTY artifact proves startup + status-line read + clean shutdown. `cargo build --release` green. Spike verdicts documented in ADR-001/002/003.
- **Artifact:** `autocode/docs/qa/test-results/<ts>-rust-m1-scaffold.md`.

#### Rust-M2 — JSON-RPC codec parity + conformance harness
- **Goal:** All 16 message types (8 notifications + 2 inbound requests + 9 outbound requests + `on_cost_update`) round-trip with **semantic/canonical parity** — same method, id, params/result/error content, and event order. Unit tests for every serde struct.
- **Dependencies:** Rust-M1.
- **Exit gate:** Conformance harness green (100+ Go wire trace replays pass semantic comparison; raw byte-diff advisory fixtures stored but not blocking). Unit tests for all 16 types.
- **Artifact:** `<ts>-rust-m2-rpc-conformance.md`.

#### Rust-M3 — Raw input loop + streaming display
- **Goal:** Raw-mode keyboard input; Enter sends `chat`; `on_token` renders with sliding-window flush; `on_done` commits to scrollback.
- **Dependencies:** Rust-M2.
- **Exit gate:** PTY smoke passes startup + "hi<Enter>" + streamed response + scrollback preservation scenario.
- **Artifact:** `<ts>-rust-m3-streaming.md`.

#### Rust-M4 — Composer (line editing, history, multi-line)
- **Goal:** Backspace, left/right, Alt+Enter newline, up/down history, frecency sort.
- **Dependencies:** Rust-M3.
- **Exit gate:** Composer unit tests + PTY scenario for multi-line entry and history recall.
- **Artifact:** `<ts>-rust-m4-composer.md`.

#### Rust-M5 — Status bar + spinner
- **Goal:** Status bar updates on `on_status` / `on_done` / `on_cost_update`; 187-verb rotating spinner on 100ms tick.
- **Dependencies:** Rust-M4.
- **Exit gate:** Track 4 `ready` + `active` scenes XPASS (or remain xfail with documented pixel-diff rationale).
- **Artifact:** `<ts>-rust-m5-statusbar.md`.

#### Rust-M6 — Slash command router + Ctrl+K palette
- **Goal:** `/clear /exit /fork /compact /plan /sessions /resume /model /provider /help` routed; Ctrl+K opens palette; typeahead filters.
- **Dependencies:** Rust-M5.
- **Exit gate:** Palette unit tests + PTY palette scenario green.
- **Artifact:** `<ts>-rust-m6-commands.md`.

#### Rust-M7 — Pickers (model / provider / session, arrow + filter)
- **Goal:** Three picker modals with arrow-key navigation AND type-to-filter (per memory). Two-stroke Escape. Ctrl+C always exits.
- **Dependencies:** Rust-M6.
- **Exit gate:** Per-picker unit tests mirror `model_picker_test.go` / `provider_picker_test.go` / `session_picker_test.go` structure; PTY picker scenario green; `pty_tui_bugfind.py` finds 0 picker-related bugs.
- **Artifact:** `<ts>-rust-m7-pickers.md`.

#### Rust-M8 — Approval / ask-user / steer / fork
- **Goal:** Approval modal blocks tool execution until answered; ask-user supports options + free-text; first Ctrl+C mid-stream → steer prompt; `/fork` exchanges `ForkSessionParams` → `ForkSessionResult`.
- **Dependencies:** Rust-M7.
- **Exit gate:** Backend-parity PTY smoke (`pty_smoke_backend_parity.py`) green; steer + fork scenarios green.
- **Artifact:** `<ts>-rust-m8-approval-steer-fork.md`.

#### Rust-M9 — Editor launch + plan mode + task panel + followup queue + markdown
- **Goal:** Ctrl+E suspends raw-mode, spawns `$EDITOR` on temp file, resumes with buffer contents; `/plan` toggles plan mode + status indicator; `on_tasks` renders task panel; followup queue sends on `on_done`; markdown inline rendering.
- **Dependencies:** Rust-M8.
- **Exit gate:** Full Track 4 scene suite (ready/active/narrow/recovery + 10 stubbed scenes newly populated); all VHS scenes green against rebaselined PNGs.
- **Artifact:** `<ts>-rust-m9-final-features.md`.

#### Rust-M10 — Linux release hardening + performance gate
- **Goal:** Linux release hardening complete. Redraw latency <50ms. Key-to-render <16ms. Windows remains post-v1.
- **Dependencies:** Rust-M9.
- **Exit gate:** Performance measurement artifact; Linux CI green; `docs/reference/rust-tui-architecture.md` + `docs/reference/rust-tui-rpc-contract.md` published.
- **Artifact:** `<ts>-rust-m10-release-gate.md`.

#### Rust-M11 — Cutover (remove Go TUI, remove Python inline)
- **Goal:** Delete `autocode/cmd/autocode-tui/`; delete `autocode/src/autocode/inline/`; update all docs to reflect Rust-only frontend. Binary is already named `autocode-tui` from M1.
- **Dependencies:** Rust-M10 green. Full 23-lane benchmark regression green with Rust frontend. User explicit sign-off.
- **Exit gate:** User-authored commit (per commit policy); release note published; no Go or Python inline references in non-archive docs.
- **Artifact:** `<ts>-rust-m11-cutover.md`.

### 1h.9 Build-And-Replace Strategy (No Coexistence)

**No coexistence period. No selector env var. One binary: `autocode-tui`.**

Per user decision: Go TUI is removed at Rust-M11 cutover. There is no extended period where both exist as alternatives. During development (M1–M10), Go TUI remains frozen (maintenance-only) but is still the production binary — the Rust binary is not shipped until M10 is green. At M11, Go is removed, Rust is the only binary.

**During development (Rust-M1 through Rust-M10):**
- Go TUI: `autocode/cmd/autocode-tui/` — frozen; maintenance-only (critical bugs only, no new features).
- Rust TUI: `autocode/rtui/` — in development; tested but not production default.
- No `AUTOCODE_FRONTEND` env var. Testers run the Rust binary directly via `$AUTOCODE_TUI_BIN`.
- `$AUTOCODE_TUI_BIN` is already how all 4 testing dimensions select the binary.

**At M11 cutover:**
- Go TUI deleted from repo.
- Python inline fallback deleted from repo.
- `autocode-tui` binary (Rust) is the only frontend.
- Git history preserves Go code if ever needed.

**If Rust-M1 through M9 reveal a blocking problem:**
- The fix is to address the blocking problem, not to restore coexistence.
- Go TUI is still frozen — it does not receive new features to compensate.
- If the problem is fatal to the migration, the user decides whether to abandon §1h entirely and unfreeze Go, or continue with the fix.

**Schedule risk acknowledgment:** freezing Go C/D/E/F while Rust is speculative is a deliberate schedule bet. If Rust-M1/M2 slip materially, the project has stopped closing known Go gaps with no replacement ready. Accepted per user decision (d).

### 1h.10 Performance And Cross-Platform Requirements

| Target | Value | Measurement |
|---|---|---|
| First-token render latency | <50ms after `on_token` arrival | Timestamped log + PTY artifact |
| Keystroke-to-render | <16ms (1 frame @60Hz) | Synthetic key injection in conformance harness |
| Idle CPU | <1% on Linux | `top -p $(pidof autocode-tui)` sampling |
| Memory footprint | <50MB RSS | `/proc/self/status` sampling |
| Scrollback ring | Bounded to 10,000 lines | Ring buffer assertion in unit tests |
| Startup time | <200ms cold (excluding Python backend spawn) | `time autocode-tui --version` |

**Platforms:**
- **Linux:** xterm, Ghostty, kitty, alacritty, gnome-terminal, tmux. ← the supported v1 platform.
- **Windows:** post-v1 when ready; keep architecture ConPTY-capable but do not build toward it during §1h.

**CI matrix (GitHub Actions):**
- Linux x86_64 (required).
- Windows x86_64 (post-v1, added when Windows work begins).

### 1h.11 Risk Register

| ID | Severity | Risk | Mitigation |
|---|---|---|---|
| R1 | HIGH | PTY framing differences cause RPC deadlocks on Windows ConPTY | Post-v1 Windows; extensive conformance harness before enabling |
| R2 | HIGH | Rust ecosystem for complex TUI overlays (pickers, palette) less mature than BubbleTea | M7 picker slice has explicit spike budget; ratatui vendoring allowed if upstream blocks |
| R3 | MED | Async Rust + stdin/stdout blocking is a known footgun | Dedicated blocking I/O thread per stream; tokio channels for internal dispatch; decision recorded as ADR |
| R4 | MED | Pixel-for-pixel parity constraint freezes UX improvements | §1h.1 decision (i) defaults to permission-to-improve; Track 4 re-baseline at cutover |
| R5 | MED | Migration freezes Section 1f Milestones C/D/E/F | §1h.1 decision (d) + plan explicitly absorbs stable-v1 gates into Rust-M5 through Rust-M10 |
| R6 | MED | Contributor onboarding needs Rust toolchain | Document `rustup install stable`, `cargo build`, platform deps in `autocode/rtui/README.md` |
| R7 | LOW | Claude/Codex have less Rust-specific review context than Go | Reviewer-agent prompts updated with Rust idiom references; Codex-specific Rust checklist in `AGENT_COMMUNICATION_RULES.md` |
| R8 | LOW | Go TUI frozen while Rust is speculative — known gaps stay open | Accepted schedule bet per user decision (d); fatal Rust blocker = user decision on whether to abandon §1h |
| R9 | LOW | Binary size >10MB may surprise users | Strip + LTO + cargo config minimal-deps profile; document target in M10 |
| R10 | MED | `tui-textarea` default keybindings (`Ctrl+K`, `Ctrl+C`, `Ctrl+J`, `Ctrl+U`, `Ctrl+R`) collide with app-owned controls | M1 spike proves the crate can be used with all defaults suppressed; if not, hand-roll composer |
| R11 | MED | `crossterm` semver skew in dep graph (ratatui + direct crossterm dep) causes lost events or broken raw-mode restore | Pin crossterm to ratatui's required range from day one; no direct crossterm dep outside of what ratatui re-exports |

### 1h.12 Documentation Deliverables

Created/updated as part of the migration:

- `docs/reference/rust-tui-architecture.md` — architecture overview (lands in M1)
- `docs/reference/rust-tui-rpc-contract.md` — frozen JSON-RPC spec (lands in M2)
- `docs/decisions/ADR-001-rust-tui-migration.md` — decisions (a)–(l) recorded with rationale
- `docs/decisions/ADR-002-rust-async-runtime.md` — tokio vs async-std choice (M1 spike output)
- `docs/decisions/ADR-003-ratatui-vs-raw-crossterm.md` — layering choice (M1 spike output)
- `autocode/rtui/README.md` — build + run + contributor setup
- Update `docs/tui-testing/tui-testing-strategy.md` — Rust binary resolution path
- Update `autocode/tests/tui-comparison/README.md` — binary retargeting note
- Update `autocode/tests/tui-references/README.md` — Rust-cutover re-baseline policy
- Update `CLAUDE.md` + `AGENTS.md` — frontend language reference (at M11 cutover only, NOT before)
- Update `docs/session-onramp.md` — new contributor flow

### 1h.13 Ordered Build Sequence And Review Gates

The build sequence is strictly linear. Each step has a Codex/Claude reviewer gate before the next begins.

1. **User approves §1h.1 decisions (a)-(l) in writing** — this is the single unblocking event for ALL other work.
2. Rust-M1 spike → ADR-001/002/003 published → Codex review.
3. Rust-M2 conformance harness → Codex review (byte-parity is the highest-risk item).
4. Rust-M3 through Rust-M9 → per-milestone PTY artifact + Codex review.
5. Rust-M10 cross-platform + performance → Codex + user review.
6. Full 23-lane benchmark regression with Rust binary green.
7. Rust-M11 cutover → user-authored commit.

### 1h.14 Explicit Non-Goals For §1h

- Changing the JSON-RPC protocol (even additive changes are out of scope; they happen in a separate plan).
- Changing the Python backend surface.
- Retiring hooks, skills, or rules loader.
- Parity with non-autocode TUIs (claude-code / opencode / codex / aider) beyond the existing Track 4 research.
- Remote-client architecture (already §1f non-goal; §1h inherits).
- New agent behavior on the backend.

### 1h.15 Questions Blocking The Plan (Must Resolve Before Any Code)

Re-stated explicitly for the review pass:

1. (Decision a) Strategic go/no-go — **is this migration approved?**
2. (Decision d) Freeze 1f Milestones C/D/E/F at current Go state, or finish them on Go first?
3. (Decision g) Is Windows an MVP blocker or post-v1?
4. (Decision j) Who is the Builder agent?
5. (Decision k) Does Python `--inline` fallback die at cutover?

If the answer to (1) is no, this entire section becomes archive; §1f continues on Go as-is.
