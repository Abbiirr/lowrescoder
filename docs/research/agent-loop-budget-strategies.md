# Agent Loop Budget, Iteration Limits & Retry Strategies — Cross-Industry Research

> Researched: 2026-03-18
> Author: Claude
> Purpose: Inform AutoCode's benchmark harness budget enforcement strategy
> Status: PENDING REVIEW (posted to AGENTS_CONVERSATION.MD Entry 700)

---

## Executive Summary

We implemented per-attempt tool-call budget splitting (total_budget / 3 attempts) in the AutoCode benchmark harness. This research examines whether the industry's top coding agents do the same — and whether our approach helps or hurts.

**Key finding:** No major agent splits a fixed tool-call budget across retries. Instead, the industry consensus is:

1. **Generous per-attempt limits** (50-250 iterations per attempt)
2. **Multiple independent attempts with fresh context** (3-5 attempts)
3. **Cost/turn limits as safety nets**, not performance optimizers
4. **Context compaction** as the primary mechanism to extend agent capability within a session
5. **Selection/discrimination** across attempts rather than budget rationing within them

**Recommendation:** Revert the per-attempt budget split. Give each attempt the full tool budget. Add a total budget across all retries as a safety net only. The research strongly suggests that constraining individual attempts hurts solve rate more than it prevents waste.

---

## Detailed Findings by Agent

### 1. Claude Code (Anthropic)

| Parameter | Value | Source |
|---|---|---|
| Max iterations (AgentLoop) | **1,000** (LLM rounds, not tool calls) | `src/autocode/agent/loop.py:34` |
| Per-turn tool call ceiling | ~10-20 (server-side `stop_reason: pause_turn`) | Agent SDK docs |
| Max turns (Agent SDK) | Configurable via `max_turns` | [Agent SDK docs](https://platform.claude.com/docs/en/agent-sdk/agent-loop) |
| Cost limit (Agent SDK) | Configurable via `max_budget_usd` | Agent SDK docs |
| Budget splitting | **No** — single agent loop per session, no multi-attempt retry | — |
| Context management | Auto-compaction at ~95% capacity; `/compact` manual command | Claude Code docs |
| Retry strategy | **No automatic retries** — user-driven continuation | — |

**Key insight:** Claude Code does NOT retry failed attempts automatically. Each task gets one agent loop that runs until the model finishes. The 1,000 iteration limit is a safety net, not a performance constraint. The model itself decides when it's done.

### 2. Codex CLI (OpenAI)

| Parameter | Value | Source |
|---|---|---|
| Max iterations | **None explicit** — context-window-driven | [Unrolling the Codex agent loop](https://openai.com/index/unrolling-the-codex-agent-loop/) |
| Max retries | **0** by default (`--max-retries`) | Codex CLI docs |
| Budget splitting | **No** | — |
| Context management | Encrypted server-side compaction at ~95% capacity | [Context compaction research](https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f) |
| Compaction | Lossy, AES-encrypted, opaque to client | — |
| Rate limit handling | **Exits abruptly** on `rate_limit_exceeded` (known bug) | [Issue #690](https://github.com/openai/codex/issues/690) |

**Key insight:** Codex has the weakest retry/budget handling of any major agent. No backoff, no budget splitting, no retry on failure. The agent loop just runs until the context window fills. Prompt length grows quadratically with conversation depth.

### 3. Gemini CLI (Google)

| Parameter | Value | Source |
|---|---|---|
| Max turns (main agent) | **100** (`MAX_TURNS` in `client.ts`) | [Gemini CLI source](https://github.com/google-gemini/gemini-cli) |
| Max turns (subagent) | **30** | Subagent config |
| Subagent timeout | **10 minutes** | Subagent config |
| Tool call limit | **None** — bounded indirectly by turn limit | — |
| Budget splitting | **No** | — |
| Context management | LLM summarizer producing XML snapshot at 50% capacity | `chatCompressionService.ts` |
| Recent context preserved | **30%** of history kept verbatim during compaction | `COMPRESSION_PRESERVE_THRESHOLD = 0.3` |
| Verification | Second LLM pass confirms summary completeness | — |
| API retries | **10 attempts** max, exponential backoff | `geminiChat.ts` |
| Mid-stream retries | **4 attempts** (1+3), from 1000ms | — |
| Loop detection | 3 mechanisms: identical tool calls (5x threshold), content chanting (10x), LLM-based (after 30 turns, checks every 10) | `loopDetectionService.ts` |
| Loop recovery | Injects "rethink" feedback into existing context (NOT fresh) | — |

**Key insight:** Gemini CLI has the most sophisticated loop detection (3 layered mechanisms) but does NOT split budgets or do multi-attempt retries. It uses a generous 100-turn limit and relies on loop detection + context compaction to keep the agent productive. The LLM-based loop detector after 30 turns is unique.

### 4. SWE-agent (Princeton NLP)

| Parameter | Value | Source |
|---|---|---|
| Step limit | **250** (competitive config), 0=unlimited (default) | [SWE-agent config reference](https://swe-agent.com/latest/reference/agent_config/) |
| Recommended limit | **50 turns** with **$1/instance** cost limit | SWE-agent docs |
| Cost limit | **$3.00/instance** default | `per_instance_cost_limit` |
| Max requeries (formatting errors) | **3** per step | — |
| Multi-attempt (competitive) | **5 attempts** + o1 discriminator | [Competitive runs](https://swe-agent.com/latest/usage/competitive_runs/) |
| Budget splitting across attempts | **Yes — remaining budget divided per attempt** | RetryAgentConfig |
| Context management | History processors (no auto-compaction) | — |
| API retries | **20 retries**, 10-120s exponential random backoff | tenacity config |

**Key insight:** SWE-agent is the **only** major agent that splits budget across retry attempts (via `RetryAgentConfig`). But critically: each attempt still gets a **generous** budget (250 steps), and the competitive config runs 5 full attempts. The budget split is across the retry meta-agent, not within individual attempts. Their recommended 50-turn limit is much higher than our 33 (100/3).

### 5. Aider

| Parameter | Value | Source |
|---|---|---|
| Max reflections | **3** (hardcoded) | `aider/coders/base_coder.py` ~line 91 |
| Cost/iteration budget | **None** | — |
| Budget splitting | **N/A** (no multi-attempt) | — |
| Context management | Chat summarization with weak/fast model | — |
| Recommended context | **<25K tokens** for reliable edit formatting | Aider docs |
| Model alternation | Architect mode (reasoning model → editor model) | [Aider modes](https://aider.chat/docs/usage/modes.html) |
| Known issue | Infinite lint loop when `max_reflections` can't fix an error | [Issue #1090](https://github.com/paul-gauthier/aider/issues/1090) |

**Key insight:** Aider's `max_reflections=3` is the most constrained retry limit in the industry, but it applies to edit-lint-test cycles, not tool calls. Each reflection gets the full context. No budget splitting. Users have forked to increase to 20 reflections.

### 6. OpenHands (formerly OpenDevin)

| Parameter | Value | Source |
|---|---|---|
| Max iterations (SWE-bench) | **100** | v0.34.0 submission config |
| Max iterations (template) | **500** | Default config templates |
| Global max iterations | Caps total across parent + child agents (prevents N² explosion) | [Issue #2121](https://github.com/All-Hands-AI/OpenHands/issues/2121) |
| Cost limit | **None** (iteration-based only) | — |
| Multi-attempt (competitive) | **5 trajectories** + critic model (Qwen 2.5 Coder 32B) | [SOTA blog post](https://openhands.dev/blog/sota-on-swe-bench-verified-with-inference-time-scaling-and-critic-model) |
| Budget per attempt | **Each attempt gets own full max_iterations** | — |
| Context management | LLMSummarizingCondenser + history truncation | [Condenser docs](https://docs.openhands.dev/sdk/guides/context-condenser) |
| Solve rate (1 attempt) | **60.6%** | SWE-bench Verified |
| Solve rate (5 attempts) | **66.4%** (log-linear improvement) | — |
| Known issue | Condenser infinite loop if output still exceeds limits | [Issue #6357](https://github.com/All-Hands-AI/OpenHands/issues/6357) |

**Key insight:** OpenHands gives each attempt its **full** iteration budget (100-500). Budget is NOT split. The 5-attempt strategy with a trained critic model for selection is the state of the art for inference-time scaling.

### 7. Cursor

| Parameter | Value | Source |
|---|---|---|
| Tool calls (standard) | **25** per interaction | [Forum discussion](https://forum.cursor.com/t/increase-the-25-tool-calls-limit/72553) |
| Tool calls (MAX mode) | **200** per interaction | — |
| Tool calls (Pro/Ultra, post-June 2025) | **Unlimited** | — |
| Budget splitting | **No** — user manually clicks "Continue" | — |
| Context management | Summarization on overflow; dynamic context discovery | [Cursor blog](https://cursor.com/blog/dynamic-context-discovery) |

**Key insight:** Cursor's 25-call limit was explicitly designed to prevent spinning. But they **removed** it for paid tiers — suggesting it was more of a cost control than a quality improvement.

### 8. Goose (Block)

| Parameter | Value | Source |
|---|---|---|
| Max turns | **1,000** (`GOOSE_MAX_TURNS`) | [Env vars reference](https://block.github.io/goose/docs/guides/environment-variables/) |
| Subagent max turns | **25** (`GOOSE_SUBAGENT_MAX_TURNS`) | — |
| Tool call limit | **None** per turn | — |
| Budget splitting | **No** | — |
| Context management | Auto-compaction at 80% of context window (128K default) | [Smart context management](https://block.github.io/goose/docs/guides/sessions/smart-context-management/) |
| Tool output summarization | After **10 tool calls** in session | `GOOSE_TOOL_CALL_CUTOFF` |
| Tool output truncation | **200,000 chars** hardcoded | — |
| Context overflow strategies | `summarize`, `truncate`, `clear`, `prompt` (user choice) | — |
| Provider retries | **3-6** with exponential backoff (provider-specific) | — |

**Key insight:** Goose has the most generous turn limit (1,000) and no per-turn tool budget. It relies on context compaction at 80% threshold and tool output summarization after 10 calls. No budget splitting.

### 9. Pi Coding Agent (badlogic/pi-mono)

| Parameter | Value | Source |
|---|---|---|
| Max iterations | **None** — author explicitly chose no limit | [Blog post](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/) |
| Tool call limit | **None** | — |
| Budget splitting | **No** | — |
| Context management | Auto-compaction with 16,384 reserve tokens; keeps last 20,000 tokens | [Settings docs](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/settings.md) |
| Compaction trigger | `contextTokens > model.contextWindow - reserveTokens` | — |
| API retries | **3** with 2s base, 60s max, exponential backoff | — |
| Design philosophy | "I never found a use case for [max steps], so why add it?" | Author statement |

**Key insight:** Pi's author explicitly rejected iteration limits as unnecessary. The agent loop runs until the model decides it's done. Context compaction is the only constraint.

### 10. OpenCode (sst/opencode)

| Parameter | Value | Source |
|---|---|---|
| Max iterations | Optional `steps` field, **unlimited by default** | [Agents docs](https://opencode.ai/docs/agents/) |
| Graceful degradation | When `steps` reached, agent summarizes work + lists remaining tasks | — |
| Tool call limit | **None** | — |
| Budget splitting | **No** | — |
| Context management | Dual: pruning (protects last ~40K tokens) + compaction (10K reserved) | [DeepWiki](https://deepwiki.com/sst/opencode/2.4-context-management-and-compaction) |
| Prune threshold | Won't prune unless **>20K tokens** removable | — |
| Output token cap | **32,000 tokens** | `SessionPrompt.OUTPUT_TOKEN_MAX` |
| Overflow behavior | Session terminates with `ContextOverflowError` if compaction fails | — |

**Key insight:** OpenCode has the most interesting graceful degradation — when the step limit is reached, the agent is instructed to summarize and hand off rather than being hard-killed.

---

## Cross-Industry Comparison Table

| Agent | Iteration Limit | Budget Split? | Retries/Attempts | Context Strategy | Loop Detection |
|---|---|---|---|---|---|
| **Claude Code** | 1,000 (rounds) | No | None (user-driven) | Auto-compact ~95% | None |
| **Codex CLI** | None (context-driven) | No | 0 default | Encrypted server-side compaction | None |
| **Gemini CLI** | 100 (turns) | No | 10 API retries | XML snapshot at 50%, preserve 30% | **3 mechanisms** (best in class) |
| **SWE-agent** | 250 (steps) | Yes (only one) | 5 attempts + discriminator | History processors | None |
| **Aider** | 3 reflections | No | N/A | Chat summarization | Infinite loop bug |
| **OpenHands** | 100-500 | No (full per attempt) | 5 trajectories + critic | LLM condenser + truncation | Global iteration cap |
| **Cursor** | 25/200/unlimited | No | Manual "Continue" | Summarization | None |
| **Goose** | 1,000 | No | 3-6 (provider) | Auto-compact at 80% | None |
| **Pi** | **None** | No | 3 API retries | Auto-compact, keep 20K recent | None |
| **OpenCode** | Optional `steps` | No | None documented | Prune + compact | None |

---

## Academic Research

### SWE-Effi (arXiv:2509.09853) — Cost-Efficiency Analysis

The most rigorous analysis of agent loop economics:

- **Expensive failures dominate costs.** SWE-Agent + GPT-4o-mini consumed **8.8M tokens on failed attempts** vs **1.8M on successful ones** — a 4.2x cost multiplier for failures.
- **Token snowball effect.** Agents that can't solve a problem spiral, burning tokens without progress. Hard iteration limits are the only defense.
- **Diminishing returns are real.** Agents achieve near-optimal performance at significantly lower iteration budgets than commonly assumed.
- **Lightweight frameworks win.** Agentless + Qwen3-32B achieved 48% resolve rate with far fewer tokens than SWE-Agent + GPT-4o-mini at 10%.

### OpenHands Inference-Time Scaling

- **Log-linear improvement:** 60.6% (1 attempt) → 66.4% (5 attempts) with trained critic
- **Fresh sessions outperform continuation.** Each attempt starts clean. The critic selects the best result.
- **The marginal value of additional attempts decreases.** Most of the gain is in the first 3 attempts.

---

## Implications for AutoCode's Benchmark Harness

### What We Did (Entry 696/698)

We split `total_tool_budget / MAX_GRADE_ATTEMPTS` (100 / 3 ≈ 33 tools per attempt) and cancel the loop via `loop.cancel()` when the per-attempt budget is exhausted.

### What the Industry Does

**Nobody does this.** The closest is SWE-agent's `RetryAgentConfig`, but even it gives each attempt a generous budget (250 steps) — not 33.

The industry consensus is:
1. Give each attempt a **generous** limit (50-250 iterations)
2. Run **multiple independent fresh attempts** (3-5)
3. Use a **selection mechanism** to pick the best result
4. Use **context compaction** to extend productive session length
5. Use **loop detection** to catch spinning (Gemini CLI's 3-mechanism approach is best-in-class)

### Recommended Changes

| Current | Recommended | Rationale |
|---|---|---|
| `per_attempt_budget = total / 3` (≈33) | `per_attempt_budget = total` (100) | Industry gives full budget per attempt |
| Total budget = sum of per-attempt | Total budget = `total * MAX_GRADE_ATTEMPTS` (300) | Safety net only, not performance constraint |
| Cancel at budget via `loop.cancel()` | Keep cancel but at full per-attempt budget | Prevents runaway but doesn't limit problem-solving |
| No loop detection | Add spinning detection (e.g., 5 identical tool calls) | Gemini CLI pattern; catches unproductive loops |
| No selection across attempts | Future: add discriminator model | OpenHands/SWE-agent pattern; log-linear improvement |

### What to Keep

- **Fresh AgentLoop per retry** — matches industry consensus (OpenHands, SWE-agent, our P1-B)
- **ContextEngine wiring** — matches Goose (80%), Gemini (50%), Pi (auto-compact)
- **Syntax gate in tool results** — matches SWE-agent's linter, Aider's auto_lint
- **task.md inclusion** — infrastructure, not solver intelligence
- **Traceback frame extraction** — deterministic, parity-safe

---

## Summary

The per-attempt budget split of 33 tool calls is **the most constrained approach in the entire industry**. No major agent limits individual attempts this tightly. The risk is that we're measuring our budget enforcement, not our agent's capability.

**Recommended action:** Increase `per_attempt_budget` to the full `total_tool_budget` (100) per attempt. Keep the total budget across all retries as a safety net (300). Add Gemini-style loop detection instead of hard budget cuts.
