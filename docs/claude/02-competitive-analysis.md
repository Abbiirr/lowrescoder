# Research: Competitive Analysis — AI Coding Assistants (Feb 2026)

> Generated from web research for HybridCoder project planning

---

## 1. Market Overview

The AI coding assistant market in 2026 is dominated by cloud-dependent tools. Key players:

### Tier 1: Cloud-Native Commercial
- **Cursor** — AI-native IDE (VS Code fork), $20/mo, deep model integration, agent mode
- **GitHub Copilot** — Inline completion + CLI, $10/mo, GPT-4/Claude backend
- **Claude Code** — Anthropic's CLI, subscription, agentic multi-file editing
- **Windsurf (Codeium)** — IDE with AI, freemium model

### Tier 2: Open-Source / BYO-API
- **Aider** — CLI-first, open-source, git-native, supports local models via Ollama. Best polyglot benchmark scores. Leader in terminal-based AI coding.
- **Cline** — VS Code agent + new CLI, open-source, plan-and-act workflow, snapshot checkpoints
- **Continue** — IDE extension, model-agnostic, supports local models, open-source
- **Tabby** — Self-hosted AI coding assistant for teams, enterprise-focused

### Tier 3: Local-First / Edge
- **Goose** (Block/Square) — Open-source AI agent framework, extensible, runs locally
- **(HybridCoder — this project)** — Edge-native, deterministic-first, zero LLM tokens for 60-80% of operations

---

## 2. Detailed Competitor Analysis

### Aider (Primary Competitor)
- **Interface**: CLI/Terminal
- **Model Support**: GPT-4, Claude, local via Ollama, any OpenAI-compatible
- **Key Strength**: Git-native, multi-file editing, polyglot benchmark leader
- **Polyglot Benchmark**: Top scores ~76% with Claude 4.5 Opus (cloud). Local 7B models score ~30-40%
- **Weakness**: LLM-first architecture — every query hits the model. No deterministic layer.
- **Cost**: Free tool + API costs ($0.01-$0.50/task)
- **Local Support**: Yes via Ollama, but LLM is ALWAYS called

### Cline
- **Interface**: VS Code extension + CLI (new)
- **Model Support**: Claude, DeepSeek, Gemini, Ollama
- **Key Strength**: Plan-and-act workflow, snapshot checkpoints, transparent execution
- **Weakness**: VS Code dependency for full features, LLM-first
- **Cost**: Free + API costs

### Cursor
- **Interface**: Full IDE (VS Code fork)
- **Key Strength**: Deep codebase understanding, agent mode, inline completions
- **Weakness**: Proprietary, cloud-only, $20/mo, no offline mode
- **Cost**: $20/mo subscription

### Claude Code
- **Interface**: CLI
- **Key Strength**: Best-in-class reasoning, agentic multi-file editing
- **Weakness**: Cloud-only, expensive, no local model support
- **Cost**: API usage-based (expensive for heavy use)

---

## 3. Benchmark Landscape

### Aider Polyglot Benchmark
- 225 Exercism problems across C++, Go, Java, JavaScript, Python, Rust
- Two attempts per problem (retry with test output)
- **Top scores (cloud models)**: ~76% (Claude 4.5 Opus + agent scaffolding)
- **7B local models**: ~30-40% (Qwen2.5-Coder-7B range)
- **Our target**: >40% pass@1

### SWE-bench Verified
- 500 real GitHub issues, verified solvable
- **Top scores**: ~70% (Qwen3-Coder-Next, Claude 4.5)
- **Small models**: Limited data for 7B, but improving
- 59 models evaluated

---

## 4. Market Gaps HybridCoder Exploits

| Gap | Explanation |
|-----|------------|
| **No deterministic layer** | Every competitor calls LLM for ALL queries, even "find references" or "what type is X?" |
| **No edge-native tool** | All tools treat local as secondary mode, not primary architecture |
| **Token waste** | Competitors use 3-10x more tokens than necessary for simple operations |
| **Latency** | Cloud tools: 2-5s per query. HybridCoder Layer 1: <50ms |
| **Cost** | All competitors have ongoing costs (API or subscription). HybridCoder: $0 after setup |
| **Privacy** | Most tools send code to cloud. HybridCoder: 100% local |
| **Offline** | Most tools fail offline. HybridCoder: fully functional |

---

## 5. Model Landscape Update (Feb 2026)

### New Models Since Original Plan
- **Qwen3-8B**: Successor to Qwen2.5-Coder-7B. Thinking/non-thinking modes. Q4_K_M = 5.03 GB. Fits 8GB VRAM.
- **Qwen3-Coder-Next** (80B/3B active MoE): Incredible performance but needs 42+ GB — NOT for 8GB VRAM.
- **Qwen3-Coder-30B-A3B**: 30B total / 3B active MoE. Q4_K_M = ~18.6 GB — needs 24GB+ VRAM.
- **DeepSeek V4** (upcoming Feb 2026): Claims 98% HumanEval, consumer GPU variant expected.
- **Nemotron Nano 9B**: NVIDIA's coding model, strong on coding benchmarks.

### Recommended Model Updates for HybridCoder
| Layer | Original Plan | Updated Recommendation | Reason |
|-------|--------------|----------------------|--------|
| Layer 4 (reasoning) | Qwen2.5-Coder-7B | **Qwen3-8B** | Better reasoning, thinking mode, same VRAM |
| Layer 3 (constrained) | Qwen2.5-Coder-1.5B | **Qwen3-1.5B or Qwen2.5-Coder-1.5B** | Verify Qwen3 small models exist |
| Embeddings | jina-v2-base-code | **jina-v3 or Nomic Embed Code** | Newer, better code understanding |

---

## Sources
- [Best AI Coding Assistants Feb 2026 - Shakudo](https://www.shakudo.io/blog/best-ai-coding-assistants)
- [Agentic CLI Tools Compared - AIMultiple](https://research.aimultiple.com/agentic-cli/)
- [Best AI Coding Agents 2026 - Faros AI](https://www.faros.ai/blog/best-ai-coding-agents-2026)
- [Aider LLM Leaderboards](https://aider.chat/docs/leaderboards/)
- [Aider Polyglot - Epoch AI](https://epoch.ai/benchmarks/aider-polyglot)
- [Top 7 Open-Source AI Coding Assistants 2026](https://www.secondtalent.com/resources/open-source-ai-coding-assistants/)
- [Qwen3-Coder-Next - GitHub](https://github.com/QwenLM/Qwen3-Coder)
- [Qwen3-Coder-Next - VentureBeat](https://venturebeat.com/technology/qwen3-coder-next-offers-vibe-coders-a-powerful-open-source-ultra-sparse)
- [SWE-bench Verified Leaderboard](https://llm-stats.com/benchmarks/swe-bench-verified)
