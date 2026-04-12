> **SUPERSEDED** — This document has been superseded by `docs/plan/phase4-agent-orchestration.md` v3.2 (2026-02-14).
> This file is preserved for provenance only. Do not use for implementation.

---

# Phase 4 Plan Revision v3.1: 3-Sprint Split + Full Concern Resolution

## Context

Codex reviewed the Phase 4 plan across 4 entries (307, 309, 311, 312) totaling 22 concerns. After extensive research into Claude Code subagents, OpenCode agent internals, asyncio scheduling, and community patterns, this plan:

1. **Splits Phase 4 into 3 sprints** (~1 week each)
2. **Zero deferrals** — all items ship in Phase 4 (per user directive, Entry 312)
3. **Addresses all 22 Codex concerns** across Entries 307, 309, 311, 312
4. **Incorporates research** from Claude Code official docs, OpenCode docs, cefboud.com deep dive, asyncio patterns, graphlib

## Concern Disposition Summary

### Entry 307 (7 concerns)
| # | Concern | Decision | Sprint |
|---|---------|----------|--------|
| 1 | Plan mode as execution mode | ACCEPTED | 4B |
| 2 | Scheduling policy | ACCEPTED | 4B |
| 3 | cancel_subagent tool | ACCEPTED | 4B |
| 4 | Cycle detection mandatory | ACCEPTED | 4A |
| 5 | Checkpoint restore semantics | ACCEPTED (scoped) | 4C |
| 6 | Markdown plan artifact | **RESTORED** (Entry 312) | 4C |
| 7 | UI target split | ACCEPTED | All |

### Entry 309 (7 concerns)
| # | Concern | Decision | Sprint |
|---|---------|----------|--------|
| 1 | Subagent approval routing | ACCEPTED | 4B |
| 2 | Auto-delegation behavior | ACCEPTED (minimal) | 4B |
| 3 | Plan mode transitions | Already addressed (=307 C1) | 4B |
| 4 | Subagent stateless contract | ACCEPTED | 4B |
| 5 | Per-subagent permission policy | INCLUDED (lightweight) | 4B |
| 6 | Markdown plan artifact | **RESTORED** (Entry 312) | 4C |
| 7 | Orchestration observability | INCLUDED (basic logging) | 4B |

### Entry 311 (8 concerns)
| # | Concern | Decision | Sprint |
|---|---------|----------|--------|
| 1 | Entry numbering collision | FIXED (use next available) | 0B |
| 2 | PriorityLock race condition | ACCEPTED → LLM Scheduler Queue | 4B |
| 3 | Plan mode tool gating brittle | ACCEPTED → capability flags | 4B |
| 4 | Checkpoint restore transactions | ACCEPTED | 4C |
| 5 | L2 routing narrowed to SEMANTIC_SEARCH | ACCEPTED → include SIMPLE_EDIT | 4C |
| 6 | Markdown plan artifact | **RESTORED** (Entry 312) | 4C |
| 7 | Subagent approval routing UX | ACCEPTED | 4B+4C |
| 8 | Hard-coded test counts | FIXED → relative gates | All |

### Entry 312 (task handoff — zero deferrals)
| Item | Decision | Sprint |
|------|----------|--------|
| Markdown plan artifact | RESTORED into Phase 4 | 4C |
| Go-native task panel | RESTORED into Phase 4 | 4C |

### Entry 314 (review addendum — 5 concerns)
| # | Concern | Decision | Sprint |
|---|---------|----------|--------|
| A | JSON-RPC contract/schema for new methods | ACCEPTED | 4A (define schemas), 4B+4C (implement) |
| B | Verification uses store_test_results.sh | ACCEPTED | All (update verification blocks) |
| C | Multi-frontend command parity table | ACCEPTED | 4C (add parity matrix + tests) |
| D | DB migration/init for new tables | ACCEPTED | 4A (ensure_tables() in models.py) |
| E | Research doc structured with acceptance criteria | ACCEPTED | 0A (structure research doc) |

---

_v3.1 draft archived 2026-02-14. See v3.2 for the implementation-ready plan._
