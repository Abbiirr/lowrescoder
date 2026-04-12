# OpenCode & Competitor Coding Assistants — Research Notes

> Researched: 2026-02-17
> Sources: opencode.ai, aider.chat, docs.continue.dev, cline.bot, cursor.com

---

## 1. OpenCode (opencode.ai / sst/opencode)

**Overview**: Go TUI + JS HTTP server coding assistant (95K+ GitHub stars). Client/server architecture similar to AutoCode.

### Agent Hierarchy

**Primary Agents** (user-facing):
- **Build Agent**: Default. All tools enabled, full filesystem access. For development.
- **Plan Agent**: Read-only by default. Denies file edits. For analysis and planning.

**Subagents** (delegated):
- **Explore Agent**: Fast, read-only. Cannot modify files. For codebase exploration.
- **General Agent**: General-purpose with full tool access (except `todo`).

### Invocation
- By primary agents via **Task tool** (auto-delegation based on description)
- By user via **@mention** syntax (e.g., `@explore find all database queries`)

### Multi-Model Support
Each agent can specify its own model. Example config:
```json
{
  "agent": {
    "code-reviewer": {
      "model": "anthropic/claude-sonnet-4-5",
      "tools": { "write": false, "edit": false, "bash": true, "read": true }
    }
  }
}
```

### Tool Access Control
**Boolean registry** per agent + **permission levels** (ask/allow/deny):
- Permissions can be overridden per-agent with glob patterns
- Agent permissions merge with global config (agent rules take precedence)
- `permission.task` controls which subagents an agent can invoke

### Context Isolation
- Each subagent invocation creates a **new session with no memory**
- No continuity between @agent calls
- Results flow back via Task tool return value

### LSP Feedback Loop
After edits, LSP diagnostics feed back into LLM context. This grounds the LLM.

---

## 2. Cursor

### Background Agents (Cursor 2.0, October 2025)
- Autonomous agents in **isolated Ubuntu VMs** with internet access
- Work on separate git branches, can open PRs
- Up to **8 agents in parallel** on single prompt
- Each in isolated workspace using git worktrees

### Multi-Model
- Proprietary **Composer model** (RL-optimized, possibly MoE)
- Plan mode: one model plans, different model executes
- Most turns complete in <30 seconds

---

## 3. Roo Code / Cline

### Orchestrator Mode ("Boomerang Tasks")
Most sophisticated built-in multi-agent among VS Code extensions.

**Built-in Modes**: Code, Architect, Debug, Ask, Orchestrator

**Key design**: Orchestrator **intentionally cannot read files** — keeps context focused on orchestration. Subtasks handle detail, return concise summaries.

### Context Isolation
- Each subtask runs in **isolated context** with separate conversation history
- Parent orchestrator does NOT see execution details
- Only concise summaries flow back

---

## 4. Comparative Summary

| Feature | OpenCode | Aider | Continue | Cursor | Roo Code |
|---|---|---|---|---|---|
| Subagents | Yes | No | No | Background agents | Yes (Boomerang) |
| Multi-model | Per-agent config | Architect/Editor pair | Single model | Proprietary + split | Per-mode |
| Tool control | Boolean per-tool + perms | N/A (no tools) | Per-tool policy | Fixed | Per-mode |
| Context isolation | New session per subagent | Editor sees only architect output | Single context | Isolated git worktrees | Isolated per subtask |
| Task delegation | Task tool → child session | One-directional arch→edit | None | Parallel agents | Orchestrator → modes |

---

## 5. Key Patterns for AutoCode

1. **OpenCode is architecturally closest** — Go TUI + backend, per-agent tool config, separate sessions for subagents
2. **Aider's Architect/Editor maps to L3/L4** — reasoning model proposes, constrained model edits
3. **Roo Code's orchestrator isolation** — orchestrator can't read files, stays focused on coordination
4. **OpenCode's LSP feedback loop** — L1 diagnostics ground L4 reasoning (exactly our approach)
5. **All tools prevent recursive subagent spawning** — either remove Task tool from subagents or use permissions
