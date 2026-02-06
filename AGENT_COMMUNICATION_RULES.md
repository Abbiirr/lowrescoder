# Agent Communication Rules

> **All agent-to-agent communication happens in `AGENTS_CONVERSATION.MD`.**
> This file defines the rules. That file is the message log. No other channels exist.

## Agent Roles

Any agent or human may participate in this communication system. The following table shows example roles, but **the system is open to infinite agents and humans**.

| Participant | Type | Primary Role | Responsibilities |
|-------------|------|-------------|-----------------|
| **Claude** | AI Agent | Coder | Writes implementation code, builds features, fixes bugs, executes sprint tasks |
| **Codex** | AI Agent | Reviewer / Architect | Reviews code and docs, validates architecture, flags issues, maintains docs/codex/ research notes |
| **OpenCode** | AI Agent | Reviewer / Architect | Code review, research, cross-cutting analysis |
| **User** | Human | Product Owner / Director | Sets direction, makes final decisions, provides feedback |
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

Agents must **NOT** read from `docs/communication/old/` by default. Only read archived messages when:

1. **The user explicitly asks** — e.g., "check the old conversation about X", "look up what was decided about Y"
2. **An active entry references an archived thread** — e.g., "See `docs/communication/old/2026-02-05-kickoff.md` for prior context". Only read the specific file referenced, not the whole directory.
3. **Resolving a dispute** — If two agents disagree on a prior decision, the user may direct them to check the archive for evidence.

In all other cases, treat archives as if they don't exist. Do not scan, list, or load archived files to "catch up" or "review history" — that defeats the purpose of archival.

## Testing Requirements

**All agents MUST run tests before posting any review request or task completion message.**

```bash
# Required before any review request or task handoff
uv run pytest tests/ -v
uv run ruff check src/ tests/
uv run mypy src/

# Sprint verification (required at sprint boundaries)
uv run pytest tests/test_sprint_verify.py -v
```

- If tests fail, fix the issues before posting. Do not send review requests with failing tests.
- Include test results (pass count, any failures) in review requests and task completion messages.
- New code must include tests. Reviewers should flag missing test coverage.

---

## Examples

### Concern (directed to a specific agent)

```
Agent: Codex | Role: Reviewer | Layer: 2 | Context: Plan review | Intent: Flag feasibility risk
Directed to: Claude

Concern: The timeline in `plan1.md:14` appears unfeasible given current scope.
Severity: Medium
Evidence: `plan1.md:14` targets full Layer 2 retrieval in 1 week; in similar builds, embedding pipeline + index tuning exceeded 2 weeks.
Proposed Fix: Extend the milestone by one week or split into chunking first, embeddings/index second.
Question: Is the 1-week target fixed due to an external deadline?
```

### Review (directed to multiple reviewers)

```
Agent: Claude | Role: Coder | Layer: 3 | Context: Phase 2D review request | Intent: Get code reviewed
Directed to: Codex, OpenCode

Phase 2D implementation complete. Requesting review of inline UX rewrite.
Files: src/hybridcoder/inline/app.py, src/hybridcoder/inline/renderer.py
Tests: 396 passed, ruff clean, mypy clean.
```

### Task Handoff (directed to an agent)

```
Agent: Claude | Role: Architect | Layer: N/A | Context: Sprint 0 setup | Intent: Assign project scaffolding to Codex
Directed to: Codex

Action requested: Create project scaffolding with pyproject.toml, src/hybridcoder/, and tests/ directories.
Files involved: pyproject.toml, src/hybridcoder/__init__.py, tests/conftest.py
Context: docs/claude/phase4-implementation.md Sprint 0
Priority: High — blocks all other work.
```

### Asking the human for a decision

```
Agent: Codex | Role: Architect | Layer: N/A | Context: UX direction | Intent: Get product decision
Directed to: User

Question: Should we keep two UIs long-term (inline + Textual) or converge to a single renderer?
Options: (A) Keep both, inline canonical. (B) Converge to custom renderer in Phase 5.
```
