# autocode — goal (the north star the self-improving loop optimizes toward)

## Mission
Make autocode the strongest autonomous coding harness we can, measured on external
harness benchmarks — Terminal-Bench, SWE-bench Verified, BaxBench, and our proxy
lanes. Concrete bar: beat the Codex gpt-5.5:xhigh baseline of **81.5% (22/27)** on
harness-bench v2, then push higher and hold it across lanes.

## What "better" means (priority order)
1. **More tasks RESOLVED** on held-out tasks — the only score that counts.
2. **No regressions** — a fix for one failure class must not break a passing task.
3. **Robustness** — degrade gracefully under gateway flakiness; infra-fails are neither wins nor losses.
4. **Efficiency** — same result with fewer tool calls / tokens / wall-time is better, never the reverse.
5. **Simplicity** — the smallest harness that clears the bar. Deleting beats adding.

## Where gains come from (the agent-computer interface, not the model)
Edit the harness under `src/autocode/` only: system prompt, tool definitions &
schemas, the agent loop / retry / stagnation logic, context loading & compaction,
auto-verification. Fix the *failure class* a trace reveals, not the one-off symptom.

## Hard rails (non-negotiable — a change that breaks one is a failure, not progress)
- Edit ONLY `src/autocode/`. Never touch graders, fixtures, `verify.sh`, `benchmarks/`, or tests used as oracle.
- Never weaken, stub, loosen, or disable a check to make a task pass.
- No new dependencies. No mutating git. Every change minimal and reversible.
- Don't overfit one lane (must not regress others). Don't reward-hack the grader.

## Done
A sustained, multi-lane lift on a frozen validation slice with every rail intact —
not one lucky run. A gain that doesn't hold in the ledger is not a gain.
