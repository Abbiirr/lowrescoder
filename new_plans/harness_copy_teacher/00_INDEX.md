# AutoCode Self-Improvement Program — Research & Build Plan

**Status:** Draft v1 for User review
**Subject:** Copycat mode, Teacher mode, and a self-maintaining harness for AutoCode (`Abbiirr/lowrescoder`)
**Basis:** validation of `deep-research-report__18_.md` + repo state read (README, `north-star.md`, `PLAN.md`) + 2026 harness-engineering literature
**Author stance:** factual, corrective. Where the source report is wrong, this set says so and shows why.

---

## The one-paragraph reframe

The source report calls this "copycat + teacher + self-maintaining edge harness." In current (2026) terms that is **Agentic Harness Engineering (AHE)**: hold the model *frozen* and evolve the harness around it, driven by observability, measured against an executable benchmark. That framing is not a downgrade of your idea — it is the published, peer-reviewed version of it (arXiv:2604.25850), and it fits AutoCode's locked invariants almost exactly: a frozen model stays on consumer hardware, and an *offline* improvement loop keeps the *runtime* edge-native and cloud-free. The single biggest correction to the report: for coding agents, the measured gains come from **tools, middleware, and long-term memory — not from prompt/program optimization.** The report over-weights prompts (DSPy/GEPA) and distillation. Re-weight toward tool and middleware synthesis, grounded in execution-verified evaluation built from your own session history.

---

## Read in this order

| # | File | What it answers | Read if you want… |
|---|------|-----------------|-------------------|
| 01 | `01_VALIDATION_AND_CORRECTIONS.md` | What the source report gets right, and the 8 things it gets wrong | The honest critique first |
| 02 | `02_REPO_STATE_AND_GAP_ANALYSIS.md` | What AutoCode already has vs. what this needs | To know what's reusable |
| 03 | `03_HARNESS_ENGINEERING_SOTA.md` | The 2026 landscape: AHE, ACE, GEPA, on-policy distillation, Ralph loop | The evidence base |
| 04 | `04_ARCHITECTURE.md` | The unified design: 3 observability pillars + escalation ladder + offline/runtime split | The core design doc |
| 05 | `05_COPYCAT_MODE.md` | Capability acquisition done right (3 feasible channels) | To build copycat |
| 06 | `06_TEACHER_MODE.md` | Execution-grounded teaching + playbook evolution | To build teacher |
| 07 | `07_SELF_MAINTENANCE_ENGINE.md` | The autonomous loop, falsifiable contracts, kill switches | To build the loop |
| 08 | `08_EVALUATION_AND_VERIFICATION.md` | The eval flywheel, metrics, statistical rigor | To trust any of it |
| 09 | `09_BUILD_ROADMAP.md` | Phased plan, exit gates, the first two weeks | To start Monday |
| 10 | `10_RISKS_OPEN_QUESTIONS_DECISIONS.md` | Hardware reality, legal/ToS, what could kill this, decisions you must make | Before committing |
| — | `REFERENCES.md` | Every source with arXiv ID / URL | To verify claims |

---

## Naming

This document set uses **Anvil** as a working codename for the *offline harness-evolution subsystem* (the thing that hammers the harness into shape between sessions). It is just a label; rename freely. Anvil is **not** part of the runtime. The runtime is AutoCode as it exists today. Anvil runs on your schedule, may touch the cloud, and emits eval-gated **patch bundles** that AutoCode then runs fully locally.

```
   [ AutoCode runtime ]  ──emits trajectories──▶  [ Anvil (offline) ]
   local-first, cloud-free                         may use cloud teacher
        ▲                                                  │
        └────────────  eval-gated patch bundle  ◀──────────┘
              (new tools, middleware, memory, rules, maybe adapter)
```

This split is the load-bearing idea. If you remember nothing else: **the teacher and the copycat live in Anvil; only their eval-passing artifacts cross back into the runtime, and the runtime never depends on them.**

---

## What "done" means for this program

Success is defined exactly as the source report's closing paragraph defines it, with two additions in bold:

1. AutoCode is **measurably** better each maintenance cycle on your own benchmark suite, **with the model held frozen**;
2. latency and the L1→L4 cost distribution are preserved or improved (an edge agent that gets smarter by escalating more often has *failed*);
3. every modification carries a full provenance trail **and a falsifiable prediction that was checked**;
4. the loop never learns from a teacher/target that lacks explicit authorization.

The frozen-model + cost-distribution constraints (1 and 2) are what make this *AutoCode's* program and not a generic "make the agent smarter" project.
