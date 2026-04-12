# Agent Communication — Message Templates

> Reference examples for AGENT_COMMUNICATION_RULES.md message types.
> These templates show the expected format for each message type.

## Concern (directed to a specific agent)

```
Agent: Codex | Role: Reviewer | Layer: 2 | Context: Plan review | Intent: Flag feasibility risk
Directed to: Claude

Concern: The timeline in `plan1.md:14` appears unfeasible given current scope.
Severity: Medium
Evidence: `plan1.md:14` targets full Layer 2 retrieval in 1 week; in similar builds, embedding pipeline + index tuning exceeded 2 weeks.
Proposed Fix: Extend the milestone by one week or split into chunking first, embeddings/index second.
Question: Is the 1-week target fixed due to an external deadline?
```

## Review (directed to multiple reviewers)

```
Agent: Claude | Role: Coder | Layer: 3 | Context: Phase 2D review request | Intent: Get code reviewed
Directed to: Codex, OpenCode

Phase 2D implementation complete. Requesting review of inline UX rewrite.
Files: src/hybridcoder/inline/app.py, src/hybridcoder/inline/renderer.py
Tests: 396 passed, ruff clean, mypy clean.
```

## Task Handoff (directed to an agent)

```
Agent: Claude | Role: Architect | Layer: N/A | Context: Sprint 0 setup | Intent: Assign project scaffolding to Codex
Directed to: Codex

Action requested: Create project scaffolding with pyproject.toml, src/hybridcoder/, and tests/ directories.
Files involved: pyproject.toml, src/hybridcoder/__init__.py, tests/conftest.py
Context: docs/claude/phase4-implementation.md Sprint 0
Priority: High — blocks all other work.
```

## Asking the human for a decision

```
Agent: Codex | Role: Architect | Layer: N/A | Context: UX direction | Intent: Get product decision
Directed to: User

Question: Should we keep two UIs long-term (inline + Textual) or converge to a single renderer?
Options: (A) Keep both, inline canonical. (B) Converge to custom renderer in Phase 5.
```
