# new_plans/ — master index

**Date:** 2026-06-23
**Purpose:** the single top-level map of this directory. It ties the five PLANs
together with the two source-doc clusters they were distilled from (Anvil,
ClipMind) and the autocode-station material, and states the **dependency order**
between them. Before this file the directory had no top-level map: `README.md`
covered only ClipMind, and `harness_copy_teacher/00_INDEX.md` covered only Anvil.

For *what's left to build*, read the three audit docs at the bottom of this page.

---

## The five plans + their components

Each plan brief in this directory maps to a built (or partially built) component
of the AutoCode suite. The component column is where the code lives.

| Plan | Brief | Component (where the code lives) | Source-doc cluster |
|---|---|---|---|
| **PLAN_01** | `PLAN_01_HARNESS_IDE.md` | `harness-ide/` (Rust: MCP server, REPL, tool registry, permission model, audit log) | — |
| **PLAN_02** | `PLAN_02_VIDEO_AGENT.md` | `video-agent/` (Python: typed-op proposer/compiler + FFmpeg render) | **ClipMind** (the 4 flat security docs in this dir) |
| **PLAN_03** | `PLAN_03_FULL_CODEX_IDE.md` | `harness-ide/crates/station/` (Rust: egui/wgpu GPU IDE) | **autocode-station** (requirements + 2 HTML mockups + market research, this dir) |
| **PLAN_04** | `PLAN_04_TEACHER_MODE.md` | `autocode/src/autocode/anvil/teacher/` (Python: root-cause analyst + ACE playbook) | **Anvil** (`harness_copy_teacher/`, esp. docs 04/06/07/08) |
| **PLAN_05** | `PLAN_05_COPYCAT_MODE.md` | `autocode/src/autocode/anvil/{copycat,registry,gate,promote}.py` (Python: registry + 3-channel imitation) | **Anvil** (`harness_copy_teacher/`, esp. docs 04/05) |

The two source-doc clusters in this directory:

- **Anvil** — `harness_copy_teacher/` (11 files + `REFERENCES.md`). The research +
  build plan behind PLAN_04 (teacher) and PLAN_05 (copycat). Its own reading
  order is `harness_copy_teacher/00_INDEX.md`. "Anvil" is the working codename
  for the *offline harness-evolution subsystem*; it is not part of the runtime.
- **ClipMind** — `README.md` + `00-adversarial-validation.md`,
  `01-trust-domains.md`, `01-phase-plan.md`, `02-open-questions.md`. The
  security/build stack behind PLAN_02. (The `README.md` doc-map was corrected on
  2026-06-23 to the flat 4-file reality; the once-advertised nested security tree
  was never written.)
- **autocode-station** — `autocode-station-requirements.md`,
  `autocode-station-v3.html`, `codestation-mockup-v2 (1).html`,
  `market-research-agent-cockpit (1).md`. The requirements + mockups + market
  framing behind PLAN_03.

---

## Dependency order (read this before sequencing work)

The plans are not independent. The edges below are the integration contracts;
the two cross-component contracts they imply are specified in
`CROSS_CUTTING_CONTRACTS.md` (this directory).

```
            shares the harness-ide crate
   PLAN_01  ─────────────────────────────▶  PLAN_03
 (harness-ide                              (crates/station/ is a
  substrate: MCP,                           consumer of the same
  tools, audit,                             harness-ide engine —
  trajectories)                             trust spine + tools)
       │
       │ emits trajectories
       │ (NDJSON; layer_distribution)
       ▼
   PLAN_04 / PLAN_05  ◀───── teacher↔copycat share registry+gate+promote
   (Anvil: teacher consumes student+teacher trajectories;
    copycat consumes the same gate/registry/promote loop)


   PLAN_04  ◀──────────────────────────▶  PLAN_05
   teacher emits self_distill bundles      copycat Channel C-cheap consumes them
   (PLAN_04 §4.5 == PLAN_05 §5.4 — shared work)


   PLAN_02  (standalone — a separate product; no code dependency on the others,
             but shares the "untrusted-proposes / trusted-authorizes" pattern;
             see CROSS_CUTTING_CONTRACTS.md §2)
```

Resolved as a build/sequencing order:

1. **PLAN_01 (harness-ide)** is the substrate. It is the runtime that PLAN_03
   embeds and the **producer of the trajectories** the Anvil flywheel consumes.
   Nothing in PLAN_03/04/05 closes its loop without it.
2. **PLAN_03 (station)** is a *consumer* of the PLAN_01 crate — same engine, same
   trust-domain spine, same tool surface; it adds the GPU IDE shell. It cannot
   ship ahead of the PLAN_01 tools it surfaces.
3. **PLAN_04 (teacher) + PLAN_05 (copycat)** are the **Anvil** offline subsystem.
   They depend on PLAN_01 emitting trajectories whose schema the
   `teacher/recorder.py` consumer parses (the `layer_distribution` contract).
   Within Anvil, teacher and copycat share one registry → gate → promote → audit
   loop, and PLAN_04 §4.5 is the same work as PLAN_05 §5.4.
4. **PLAN_02 (video-agent / ClipMind)** is standalone — no code dependency on the
   other four. It shares only the cross-cutting authorization pattern (§2 below).

---

## The two cross-component contracts (unowned by any single plan)

These span plan boundaries, so no per-plan section owns them. Both are specified
in **`CROSS_CUTTING_CONTRACTS.md`** (this directory):

1. **Trajectory schema contract** — PLAN_01 is the *producer* (the runtime emits
   trajectories), Anvil's `teacher/recorder.py` is the *consumer* (it parses
   `layer_distribution`). PLAN_01's brief never commits to the schema; the
   contract doc pins it on both sides.
2. **Authorization-barrier spec** — the "untrusted-proposes / trusted-authorizes"
   pattern is implemented **three times**: ClipMind's `compiler/validate.py`, the
   station's `approver.rs`, and Anvil's `gate.py` + `registry.py`. The contract
   doc specifies one shared threat model, approval semantics, and audit-log format
   the three should reference (spec only — not a forced shared library).

---

## Audit / remaining-work docs (canonical)

For the state of the corpus and what's left to build, in priority order:

- `NEW_PLANS_REMAINING_TODO.md` — the remaining-work checklist (Tier-0/Tier-1
  tables + Addendum). Start here for "what to do next."
- `NEW_PLANS_GAPS.md` — the gap analysis the checklist is built from.
- `NEW_PLANS_REST_AUDIT.md` — the source-doc + empirical audit (audits the
  material the plans were distilled from, plus a live test run).

The repo-root `TODO.md` is the plan-level roll-up that points back at these three.
