# Starter Prompt — Build a Coding Harness That Stands Out Beyond Claude Code and Codex

## Purpose

Use this document as the **starter prompt / project brief** for a new conversation whose goal is to design and implement a coding-agent harness that clearly stands out against vanilla Claude Code and Codex CLI on:

- terminal productivity
- long-horizon task reliability
- user friendliness
- cost efficiency
- benchmark performance
- practical safety and recoverability

This brief is based on prior research comparing **Claude Code**, **Codex CLI**, **ForgeCode**, **OpenCode**, and **Terminal-Bench / Harbor**.

---

## Core thesis

We do **not** need to rebuild Claude Code or Codex from scratch.

We should instead build a layered harness around them:

1. **Skills** for workflow and task decomposition
2. **Hooks / policies** for deterministic enforcement
3. **Minimal external tools** for verification, rollback, search, and evidence capture
4. **Optional MCP / indexing sidecars** only after Phase 1 works
5. **Role separation** so planning, building, and review are distinct

The main insight is:

> Skills alone improve behavior, but the real competitive gains come from enforcement, tooling, retrieval, and recovery.

ForgeCode’s documented edge comes from runtime-level mechanisms like semantic sync, `sem_search`, tool-call guardrails, and skill/runtime steering. OpenCode’s edge comes from good mode separation, automatic formatting, permissions, snapshots/undo, and strong TUI ergonomics. Claude Code and Codex already expose enough extension primitives to emulate many of these strengths if we build the right operating layer around them.

---

## What already exists in Claude Code and Codex

### Claude Code already has

- `SKILL.md` skills with YAML frontmatter
- hooks across many lifecycle events
- plugins that can bundle skills, agents, hooks, MCP, LSP, and plugin-local binaries
- permissions and multiple operating modes
- checkpointing / rewind
- memory support
- headless mode
- subagents / forked context

### Codex already has

- `SKILL.md` skills
- plugins
- MCP support
- sandboxing and approvals
- rules / policy files
- hooks, though narrower and still less capable than Claude’s
- non-interactive `codex exec`
- subagents
- session resume and slash commands

### Important competitive reality

The goal is **not** to clone ForgeCode/OpenCode literally.

The goal is to reproduce the practical advantages users feel:

- better trajectory control
- fewer hallucinated completions
- less wasted context
- safer edits
- easy rollback
- better repo navigation
- cleaner UX in long terminal sessions
- better outcome rate on task benchmarks

---

## Product goal

Design a harness that can:

- sit on top of Claude Code first, then Codex second
- outperform “raw” host behavior on realistic coding tasks
- improve user confidence through visible evidence and recovery mechanisms
- remain cheap enough for daily use
- be benchmark-friendly without becoming benchmark-only

This harness should be useful for:

- real product engineering
- long-running code tasks
- bug fixing
- refactors
- CI failures
- structured benchmark runs such as Terminal-Bench style tasks

---

## Constraints

### Hard constraints

- Phase 1 must stay small
- no massive embeddings/indexing system in Phase 1
- no attempt to fully reimplement ForgeCode Services
- no attempt to build a whole IDE
- no overfitting to benchmark hacks
- minimal operational complexity for first adoption

### Soft constraints

- prefer Claude Code as primary host in Phase 1
- support Codex second where practical
- keep portability in mind, but do not let portability dominate the roadmap
- design for Linux / terminal-first usage
- avoid expensive always-on infrastructure unless it proves ROI

---

## What we want to build

## Phase 1 target

Build a small but powerful harness kit with the following:

### 1. Three core skills only

Do **not** build a huge skill library initially.

Ship only:

- `plan-first`
- `build-verified`
- `review-and-close`

Each skill must be:

- short
- high-signal
- activation-oriented
- explicit about inputs, outputs, and stop conditions
- backed by tooling and hooks instead of relying on prompt obedience

### 2. Two mandatory enforcement hooks

#### Stop-time verification gate

Before the agent can mark a task complete, it must produce a machine-readable evidence bundle showing that verification passed.

This should block premature completion.

#### Pre-tool-use guard

For Claude:
- validate dangerous commands
- optionally rewrite almost-correct tool input when safe

For Codex:
- block dangerous bash commands
- return corrective guidance
- rely on sandbox + rules for deeper safety

### 3. Verification wrapper

Create a portable verification layer, for example:

- `tools/verify/verify.sh`
- `tools/verify/verify.json`

The repo defines its own commands in config.

The wrapper should:

- run format / lint / typecheck / tests as configured
- collect exit codes and summaries
- emit `verify.json`
- produce a readable summary for the user

Key rule:

> Bring your own commands first. Auto-detection is Phase 2.

### 4. Rollback / checkpoint safety net

Use Git-based rollback in a host-agnostic way.

Examples:

- worktree-based checkpoint
- stash-based fallback
- diff artifact capture
- restore command

Important:

Claude checkpointing is useful, but Bash-made edits are not fully covered. So external rollback is still needed.

### 5. Minimal repo search helper

Do **not** start with embeddings.

Phase 1 search should be:

- `rg`
- optional `ctags`
- maybe tree-sitter later
- a small `symfind` script for symbol / entrypoint discovery

Goal:

- better codebase traversal
- faster entrypoint location
- lower context waste

### 6. Role separation

Keep roles small and practical:

- **Plan** — read/search only, no edits
- **Build** — edits + commands + verification requirement
- **Review** — diff + evidence review, risk summary, go/no-go

Do not build 6-agent orchestration initially.

### 7. Artifact and evidence system

Every serious task should write:

- commands run
- diff / changed files
- verification result
- short risk summary
- next-step or handoff summary

The harness must make progress visible.

---

## What not to build in Phase 1

Do not build these first:

- embeddings-based semantic retrieval
- freshness-aware index ranking
- automatic command discovery across arbitrary ecosystems
- full plugin marketplace
- rich TUI dashboard
- full multi-host abstraction for every agent system
- six-role orchestration fabric
- expensive background services

These are Phase 2 or later.

---

## Why this can stand out

A strong harness will stand out if it combines the following better than the defaults:

### Reliability

- agents cannot “declare success” without evidence
- repeated failure loops are detected
- edits are recoverable
- risky commands are intercepted early

### UX

- visible progress artifacts
- clear handoffs
- consistent task lifecycle
- easy rollback
- minimal setup once installed

### Cost

- short skills
- focused reads
- evidence-first workflow
- cheaper subagent roles when possible
- avoid large index infrastructure until proven useful

### Benchmark friendliness

- structured plan → build → verify → review flow
- artifact-driven completion criteria
- repeatable headless execution
- fewer false finishes
- safer long-horizon execution

---

## Research-backed design priorities

Prioritize in this order:

1. **Verification gating**
2. **Rollback**
3. **Role separation**
4. **Minimal search helper**
5. **Portable skill pack**
6. **Hook-driven correction / blocking**
7. **Phase 2 retrieval sidecar**

Rationale:

- The biggest practical gap is not “better prompts,” it is runtime discipline.
- Forge-like strengths that matter most are verification, context steering, and reduced wasted motion.
- OpenCode-like strengths that matter most are mode separation, formatting, permissions, undo, and good UX defaults.
- Claude and Codex already provide enough primitives to recover much of this if we build narrowly and well.

---

## Initial architecture

```text
Host (Claude Code first, Codex second)
  ├─ Skills layer
  │   ├─ plan-first
  │   ├─ build-verified
  │   └─ review-and-close
  ├─ Hooks / policy layer
  │   ├─ stop gate
  │   └─ pre-tool guard
  ├─ Minimal tools
  │   ├─ verify.sh
  │   ├─ rollback scripts
  │   └─ symfind
  ├─ Artifacts
  │   ├─ verify.json
  │   ├─ commands.log
  │   ├─ diff.patch
  │   └─ risk.md
  └─ Optional Phase 2 MCP / retrieval layer
```

---

## Success criteria

The harness is successful if it does all of the following:

### For real users

- reduces manual babysitting
- gives clear confidence on whether a task is actually done
- makes it easy to resume or recover work
- improves repo navigation and change quality
- feels cleaner and more predictable than raw host behavior

### For technical evaluation

- fewer false-complete outcomes
- better pass rate on repeated internal task suites
- lower repeated-command loops
- lower wasted token/context usage for long tasks
- reproducible artifacts for each run

### For benchmark-style runs

- stable headless execution
- deterministic config and behavior
- evidence gating
- better completion quality on long tasks without hacks

---

## Exact ask for the next conversation

Use this brief to help design and implement the harness in a practical, skeptical, engineering-first way.

### What I want from you

1. Turn this brief into a concrete repo blueprint.
2. Propose the exact folder structure.
3. Draft the three Phase 1 skills.
4. Draft the Claude hooks and Codex hooks.
5. Draft the `verify.sh` design and `verify.json` schema.
6. Draft rollback scripts and artifact schema.
7. Propose the minimal `symfind` tool.
8. Show how to package this first for Claude Code, then adapt it for Codex.
9. Be critical about complexity, maintenance, and false optimism.
10. Keep Phase 1 small and shippable.

### Important guidance

- Do not over-engineer Phase 1.
- Prefer deterministic tooling over more prompting.
- Separate what can be done with skills from what needs hooks or tools.
- Make the UX good for terminal users.
- Optimize for real usefulness first, benchmarks second.
- Call out anything that sounds attractive but is not worth building yet.

---

## Output format requested from the next conversation

Please produce:

1. a concrete implementation plan
2. a repo layout
3. the actual starter files for Phase 1
4. a risk register
5. a minimal testing strategy
6. a benchmark-readiness checklist
7. a note on cost control and model selection

