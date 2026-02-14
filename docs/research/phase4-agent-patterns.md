# Phase 4 Agent Orchestration Research

> **Created:** 2026-02-14
> **Purpose:** Compiled research for Phase 4 decisions (Entry 314 CE)
> **Cross-reference:** `docs/plan/phase4-agent-orchestration.md` v3.2

---

## 1. Source List

### High Confidence (Official Docs)

| Source | Topic | Used For |
|--------|-------|----------|
| [Claude Code Docs — Tutorials](https://docs.claude.com/en/docs/claude-code/tutorials) | Plan mode, shift+tab think | Plan mode design (Entry 307 C1) |
| [Claude Code Docs — IDE Integrations](https://docs.claude.com/en/docs/claude-code/ide-integrations) | Plan mode with editing | Plan mode UX contract |
| [Claude Code Docs — Sub-agents](https://docs.claude.com/en/docs/claude-code/sub-agents) | Subagent spawning, isolation | SubagentLoop design (Entry 309 C4) |
| [Claude Code Docs — Checkpointing](https://docs.claude.com/en/docs/claude-code/checkpointing) | Checkpoint restore modes | CheckpointStore design (Entry 307 C5) |
| [OpenCode Agents Docs](https://opencode.ai/docs/agents/) | Primary/subagent roles, plan/build, permissions | Subagent types, plan mode, approval routing |
| [Python asyncio Docs — Locks](https://docs.python.org/3/library/asyncio-sync.html#lock) | Lock acquisition fairness | LLM Scheduler design (Entry 311 C2) |
| [Python graphlib Docs](https://docs.python.org/3/library/graphlib.html) | TopologicalSorter for DAG cycle detection | TaskStore cycle detection (Entry 307 C4) |
| [GitHub Task Lists](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/about-tasklists) | Markdown task list format | PlanArtifact format (Entry 307 C6) |

### Medium Confidence (Technical Deep Dives)

| Source | Topic | Used For |
|--------|-------|----------|
| [OpenCode Deep Dive (cefboud.com)](https://cefboud.com/posts/coding-agents-internals-opencode-deepdive/) | Agent internals, plan->build transition, task tool | Plan mode transition, subagent invocation |
| [claude-code-proxy (GitHub)](https://github.com/seifghazi/claude-code-proxy) | Request monitoring, conversation threading | Observability patterns (Entry 309 C7) |

### Low/Anecdotal Confidence

| Source | Topic | Used For |
|--------|-------|----------|
| [Reddit — Understanding Claude Code Subagents](https://www.reddit.com/r/ClaudeAI/comments/1lvy3q6/) | Subagent isolation, summary return | Mental model validation |
| [Reddit — OpenCode Agent Best Practices](https://www.reddit.com/r/opencodeCLI/comments/1oyp9bi/) | Custom agents, command files | Markdown-first agent config patterns |
| [OpenCode Issue #3374](https://github.com/anomalyco/opencode/issues/3374) | Auto vs manual subagent invocation | Delegation policy gaps |
| [OpenCode Issue #4252](https://github.com/anomalyco/opencode/issues/4252) | Approval hidden in subagent session | Approval routing UX (Entry 309 C1) |

---

## 2. Per-Topic Findings

### 2.1 Plan Mode

**Finding:** Claude Code implements Plan Mode as an explicit execution mode where the agent investigates and plans before making changes. Tools are restricted — no writes or shell commands until the user approves the plan.

**Direct implications for Phase 4:**
- Plan mode is a first-class `AgentMode.PLANNING` state (not just a subagent type)
- Entry/exit: `/plan on` → `/plan approve` (transition to NORMAL) → `/plan off`
- Tool restriction: capability-based (`mutates_fs`, `executes_shell` flags), not name-based

**OpenCode parallel:** OpenCode has a built-in `plan` primary agent that is permission-restricted for analysis-only work. The deep dive notes an explicit plan→build transition reminder.

### 2.2 LLM Scheduling Under Shared GPU

**Finding:** Python asyncio.Lock provides FIFO fairness among waiters, but does not support priority. When 3+ subagents contend with the foreground, the foreground can starve.

**Direct implications for Phase 4:**
- Replaced `asyncio.Lock` with `LLMScheduler` (PriorityQueue + single worker)
- Foreground requests (priority=0) always process before background (priority=1)
- FIFO within each priority tier via monotonic counter
- Eliminates the race condition in the original PriorityLock design (Entry 311 C2)

**Rejected alternative:** `asyncio.Condition` with manual waiter queues — more complex, same semantics achievable with PriorityQueue.

### 2.3 Subagent Isolation & Lifecycle

**Finding:** Both Claude Code and OpenCode implement subagents as isolated, stateless, one-shot tasks. They get a fresh context, run to completion, and return a structured summary. No resume, no interactive child sessions.

**Direct implications for Phase 4:**
- `SubagentLoop` is one-shot stateless (fresh context per invocation)
- Cannot spawn sub-subagents (flat hierarchy)
- Circuit breaker: 2 consecutive errors = auto-cancel
- Structured `SubagentResult` with `summary`, `files_touched`, `status`, `iterations_used`, `duration_ms`

**Rejected alternative:** Interactive child sessions (OpenCode-style navigation) — too complex for Phase 4 scope; would require session management refactor.

### 2.4 Subagent Approval Routing

**Finding:** OpenCode Issue #4252 documents a real UX problem: when a subagent needs approval, the main agent appears blocked with no visible indication. Users don't know to check the child session.

**Direct implications for Phase 4:**
- Background subagents auto-deny approval-requiring tools (no hidden blocking)
- Status bar shows "subagent waiting" only for foreground execute-type subagents
- Cancel propagation: cancelling main agent cancels all running subagents

### 2.5 DAG Cycle Detection

**Finding:** Python stdlib `graphlib.TopologicalSorter` can validate acyclicity. Building the full dependency graph and calling `prepare()` will raise `CycleError` if cycles exist.

**Direct implications for Phase 4:**
- `TaskStore.add_dependency()` builds full graph + proposed edge, then validates via `TopologicalSorter`
- Raises `ValueError("Cycle detected")` if invalid
- Mandatory — not optional (Entry 307 C4)

### 2.6 Checkpoint Restore Semantics

**Finding:** Claude Code checkpointing documents explicit restore modes and boundaries. Key insight: file system state is git's responsibility, not the checkpoint system's.

**Direct implications for Phase 4:**
- Restore is transactional (atomic commit/rollback on SQLite)
- Task state is fully rehydrated from snapshot
- Context summary injected as system message
- Conversation history preserved (not rolled back)
- Filesystem state NOT restored — user uses git for that

### 2.7 Markdown Plan Artifacts

**Finding:** Both Claude Code (`.claude/agents/*.md`) and OpenCode (`.opencode/agents/`) use markdown-based artifacts for agent configuration. GitHub task lists provide a robust format for human-readable progress tracking.

**Direct implications for Phase 4:**
- `.hybridcoder/plans/<session-id>.md` as canonical plan file
- GitHub-style task list format (checkboxes)
- Bidirectional sync: `/plan export` (TaskStore → markdown), `/plan sync` (markdown → TaskStore)

---

## 3. Accepted vs Rejected Alternatives

| Decision Point | Accepted | Rejected | Rationale |
|---------------|----------|----------|-----------|
| LLM serialization | PriorityQueue scheduler | asyncio.Lock / PriorityLock | Race-free, strict priority, metrics-ready |
| Plan mode gating | Capability flags | Tool name checks | Extensible, no maintenance burden on new tools |
| Subagent lifecycle | One-shot stateless | Interactive child sessions | Simpler, avoids session management complexity |
| Subagent approval | Auto-deny background | Bubble up to main UI | Prevents hidden blocking; Phase 5 can add navigation |
| Cycle detection | graphlib.TopologicalSorter | Manual DFS | stdlib, well-tested, clear error messages |
| Checkpoint restore | SQLite transaction | File-level snapshots | git handles files; we handle task/context state |
| Plan artifact format | GitHub task list markdown | Custom format / YAML | Human-readable, editor-friendly, familiar format |
| L3 routing | SIMPLE_EDIT → L3 | SIMPLE_EDIT → L2 | Matches types.py mapping; L2 is for search only |

---

## 4. Concern Cross-Reference

| Research Topic | Concerns Addressed |
|---------------|-------------------|
| Plan mode | 307-C1, 309-C3, 311-C3 |
| LLM scheduling | 307-C2, 311-C2 |
| Subagent isolation | 309-C4, 311-C7 |
| Approval routing | 309-C1, 311-C7 |
| Cycle detection | 307-C4 |
| Checkpoint restore | 307-C5, 311-C4 |
| Markdown artifacts | 307-C6, 309-C6, 311-C6, 312 |
| Observability | 309-C7 |
| L2/L3 routing | 311-C5, 318-C2, 326-B |
| Benchmark gates | 322-C1 through C5, 326-C/D |
