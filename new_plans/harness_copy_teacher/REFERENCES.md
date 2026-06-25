# REFERENCES

Sources behind the claims in this set. Grouped by topic. arXiv IDs and URLs are as retrieved June 2026; verify before citing in anything formal.

> Note on dates: several arXiv IDs carry 2026 prefixes (e.g., `2604.*`, `2605.*`, `2602.*`) reflecting submission cycles in early-to-mid 2026. They were the current literature at time of writing this plan.

---

## Harness engineering (the organizing frame)

- **Agentic Harness Engineering (AHE)** — *Observability-Driven Automatic Evolution of Coding-Agent Harnesses.* Lin, Liu, Pan, et al. arXiv:2604.25850 (28 Apr 2026). Code: https://github.com/china-qijizhifeng/agentic-harness-engineering
  - The centerpiece. Frozen model; evolve 7 harness components; three observability pillars (component/experience/decision); 69.7→77.0% on Terminal-Bench 2 over 10 iters; transfers to SWE-bench-Verified at 12% fewer tokens; ablation localizes gains to **tools/middleware/memory, not system prompt**.
- **Agent Harness Engineering** — Addy Osmani (O'Reilly Radar / addyosmani.com, Apr–May 2026). https://www.oreilly.com/radar/agent-harness-engineering/ , https://addyosmani.com/blog/agent-harness-engineering/
  - "Harness is a living system"; Ralph loop; "treat agent mistakes as permanent signals"; the harness gap > the model gap.
- **Harness Engineering for AI Coding Agents** — Augment Code guide (Apr 2026). https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents
  - "Agent = Model + Harness" (LangChain); prompt vs context vs harness layers; DORA measurement.
- **Building AI Coding Agents for the Terminal: Scaffolding, Harness, Context Engineering** — arXiv:2603.05344 (Mar 2026).
  - Scaffolding (pre-prompt: system prompt, tool schemas, subagent registry) vs harness (runtime: dispatch, context mgmt, safety). Three core challenges.
- **ForgeCode / Terminal-Bench 2.0 harness-first writeup** — Hightower (Apr 2026). https://medium.com/@richardhightower/forgecode-dominating-terminal-bench-2-0-...
  - 81.8% on TB2 with Muse/Forge/Sage three-agent split; orchestration > raw model.

## Context / memory evolution

- **ACE — Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models.** Zhang et al. (SambaNova + Stanford + UC Berkeley). arXiv:2510.04618 (6 Oct 2025). Open-sourced Dec 2025: https://sambanova.ai/blog/ace-open-sourced-on-github
  - Evolving playbook; Generator/Reflector/Curator (+Pruner→Master Rules); fixes brevity bias + context collapse via delta updates; +10.6% agents / +8.6% finance; no labeled supervision; lower overhead than fine-tuning *and* prompt optimization.
- **Position: Agentic Evolution is the Path to Evolving LLMs** — arXiv:2602.00359. Survey context distinguishing context/prompt evolution (ACE, SCOPE) from tool/memory synthesis (Youtu-Agent, AgentEvolver).

## Prompt / program optimization

- **GEPA — Reflective Prompt Evolution Can Outperform Reinforcement Learning.** Agrawal et al. arXiv:2507.19457 (25 Jul 2025; ICLR 2026 oral). Code: https://github.com/gepa-ai/gepa ; docs: https://dspy.ai/api/optimizers/GEPA/overview/
  - Genetic-Pareto reflective evolution; reads traces + textual feedback; +~20% vs GRPO, +~13% vs MIPROv2, **35× fewer rollouts**; TerminalBench (Terminus) adapter; DSPy Full Program Adapter (signatures/modules/control flow).

## Distillation (tier-5 lever)

- **On-Policy Distillation** — Thinking Machines Lab (27 Oct 2025). https://thinkingmachines.ai/blog/on-policy-distillation/
  - Student generates own rollouts; teacher scores student-visited states; corrects exposure bias; Qwen3 recipe at a fraction of RL compute.
- **Rethinking On-Policy Distillation: Phenomenology, Mechanism, and Recipe** — arXiv:2604.13016 (Apr 2026). Mechanistic analysis; OPD fragility.
- **SOD — Step-wise On-policy Distillation for Small Language Model Agents.** Lin et al. arXiv:2605.07725 (8 May 2026).
  - Tool-call errors cascade and corrupt teacher token-level supervision in small agents; step-wise divergence reweighting; 0.6B student → 26.13% AIME 2025; up to +20.86% over second-best.
- **SODA — Semi On-Policy Black-Box Distillation** — arXiv:2604.03873. Static snapshot of student's inferior behaviors; ~10× speedup over GAD.
- **Awesome On-Policy Distillation** (survey list) — https://github.com/chrisliu298/awesome-on-policy-distillation (GAD black-box, ROPD rubric-based, MAD-OPD, TCOD, etc.).
- **Small Language Models are the Future of Agentic AI** — Belcak et al. (NVIDIA). arXiv:2506.02153 (2025). The thesis citation for AutoCode's whole premise.

## Benchmarks

- **Terminal-Bench** — 89 human-verified Docker tasks (NL instruction + container + test suite + oracle). Refs: arXiv:2602.21193 ("On Data Engineering for Scaling LLM Terminal Capabilities"), arXiv:2603.05344. TB 2.0 leaderboard (NexAU-AHE 84.7%±2.1, GPT-5.5).
- **SlopCodeBench — Benchmarking How Coding Agents Degrade Over Long-Horizon Iterative Tasks** — arXiv:2603.24755. Long-horizon degradation; native-harness evaluation argument; pass^k reliability.
- **SWE-bench / SWE-agent** — Jimenez/Yang et al. (referenced via AHE transfer results and the terminal-agent survey). The cross-benchmark transfer target.

## Classical foundations (kept from the source report)

- Knowledge distillation (Hinton et al., 2015); Distilling Step-by-Step (Hsieh et al., 2023).
- Self-Refine (Madaan et al., 2023); Reflexion (Shinn et al., 2023); Constitutional AI / RLAIF (Bai et al., 2022; Lee et al., 2023).
- Let's Verify Step by Step / process supervision (Lightman et al., 2023).
- ReAct (Yao et al., 2022); Toolformer (Schick et al., 2023).
- DSPy (Khattab et al.); MCP (Anthropic, 2024).
- HELM (Liang et al.); GAIA (Mialon et al.); LLM-as-a-judge / MT-Bench (Zheng et al., 2023).
- LoRA (Hu et al., 2021); QLoRA (Dettmers et al., 2023).
- NIST AI RMF (Govern/Map/Measure/Manage); W3C PROV.

## Repo-internal sources (AutoCode / lowrescoder)

- `README.md`, `north-star.md`, `PLAN.md` (2,327 lines), `AGENTS.md`, `CLAUDE.md` @ `Abbiirr/lowrescoder` master.
- `docs/research/harness-improvement-proposal-v2-2026-04-08.md` (+ adoption plan), `autocode-internal-first-orchestration.md`, `large-codebase-comprehension-and-external-harness-orchestration.md`.
- `research-components/` mirrors: claude-code-sourcemap, pi-mono, opencode, openai-codex, aider, goose, open-swe.
- PLAN §0 (4-plane context, tool metadata, artifact resumability), §1f (stable-v1: memory/skills/hooks/permissions/compaction), §1g (TUI-comparison Tracks 1–4), §2 (external-harness orchestration), §3 (Terminal-Bench / harness engineering).
