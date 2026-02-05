# Agent Communication Rules

> **All agent-to-agent communication happens in `AGENTS_CONVERSATION.MD`.**
> This file defines the rules. That file is the message log. No other channels exist.

## Identity Protocol

Start each message with:

```
Agent: <name> | Role: <role> | Layer: <1-4 or N/A> | Context: <scope> | Intent: <goal>
```

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
3. **Analysis**: Technical analysis referencing the 4-Layer architecture.
4. **Concerns**: Specific issues, or "None".
5. **Suggested Changes**: Concrete improvements, or "None".

### Task Handoff

1. **Action requested**: What the other agent should do.
2. **Files involved**: Which files to read/modify.
3. **Context**: Link to relevant docs or prior entries.
4. **Deadline/Priority**: If applicable.

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

## Resolution & Archival

### Who resolves a thread

- **The original author** (the agent who created the `### Entry`) is the ONLY agent that can mark it resolved. No exceptions.
- **The user** can override this and resolve any thread by instructing an agent to archive it.
- **The receiving agent CANNOT self-resolve.** It replies with results; the original author reviews the reply and decides when the thread is done. If a receiving agent marks a thread as resolved, that resolution is invalid — the original author must re-confirm.

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

## Examples

### Concern

```
Agent: Codex | Role: Reviewer | Layer: 2 | Context: Plan review | Intent: Flag feasibility risk

Concern: The timeline in `plan1.md:14` appears unfeasible given current scope.
Severity: Medium
Evidence: `plan1.md:14` targets full Layer 2 retrieval in 1 week; in similar builds, embedding pipeline + index tuning exceeded 2 weeks.
Proposed Fix: Extend the milestone by one week or split into chunking first, embeddings/index second.
Question: Is the 1-week target fixed due to an external deadline?
```

### Review

```
Agent: Claude | Role: Reviewer | Layer: 3 | Context: Code review | Intent: Approve grammar module

Layer Assessment: 3
Verdict: APPROVE
Analysis: The Pydantic schemas enforce valid structured output. Outlines integration uses llama-cpp-python backend correctly.
Concerns: None
Suggested Changes: None
```

### Task Handoff

```
Agent: Claude | Role: Architect | Layer: N/A | Context: Sprint 0 setup | Intent: Assign project scaffolding to Codex

Action requested: Create project scaffolding with pyproject.toml, src/hybridcoder/, and tests/ directories.
Files involved: pyproject.toml, src/hybridcoder/__init__.py, tests/conftest.py
Context: docs/claude/phase4-implementation.md Sprint 0
Priority: High — blocks all other work.
```
