# Agent-to-Agent Communication Setup Guide

> How to set up multi-agent collaboration between Claude Code, Codex CLI, and OpenCode using a shared message log.

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [File Structure](#file-structure)
3. [Step 1: Create the Rules File](#step-1-create-the-rules-file)
4. [Step 2: Create the Message Log](#step-2-create-the-message-log)
5. [Step 3: Create the /comms Skill](#step-3-create-the-comms-skill)
6. [Step 4: Configure Each Agent](#step-4-configure-each-agent)
7. [Step 5: Set Up Project Instructions](#step-5-set-up-project-instructions)
8. [Daily Workflow](#daily-workflow)
9. [Troubleshooting](#troubleshooting)

---

## How It Works

Three AI coding agents collaborate through a **single shared markdown file** (`AGENTS_CONVERSATION.MD`). Each agent reads the file at the start of its session, checks for messages addressed to it, and posts replies. A separate rules file defines the communication protocol.

```
┌──────────┐     ┌──────────────────────────┐     ┌──────────┐
│  Claude   │────>│  AGENTS_CONVERSATION.MD  │<────│  Codex   │
│ (Coder)   │<────│    (shared message log)   │────>│(Reviewer)│
└──────────┘     └────────────┬─────────────┘     └──────────┘
                              │
                   ┌──────────┴─────────────┐
                   │                        │
              ┌────┴─────┐          ┌───────┴────────┐
              │ OpenCode  │          │  Archive files  │
              │ (Builder) │          │ docs/comm/old/  │
              └──────────┘          └────────────────┘
```

**Key principle:** Agents never talk to each other directly. All communication goes through the message log. The human user is the orchestrator — they run each agent, tell it to check messages (`/comms`), and approve actions.

---

## File Structure

You need 3 files in your project root, plus optional archive storage:

```
project-root/
├── AGENT_COMMUNICATION_RULES.md    # Protocol definition (rules)
├── AGENTS_CONVERSATION.MD          # Active message log (read/write)
├── .claude/commands/comms.md       # /comms skill (auto-loaded by Claude)
├── docs/
│   └── communication/
│       └── old/                    # Archived resolved threads
│           ├── 2026-02-05-topic-a.md
│           └── 2026-02-05-topic-b.md
```

---

## Step 1: Create the Rules File

Create `AGENT_COMMUNICATION_RULES.md` in your project root. This is the protocol all agents follow.

```markdown
# Agent Communication Rules

> **All agent-to-agent communication happens in `AGENTS_CONVERSATION.MD`.**
> This file defines the rules. That file is the message log. No other channels exist.

## Agent Roles

| Agent | Primary Role | Responsibilities |
|-------|-------------|-----------------|
| **Claude** | Coder | Writes implementation code, builds features, fixes bugs |
| **Codex** | Reviewer / Architect | Reviews code and docs, validates architecture, flags issues |
| **OpenCode** | Builder | Executes build tasks, runs tests, handles infrastructure |

These roles define the default division of labor. The user may override on a per-task basis.

## Identity Protocol

Start each message with:

    Agent: <name> | Role: <role> | Layer: <1-4 or N/A> | Context: <scope> | Intent: <goal>

- If responding to another agent: `Replying to: <agent name>`
- If you used any tools, list them at the end: `Tools Used: <list>`

## Message Types

### Concern / Issue
1. State the concern in one sentence.
2. Classify severity: `Low | Medium | High | Critical`
3. Cite evidence (file path, line if known, or observed behavior).
4. Propose a fix or mitigation (one clear action).
5. Ask one focused question if clarification is required.

### Review (code, docs, or architecture)
1. **Layer Assessment**: Which Layer (1-4) does the code/solution operate at?
2. **Verdict**: `APPROVE | NEEDS_WORK | REJECT`
3. **Analysis**: Technical analysis.
4. **Concerns**: Specific issues, or "None".
5. **Suggested Changes**: Concrete improvements, or "None".

### Task Handoff
1. **Action requested**: What the other agent should do.
2. **Files involved**: Which files to read/modify.
3. **Context**: Link to relevant docs or prior entries.
4. **Deadline/Priority**: If applicable.

## General Rules

- Be concise and factual.
- Prefer deterministic evidence over assumptions.
- If blocking, say `Blocker: <reason>` and stop further action.
- `AGENTS_CONVERSATION.MD` is the **single channel** — no side files, no review queues.

## Workflow

- Log a pre-task intent entry before any task that changes code or docs.
- Log a concern or message after completing a task or review.
- Record review requests and verdicts in `AGENTS_CONVERSATION.MD` — not in separate files.

## Resolution & Archival

### Who resolves a thread
- **The original author** (the agent who created the entry) is the ONLY agent that can mark it resolved.
- **The user** can override this and resolve any thread.
- **The receiving agent CANNOT self-resolve.** It replies; the original author decides when it's done.

### How to archive
1. The original author appends: `Status: RESOLVED — <one-line summary>`
2. Move the thread to `docs/communication/old/<date>-<topic>.md`
3. Remove archived entries from `AGENTS_CONVERSATION.MD`
4. **NEVER delete archived files.** They are permanent records.

### When to read archives
Only read from `docs/communication/old/` when:
1. The user explicitly asks
2. An active entry references a specific archived thread
3. Resolving a dispute where prior decisions are needed
```

**Customize the Agent Roles table** for your project. The roles above are examples — adjust responsibilities to match your workflow.

---

## Step 2: Create the Message Log

Create `AGENTS_CONVERSATION.MD` in your project root:

```markdown
# Agents Conversation

> **Single message log for all agent-to-agent communication.**
> Rules and protocols: see [`AGENT_COMMUNICATION_RULES.md`](AGENT_COMMUNICATION_RULES.md)

## Message Log

Append new entries below this line. Keep newest entries at the bottom.

---
```

Also create the archive directory:

```bash
mkdir -p docs/communication/old
```

---

## Step 3: Create the /comms Skill

The `/comms` skill is a reusable prompt that any agent can load to handle communication. Each agent platform loads it differently.

### For Claude Code

Create `.claude/commands/comms.md`:

```markdown
# /comms — Agent Communication Manager

You are an agent participating in a multi-agent project. This skill handles all cross-agent communication.

## Step 1: Identify yourself

Determine which agent you are based on your environment:
- **Claude** (Claude Code CLI)
- **Codex** (OpenAI Codex CLI)
- **OpenCode** (or other agent — use your tool/CLI name)

Store your agent name for use in message headers.

## Step 2: Read the rules

Read `AGENT_COMMUNICATION_RULES.md` in the project root. This defines:
- Identity header format
- Message types (Concern, Review, Task Handoff)
- Review principles
- Workflow (pre-task intent, post-task messages)
- Resolution & archival rules (who resolves, when, how)

You MUST follow these rules for all messages you write.

## Step 3: Check for pending messages

Read `AGENTS_CONVERSATION.MD` in the project root. Scan the Message Log for:

1. **Messages addressed to you** — look for `Replying to: <your name>` or task handoffs assigning work to you
2. **Open questions** — any entry ending with a `Question:` that hasn't been answered
3. **Unresolved threads** — entries without a `Status: RESOLVED` follow-up

Report what you found to the user:
- Number of active entries
- Any messages requiring your response
- Any threads ready for archival

## Step 4: Take action

Based on what was found, offer the user these options:

### If there are messages requiring a response:
- Draft a reply following the identity header format from the rules
- Use the correct message type (Concern, Review, or Task Handoff)
- Append the reply to the bottom of `AGENTS_CONVERSATION.MD`

### If there are threads ready for archival:
- Show which threads are resolved
- If the user confirms, archive them:
  1. Append `Status: RESOLVED — <summary>` to the thread
  2. Move the thread to `docs/communication/old/<date>-<topic>.md`
  3. Remove the archived entries from `AGENTS_CONVERSATION.MD`
  4. NEVER delete the archive file after creating it

### If the user wants to send a new message:
- Ask: who is it for, what type (Concern / Review / Task Handoff / General), and what's the content
- Format it according to the rules
- Assign the next Entry number and append to `AGENTS_CONVERSATION.MD`

### If there's nothing pending:
- Report "No pending messages. Conversation log is clean."

## Rules to always follow

- NEVER read from `docs/communication/old/` unless the user explicitly asks
- NEVER delete archived files
- NEVER self-resolve a thread assigned to you — only the originator or user resolves
- Always use the identity header
- Keep `AGENTS_CONVERSATION.MD` lean — active entries only
```

With this file in place, typing `/comms` in Claude Code will load the skill automatically.

### For Codex CLI

Codex reads project instructions from `AGENTS.md` (or `CODEX.md`). Add to your `AGENTS.md`:

```markdown
## Agent Communication (Required)

Before any action, check `AGENTS_CONVERSATION.MD` for pending items or messages from other agents.

| File | Purpose |
|------|---------|
| `AGENT_COMMUNICATION_RULES.md` | Rules — protocols, message types, workflow, archival |
| `AGENTS_CONVERSATION.MD` | Message log — read and write messages here |

When the user says "check comms" or "reply", follow this protocol:
1. Read `AGENT_COMMUNICATION_RULES.md` for the rules
2. Read `AGENTS_CONVERSATION.MD` for pending messages
3. Report findings to the user
4. Draft and post replies as instructed
```

Codex doesn't have a `/comms` slash command natively. Instead, the user triggers it by saying "check comms", "reply to messages", or similar. The instructions in `AGENTS.md` tell Codex how to handle it.

**Tip:** You can also paste the full `/comms` skill content into Codex's system prompt or a custom instruction file if your setup supports it.

### For OpenCode

OpenCode reads project instructions from `AGENTS.md` or a project-level config. Add the same communication section as Codex:

```markdown
## Agent Communication (Required)

Before any action, check `AGENTS_CONVERSATION.MD` for pending items or messages from other agents.

| File | Purpose |
|------|---------|
| `AGENT_COMMUNICATION_RULES.md` | Rules — protocols, message types, workflow, archival |
| `AGENTS_CONVERSATION.MD` | Message log — read and write messages here |

When the user says "check comms" or "reply", follow this protocol:
1. Read `AGENT_COMMUNICATION_RULES.md` for the rules
2. Read `AGENTS_CONVERSATION.MD` for pending messages
3. Report findings to the user
4. Draft and post replies as instructed
```

If OpenCode supports custom commands or prompt files, create the equivalent of `/comms` in its configuration directory. The content is the same — only the loading mechanism differs.

---

## Step 4: Configure Each Agent

### Claude Code

**Project instructions** (`CLAUDE.md`): Add a section pointing to the communication files:

```markdown
## Agent Communication (Required)

This project uses two files for cross-agent communication:

| File | Purpose |
|------|---------|
| `AGENT_COMMUNICATION_RULES.md` | Rules — protocols, message types, review principles, workflow, archival |
| `AGENTS_CONVERSATION.MD` | Message log — active/unresolved entries only |

**Before any action**, check `AGENTS_CONVERSATION.MD` for pending items or messages from other agents.

### Archival Rules
- When a thread is resolved, move it to `docs/communication/old/<date>-<topic>.md`
- **NEVER delete archived conversations.** They are permanent records.
- **NEVER read from `docs/communication/old/` unless the user explicitly asks.**
```

**Usage:** Type `/comms` in Claude Code to check messages and post replies.

### Codex CLI

**Project instructions** (`AGENTS.md`): Include the communication section shown in Step 3.

**Usage:** Tell Codex "check comms" or "read AGENTS_CONVERSATION.MD and reply to any messages for you." Codex will follow the instructions from `AGENTS.md`.

### OpenCode

**Project instructions** (`AGENTS.md`): Include the communication section shown in Step 3.

**Usage:** Tell OpenCode "check comms" or "check AGENTS_CONVERSATION.MD for messages." The behavior mirrors Codex.

---

## Step 5: Set Up Project Instructions

Each agent reads different instruction files. Here's the full mapping:

| Agent | Instruction File | Auto-loaded? |
|-------|-----------------|-------------|
| Claude Code | `CLAUDE.md` | Yes (always loaded) |
| Codex CLI | `AGENTS.md` | Yes (always loaded) |
| OpenCode | `AGENTS.md` | Yes (always loaded) |

Make sure **both** `CLAUDE.md` and `AGENTS.md` reference the communication files. This ensures every agent knows the protocol regardless of which instruction file it reads.

---

## Daily Workflow

### Starting a session with any agent

1. **User opens agent CLI** (Claude Code, Codex, or OpenCode)
2. **User types `/comms`** (or "check comms" for agents without slash commands)
3. **Agent reads** `AGENT_COMMUNICATION_RULES.md` and `AGENTS_CONVERSATION.MD`
4. **Agent reports:** "3 active entries. Entry 5 has a question for you. Entry 4 is ready to archive."
5. **User decides:** "Reply to Entry 5" or "Archive Entry 4" or "Post a new message to Codex"

### Typical multi-agent cycle

```
Session 1 (Claude):
  User: "Implement the config system"
  Claude: [writes code, posts Entry 14 — task completion report]

Session 2 (Codex):
  User: "/comms" (or "check comms")
  Codex: "Entry 14 from Claude — config system complete, requesting review"
  User: "Review it"
  Codex: [reads code, posts Entry 15 — APPROVE WITH MODIFICATIONS]

Session 3 (Claude):
  User: "/comms"
  Claude: "Entry 15 from Codex — approved with 2 modifications"
  User: "Accept and resolve"
  Claude: [applies fixes, posts Entry 16 — accepted, archives Entries 14-16]

Session 4 (OpenCode):
  User: "check comms"
  OpenCode: "No pending messages. Conversation log is clean."
```

### Archiving resolved threads

When a thread is fully resolved (all parties acknowledged, no open questions):

1. The **original author** (or user) marks it: `Status: RESOLVED — <summary>`
2. Move the entry/entries to `docs/communication/old/<date>-<topic>.md`
3. Remove them from `AGENTS_CONVERSATION.MD`
4. Never delete archive files

---

## Troubleshooting

### Agent doesn't see messages
- Verify `AGENTS_CONVERSATION.MD` exists in the project root
- Check that the agent's instruction file (`CLAUDE.md` or `AGENTS.md`) references the communication files
- Make sure the agent reads the file — say "read AGENTS_CONVERSATION.MD" explicitly

### Agent posts in wrong format
- Point the agent to `AGENT_COMMUNICATION_RULES.md` — say "read the communication rules first"
- Check the identity header includes all fields: Agent, Role, Layer, Context, Intent

### Edit conflicts between agents
- Only one agent should write to `AGENTS_CONVERSATION.MD` at a time
- The human user is the orchestrator — run one agent session at a time, or ensure agents write to different sections
- If a conflict occurs, re-read the file and retry the edit

### Agent tries to self-resolve a thread
- Per the rules, only the **original author** can resolve a thread
- If an agent self-resolves, that resolution is invalid — the original author must re-confirm
- The user can override this and instruct any agent to resolve any thread

### Too many active entries cluttering the log
- Archive resolved threads regularly (use `/comms` and say "archive resolved")
- Group related entries into a single archive file (e.g., `2026-02-05-sprint-1-reviews.md`)
- Keep only active/unresolved entries in the main log

---

## Quick Reference

| Action | Claude Code | Codex CLI | OpenCode |
|--------|------------|-----------|----------|
| Check messages | `/comms` | "check comms" | "check comms" |
| Post a reply | `/comms reply` | "reply to Entry N" | "reply to Entry N" |
| Archive threads | `/comms` → "archive resolved" | "archive resolved entries" | "archive resolved entries" |
| Send new message | `/comms` → "send message to X" | "post message to X in comms" | "post message to X in comms" |
| Read rules | Automatic (via /comms) | "read AGENT_COMMUNICATION_RULES.md" | "read AGENT_COMMUNICATION_RULES.md" |
