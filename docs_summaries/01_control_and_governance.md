# Control And Governance Summary

## What these docs do

These docs define how work is prioritized, how agents operate, and which docs are authoritative.

## Core rule set

- [current_directives.md](../current_directives.md) is the live top-level direction file.
  - Current product queue: HR-5 TUI runtime correctness/parity follow-through.
  - Current temporary user override: backend-tightening before more frontend binding work.
- [EXECUTION_CHECKLIST.md](../EXECUTION_CHECKLIST.md) is the live execution checklist and near-term status board.
  - It points to the active plan/checklist files and records what is complete vs still active.
- [PLAN.md](../PLAN.md) is the long-form roadmap and backlog map.
  - It is broad and historically layered, not the fastest “what next today?” file.

## Agent operating docs

- [AGENTS.md](../AGENTS.md) is the repository-specific operating contract for coding agents.
  - Read order, role split, commit policy, TUI testing requirements, and where to look are all here.
- [CLAUDE.md](../CLAUDE.md) overlaps with `AGENTS.md` as a session and repo guide.
- [AGENT_COMMUNICATION_RULES.md](../AGENT_COMMUNICATION_RULES.md) defines the protocol for agent-to-agent communication.
- [AGENTS_CONVERSATION.MD](../AGENTS_CONVERSATION.MD) is the live message log.
- [docs/agent_to_agent_comms_setup_guide.md](../docs/agent_to_agent_comms_setup_guide.md) explains how the comms system is set up and operated.

## Operator / onboarding docs

- [README.md](../README.md) is the public-facing quick start and project overview.
  - Good for install/run/build/test commands and the big-picture architecture.
- [docs/session-onramp.md](../docs/session-onramp.md) is the fastest session-start guide.
  - It tells a contributor what to read, what commands matter, and how to store artifacts.
- [DEFERRED_PENDING_TODO.md](../DEFERRED_PENDING_TODO.md) is a parking lot, not the active source of truth.

## Practical reading order

For an engineering session:

1. [current_directives.md](../current_directives.md)
2. [EXECUTION_CHECKLIST.md](../EXECUTION_CHECKLIST.md)
3. the active plan file named there
4. [AGENTS.md](../AGENTS.md) for repo rules
5. [docs/session-onramp.md](../docs/session-onramp.md) if you need command/tooling refresh

## Drift / caution notes

- [docs/guide/commands.md](../docs/guide/commands.md) looks like an older CLI-oriented reference.
  - It still centers `autocode chat` as a core command surface.
  - The repo’s current user guidance prefers bare `autocode`; use `AGENTS.md`, `README.md`, and current directives first.
- [docs/plan/archive/project-status.md](../docs/plan/archive/project-status.md) and [docs/plan/vision.md](../docs/plan/vision.md) are useful context docs, but they are not the daily priority queue.

## Source references

- [current_directives.md](../current_directives.md)
- [EXECUTION_CHECKLIST.md](../EXECUTION_CHECKLIST.md)
- [PLAN.md](../PLAN.md)
- [AGENTS.md](../AGENTS.md)
- [CLAUDE.md](../CLAUDE.md)
- [AGENT_COMMUNICATION_RULES.md](../AGENT_COMMUNICATION_RULES.md)
- [AGENTS_CONVERSATION.MD](../AGENTS_CONVERSATION.MD)
- [README.md](../README.md)
- [docs/session-onramp.md](../docs/session-onramp.md)
- [docs/agent_to_agent_comms_setup_guide.md](../docs/agent_to_agent_comms_setup_guide.md)
- [docs/guide/commands.md](../docs/guide/commands.md)
