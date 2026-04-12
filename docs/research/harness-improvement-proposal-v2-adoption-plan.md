# Harness Improvement Proposal v2 — Adoption Plan

> Date: 2026-04-08
> Source proposal: `harness-improvement-proposal-v2-2026-04-08.md`
> Goal: decide which ideas from the proposal should be adopted in AutoCode now, which should be deferred, and which should be reframed to fit the current architecture.

## 1. Bottom Line

Yes, the proposal is usable here, but only as a **selective adoption plan**.

It should **not** be treated as a new parallel harness architecture.

The right move is:

1. keep AutoCode’s current control-plane direction
2. absorb the durable harness patterns that improve context control and execution quality
3. avoid introducing a second competing file/layout/runtime model beside the current one

The proposal is strongest when read as:

- a pattern library for memory/context/tool/runtime design
- a set of guardrails for external harness integration
- a reminder that the harness is a control system, not just “a model with tools”

It is weakest when read as:

- a mandate to add a new `.harness/` filesystem structure immediately
- a reason to duplicate existing AutoCode docs/rules/memory files
- a reason to build “enterprise policy” layers before the local-first core is fully stabilized

## 2. Research Basis

This adoption plan is based on:

- local proposal review:
  - [harness-improvement-proposal-v2-2026-04-08.md](/home/bs01763/projects/ai/lowrescoder/harness-improvement-proposal-v2-2026-04-08.md)
- existing local research:
  - [autocode-internal-first-orchestration.md](/home/bs01763/projects/ai/lowrescoder/docs/research/autocode-internal-first-orchestration.md)
  - [large-codebase-comprehension-and-external-harness-orchestration.md](/home/bs01763/projects/ai/lowrescoder/docs/research/large-codebase-comprehension-and-external-harness-orchestration.md)
  - [external-harness-adapter-command-matrix.md](/home/bs01763/projects/ai/lowrescoder/docs/research/external-harness-adapter-command-matrix.md)
- official/public references:
  - Anthropic context management: https://www.anthropic.com/news/context-management
  - Vercel `bash-tool` / `just-bash` direction: https://vercel.com/changelog/introducing-bash-tool-for-filesystem-based-context-retrieval/
  - Vercel Agent docs: https://vercel.com/docs/agent
  - Claude Code docs already cited in the internal-first research

## 3. What Already Exists in AutoCode

The proposal overlaps heavily with work that is already partially or fully present:

- structured carry-forward memory
- deferred tool loading / `tool_search`
- working-set-biased retrieval
- research mode
- orchestrator substrate
- policy context / approvals / delegation substrate
- event normalization and external adapter contract
- artifact collection and verification wiring

So the right framing is not “adopt the proposal from zero.”

It is:

- formalize what is already half-landed
- fill the highest-value gaps
- avoid duplicating concepts under a new naming scheme

## 4. Adopt Now

These are the highest-value items to adopt immediately.

### 4.1 Four-plane context model, in AutoCode terms

The proposal’s strongest idea is the **four-plane context system**:

- durable instructions
- durable project memory
- live session plane
- ephemeral scratch plane

AutoCode should adopt this concept, but **not** by creating a mandatory new `.harness/` tree yet.

Instead, map it onto the current system:

- durable instructions:
  - `AGENTS.md`
  - repo rules
  - current directives / policy docs
- durable memory:
  - structured memory artifacts and indexed summaries
- live session:
  - current loop/orchestrator state
  - carry-forward summaries
  - task board / mailbox / approvals
- ephemeral scratch:
  - research mode
  - transient retrieval output
  - subagent exploration notes that should not pollute the parent context

Immediate implementation value:

- compaction becomes rules-based instead of ad hoc
- state survives context pressure more intentionally
- external harness orchestration gets a clean separation between durable policy and transient transcript noise

### 4.2 Memory write policy

The proposal is right that “memory exists” is not enough.

AutoCode needs an explicit write policy:

- who can write durable memory
- what qualifies as durable memory
- what gets indexed vs summarized vs dropped
- what is session-only

This should become a small design doc plus enforcement rules in the memory/consolidation path.

### 4.3 Runtime state normalization

The proposal’s runtime-state list is correct and useful:

- permission mode
- session/task id
- branch/worktree
- recently accessed files
- cost/budget counters
- active plan/todo
- checkpoint stack
- last compact summary
- subagent registry
- pending approvals

AutoCode already has parts of this spread across loop/frontend/session/orchestrator state.

This should be normalized into one canonical runtime-state shape before deeper external orchestration work.

### 4.4 Tool metadata expansion

The proposal is right that every tool should carry more than input/output shape.

Useful additions:

- mutates_fs
- destructive
- concurrency safety
- interruptability
- output budget hints
- direct-call vs orchestrated/programmatic-call eligibility

This is immediately actionable and improves:

- scheduling
- compaction
- verification policy
- external adapter behavior

### 4.5 Artifact-first resumability

The proposal’s artifact emphasis aligns with Anthropic’s context-management guidance.

AutoCode should strengthen intentional resumability through durable artifacts:

- checkpoint metadata
- compact summaries
- plan/todo exports
- artifact manifests
- handoff notes
- structured “session resume packet” data

This is more valuable than trying to keep ever-larger raw transcripts alive.

## 5. Adopt Later

These are good ideas, but they should follow the current frontier rather than cut in front of it.

### 5.1 Subagent isolation hardening

This is valuable, but should follow:

- canonical runtime state
- memory write policy
- event normalization

Otherwise isolation rules will be bolted onto unstable semantics.

### 5.2 Programmatic tool calling for complex workflows

This is useful for:

- external harness integration
- data-heavy workflows
- multi-step benchmark/eval procedures

But it should come after:

- tool metadata expansion
- event normalization
- policy normalization

Otherwise AutoCode will gain power without a stable policy envelope.

### 5.3 Split execution model

The proposal’s split execution idea is directionally correct:

- real shell/container
- bounded virtual shell / safe exploration
- typed orchestration layer

But the repo already has overlapping execution layers.

So this should be treated as a clarification/refactor pass, not a brand-new runtime stack.

## 6. Do Not Adopt Literally

### 6.1 Mandatory `.harness/` repo layout

This is the clearest thing to reject for now.

Why:

- it duplicates existing policy/docs structures
- it risks splitting source-of-truth between current docs and new harness files
- it adds migration churn without solving the highest-value gaps first

If a file-based instruction/memory tree is adopted later, it should be introduced deliberately and minimally, with clear ownership and migration rules.

### 6.2 “Enterprise-ready managed policy hooks” as a current priority

Too early.

The local-first core still benefits more from:

- memory policy
- event normalization
- runtime state cleanup
- large-repo validation
- external adapter integration quality

Enterprise policy should remain a later concern.

### 6.3 Leak-shaped implementation mimicry

The proposal itself warns against this, and that warning is correct.

Use only durable public patterns:

- compaction
- policy envelopes
- artifact-first resumability
- context-plane separation
- retrieval-first large-repo handling

## 7. Recommended Execution Order

### Step 1. Formalize context planes

Write a design doc that maps:

- durable instructions
- durable memory
- live session state
- ephemeral scratch

onto the existing AutoCode modules.

### Step 2. Define memory write rules

Add one explicit policy doc for:

- durable memory writes
- session-only state
- compaction preservation
- subagent handoff summarization

### Step 3. Expand tool metadata

Add the missing scheduling/policy/compaction metadata to the tool system.

### Step 4. Normalize runtime state

Create one canonical runtime-state shape and make loop/orchestrator/frontends converge on it.

### Step 5. Improve resume artifacts

Define the minimal durable artifact set required for long-running and resumed work.

### Step 6. Only then deepen external harness orchestration

Once the internal state/memory model is cleaner:

- normalize external harness events into the same model
- let external runtimes attach transcripts/artifacts into AutoCode’s control plane

## 8. Discussion Items That Need Team Agreement

These are the points that should be discussed before implementation broadens.

### D1. Should AutoCode introduce a dedicated file-based instruction/memory tree?

Options:

- no, keep using current docs and memory artifacts
- yes, but only as a thin compatibility layer
- yes, as a future migration after ownership rules are defined

Recommendation:

- **not now**

### D2. What qualifies as durable memory?

This needs an explicit answer.

Examples that probably should be durable:

- repo-specific gotchas
- stable command recipes
- architecture decisions
- recurring benchmark quirks

Examples that probably should not:

- raw tool output
- transient exploration notes
- one-off dead ends

### D3. Where should subagent findings land?

Options:

- parent transcript only
- structured handoff summary only
- both

Recommendation:

- parent gets the structured summary by default
- raw detail stays in child artifacts unless explicitly pulled in

### D4. Should tool metadata become a compatibility contract for external harness adapters?

Recommendation:

- **yes**

This is one of the cleanest ways to make internal and external runtimes convergent without making them identical.

### D5. Should AutoCode prioritize runtime-state normalization before adding more adapter features?

Recommendation:

- **yes**

Without this, each adapter will invent its own shadow state and the control plane will drift.

## 9. Practical Conclusion

Use the proposal, but use it selectively.

The meaningful next move is:

1. adopt the context-plane model in AutoCode-native terms
2. define memory write/preservation rules
3. normalize runtime state
4. expand tool metadata
5. improve artifact-first resumability
6. then continue external harness orchestration

That sequence gives real product value and avoids introducing a second architecture beside the one already landed.
