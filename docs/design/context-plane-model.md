# Four-Plane Context Model

> Date: 2026-04-08
> Purpose: Formalize the four context planes in AutoCode-native terms for compaction, handoff, and memory design.

## Overview

AutoCode manages four distinct context planes that differ in durability, size, and purpose.

## The Planes

| Plane | Purpose | Durability | Typical Size | Key Examples |
|-------|---------|----------|-------------|-------------|
| **1. Durable Instructions** | Policy, rules, system prompts | Permanent | <2KB | `CLAUDE.md`, `AGENTS.md`, tool prompts |
| **2. Durable Project Memory** | Learned facts about the repo | Permanent until cleared | <10KB | `.autocode/memory.md`, consolidation learnings |
| **3. Live Session State** | Current task, messages, working set | Per-session | <50KB | session messages, checkpoint stack |
| **4. Ephemeral Scratch** | Temp calculations, exploration | Per-turn | <5KB | tool results, search hits |

## Mapping to Current Modules

### Plane 1: Durable Instructions

- `autocode/src/autocode/agent/prompts.py` — tool + system prompts
- `CLAUDE.md` — agent collaboration rules
- `AGENTS.md` — agent communication protocol
- `autocode/src/autocode/agent/policy_router.py` — routing rules

### Plane 2: Durable Project Memory

- `.autocode/memory.md` — user-defined project memory
- `autocode/src/autocode/session/consolidation.py` — `SessionConsolidator` with `SessionLearning` extraction
- `autocode/src/autocode/agent/memory.py` — `MemoryStore`

### Plane 3: Live Session State

- `autocode/src/autocode/session/store.py` — `SessionStore` (messages, metadata)
- `autocode/src/autocode/session/checkpoint_store.py` — checkpoint stack
- `autocode/src/autocode/agent/orchestrator.py` — agent state
- `autocode/src/autocode/agent/context.py` — `ContextEngine`

### Plane 4: Ephemeral Scratch

- `autocode/src/autocode/agent/loop.py` — per-turn tool results
- `autocode/src/autocode/layer2/search.py` — search hit accumulation
- `autocode/src/autocode/agent/worktree.py` — temp working set

## Design Rules

1. **No cross-plane promotion** — Plane 4 content must not be auto-promoted to Plane 2
2. **Explicit consolidation** — Only `SessionConsolidator.gather()` can extract learnings for Plane 2
3. **Size budgets** — Each plane has an implicit size ceiling that triggers compaction
4. **Separation by owner** — Frontends own Plane 4; consolidation owns Plane 2; orchestrator owns Plane 3

## API Reference

```python
from dataclasses import dataclass
from enum import Enum, auto


class ContextPlane(Enum):
    """The four context planes."""
    DURABLE_INSTRUCTIONS = auto()    # Plane 1: policy/rules
    DURABLE_MEMORY = auto()       # Plane 2: learned project facts  
    LIVE_SESSION = auto()         # Plane 3: current task state
    EPHEMERAL = auto()          # Plane 4: per-turn scratch


@dataclass
class PlaneBudget:
    """Budget limits per plane (in tokens, estimated at 4 chars/token)."""
    durable_instructions: int = 512    # ~2KB
    durable_memory: int = 2560          # ~10KB
    live_session: int = 12800         # ~50KB
    ephemeral: int = 1280              # ~5KB


@dataclass
class PlaneState:
    """Current state within each plane."""
    plane: ContextPlane
    token_count: int
    compacted: bool = False
    last_compaction: str | None = None
```

## Compaction Behavior by Plane

| Plane | Trigger | Strategy | Keeps |
|-------|---------|----------|-------|
| 1 | Manual only | N/A | All |
| 2 | Confidence threshold | Prune <0.5 confidence | High-confidence learnings only |
| 3 | >75% budget | Summarize + checkpoint | Last compact summary + checkpoint |
| 4 | Every turn | Always discard | Nothing (per-turn only) |

## Migration Notes

- No new files introduced — this formalizes existing patterns
- No `.harness/` tree created
- Existing `SessionConsolidator` already follows this model — this just makes it explicit
- Future compaction logic should reference `ContextPlane` enum instead of ad hoc string matching