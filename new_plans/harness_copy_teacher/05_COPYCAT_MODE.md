# 05 — Copycat Mode: Capability Acquisition Done Right

The source report's copycat design assumes you can record another harness's internal traces. You can't (file 01, Correction 3). This file replaces that with the **three channels that are actually observable**, ordered by feasibility and legal safety. All three live in Anvil; none touch the runtime; all are authorization-gated.

---

## 5.0 The authorization registry (keep this from the report)

Before any channel runs, the target must be in `anvil/copycat/registry.yaml`. The report was right about this; it's the difference between "internal capability transfer" and "model extraction."

```yaml
targets:
  - id: claude-code
    channel: [structural]               # which channels are permitted for this target
    source: research-components/claude-code-sourcemap   # local mirror only
    license: "review-before-use"        # you must confirm the mirror's license permits study
    reuse_scope: structure_only         # structure_only | outcomes | weights
    notes: "Public source map. Structural study only. Do NOT ship verbatim code."
  - id: gateway-thinking-alias
    channel: [outcome, self_distill]
    source: "http://localhost:4000/v1"  # your own gateway; a strong model as teacher
    license: "per-provider-ToS"         # SEE FILE 10 — distillation clauses vary by provider
    reuse_scope: outcomes
    rate_limit: { runs_per_day: 200 }
```

`reuse_scope` is the hard gate: `structure_only` forbids shipping the target's code; `outcomes` permits using produced diffs as eval/distill targets; `weights` (training on outputs) is the most ToS-sensitive and defaults off. File 10 covers the legal reality per provider.

---

## 5.1 Channel A — Structural imitation (lowest risk, highest leverage)

**What:** read the *public* structure of strong harnesses and port the *structure*, not the code or traces. Per AHE's ablation, "factual harness structure transfers" — so this is the channel most likely to actually help.

**Why you're already set up:** `research-components/` mirrors claude-code-sourcemap, pi-mono, opencode, openai-codex, aider, goose, open-swe. PLAN §1g already extracted Claude Code's component structure. You have the corpus and a precedent.

**The pipeline (extends your existing TUI-comparison harness, repointed from pixels to structure):**

1. **Component census.** For each reference harness, enumerate its analog of your seven component kinds: what tools does it expose? what's its compaction strategy? does it have subagents? what's its memory model? Write to `anvil/copycat/census/<target>.yaml`.
2. **Gap diff.** Diff each reference's component set against AutoCode's `manifest.yaml`. Output: "opencode has a `/sandbox` mode switch and a 9-op LSP surface AutoCode lacks; codex has symmetric `/resume <id>` + `fork`." (PLAN §1g already lists several of these.)
3. **Capability proposal, not code copy.** For each gap, Anvil proposes a *clean-room* component for AutoCode that achieves the same *capability*, expressed against your manifest, with a prediction contract. **It must not paste the reference's source.** The verifier + eval gate decide if the re-implementation actually helps.

**Concrete first targets** (already surfaced in PLAN §1g's "best from research-components" list):
- middleware: the **Ralph loop** continuation primitive (turns single-session into multi-session) — port the *idea*.
- tool/middleware: opencode's `/sandbox` mode switch + broader LSP op surface.
- subagent pattern: ForgeCode's planner/executor/researcher split (Muse/Forge/Sage) — but only adopt if it survives your eval gate *and* doesn't blow the edge cost budget (3 agents = 3× context; watch `layer_distribution`).

**Hard rule:** structural imitation produces *new AutoCode components evaluated on your oracle*, never vendored third-party code. This keeps you clear of license problems and, per AHE, is where the real transfer is anyway.

---

## 5.2 Channel B — Outcome distillation (medium risk, needs ToS check)

**What:** drive a strong model (via your gateway's `thinking`/`big` alias, or a paid frontier API) on a task, capture **only the observable final artifact** — the diff/patch/file set — and use it two ways:

1. **As an eval oracle.** For a task with no shipped test, the strong model's accepted solution becomes a *reference* the verifier can diff against (weak oracle; use sparingly, prefer executable tests).
2. **As a distillation target** (feeds tier 5, file 10) — *only if* `reuse_scope: weights` and the provider's ToS permits training on outputs.

**Pipeline:**
```
task ──▶ strong model (authorized) ──▶ final diff ──▶ verifier(diff) ──▶ {label, tests}
                                                          │
                              keep only diffs that VERIFY (build+tests pass)
                                                          ▼
                              outcome-pairs corpus: (task, verified_diff)
```

**Critical discipline:** keep *only verified* outcomes. An unverified frontier diff is just a confident guess; storing it pollutes your corpus. The executable verifier (file 04 §4.3) is what makes this channel sound — you're not trusting the teacher, you're trusting the tests.

**Legal reality (file 10, don't skip):** several frontier providers' ToS restrict using their outputs to train competing models. "Structure_only" and "outcomes-as-eval" are far safer than "outcomes-as-training-data." Default to eval use; gate training use behind an explicit per-provider ToS check that you record in the registry.

---

## 5.3 Channel C — Self-distillation (lowest legal risk, best technical fit)

**What:** the report under-emphasizes this and it's the best option. Run **your own AutoCode loop** with a strong model wired in as the L4 brain, log the trajectories *your harness* produces, and use them to improve the local model and harness. The traces are **yours** (your harness, your prompts, your tools) — no third-party trace problem, minimal ToS exposure.

**Why it's the right technical fit:** it's **on-policy** — the trajectories are over states *your harness actually visits* (Thinking Machines OPD; file 03 §4). Off-policy distillation from a foreign harness would teach your small model to imitate states it never reaches. Self-distillation teaches it to handle *its own* situations better.

**Pipeline:**
```
AutoCode harness + L4=strong-model ──▶ trajectories (file 04 §4.2) ──▶ verifier ──▶ keep successes
                                                                            │
   ┌────────────────────────────────────────────────────────────────────────┤
   ▼ harness-level (cheap, tiers 1–3)                                         ▼ weight-level (tier 5, file 10)
   distiller → teacher → playbook/tool/middleware deltas              SOD-style step-wise OPD or QLoRA
   (improve the harness so the LOCAL model succeeds                   on the 1.5B (4060 Ti), gated last
    on what the STRONG model just showed works)
```

**The cheap left branch is the point.** You don't need to retrain to benefit. When the strong-L4 run succeeds on a task the local-L4 run failed, the *difference in their trajectories* tells you what harness change would let the local model succeed too — a new tool, a better retrieval step, a playbook entry. That's harness self-distillation, fully on consumer hardware, no training. Run the expensive right branch only when the harness changes provably can't close the gap.

---

## 5.4 Channel comparison

| | A — Structural | B — Outcome | C — Self-distill |
|---|---------------|-------------|------------------|
| Observability needed | public source (have it) | API output only | your own traces |
| Legal/ToS risk | low (clean-room) | medium (training clause) | low |
| On-policy? | n/a (structure) | partial | **yes** |
| Hardware cost | none | API calls | API calls (+ optional training) |
| AHE-evidence value | **high** (structure transfers) | medium | high (harness branch) |
| Build first? | **yes** | second | second |

**Build order:** Channel A first (you have the corpus and a precedent; lowest risk; highest evidence value). Channel C's *cheap harness branch* second (reuses the trajectory recorder you're building anyway). Channel B and C's *weight branch* last, behind the ToS and hardware gates.

---

## 5.5 What copycat mode is explicitly NOT

- Not scraping Claude Code/Codex internal traces (impossible).
- Not vendoring third-party source into AutoCode (license risk; and structure-port is better anyway).
- Not training on frontier outputs without a recorded per-provider ToS check.
- Not a runtime feature. Copycat runs in Anvil, offline, and only its eval-passing *re-implementations* reach the runtime.

The reframed copycat is, in one line: **acquire capability from what you can legitimately observe — public structure, verified outcomes, and your own on-policy traces — and let the executable oracle decide what actually transfers.**
