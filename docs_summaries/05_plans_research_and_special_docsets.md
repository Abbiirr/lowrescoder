# Plans, Research, And Special Docsets Summary

## What lives here

This family contains:

- active and historical plan docs
- research memos
- vendor/tooling research notebooks
- side-project docsets like `ailogd`

## Plan docs

The `docs/plan/` folder is a mixed collection:

- active execution plans
- historical phase plans
- status/vision docs
- benchmark hardening notes
- special-purpose research checklists

Important current plan docs:

- [docs/plan/backend-tightening-refinement-plan.md](../docs/plan/backend-tightening-refinement-plan.md)
- [docs/plan/hr5-phase-a-benchmark-latency-plan.md](../docs/plan/hr5-phase-a-benchmark-latency-plan.md)
- [docs/plan/stabilization-and-parity-plan.md](../docs/plan/stabilization-and-parity-plan.md)
- [docs/plan/archive/project-status.md](../docs/plan/archive/project-status.md)
- [docs/plan/vision.md](../docs/plan/vision.md)
- [docs/plan/archive/phase7-ship-ready.md](../docs/plan/archive/phase7-ship-ready.md)
- [docs/plan/research-components-feature-checklist.md](../docs/plan/research-components-feature-checklist.md)

How to read them:

- use `current_directives.md` and `EXECUTION_CHECKLIST.md` to know which plan is active now
- use `project-status.md`, `vision.md`, and `phase7-ship-ready.md` for broader historical/product context
- use specialized plan files only for the slice they name

## Research docs

The `docs/research/` family is strategic analysis, not runtime policy.

Two especially relevant research docs are:

- [docs/research/autocode-internal-first-orchestration.md](../docs/research/autocode-internal-first-orchestration.md)
- [docs/research/harness-improvement-proposal-v2-adoption-plan.md](../docs/research/harness-improvement-proposal-v2-adoption-plan.md)

These mostly answer:

- what AutoCode already has
- what orchestration/harness patterns are still missing
- what should be adopted now vs later

They are useful for architecture direction, not for daily operator commands.

## Competitive and vendor research docsets

### `docs/claude/`

This folder is a Claude-authored research/planning notebook set.

- [docs/claude/00-master-plan-index.md](../docs/claude/00-master-plan-index.md) is the index
- the rest are topic-focused research and phase docs

Use it as historical planning/research context.

### `docs/codex/`

This folder is a tool/vendor research notebook set.

It covers:

- coding agents
- protocol/tooling components
- retrieval/toolchain dependencies
- external tool/library notes

It is a research library, not an operating manual.

### `docs/competitive-intelligence-2026.md`

This is the high-level competitor/strategy memo challenging core AutoCode assumptions. It belongs with research, not with active product policy.

## `ailogd` docset

The `docs/ailogd/` family is essentially a standalone design/implementation docset for a universal AI tool logger.

- [docs/ailogd/README.md](../docs/ailogd/README.md) is the index
- the numbered files move from architecture and schema through hooks, proxying, daemon behavior, install, testing, and risks

Treat it as a contained subproject documentation set.

## Practical takeaway

This family is where you go for:

- historical why
- architecture reasoning
- research-informed future work
- subproject design documents

It is not the first place to look for “what is active today”.

## Source references

- [docs/plan/backend-tightening-refinement-plan.md](../docs/plan/backend-tightening-refinement-plan.md)
- [docs/plan/archive/project-status.md](../docs/plan/archive/project-status.md)
- [docs/plan/vision.md](../docs/plan/vision.md)
- [docs/plan/stabilization-and-parity-plan.md](../docs/plan/stabilization-and-parity-plan.md)
- [docs/plan/archive/phase7-ship-ready.md](../docs/plan/archive/phase7-ship-ready.md)
- [docs/plan/research-components-feature-checklist.md](../docs/plan/research-components-feature-checklist.md)
- [docs/research/autocode-internal-first-orchestration.md](../docs/research/autocode-internal-first-orchestration.md)
- [docs/research/harness-improvement-proposal-v2-adoption-plan.md](../docs/research/harness-improvement-proposal-v2-adoption-plan.md)
- [docs/competitive-intelligence-2026.md](../docs/competitive-intelligence-2026.md)
- [docs/claude/00-master-plan-index.md](../docs/claude/00-master-plan-index.md)
- [../docs/codex/](../docs/codex/)
- [docs/ailogd/README.md](../docs/ailogd/README.md)
