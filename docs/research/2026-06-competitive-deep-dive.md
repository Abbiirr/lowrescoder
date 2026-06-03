# AutoCode Competitive Deep Dive — June 2026

Scope: SOTA in coding-agent harnesses as of mid-2026, focused on what AutoCode
(local-first, 4-layer, Python + Rust TUI) can lift, copy, or sidestep.

Confidence legend: **[H]** = well-supported by multiple primary sources or
vendor docs; **[M]** = consistent across secondary aggregators but not directly
verified from primary source; **[S]** = single source / speculative / vendor
self-report — treat as direction not gospel.

---

## A. Benchmark leaderboards (mid-2026)

The benchmark map has split into "model" leaderboards and "agent + model"
leaderboards, with the gap between the two now being the main story.

- **SWE-bench Verified** — Claude family dominates. Aggregators report Claude
  Mythos Preview at ~93.9% and Claude Opus 4.8 at ~88.6% (Jun 2026 snapshot)
  **[S]**, with Anthropic-internal scaffolds doing the heavy lifting. Cognition's
  Devin 2.0 sits around 45.8% "standard" (single-agent, no BoN, no human)
  **[M]**. Llama3-SWE-RL-70B is the strongest RL-fine-tuned open baseline at
  41.0% **[H]**, and a 72B agent RL-trained from a 20% base to 39% shows the
  ceiling of pure-RL without scaffolding **[H]**.
  ([BenchLM](https://benchlm.ai/benchmarks/sweVerified),
  [SWE-RL/ICLR'26](https://openreview.net/forum?id=ULblO61XZ0),
  [arXiv 2508.03501](https://arxiv.org/html/2508.03501v1))

- **SWE-bench Pro** — the most useful diagnostic this cycle. Same Opus 4.5
  goes 45.9% raw → 50.2% in Cursor → 55.4% in Claude Code; GPT-5.3-Codex with
  custom scaffold hits 57%. **Scaffolding alone is worth 5–10 points**, and
  "superior context retrieval" alone is a 4–10 point lift **[H]**.
  ([Morph LLM](https://www.morphllm.com/swe-bench-pro))

- **SWE-bench-Live / Multi-SWE-bench** — Microsoft's continuously-refreshed
  benchmark (1,319 issues from real GitHub since 2024, +50/month, plus a
  Windows/PowerShell track and a MultiLang HF release). Headline: contamination
  resistance reshuffles open-model ranking vs. Verified **[H]**.
  ([SWE-bench-Live](https://swe-bench-live.github.io/),
  [NeurIPS'25 paper](https://arxiv.org/pdf/2505.23419))

- **Terminal-Bench 2.0** — GPT-5.5 ~82.0%, Gemini 3.5 Flash 76.2%, Opus 4.8
  74.6% on the public leaderboard **[M]**. Crucially, the **same model swings
  2–6 points based purely on the agent wrapper** — Forge Code + Gemini 3.1 Pro
  hits 78.4%, Factory Droid + GPT-5.3-Codex 77.3%, while the underlying models
  alone trail noticeably **[H]**.
  ([tbench.ai](https://www.tbench.ai/leaderboard/terminal-bench/2.0),
  [Morph TB2](https://www.morphllm.com/terminal-bench-2))

- **LiveCodeBench** — Gemini 3 Pro Preview 91.7%, Gemini 3 Flash 90.8%,
  DeepSeek V3.2 Speciale 89.6% (May 2026) **[M]**. Reasoning models now sit
  near the saturation line; competitive coding is no longer the differentiator.
  ([LiveCodeBench leaderboard](https://llm-stats.com/benchmarks/livecodebench))

- **SWE-Lancer** — small but informative leaderboard: GPT-5.1 Codex 0.663 on
  the main split; GPT-5 hits 1.000 on IC-Diamond **[M]**. Vendor-self-reported,
  so treat as directional.
  ([SWE-Lancer leaderboard](https://llm-stats.com/benchmarks/swe-lancer))

**Headline implication for AutoCode**: the harness gap is now wider than the
model gap on every benchmark that matters. Spending engineering on scaffold
quality has higher ROI than chasing a model swap.

---

## B. Scaffolding techniques that broke through (late 2025 → early 2026)

1. **Test-time compute via summary-and-vote** — Joongwon Kim et al.'s
   "Scaling Test-Time Compute for Agentic Coding" (arXiv 2604.16529, ICLR'26
   submission) introduces **Recursive Tournament Voting** over compact rollout
   summaries plus **Parallel-Distill-Refine** for sequential scaling. Lifts
   Claude-4.5-Opus on SWE-bench Verified from 70.9% → 77.6% and Terminal-Bench
   v2.0 from 46.9% → 59.1% **[H]**. The key insight: don't vote on raw
   trajectories, vote on **distilled hypothesis summaries** — preserves signal,
   discards noise.
   ([HF papers/2604.16529](https://huggingface.co/papers/2604.16529))

2. **SWE-RL & execution-free reward** — SWE-RL (ICLR'26) used GitHub commit
   pairs as ground truth with similarity-based rewards; Llama3-SWE-RL-70B hit
   41.0% on Verified **[H]**. The Dec 2025 SWE-RM paper added execution-free
   feedback so RL doesn't need a working test harness for every step — much
   cheaper signal.
   ([SWE-RL](https://openreview.net/forum?id=ULblO61XZ0),
   [SWE-RM](https://www.arxiv.org/pdf/2512.21919))

3. **Multi-agent verification (BoN-MAV)** — multiple verifier models on
   distinct rollouts scales better than self-consistency or single reward
   models. Maps cleanly onto AutoCode's L1/L2 deterministic checks acting as
   cheap verifiers around the L4 generator **[H]**.
   ([arXiv 2502.20379](https://arxiv.org/pdf/2502.20379))

4. **Anthropic's "long-running harness" pattern (Nov 2025)** — two agents:
   an **initializer** that emits `init.sh`, a `claude-progress.txt`, an initial
   git baseline, and a JSON feature list (200+ pass/fail items), then a
   **coding agent** that resumes per session and verifies via Puppeteer MCP.
   Five principles: constrain, inform, verify, correct, keep humans in loop
   at high-stakes points **[H]**. AutoCode's checkpoints + `/rollback` already
   echo this; the missing piece is the explicit per-session **progress file**
   and an initializer-coder split.
   ([Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents))

5. **Claude Code Dynamic Workflows (May 2026)** — JS orchestration scripts
   fan out up to 1,000 subagents, 16 concurrent. Jarred Sumner ported ~1M LoC
   Zig→Rust in 6 days using it **[M]**. The architectural lesson: subagent
   state lives in script variables **outside** the parent context window —
   the orchestrator is a program, not a prompt.
   ([MarkTechPost](https://www.marktechpost.com/2026/05/28/anthropic-ships-claude-opus-4-8-alongside-dynamic-workflows-and-cheaper-fast-mode-with-workflows-capped-at-1000-subagents/),
   [CloudZero](https://www.cloudzero.com/blog/claude-code-agents/))

6. **Cursor Composer-1 & Morph Fast Apply** — separate, small, fast "edit
   merger" models. Morph's 7B applies edits at **10,500 tok/s with ~96–98%
   accuracy**, turning a 1k-line file merge into 1.3s instead of 60s+ on a
   frontier model **[H]**.
   ([Morph fast-apply](https://www.morphllm.com/fast-apply-model))

---

## C. Local-model coding harness reality (mid-2026)

**Strongest open coding models** (consensus across LiveBench, kilo.ai, Pinggy,
InsiderLLM, MarkTechPost, May–Jun 2026):

| Model | Coding signal | Notes |
|---|---|---|
| Qwen3-Coder-Next (80B MoE / 3B active) | ~70.6% SWE-bench Verified **[S]** | Designed for agents, 256K ctx, GGUF available |
| Kimi K2.6 Thinking (1T / 42B active) | 78.6 LiveBench coding, 58.3 agentic **[M]** | Too large for 8GB VRAM target |
| DeepSeek V4 / V3.2 Speciale | 69.99 LB / 89.6 LCB **[M]** | V3.2 lighter quants viable on 24GB |
| GLM-5 / GLM-5.1 | 73.6 / 75.4 LB coding **[M]** | Strong agentic scores |
| Devstral 2 / Devstral Small 2 (24B) | 68% SWE-bench Verified **[S]** | Mistral, agent-tuned |
| Qwen3-Coder 32B / Qwen2.5-Coder 32B | 73.7 Aider **[H]** | Sweet spot for AutoCode's 16GB RAM target |

For AutoCode's **8GB VRAM / 16GB RAM** envelope, **Qwen3-Coder 32B quantized
(Q4_K_M)** and **Qwen3-Coder-Next 80B MoE with 3B active** are the two
realistic anchors. The MoE wins on quality-per-active-param if RAM allows
weight residency.

**Prompt / KV-cache reuse** is the highest-ROI local optimization:

- vLLM Automatic Prefix Caching and SGLang RadixAttention are the standards.
  SGLang's token-level radix tree beats vLLM's block-level hashing for
  dynamic/multi-turn workloads; in agent loops with stable system prompts +
  retrieved context, **60–85% hit rates** drop per-call cost 5–12× **[H]**.
  ([vLLM APC docs](https://docs.vllm.ai/en/stable/design/prefix_caching/),
  [SGLang vs vLLM](https://medium.com/byte-sized-ai/prefix-caching-sglang-vs-vllm-token-level-radix-tree-vs-block-level-hashing-b99ece9977a1),
  [KVFlow](https://arxiv.org/html/2507.07400v1))

- llama.cpp's prompt cache works but is per-process; for AutoCode's
  multi-session model, SGLang is the cleaner local backend.

**Constrained decoding for tool-call reliability**:

- **XGrammar / XGrammar-2** is now the default backend for vLLM, SGLang, and
  TensorRT-LLM. <40 µs/token overhead; guarantees **100% schema-valid tool
  calls** and meaningfully improves tool-call accuracy on smaller models **[H]**.
  ([XGrammar-2 blog](https://blog.mlc.ai/2026/05/04/xgrammar-2-fast-customizable-structured-generation),
  [JSONSchemaBench](https://arxiv.org/pdf/2501.10868))
- Outlines suffers compile-time timeouts on complex recursive schemas, lowest
  compliance in JSONSchemaBench **[H]**. Don't ship Outlines for tool calls.

**Speculative decoding**: EAGLE-3 / Medusa / DeepSeek MTP are the production
defaults; ~2.8× latency, ~47% cost reduction quoted on Llama-3.1 / H100 **[M]**.
For agent loops on local hardware, **SuffixDecoding** (cache-aware draft over
recent tokens) shines because the conversation prefix is highly predictable.
([Premai](https://blog.premai.io/speculative-decoding-2-3x-faster-llm-inference-2026/),
[SuffixDecoding](https://arxiv.org/pdf/2411.04975))

**Tool-call format on open weights**: **Hermes JSON** has won the
interoperability war. Qwen3's chat template natively supports the Hermes
tool-use convention; Hermes Agent on Qwen3.6-35B-A3B reports **37.0 MCPMark
and 73.4% SWE-bench** **[S]** with the same parser stack across model families.
Qwen2.5:32b matches GPT-4.1 on tool-init reliability in the 1,980-instance
eval **[M]**. **Recommendation: standardize AutoCode on Hermes JSON tool
schema with per-provider parsers — same path Hermes Agent took.**
([Hermes/Qwen3.6 setup](https://lushbinary.com/blog/hermes-agent-qwen-3-6-setup-guide/),
[Qwen function-call docs](https://qwen.readthedocs.io/en/latest/framework/function_call.html))

---

## D. Agent architecture patterns winning in 2026

- **Single-agent is winning the default**, multi-agent wins on parallelizable
  fan-out. Google Research: multi-agent gives +81% on parallelizable tasks but
  **−70% on sequential ones**. Operand Quant (single-agent) beat multi-agent
  systems on MLE-Bench **[H]**. Settled: code edits are usually sequential →
  single-agent; research / breadth-first exploration → multi-agent.
  ([Augment guide](https://www.augmentcode.com/guides/single-agent-vs-multi-agent-ai),
  [Operand Quant](https://arxiv.org/pdf/2510.11694))

- **Memory**: Letta (production MemGPT) is the default for serious long-horizon
  agents; LangMem only wins inside LangChain shops. **But for coding harnesses,
  most leaders roll their own** — Anthropic uses `claude-progress.txt` + JSON
  feature list, Claude Code uses a 5-layer compaction pipeline, Cursor uses
  Merkle-tree-hashed tree-sitter chunks **[H]**.
  AutoCode's Scratch Store + File-System Memory are already on this trajectory;
  the gap is **episodic recall** (which past session solved what).

- **Verification patterns now winning**: "edit-then-verify" loops with cheap
  deterministic verifiers (compile, type-check, fast tests) are the dominant
  pattern. SWE-Bench Pro shows the 22-point swing between basic and
  verifier-equipped scaffolds **[H]**. AutoCode's auto-verify loop + L1
  deterministic layer is exactly the right shape — invest in **more L1
  verifiers** not bigger L4.

- **MCP**: 10K+ active public servers (Dec 2025), 97M monthly SDK downloads,
  9,652 registry records, 15,926 GitHub repos by May 2026. Cross-vendor:
  Anthropic, OpenAI, Google, MS, Cursor, ChatGPT, Vercel **[H]**. MCP is no
  longer optional. Killer MCP servers for coding: filesystem, git, GitHub,
  Puppeteer (Anthropic uses for verify), Sentry, Linear, Postgres. **Should a
  harness be MCP-first?** Yes for *tool surface*; no for *core edit/verify
  loop* (latency + auditability still better in-process).
  ([MCP roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/),
  [Digital Applied stats](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol))

---

## E. UX & user adaptation

- **Beyond static AGENTS.md / CLAUDE.md**: a Feb 2026 ETH Zurich study found
  **LLM-generated context files lower task success by ~3% and raise cost by
  20%+**; human-written files improve success by ~4% **[M]**. Auto-scaffolders
  are net-negative. The 2026 trend is **learned long-term + short-term
  preference vectors** (VARS-style), but mainstream tools still ship static
  files. Opportunity for AutoCode: **emit a CLAUDE.md *template* and have the
  user fill it in** rather than auto-generating it.
  ([Codersera comparison](https://codersera.com/blog/agents-md-vs-claude-md-vs-cursor-rules-comparison-2026/))

- **Edit format**: Diff-XYZ (arXiv 2510.12487) found **udiff variants win for
  apply, search-replace wins for diff generation, and modified-udiff wins for
  smaller open models** **[H]**. Practical answer: open-weights 32B → ship
  **search/replace blocks** as the primary format; reserve unified diffs for
  multi-hunk edits; offload to a Morph-style **fast-apply 7B** if you need
  whole-file rewrites cheap.
  ([Diff-XYZ](https://arxiv.org/html/2510.12487v1),
  [Morph diff format](https://www.morphllm.com/edit-formats/diff-format-explained))

- **Plan-Act split**: now consensus. Anthropic, Cline, Cursor, and the
  Refine-Plan-Act pattern all agree. Net win for complex tasks; small overhead
  on trivial ones **[H]**. AutoCode's plan mode is on the right track.
  ([Anthropic harness post](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents),
  [Cline plan&act](https://cline.bot/blog/plan-smarter-code-faster-clines-plan-act-is-the-paradigm-for-agentic-coding))

- **TUI affordances that matter** (cross-tool consensus): visible diffs
  before apply, per-tool checkpoints + 1-key rollback, spinner that shows
  *what* the agent is doing (verb-level), thinking/output split, parallel
  session view. AutoCode already has all of these — the gap is the
  **session-resume UI** (which file, which feature, which test failed last).

---

## F. Things to cut / avoid (2024–25 cargo culting)

- **Elaborate ReAct loops**: ICLR-tracked work shows ReAct brittleness in
  partially observable / dynamic environments; ReflAct and grounded variants
  outperform vanilla ReAct **[H]**. Don't ship vanilla Thought→Action→Obs.
  ([ReflAct](https://arxiv.org/pdf/2505.15182))

- **Too many tools**: Vercel cut **80%** of their agent's tools and got
  better results. A 2025 study found a non-linear cliff: at ~107 tools, agents
  fail tasks they ace at 10 tools. >20 tools in the system prompt degrades
  perf **[H]**. Start at 4–5 atomic tools; gate the rest behind **logit
  masking by task phase**.
  ([Phil Schmid](https://www.philschmid.de/agent-harness-2026))

- **Auto-generated CLAUDE.md / AGENTS.md** — net-negative per ETH Zurich
  **[M]**. Stop shipping the auto-scaffolder.

- **Autonomous self-modification of the harness**: zero evidence this wins;
  high evidence it produces silent regressions. AutoCode's no-LLM-writes-to-
  harness-config invariant is correct.

- **Bloat**: indexing pipelines that never finish on large repos (Continue's
  documented scalability issue) **[M]**. Aider's symbol-graph repo-map
  remains the lean winner.

---

## G. High-leverage design choices for AutoCode

1. **Vote on summaries, not rollouts.** Add Recursive Tournament Voting over
   compact L4 rollout summaries — published 7+ point gain on SWE-bench
   Verified for Opus 4.5. Costs more compute but matches "L4 as last resort"
   philosophy: only fire when L1–L3 disagree.

2. **Ship a Morph-style Fast-Apply path.** Train or vendor a 3–7B
   apply-only model and route all whole-file rewrites through it. 10× latency
   improvement on the dominant cost step; survives even when L4 is gateway.

3. **Hermes JSON + XGrammar-2 as the only tool-call path.** Drop any
   provider-specific parser. 100% schema validity and tool-call accuracy
   floor goes way up on open weights. Re-export per provider where needed.

4. **SGLang as primary local backend.** RadixAttention prefix caching is
   the single biggest local-cost optimization available; 60–85% hit on agent
   loops, 5–12× cost drop. Keep Ollama as fallback only.

5. **Initializer + Coder pattern over current single-agent loop.** Borrow
   Anthropic's two-agent split: an init agent that emits a JSON feature list
   and `progress.md`, then per-session coder agents that resume. Closes the
   long-horizon gap without requiring memory infra.

6. **Cap tools at 8 visible + phase-gated rest.** Use AutoCode's plan mode
   as a phase marker; mask logits to expose only that phase's tools. Avoids
   Vercel's 80%-cut problem before you ship it.

7. **Search/replace as default edit format on local; udiff on frontier;
   structural patches via L1 only.** Pick per model class.

8. **Session resume UI in the TUI.** Single screen: last feature, last failing
   test, last edit. The "where did I leave off" answer.

9. **Verifier farm, not bigger model.** Each L1 verifier (lint, types, fast
   tests, deterministic refactor checks) is a BoN-MAV vote. Add 3–5 more cheap
   verifiers before adding any new model.

10. **Treat MCP as the tool *surface*, not the loop.** AutoCode keeps its
    deterministic core in-process; MCP servers (filesystem, git, GitHub,
    Puppeteer, Postgres) plug in for surface area without bloating L4.

---

## "Do this first" — top 5 priorities

Ranked by leverage × shippability for AutoCode in the next 4–6 weeks:

1. **Adopt Hermes JSON tool-call format + XGrammar-2 backend** (everywhere:
   gateway, Ollama, vLLM). Single biggest reliability win on local 32B models;
   eliminates parser drift and gives 100% schema validity floor. Low risk.

2. **Add Recursive Tournament Voting over rollout summaries for L4 escalation
   only.** Reuse existing checkpoint infra to capture rollouts; summary
   prompt is small. Published evidence: +7 SWE-bench Verified on Opus 4.5.
   Aligns perfectly with "LLM as last resort."

3. **Ship the Initializer + Coder split with a JSON feature list and
   `progress.md`** behind `/plan`. Closes long-horizon gap; no new infra
   needed beyond what `/plan` and Scratch Store already provide.

4. **Wire SGLang as a first-class local backend with prefix caching enabled
   by default.** Realistic 5–12× per-call cost drop on tight agent loops.
   Compatible with existing OpenAI-shaped gateway.

5. **Cap tools visible to L4 at ≤8 with phase-gated unlock.** Cheap to
   implement; backed by Vercel's 80% cull and the 107-tool cliff. Will
   measurably improve tool-call success on Qwen3-Coder-class models.

---

## Sources

- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Scaling Test-Time Compute for Agentic Coding (Kim+ 2026)](https://huggingface.co/papers/2604.16529)
- [SWE-RL (ICLR'26)](https://openreview.net/forum?id=ULblO61XZ0)
- [SWE-RM execution-free feedback (Dec 2025)](https://www.arxiv.org/pdf/2512.21919)
- [Training Long-Context Multi-Turn SE Agents with RL](https://arxiv.org/html/2508.03501v1)
- [Multi-Agent Verification BoN-MAV](https://arxiv.org/pdf/2502.20379)
- [Diff-XYZ benchmark](https://arxiv.org/html/2510.12487v1)
- [JSONSchemaBench](https://arxiv.org/pdf/2501.10868)
- [SuffixDecoding](https://arxiv.org/pdf/2411.04975)
- [KVFlow prefix caching for multi-agent](https://arxiv.org/html/2507.07400v1)
- [Operand Quant single-agent ML eng](https://arxiv.org/pdf/2510.11694)
- [ReflAct](https://arxiv.org/pdf/2505.15182)
- [vLLM Automatic Prefix Caching](https://docs.vllm.ai/en/stable/design/prefix_caching/)
- [SGLang vs vLLM prefix caching](https://medium.com/byte-sized-ai/prefix-caching-sglang-vs-vllm-token-level-radix-tree-vs-block-level-hashing-b99ece9977a1)
- [XGrammar-2 blog (MLC, May 2026)](https://blog.mlc.ai/2026/05/04/xgrammar-2-fast-customizable-structured-generation)
- [Morph Fast-Apply](https://www.morphllm.com/fast-apply-model)
- [Morph SWE-bench Pro analysis](https://www.morphllm.com/swe-bench-pro)
- [Morph Terminal-Bench 2.0](https://www.morphllm.com/terminal-bench-2)
- [SWE-bench-Live](https://swe-bench-live.github.io/)
- [terminal-bench@2.0 leaderboard](https://www.tbench.ai/leaderboard/terminal-bench/2.0)
- [LiveCodeBench leaderboard (llm-stats)](https://llm-stats.com/benchmarks/livecodebench)
- [SWE-Lancer leaderboard](https://llm-stats.com/benchmarks/swe-lancer)
- [BenchLM SWE-bench Verified 2026](https://benchlm.ai/benchmarks/sweVerified)
- [Cursor Composer blog](https://cursor.com/blog/composer)
- [Claude Code Dynamic Workflows (MarkTechPost)](https://www.marktechpost.com/2026/05/28/anthropic-ships-claude-opus-4-8-alongside-dynamic-workflows-and-cheaper-fast-mode-with-workflows-capped-at-1000-subagents/)
- [Claude Code agents teams/subagents (CloudZero)](https://www.cloudzero.com/blog/claude-code-agents/)
- [Cline Plan & Act paradigm](https://cline.bot/blog/plan-smarter-code-faster-clines-plan-act-is-the-paradigm-for-agentic-coding)
- [MCP 2026 roadmap](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [MCP adoption statistics (Digital Applied)](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol)
- [Phil Schmid — agent harnesses in 2026](https://www.philschmid.de/agent-harness-2026)
- [Augment — single vs multi-agent](https://www.augmentcode.com/guides/single-agent-vs-multi-agent-ai)
- [Hermes Agent with Qwen 3.6 setup guide](https://lushbinary.com/blog/hermes-agent-qwen-3-6-setup-guide/)
- [Qwen function-calling docs](https://qwen.readthedocs.io/en/latest/framework/function_call.html)
- [Qwen3-Coder-Next on HF](https://huggingface.co/Qwen/Qwen3-Coder-Next)
- [Agent memory landscape 2026](https://agentmarketcap.ai/blog/2026/04/10/agent-memory-vendor-landscape-2026-letta-zep-mem0-langmem)
- [AGENTS.md vs CLAUDE.md vs Cursor Rules (Codersera 2026)](https://codersera.com/blog/agents-md-vs-claude-md-vs-cursor-rules-comparison-2026/)
- [Repository intelligence in AI coding tools 2026](https://www.buildmvpfast.com/blog/repository-intelligence-ai-coding-codebase-understanding-2026)
- [Speculative decoding 2026 (Premai)](https://blog.premai.io/speculative-decoding-2-3x-faster-llm-inference-2026/)
