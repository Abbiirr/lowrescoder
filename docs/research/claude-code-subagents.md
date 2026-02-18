# Claude Code Subagent Architecture — Research Notes

> Researched: 2026-02-17
> Source: https://code.claude.com/docs/en/sub-agents, https://code.claude.com/docs/en/agent-teams

---

## 1. Subagent Concept

Subagents are specialized AI assistants that handle specific types of tasks. Each subagent runs in its **own context window** with a custom system prompt, specific tool access, and independent permissions. When Claude encounters a task that matches a subagent's description, it delegates to that subagent, which works independently and returns results.

Key benefits:
- **Preserve context** — exploration/implementation stays out of main conversation
- **Enforce constraints** — limit which tools a subagent can use
- **Reuse configurations** — across projects with user-level subagents
- **Specialize behavior** — focused system prompts for specific domains
- **Control costs** — route tasks to faster, cheaper models like Haiku

---

## 2. Built-in Subagent Types

### Explore
- **Model**: Haiku (fast, low-latency, cheapest)
- **Tools**: Read-only tools (denied Write and Edit)
- **Purpose**: File discovery, code search, codebase exploration
- **Thoroughness levels**: quick / medium / very thorough
- **Key insight**: Uses the cheapest model because exploration is read-only and doesn't need deep reasoning

### Plan
- **Model**: Inherits from main conversation
- **Tools**: Read-only tools (denied Write and Edit)
- **Purpose**: Codebase research during plan mode
- **Note**: Subagents cannot spawn other subagents (prevents infinite nesting)

### General-purpose
- **Model**: Inherits from main conversation
- **Tools**: All tools
- **Purpose**: Complex research, multi-step operations, code modifications

### Other built-in agents
| Agent | Model | When used |
|-------|-------|-----------|
| Bash | Inherits | Running terminal commands in separate context |
| statusline-setup | Sonnet | Configuring status line |
| Claude Code Guide | Haiku | Questions about Claude Code features |

---

## 3. Model Selection Strategy

Available model aliases: `sonnet`, `opus`, `haiku`, `inherit`

**Cost/Speed trade-offs:**
- **Haiku**: ~10-20x cheaper than Opus. Used for: search, testing, simple docs, exploration, FAQ
- **Sonnet**: Balanced performance. Used for: implementation, reviews, debugging
- **Opus**: Highest intelligence. Used for: critical security, architecture, complex reasoning

**Default behavior**: If `model` not specified, defaults to `inherit` (same model as main conversation)

**Key pattern**: Claude Code uses Haiku (cheapest) for the Explore agent because exploration is read-only and doesn't need deep reasoning. This is the core cost optimization — most subagent invocations are exploration, and those are 10-20x cheaper.

---

## 4. Subagent Configuration Format

Subagents are defined as **Markdown files with YAML frontmatter**:

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code...
```

### Configuration fields:
| Field | Required | Description |
|-------|----------|-------------|
| name | Yes | Unique identifier (lowercase + hyphens) |
| description | Yes | When Claude should delegate to this subagent |
| tools | No | Allowed tools (inherits all if omitted) |
| disallowedTools | No | Tools to deny |
| model | No | sonnet, opus, haiku, inherit |
| permissionMode | No | default, acceptEdits, delegate, dontAsk, bypassPermissions, plan |
| maxTurns | No | Max agentic turns before stopping |
| skills | No | Skills to preload into context |
| mcpServers | No | MCP servers available |
| hooks | No | Lifecycle hooks scoped to this subagent |
| memory | No | Persistent memory scope: user, project, local |

### Storage locations (priority order):
1. `--agents` CLI flag (session-only, highest priority)
2. `.claude/agents/` (project-level)
3. `~/.claude/agents/` (user-level)
4. Plugin's `agents/` directory (lowest priority)

---

## 5. Tool Access Control

Subagents can use any of Claude Code's internal tools. Control via:
- **tools** field (allowlist): `tools: Read, Grep, Glob, Bash`
- **disallowedTools** field (denylist): `disallowedTools: Write, Edit`

### Restricting which subagents can be spawned:
```yaml
name: coordinator
tools: Task(worker, researcher), Read, Bash
```
Only `worker` and `researcher` subagents can be spawned. Important: **Subagents cannot spawn other subagents** — only the main thread can.

---

## 6. Context Management

- Subagents receive only their system prompt + basic environment details (working directory)
- They do NOT get the full Claude Code system prompt or parent conversation history
- Each subagent runs in its own context window
- Results return to the main conversation as a summary
- Auto-compaction at ~95% capacity (configurable via CLAUDE_AUTOCOMPACT_PCT_OVERRIDE)

### Resume capability:
- Each invocation creates a fresh instance by default
- Can resume a previous subagent by agent ID (retains full conversation history)
- Transcripts stored at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`

---

## 7. Persistent Memory

Subagents can have persistent memory across sessions:

| Scope | Location | Use case |
|-------|----------|----------|
| user | `~/.claude/agent-memory/<name>/` | Cross-project learnings |
| project | `.claude/agent-memory/<name>/` | Project-specific (in VCS) |
| local | `.claude/agent-memory-local/<name>/` | Project-specific (not in VCS) |

When enabled:
- System prompt includes instructions for reading/writing to memory directory
- First 200 lines of `MEMORY.md` injected into system prompt
- Read, Write, Edit tools auto-enabled for memory management

---

## 8. Execution Modes

### Foreground (blocking)
- Blocks main conversation until complete
- Permission prompts pass through to user
- Clarifying questions (AskUserQuestion) pass through

### Background (concurrent)
- Runs while user continues working
- Permissions pre-approved before launch
- Auto-denies anything not pre-approved
- MCP tools NOT available in background
- Can resume in foreground if permissions failed

### Parallel execution:
- Multiple subagents can run simultaneously
- Independent tasks parallelized automatically
- Results aggregated back to main conversation

---

## 9. Hooks (Lifecycle Events)

Subagents support lifecycle hooks:

**In frontmatter:**
- PreToolUse (before tool use)
- PostToolUse (after tool use)
- Stop (when subagent finishes)

**In settings.json:**
- SubagentStart (when subagent begins)
- SubagentStop (when subagent completes)

---

## 10. Agent Teams (Experimental)

**Separate from subagents** — teams are multiple full Claude Code sessions coordinating.

### Architecture:
| Component | Role |
|-----------|------|
| Team lead | Main session, creates team, coordinates |
| Teammates | Separate Claude Code instances |
| Task list | Shared work items (pending → in_progress → completed) |
| Mailbox | Messaging system between agents |

### Key differences from subagents:
| | Subagents | Agent Teams |
|---|-----------|-------------|
| Context | Own window, results return to caller | Own window, fully independent |
| Communication | Report back to main only | Direct inter-agent messaging |
| Coordination | Main agent manages all | Shared task list, self-coordination |
| Best for | Focused tasks, result matters | Complex work needing collaboration |
| Token cost | Lower (summarized results) | Higher (each is separate instance) |

### Team features:
- **Delegate mode**: Lead restricted to coordination-only tools (Shift+Tab)
- **Display modes**: in-process (single terminal) or split-panes (tmux/iTerm2)
- **Task dependencies**: automatic unblocking when deps complete
- **File locking**: prevents race conditions on task claiming
- **Plan approval**: teammates can be required to plan before implementing
- **Quality gates**: TeammateIdle and TaskCompleted hooks

### Storage:
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`

### Limitations:
- No session resumption with in-process teammates
- One team per session
- No nested teams
- Lead is fixed (can't transfer leadership)
- Permissions set at spawn time

---

## 11. Key Patterns for HybridCoder

### Pattern 1: Tiered Model Routing
Use cheapest model for read-only exploration (our L1/L2), mid-tier for implementation (our L3), expensive for reasoning (our L4). This is exactly what Claude Code does with Haiku/Sonnet/Opus.

### Pattern 2: Markdown-defined Agents
Agent definitions as markdown files with YAML frontmatter is simple, portable, and human-readable. Our YAML config could adopt this pattern.

### Pattern 3: Tool Access Control per Agent
Allowlist/denylist per agent is clean and simple. Maps to our ToolRegistry capability filtering.

### Pattern 4: Context Isolation with Summary Return
Subagents get minimal context (system prompt + env), return summary to parent. This keeps main context clean. Maps to our SubagentLoop already.

### Pattern 5: Persistent Agent Memory
Per-agent memory directories with MEMORY.md is simple and effective. We could adapt this for our MemoryStore.

### Pattern 6: Teams as Separate Sessions
For complex parallel work, full separate sessions > subagents. Teams coordinate via shared task list + mailbox. This is the Phase 5B design direction.
