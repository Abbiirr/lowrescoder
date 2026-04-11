# Plan

Last updated: 2026-04-11
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

1. Section 1f: Claude Code Primary TUI Parity
2. Section 1: Large Codebase Comprehension
3. Section 2: Native External-Harness Orchestration
4. Section 3: Terminal-Bench / Harness Engineering
5. Section 5: Documentation Discipline
6. Section 4: Research Corpus Maintenance
7. Section 0: Harness Architecture Refinement From Proposal v2 as a landed foundation / policy reference

Current practical rule:

- treat Section 0 as landed foundation unless a new gap is discovered
- treat Section 1f as the current primary UX workstream
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

## 1f. Claude Code Primary TUI Parity

### Goal

Make AutoCode's primary full-screen terminal experience feel structurally and behaviorally close to Claude Code, while preserving AutoCode-specific features and avoiding drift toward a Pi-style multi-pane orchestrator dashboard.

### Research Basis

- `docs/design/claude-code-visual-parity.md`
- `docs/research/deep-research-report.md`
- `docs/qa/manual-ai-bug-testing-playbook.md`
- `research-components/claude-code/CHANGELOG.md`
- `autocode/cmd/autocode-tui/view.go`
- `autocode/cmd/autocode-tui/styles.go`
- `autocode/cmd/autocode-tui/statusbar.go`
- `autocode/cmd/autocode-tui/model.go`
- `autocode/cmd/autocode-tui/update.go`
- `autocode/cmd/autocode-tui/commands.go`
- `autocode/src/autocode/tui/commands.py`
- `autocode/src/autocode/gateway_auth.py`
- `autocode/src/autocode/agent/prompts.py`
- `autocode/src/autocode/agent/tools.py`
- existing `claude_like` rendering/tests under `autocode/src/autocode/inline/` and `autocode/src/autocode/tui/`

### Product Decision

- The parity target is the Claude Code terminal UX, not the Pi dashboard UX.
- First implementation target for this workstream: the primary full-screen TUI surface.
- Existing inline/Textual `claude_like` scaffolding is useful reference material, but it is not the completion gate for this workstream.
- Do not copy Claude Code code verbatim. Copy behavior and hierarchy.

### Current Worktree Status (2026-04-11)

Already landed in the active Go TUI worktree:
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

Still unfinished:
- compact approval prompt parity
- completion/scrollback consistency with the live tool-row presentation
- task-panel demotion when it creates dashboard noise
- narrow-terminal and truncation hardening
- focused Go TUI render/interaction coverage beyond the first-pass string updates
- manual smoke artifacts
- every manual sweep must produce a filled artifact from `docs/qa/manual-ai-bug-test-report-template.md`
- bare `/` command-discovery parity with the shared Python router
- cursorable slash-command menu: typing `/` should show the visible command list, Up/Down should move selection, and Enter should accept the highlighted command
- `/model` should support an on-screen model picker rather than requiring the user to manually type the target alias
- gateway-authenticated `/model` listing against `http://localhost:4000/v1`
- stronger provider visibility and explicit provider-switching UX
- prompt/tool-schema consistency around `list_files` vs the live callable tool surface
- manual AI behavior sweeps using `docs/qa/manual-ai-bug-testing-playbook.md`

### Codebase-Specific Findings (2026-04-11 audit)

- The local gateway at `http://localhost:4000/v1/models` is healthy:
  - unauthenticated probe returns `401`
  - authenticated probe using `Authorization: Bearer $LITELLM_API_KEY` returns `200` plus the live alias catalog
- AutoCode already has a shared auth helper in `autocode/src/autocode/gateway_auth.py`.
  - The active task is integration parity, not inventing a new gateway mechanism.
- The Python slash-command router already exposes `/provider` and `/model`.
  - `create_default_router()` in `autocode/src/autocode/tui/commands.py`
  - `knownCommands` in `autocode/cmd/autocode-tui/commands.go`
  - The active task is cross-surface parity plus bare-`/` discovery quality, not creating a missing command.
- The prompt still teaches `list_files`, while real runtime screenshots show sessions where the live callable surface is narrower and relies on `tool_search`.
  - Treat this as a typed tool-surface contract bug, not a generic “the model is confused” problem.
- Go-side validation is available on this machine.
  - `go version` works
  - `cd autocode/cmd/autocode-tui && go test ./...` now passes in the current tree
  - treat Go validation as an active completion gate, not as a blocked environment issue

Resume from the current Go TUI diff. Do not restart this workstream from a blank design pass.

### Target Behaviors To Match

- single-column, chat-first layout
- minimal branded header
- bottom status/footer as the primary live-status locus
- fixed-width braille/shimmer thinking spinner
- compact grouped tool-call rows with low visual clutter
- stable layout during streaming and tool execution
- narrow-terminal-safe footer/prompt rendering
- permission and approval prompts that read cleanly at terminal speed

### Explicit Non-Goals

- do not turn the TUI into a multi-pane admin/orchestrator console
- do not add new sidebars, project trees, or session grids in the first pass
- do not broaden into external-harness UI work before core Claude-style parity is stable

### 1f.1 Refresh the Parity Contract

#### Goal

Turn the existing parity spec into the actual source of truth for this implementation pass.

#### Implementation Steps

1. Reconcile the current spec with the latest Claude Code UI behavior signals from the local changelog.
2. Distinguish already-landed scaffolding from still-open parity gaps.
3. Rewrite the spec around concrete render states, not just token names.
4. Freeze the acceptance rubric before layout edits begin.

#### Required Render States

- fresh session / welcome
- idle prompt
- streaming answer
- visible thinking
- compact tool call success
- compact tool call failure
- approval prompt
- narrow-terminal footer
- background-task indicator when present

#### Verification

- updated spec exists
- each render state has a target description
- rubric uses `Match`, `Close`, `Different`

### 1f.2 Rebuild the Core Layout Contract

#### Goal

Keep the Claude-like visual contract while fixing the newly discovered interaction bugs that sit inside the same primary TUI surface.

#### Additional Bugfix Track (must run alongside layout work)

1. Slash-command discovery
   - bare `/` must expose the real command surface
   - Go TUI completion list must not drift from the Python router
   - bare `/` must open a cursorable command menu
   - Up/Down should move command selection
   - Enter should accept the highlighted command
2. Provider/model UX
   - `/model` must work against the authenticated local gateway
   - `/model` should open a model picker state when run without args, with arrow-key selection and Enter-to-apply
   - provider must be visible in the persistent status surface
   - `/provider` should exist if provider switching remains a first-class workflow
   - all gateway-backed model listing must reuse `build_gateway_headers()` instead of duplicating ad hoc header logic
   - provider/model control should remain typed first-class UI behavior, not shell fallback
3. Prompt/tool-surface consistency
   - if the prompt teaches `list_files`, the live callable tool surface must support that cleanly
   - otherwise the prompt must be narrowed to the actual core tool set and deferred-tool path
   - deferred-tool discovery via `tool_search` must be explicit when the core set is intentionally narrow
4. Live behavior QA
   - every parity pass must run the manual playbook:
     - `docs/qa/manual-ai-bug-testing-playbook.md`
   - run it against both `autocode chat` and `autocode ask` when slash/provider/tool-surface behavior changes

Move the primary TUI to the Claude-like visual hierarchy before polishing details.

#### Implementation Steps

1. Make the layout single-column and chat-first.
2. Treat the footer/status line as the main live-status surface.
3. Keep prompt framing minimal and stable.
4. Remove or demote visual elements that make the UI feel dashboard-like or overly busy.
5. Preserve existing working improvements rather than redoing them:
   - prompt
   - header
   - spinner
   - footer simplification
6. Add one explicit contract test tying the Go slash-command surface to the Python router surface so bare `/` cannot silently drift again.

#### Likely Files

- `autocode/cmd/autocode-tui/view.go`
- `autocode/cmd/autocode-tui/statusbar.go`
- `autocode/cmd/autocode-tui/styles.go`
- `autocode/cmd/autocode-tui/model.go`

#### Verification

- render snapshots prove the new hierarchy
- no regression in input, session picking, approval, or task-panel behavior

### 1f.3 High-Salience Interaction Parity

#### Goal

Match the parts users notice most immediately.

#### Must-Hit Areas

- thinking spinner and wording
- prompt/footer hierarchy
- compact tool rows
- success/failure markers
- approval prompt tone and shape

#### Implementation Steps

1. Replace any unstable or bulky thinking presentation with a fixed-width braille/shimmer pattern.
2. Compact tool output into one-line summaries by default.
3. Keep result summaries adjacent to the triggering tool row.
4. Make footer text readable but subdued.
5. Rewrite approvals into a Claude-like compact action prompt before broad polish work.
6. Make `handleDone()` reuse the same compact tool/result rendering contract as the live view.
7. Fix the current Go compile break before claiming parity progress:
   - `autocode/cmd/autocode-tui/model.go`
   - `spinner.Braille` is undefined for the currently pinned dependency version

#### Verification

- snapshot/string-contract tests cover all high-salience states
- streaming tests confirm low layout jitter

### 1f.4 Narrow-Terminal and Render-Stability Hardening

#### Goal

Make the Claude-like layout survive real terminal constraints.

#### Implementation Steps

1. Add explicit rendering rules for 80x24 and similar narrow layouts.
2. Ensure footer and prompt remain legible when width collapses.
3. Avoid spinner-induced width jitter.
4. Add truncation/ellipsis rules for long model names, file paths, and tool args.
5. Verify Unicode and wide-character safety.
6. Check whether the task panel should disappear or collapse in quiet chat-first states.

#### Verification

- narrow-width tests exist
- long-path and Unicode cases render without corruption
- status/footer no longer duplicates or wraps unpredictably

### 1f.5 Rollout and Default-Path Decision

#### Goal

Ship parity safely instead of declaring it done based on design similarity alone.

#### Implementation Steps

1. Keep parity behind `claude_like` until all gates pass.
2. Compare default vs `claude_like` on representative transcripts.
3. Only after the gates pass, decide whether `claude_like` should become the default profile.
4. Do not call this slice complete until:
   - Python focused tests are green
   - Go TUI tests/build are green on the actual module path
   - authenticated `/model` works against the live local gateway
   - bare `/` discovery, `/help`, `/provider`, and repo-local grounding all pass the manual playbook

#### Verification

- profile-gated rollout remains intact until approval
- switching profiles does not break commands, approvals, or status updates

### Completion Gates

Do not call this work complete until all of the following are true:

1. The parity spec is refreshed and reflects the live intended behavior.
2. The primary TUI passes focused render tests for:
   - welcome
   - idle prompt
   - thinking
   - streaming
   - tool success
   - tool failure
   - approval prompt
   - narrow terminal
3. Existing TUI tests remain green:
   - `view_test.go`
   - `statusbar_test.go`
   - `update_test.go`
   - `approval_test.go`
   - `commands_test.go`
   - `e2e_test.go`
4. Manual smoke is recorded for at least:
   - 80-column terminal
   - 120+ column terminal
   - long file path/tool argument case
   - visible thinking + streaming in the same turn
5. The result is reviewed against the rubric and every zone scores `Close` or better.
6. Only after the above, consider promoting `claude_like` from gated profile to default.

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
