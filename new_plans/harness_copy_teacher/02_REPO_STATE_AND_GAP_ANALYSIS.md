# 02 — Repo State & Gap Analysis

Read of `Abbiirr/lowrescoder` @ `master` (349 commits): README, `north-star.md`, `PLAN.md` (2,327 lines), plus the directory tree. This is **not** a greenfield project and the source report's "if I were turning this into a build plan today" framing badly under-rates how much already exists. The gap is narrower and more specific than the report assumes.

> Caveat per your standing instruction: claims below come from the public repo surface I could read. Anything not directly visible (internal module behavior, test pass rates beyond what PLAN.md asserts) is marked *(asserted in PLAN, unverified)*. Treat the repo's own docs as the source of truth over this file where they conflict.

---

## What AutoCode is, concretely

- **Edge-native coding agent.** Local-first, deterministic-first, 8 GB VRAM / 16 GB RAM target. Classical AI (tree-sitter, LSP, static analysis) is the *primary* intelligence layer; LLM is last resort.
- **Split architecture.** Rust TUI (crossterm + ratatui + tokio, ~2.4 MB binary) ⇄ Python backend (agent loop, tools, providers, sessions) over **JSON-RPC 2.0 on stdin/stdout via PTY**. Wire contract: `docs/reference/rpc-schema-v1.md`.
- **4-layer intelligence model** with declared latency/token budgets:
  - L1 deterministic (<50 ms, 0 tokens) — AST/lexical, static analysis, LSP queries
  - L2 retrieval (100–500 ms, 0 tokens) — AST-aware chunking, keyword+vector search, repo map
  - L3 constrained generation (500 ms–2 s, 500–2k tokens) — grammar-constrained, 1.5B model; *opt-in optional-extra, dormant in core installs* (PLAN `S-L3DOC`)
  - L4 full reasoning (5–30 s, 2k–8k tokens) — larger model, multi-file planning, architect/editor
- **LLM Gateway** (your `lmwrapper` project): OpenAI-compatible, 9 free providers with auto-failover + latency routing, model aliases (`coding`/`fast`/`thinking`/`local`/…). AutoCode points at `http://localhost:4000/v1`.
- **Maturity markers** *(asserted in PLAN, unverified)*: ~1,999 Python tests, ~210 Rust TUI tests, ~199 benchmark; multiple closed "tranches"; release-grade regression sweeps; PTY smoke harnesses; deterministic mock backend.

---

## The decisive asset: this repo already has the substrate AHE needs

Agentic Harness Engineering needs three observability pillars (file 03/04). AutoCode already has strong precursors for all three. This is why the build is tractable.

| AHE pillar | What it requires | What AutoCode already has | Gap |
|------------|------------------|---------------------------|-----|
| **Component observability** | Every editable harness component as a revertible, file-level, git-tracked unit | Docs-as-source-of-truth culture; everything git-tracked; `north-star`/`CLAUDE.md`/`AGENTS.md` authority chain; skills as folders; tools with metadata (PLAN §0.4); 4-plane context model (PLAN §0.1) | A **machine-readable component manifest** that enumerates each component + its file + its edit surface |
| **Experience observability** | Trajectories distilled into a layered, drill-down evidence corpus | Append-only sessions; `log.jsonl`/`context.jsonl` discussion; checkpoint store; artifact collector; consolidation/compaction with provenance (PLAN §1f.4, §0.5) | A **trajectory schema + distiller** that turns raw sessions into the evidence corpus (and an *outcome label* per task) |
| **Decision observability** | Every edit paired with a prediction, verified next round | Verification profiles + hooks; QA test-results discipline; `AGENTS_CONVERSATION.MD` review entries with severity | The **prediction-contract record** and the verifier that scores predictions against outcomes |

You are not starting from zero on any pillar. You're adding a manifest, a trajectory distiller, and a prediction ledger on top of substrate that already exists.

---

## The decisive asset #2: the reference-harness corpus already exists

PLAN §1g documents that `research-components/` mirrors **claude-code-sourcemap, pi-mono, opencode, openai-codex, aider, claw-code, goose, open-swe**, and §1g already *extracted* Claude Code's `Logo.tsx`, `Spinner.tsx`, `PromptInput.tsx`, `REPL.tsx`. There's also a feature-audit checklist (`docs/plan/research-components-feature-checklist.md`) and a 7-TUI capture probe.

This is **structural copycat infrastructure that already works** (Correction 3, channel 2). You can diff AutoCode's harness components against the reference harnesses' components *today*, without any new scraping. The TUI-comparison harness (Tracks 1–4 in PLAN §1g) is a working template for the kind of capture/compare/gate pipeline Anvil needs — just pointed at *behavior/outcomes* instead of *pixels*.

---

## What's already on the roadmap (don't duplicate — extend)

PLAN.md's ordered backlog already contains the exact slots this program belongs in:

- **Section 2 — Native External-Harness Orchestration** *(backlog)*: "keep as post-stabilization harness roadmap." This is where **copycat (channels 1–2)** and the harness-adapter work live. `autocode/src/autocode/external/harness_adapter.py` already exists (referenced in PLAN §0.4).
- **Section 3 — Terminal-Bench / Harness Engineering** *(backlog)*: "re-measure before broadening." This is where the **eval flywheel + Anvil's evolution loop** live.
- **Section 0 — Harness Architecture Refinement** *(landed foundation)*: the 4-plane context model, durable-memory write rules, canonical runtime-state, tool metadata, artifact-first resumability. **Anvil's component manifest should be built on top of §0, not beside it.**
- Research corpus: `docs/research/harness-improvement-proposal-v2-2026-04-08.md` (+ adoption plan), `autocode-internal-first-orchestration.md`, `large-codebase-comprehension-and-external-harness-orchestration.md`. **Anvil's design doc should cite and extend these, not fork them.**

**This program = Sections 2 + 3, executed with the AHE/ACE/GEPA toolkit, gated on the eval flywheel.** It is not a new architecture. Frame it that way in the repo or it'll read as a competing direction and trip the north-star guardrails.

---

## Gap list (what must be built)

Ordered by dependency. Detail and code in files 04–09.

1. **Component manifest** (`G1`) — a YAML/JSON file enumerating every editable harness component, its source file(s), its edit surface, and its "plane" (durable instruction / durable memory / live session / ephemeral). Built on PLAN §0.1 + §0.4. *Blocks everything; it defines Anvil's action space.*
2. **Trajectory schema + recorder** (`G2`) — a typed record per task run: inputs, retrieved context, tool calls + args + observations, layer-escalation path, final diff, **executable outcome label** (build/test/lint/types), latency, tokens, cost. Extends existing session storage. *Blocks the eval corpus and the teacher.*
3. **Outcome verifier** (`G3`) — the deterministic oracle: apply diff → build → test → lint → typecheck, emit a structured verdict. Wraps existing verification profiles. *Blocks teacher and self-maintenance gate.*
4. **Eval corpus builder** (`G4`) — turn recorded trajectories + a Terminal-Bench harness into a held-out, versioned eval suite with executable oracles. *Blocks any trustworthy patch gate.*
5. **Experience distiller** (`G5`) — AHE pillar 2: roll millions of trajectory tokens into a layered, queryable evidence corpus the meta-agent can consume. *Blocks the evolution loop's quality.*
6. **Teacher pipeline** (`G6`) — execution-grounded critique → root-cause attribution → teaching packet → ACE-style playbook delta. *The first user-visible capability; ship it first (file 09).* 
7. **Copycat channels** (`G7`) — outcome distillation harness (channel 1, authorization-gated) + structural-diff tooling against `research-components/` (channel 2). Channel 3 (self-distillation) reuses G2.
8. **Self-maintenance engine / Anvil loop** (`G8`) — prediction contracts, patch bundles, eval gate, canary, auto-revert, kill switch.
9. **Distillation lane** (`G9`, optional, last) — QLoRA/black-box-OPD on the 1.5B, on the 4060 Ti, gated behind 1–8.

---

## What you should *not* build

- **A new architecture.** Sections 0–3 + the 4-layer model already exist. Anvil sits beside the runtime and feeds it; it does not replace anything.
- **A trace scraper for closed agents** (Correction 3). Dead end.
- **A browser/WebNN runtime** (Correction 1). Category error.
- **A judge-primary eval** (Correction 4). You have executable oracles; use them.
- **A weight-training-first plan** (Corrections 2 & 6). Hardware and evidence both say no.

---

## One honest risk specific to the repo

PLAN.md shows an *enormous* amount of process machinery — tranches, checklists, QA artifacts, review entries, multiple overlapping plan docs with "SUPERSEDED" banners. That discipline is a strength for a self-improving system (it *is* the provenance trail). But it's also a sign that **velocity is dominated by process overhead.** Anvil adds another autonomous editor to that system. If the meta-agent's edits aren't held to the *same* git-tracked, prediction-checked, eval-gated discipline as human edits — or if they multiply the doc-reconciliation burden — Anvil will make the process problem worse, not better. File 07's falsifiable-contract design and file 10's risk register both treat this as a first-class concern.
