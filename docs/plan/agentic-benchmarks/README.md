# Agentic Benchmarks Plan

> Tests that measure the **coding agent system**, not the underlying LLM model.
> The model can be swapped. What matters is what the agent adds on top.

## Why This Matters

On SWE-bench Verified, switching only the scaffold (agent layer) causes up to **15% performance difference** with the same model. A weaker model with a strong scaffold outperforms a stronger model with a weak scaffold. The agent system is the variable that matters most — and it's testable.

## Key Principle

**Every test in this suite must produce different results when you change the agent while keeping the model constant.** If swapping models changes the score more than swapping agent configurations, the test is measuring the model, not the agent.

## Documents in This Folder

| Document | Purpose |
|----------|---------|
| [philosophy.md](philosophy.md) | Why agent benchmarks differ from model benchmarks, with evidence |
| [test-dimensions.md](test-dimensions.md) | 12 concrete test dimensions with patterns and metrics |
| [scenario-catalog.md](scenario-catalog.md) | Full catalog of runnable test scenarios |
| [scoring-framework.md](scoring-framework.md) | How to score agent quality across dimensions |
| [implementation-roadmap.md](implementation-roadmap.md) | Phased rollout plan with priorities |
| [research-references.md](research-references.md) | All external benchmarks and papers referenced |

## Quick Summary: The 12 Test Dimensions

| # | Dimension | What It Measures | Key Metric |
|---|-----------|-----------------|------------|
| 1 | Tool Routing | Does the agent pick the right tool? | Tool calls vs optimal baseline |
| 2 | Context Retrieval | Does it find the right code to read? | F1 at file/block/line level |
| 3 | Edit Accuracy | Are edits syntactically correct and clean? | Application success rate |
| 4 | Error Recovery | Does it fix failures on retry? | Pass-after-retry rate |
| 5 | Fault Tolerance | Does it degrade gracefully under failures? | Degradation curve slope |
| 6 | Multi-File Coordination | Can it modify related files consistently? | Cross-file consistency rate |
| 7 | Context Scaling | Does it handle large codebases? | Performance retention at scale |
| 8 | Planning Quality | Does it break tasks into correct steps? | Step order correctness |
| 9 | Recovery from Corruption | Can it fix a broken state? | Recovery rate vs fresh rate |
| 10 | Regression Prevention | Does it avoid breaking existing code? | P2P test pass rate |
| 11 | Consistency (pass^k) | Does it produce the same result every time? | pass^k score |
| 12 | Cost Efficiency | How many tokens per resolved task? | Tokens/task ratio |

## Lane Definitions

| Lane | Trigger | Scenarios | Graders | Repetition |
|------|---------|-----------|---------|------------|
| **PR Core** | Every pull request | Calc + BugFix + CLI (3 only) | Deterministic only | Replay-first; `>=2/3` for fresh |
| **Regression Nightly** | Nightly schedule | PR Core + Wave 1 (9 total) | Deterministic + heuristic | pass^3 consistency |
| **Capability** | Nightly schedule | Full catalog | Deterministic + heuristic + sampled LLM | `>=2/3` of 3 runs |
| **Stress** | Weekly schedule | Fault injection variants | Deterministic + fault metrics | 5 runs per fault rate |

**Key policy:** LLM grader is **OFF by default** on PR lane. Opt-in via `--with-llm-grader` for sampled nightly analysis. See `scoring-framework.md` for the full suite config schema.

---

## Relationship to Existing Benchmark Hardening

The 17-item benchmark hardening plan (Entries 207/209/214/219) built the **infrastructure** — verdicts, replays, budgets, strict mode, multi-run, matrix testing. This plan builds the **test content** — what scenarios to run and what agent capabilities they measure.

| Layer | What Exists | What This Plan Adds |
|-------|------------|-------------------|
| Infrastructure | Sandbox, logging, verdicts, multi-run, replay | (already done) |
| Calculator scenario | 100-point rubric, 7 categories | (already done) |
| BugFix/CLI scenarios | Manifests defined, runner stubbed | Seed fixtures, scoring, wiring |
| Agent-specific tests | Nothing | 12 dimensions, 20+ scenario types |
