---
name: agent-comms
description: Manage cross-agent communication in this repo; use when asked to read or write AGENTS_CONVERSATION.MD, follow AGENT_COMMUNICATION_RULES.md, respond to task handoffs, draft comms replies, or archive resolved threads.
---

# Agent Comms

## Overview
Use this workflow to manage agent-to-agent communication in this repo. Follow the rules, log entries in AGENTS_CONVERSATION.MD, and archive resolved threads per AGENT_COMMUNICATION_RULES.md.

## Workflow

### 1. Identify the agent
Determine which agent you are based on your environment (Codex CLI, Claude Code CLI, etc.). Use this name in identity headers.

### 2. Read the rules
**Before reading `AGENTS_CONVERSATION.MD`, read `AGENT_COMMUNICATION_RULES.md` in the repo root.** Follow the identity header format, message types, workflow rules, and archival rules.

### 3. Check for pending messages
Read `AGENTS_CONVERSATION.MD` in the repo root. Scan for:
- Messages addressed to you (lines containing `Replying to: <your name>`) or task handoffs assigning work to you.
- Open questions or requests without a response.
- Threads ready for archival (all parties acknowledged, no open questions).

Report to the user:
- Number of active entries.
- Messages requiring a response.
- Threads ready for archival.

### 4. Take action
Before any task that changes code or docs, log a **pre-task intent** entry in `AGENTS_CONVERSATION.MD`.

Reply to a message:
- Use the correct message type (Concern, Review, Task Handoff).
- Append the reply to the bottom of `AGENTS_CONVERSATION.MD`.
- Follow the identity header format.

Send a new message:
- Ask who it is for, the message type, and the content.
- Assign the next Entry number.
- Append to the bottom of `AGENTS_CONVERSATION.MD`.

Archive a resolved thread (only if the user confirms **and** the original author is doing it):
1. Append `Status: RESOLVED — <summary>` to the thread.
2. Move the thread to `docs/communication/old/<date>-<topic>.md`.
3. Remove it from `AGENTS_CONVERSATION.MD`.
4. Never delete archived files.

### 5. Guardrails
- Never read `docs/communication/old/` unless the user explicitly asks.
- Never self-resolve or archive another agent’s entry. Only the original author can mark it resolved and perform the archive, unless the user explicitly overrides.
- If you believe another agent’s entry is resolved, post a new entry stating so and let the original author confirm and archive.
- Keep `AGENTS_CONVERSATION.MD` lean.
