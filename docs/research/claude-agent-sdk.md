# Claude Agent SDK — Research Notes

> Researched: 2026-02-17
> Source: https://platform.claude.com/docs/en/agent-sdk/overview

---

## 1. Overview

The Claude Agent SDK (formerly Claude Code SDK) provides the same tools, agent loop, and context management that power Claude Code, programmable in Python and TypeScript.

Key difference from Client SDK: Agent SDK handles the tool loop autonomously. With Client SDK you implement the loop yourself.

## 2. Built-in Tools

| Tool | What it does |
|------|-------------|
| Read | Read any file |
| Write | Create new files |
| Edit | Make precise edits |
| Bash | Run terminal commands |
| Glob | Find files by pattern |
| Grep | Search file contents with regex |
| WebSearch | Search the web |
| WebFetch | Fetch and parse web pages |
| AskUserQuestion | Ask user clarifying questions |

## 3. Subagent Definition (Programmatic)

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

async for message in query(
    prompt="Use the code-reviewer agent to review this codebase",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Task"],
        agents={
            "code-reviewer": AgentDefinition(
                description="Expert code reviewer for quality and security reviews.",
                prompt="Analyze code quality and suggest improvements.",
                tools=["Read", "Glob", "Grep"],
            )
        },
    ),
):
    print(message)
```

Key points:
- Subagents defined via `AgentDefinition` (description, prompt, tools)
- Main agent needs `Task` in allowed_tools to spawn subagents
- Messages from subagents include `parent_tool_use_id` for tracking

## 4. Hooks (Lifecycle Events)

Available hooks: `PreToolUse`, `PostToolUse`, `Stop`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`

```python
hooks={
    "PostToolUse": [
        HookMatcher(matcher="Edit|Write", hooks=[log_file_change])
    ]
}
```

Hooks are Python/TypeScript callback functions (not shell commands like in CLI).

## 5. Sessions

- Session IDs captured from init messages
- Can resume sessions with full context
- Can fork sessions to explore different approaches

## 6. Permission Modes

- `bypassPermissions`: Skip all permission checks
- `acceptEdits`: Auto-accept file edits
- Tool allowlists via `allowed_tools`

## 7. MCP Integration

```python
options=ClaudeAgentOptions(
    mcp_servers={
        "playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]}
    }
)
```

## 8. Relevance to HybridCoder

The Agent SDK validates our design direction:
- **Programmatic agent definition** (AgentDefinition) maps to our AgentCard
- **Tool allowlists** map to our ToolRegistry capability filtering
- **Hooks** map to our approval/gate system
- **Sessions with resume** map to our CheckpointStore
- **MCP integration** is our Phase 5D direction

Key difference: Agent SDK targets cloud Claude models. We target local models (Ollama, llama-cpp). But the orchestration patterns are identical.
