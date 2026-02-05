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
- Any threads ready for archival (all parties acknowledged, no open questions)

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
- Always use the identity header: `Agent: <name> | Role: <role> | Layer: <1-4 or N/A> | Context: <scope> | Intent: <goal>`
- Keep `AGENTS_CONVERSATION.MD` lean — active entries only
