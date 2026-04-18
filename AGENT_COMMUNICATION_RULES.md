# Agent Communication Rules

> **All agent-to-agent communication happens in `AGENTS_CONVERSATION.MD`.**
> This file defines the rules. That file is the message log. No other channels exist.

## Agent Roles

Any agent or human may participate in this communication system. The following table shows example roles, but **the system is open to infinite agents and humans**.

| Participant | Type | Default Role | Responsibilities |
|-------------|------|-------------|-----------------|
| **OpenCode** | AI Agent | Coder / Builder | Writes implementation code, builds features, fixes bugs, runs tests, stores artifacts |
| *Any other coding agent* | AI Agent | Coder / Builder | Same as above — by default, newly-onboarded coding agents build |
| **Claude** | AI Agent | Reviewer / Architect | Reviews code and docs, validates architecture, designs approaches. **Rarely a builder** — only when user explicitly redirects |
| **Codex** | AI Agent | Reviewer / Architect | Reviews code and docs, validates architecture, flags issues, maintains docs/codex/ research notes. **Rarely a builder** |
| **User** | Human | Product Owner / Director | Sets direction, makes final decisions, commits, provides feedback |
| *[Your Name]* | Human or Agent | *Any* | Anyone can join by following the Identity Protocol below |

### Role Guidelines

- **AI Agents**: Use your designated identifier (Claude, Codex, OpenCode, etc.)
- **Humans**: Use your name or preferred identifier (e.g., "User", "Alice", "Bob")
- **Custom Agents**: If you bring a new AI agent into the project, add it to the table above via a PR or comms entry
- Roles are **flexible** — agents can switch roles per task if needed (e.g., a Coder can also Review)
- The user always has final authority and can override any agent decision

## Identity Protocol

All participants (agents and humans) start each message with:

```
Agent: <name> | Role: <role> | Layer: <1-4 or N/A> | Context: <scope> | Intent: <goal>
```

**For Humans:** Use `Agent: <your-name>` (e.g., `Agent: User` or `Agent: Alice`). The "Agent:" prefix is a protocol requirement, not a statement of artificial nature.

- `<name>`: Your identifier (Claude, Codex, OpenCode, User, Alice, etc.)
- `<role>`: Your current role (Coder, Reviewer, Architect, Product Owner, etc.)
- `<layer>`: 1-4 for code layers, N/A for meta/organization tasks
- `<scope>`: Brief context (e.g., "Phase 3 planning", "Bug fix", "Code review")
- `<goal>`: What you intend to accomplish

**Replying:** If responding to another participant: `Replying to: <name>`

**Directing:** To assign or call out a specific participant: `Directed to: <name>` (or multiple: `Directed to: Codex, OpenCode`)

**Tools:** If you used any tools, list them at the end: `Tools Used: <list>`

## Directing Messages

Any participant can direct a message to one or more specific agents or humans. Use the `Directed to:` field in the identity header.

### How it works

- **`Directed to: <name>`** — The named participant is expected to respond or act. Other participants may still comment, but the named one owns the action.
- **Multiple targets** — `Directed to: Codex, OpenCode` means both are expected to respond.
- **Broadcast (no `Directed to:`)** — If omitted, the message is open to anyone. Any participant may respond.
- **The user can direct any agent** — e.g., "Codex, review the Phase 3 plan" or "Claude, fix the failing tests". The user's directive always takes priority.

### Common patterns

| Pattern | Header | Effect |
|---------|--------|--------|
| Request a review | `Directed to: Codex` | Codex should review and post a verdict |
| Assign a task | `Directed to: Claude` | Claude should implement and report completion |
| Ask for research | `Directed to: OpenCode` | OpenCode should research and post findings |
| Ask the human | `Directed to: User` | Requires human input before proceeding |
| Open discussion | *(no `Directed to:`)* | Anyone may respond |
| Multiple reviewers | `Directed to: Codex, OpenCode` | Both should respond independently |

### Rules

- A directed message creates an **obligation to respond**. If you are named, you must acknowledge (even if just "Acknowledged, will handle in next session").
- If you cannot fulfill a directed request, say so explicitly: `Cannot fulfill: <reason>`.
- The user can redirect any message: "Actually, Claude handle this instead of Codex."
- `Directed to:` is compatible with all message types (Concern, Review, Task Handoff, General).

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
3. **Analysis**: Technical analysis referencing the 4-Layer architecture.
4. **Concerns**: Specific issues, or "None".
5. **Suggested Changes**: Concrete improvements, or "None".

### Task Handoff

1. **Action requested**: What the other agent should do.
2. **Files involved**: Which files to read/modify.
3. **Context**: Link to relevant docs or prior entries.
4. **Deadline/Priority**: If applicable.

**Note:** Always use `Directed to: <name>` in the header when handing off a task, so the target agent knows they own it.

> For message templates and examples, see `docs/reference/comms-examples.md`.

## Review Principles

- **Deterministic wins** — Prefer tree-sitter/LSP over embeddings over LLM generation.
- **Challenge LLM-heavy approaches** — If Layer 3-4 is used, explain why Layer 1-2 couldn't solve it.
- **Token budget matters** — Every LLM call has a cost, even locally.
- **Latency is UX** — <100ms feels instant, >2s feels slow.
- **Composability** — Solutions should layer cleanly, not bypass the architecture.

## General Rules

- Be concise and factual.
- Prefer deterministic evidence over assumptions.
- If blocking, say `Blocker: <reason>` and stop further action.
- `AGENTS_CONVERSATION.MD` is the **single channel** — no side files, no review queues.

## Reply and Archive Duty

**Every agent session MUST check `AGENTS_CONVERSATION.MD` at startup and before finishing.**

- **On startup**: Read the message log. If there are entries directed to you, respond to them before starting new work.
- **Before finishing**: If you posted entries or received replies during this session, attempt to resolve and archive completed threads before the session ends.
- **Reply promptly**: If an entry is directed to you, respond in the same session if possible. Do not let directed messages sit unacknowledged across multiple sessions.
- **Archive aggressively**: Once a thread is fully resolved (both sides have acknowledged), the original author should archive it immediately — don't let resolved threads accumulate in the active log.
- **Goal**: `AGENTS_CONVERSATION.MD` should have zero or near-zero entries at rest. Every entry should be either in-progress or archived.

## Workflow

- Log a pre-task intent entry before any task that changes code or docs.
- Log a concern or message after completing a task or review.
- Record review requests and verdicts in `AGENTS_CONVERSATION.MD` — not in separate files.
- **Pre-task intent cleanup:** When a task is completed, the agent that posted the pre-task intent MUST archive it (along with the completion entry) to `docs/communication/old/`. Pre-task intents should not linger in the active log after the work is done.

## Resolution & Archival

### Who resolves a thread

- **The original author** (the agent who created the `### Entry`) is the ONLY agent that can mark it resolved and archive it. No exceptions.
- **The user** can override this and resolve any thread by instructing an agent to archive it.
- **The receiving agent CANNOT self-resolve or archive another agent's entry.** It replies with results; if the receiving agent believes the entry is resolved, it posts a new entry stating so (e.g., "Entry N appears resolved — all concerns addressed in Entry M"). The original author then reviews this claim, confirms resolution, and archives when satisfied.
- **Only the original author (or user) performs the actual archival** — moving entries to `docs/communication/old/` and removing them from the log.

### When a thread is resolved

| Message Type | Resolved when... |
|-------------|-----------------|
| **Concern** | The concern is addressed (fix applied or decision made) and the originator confirms |
| **Review** | A verdict (`APPROVE` / `NEEDS_WORK` / `REJECT`) is delivered and any `NEEDS_WORK` items are fixed |
| **Task Handoff** | The receiving agent confirms completion and the originator accepts the result |
| **General message** | Both parties have acknowledged — no open questions remain |

A thread is **NOT resolved** if:
- There are unanswered questions
- A `NEEDS_WORK` verdict has outstanding items
- A task handoff has no completion confirmation

### How to archive

1. The **original author** appends a final message: `Status: RESOLVED — <one-line summary>`
2. Move the entire thread (all entries under that `### Entry` heading) to `docs/communication/old/<date>-<topic>.md`
3. Remove the archived entries from `AGENTS_CONVERSATION.MD`

### Archive rules

- **NEVER delete archived files.** They are permanent records.
- Keep `AGENTS_CONVERSATION.MD` lean — active/unresolved entries only.

### When to read from archives

**Archives are OFF-LIMITS by default.** Agents must NOT read from `docs/communication/old/` unless one of these conditions is met:

1. **The user explicitly asks** — e.g., "check the old conversation about X", "look up what was decided about Y"
2. **An active entry references a specific archived thread** — e.g., "See `docs/communication/old/2026-02-05-kickoff.md` for prior context". Only read the specific file referenced, not the whole directory.
3. **Resolving a dispute** — If two agents disagree on a prior decision, the user may direct them to check the archive for evidence.

**In all other cases, treat archives as if they don't exist.** Do not scan, list, or load archived files to "catch up" or "review history". Do not read archives "just in case" or to build context. If you need context, read the active docs listed in CLAUDE.md's "Where to Find What" index. The whole point of archival is to keep agent context windows lean.

## Mandatory Documentation Sync

**Docs MUST always reflect the true state of the project. This is non-negotiable.**

### Rules

1. **Update docs WITH code changes, not after.** If you change code that affects plan.md, requirements_and_features.md, session-onramp.md, or any doc, update the doc in the SAME session. Do not leave doc updates for "later" — later never comes.

2. **Never deviate from the plan silently.** If implementation diverges from what's documented in plan.md or phase execution docs:
   - STOP and update the plan doc FIRST to reflect the new reality
   - Log a comms entry explaining WHY the deviation happened
   - Get user acknowledgment for significant deviations
   - Only THEN continue with the divergent implementation

3. **If you discover docs are out of sync**, fix them immediately or log a Critical severity concern in AGENTS_CONVERSATION.MD.

4. **The user is the only authority** who can approve deviations from the plan. Agents cannot unilaterally decide to change direction.

### Why this matters

If we deviate from the plan and then update documents after the fact, we lose track of what actually happened and why. The project state becomes unknowable. Docs are the single source of truth — if they're wrong, everything built on them is unreliable.

## Testing Requirements

> Full testing commands: see CLAUDE.md "Testing (Required)" section.

- All agents MUST run tests before posting any review request or task completion message.
- If tests fail, fix the issues before posting. Do not send review requests with failing tests.
- Include test results (pass count, any failures) in review requests and task completion messages.
- New code must include tests. Reviewers should flag missing test coverage.
