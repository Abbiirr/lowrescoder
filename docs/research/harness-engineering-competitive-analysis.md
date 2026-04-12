# Harness Engineering: Why ForgeCode (81.8%) Beats Claude Code (58%)

> **Date:** 2026-04-01
> **Context:** Terminal-Bench 2.0 competitive analysis — harness patterns that drive performance

## Core Finding

The 24-point gap between ForgeCode and Claude Code is **almost entirely harness engineering, not model capability**. ForgeCode proved this: same Gemini 3.1 Pro model scores 78.4% in ForgeCode vs 68.5% in Google's own harness — a 10-point delta from runtime engineering alone.

## Top 10 Harness Patterns

### Pattern 1: Non-Interactive Mode
- **What:** Rewrite system prompt to prohibit conversational branching, auto-assume defaults
- **Who:** ForgeCode, Droid, TongAgents
- **Impact:** +13 points (ForgeCode went from ~25% to ~38%)
- **AutoCode:** Add `autonomous_mode` flag to AgentLoop, `ApprovalMode.AUTONOMOUS`

### Pattern 2: Mandatory Planning Enforcement
- **What:** Runtime forces agent to call planning/todo tool before execution on multi-step tasks
- **Who:** ForgeCode (38% → 66%), Droid, TongAgents, Deep Agents
- **Impact:** +10-15 points
- **AutoCode:** `PlanningEnforcementMiddleware` tracking todo_write calls, injecting reminders

### Pattern 3: Environment Bootstrapping
- **What:** Pre-execution shell commands gather env snapshot (files, tools, OS, memory), inject into first prompt
- **Who:** Meta-Harness (eliminates 2-5 exploration turns), Droid, OpenDev
- **Impact:** +3-5 points (saves 10-20% of interaction budget)
- **AutoCode:** `EnvironmentBootstrapMiddleware` on iteration 0

### Pattern 4: Progressive Reasoning Budget
- **What:** High reasoning for planning (early), low for execution (middle), high for verification (late)
- **Who:** ForgeCode, Deep Agents ("reasoning sandwich" — xhigh/high/xhigh)
- **Impact:** +5-10 points (Deep Agents: 53.9% at constant xhigh vs 63.6% at sandwich)
- **AutoCode:** `ReasoningBudgetMiddleware` at `before_model` hook

### Pattern 5: Enforced Pre-Completion Verification
- **What:** Double-confirmation: first `task_complete` triggers verification checklist, second exits
- **Who:** ForgeCode, KIRA, TongAgents (Verifier layer), Deep Agents
- **Impact:** +5-8 points
- **AutoCode:** `PreCompletionVerificationMiddleware`, double-confirmation protocol

### Pattern 6: Doom-Loop Detection
- **What:** Track per-file edit counts and per-tool failure counts, inject recovery after threshold
- **Who:** Deep Agents (LoopDetectionMiddleware), OpenDev, ForgeCode
- **Impact:** Prevents 10-iteration loops that consume half the time budget
- **AutoCode:** `LoopDetectionMiddleware` using middleware `shared_state`

### Pattern 7: Tool Schema Optimization
- **What:** Rename args to match training data priors, flatten nested schemas, model-specific variants
- **Who:** ForgeCode (measurable error reduction), Droid (per-model edit formats)
- **Impact:** +3-5 points (tool error compounds: 5% per call × 20 calls = 36% success vs 2% × 20 = 67%)
- **AutoCode:** Schema flattening in `ToolShim`, provider-specific variants

### Pattern 8: Marker-Based Command Sync
- **What:** Append `echo '__CMDEND__N__'` after commands, poll for marker instead of fixed timeout
- **Who:** KIRA/Meta-Harness (saves 2-5s per command × 20-50 commands = 40-250s per task)
- **Impact:** Often the difference between completing and timing out
- **AutoCode:** Add marker polling to `sandbox.py` shell execution

### Pattern 9: Aggressive Context Hygiene
- **What:** 30KB output cap, explicit truncation text, progressive compaction at 70%, old observations collapsed
- **Who:** KIRA, ForgeCode, Meta-Harness, SWE-agent, OpenDev
- **Impact:** Prevents context window bloat that causes agent to "forget" the task
- **AutoCode:** `OutputTruncationMiddleware` at `after_tool`, hard caps in `context.py`

### Pattern 10: Planner-Executor-Verifier Separation
- **What:** Three-phase architecture with context isolation between planning, execution, and verification
- **Who:** TongAgents (#3), SageAgent (#4), ForgeCode (MUSE/FORGE/SAGE)
- **Impact:** Prevents "context contamination" and self-evaluation bias
- **AutoCode:** Extend `orchestrator.py` for three-phase execution, verifier subagent

## Agent Comparison Table

| Agent | Score | Architecture | Key Innovation |
|-------|-------|-------------|----------------|
| ForgeCode | 81.8% | MUSE/FORGE/SAGE (3-agent) | 7 failure modes fixed systematically |
| TongAgents | 80.2% | Planner/Executor/Verifier | Isolated contexts, full-chain tracking |
| SageAgent | 78.4% | Dynamic sub-agent creation | Meta-tools, AI-generated agent topology |
| Droid | 77.3% | Specialized Droids | Minimalist tools, system notifications |
| KIRA | 74.8% | Marker-based polling | Command sync saves 40-250s per task |
| Meta-Harness | 76.4% | Env bootstrapping | Pre-execution discovery saves 2-5 turns |
| Deep Agents | 66.5% | Middleware stack | 13.7-point improvement from middleware alone |
| Claude Code | 58.0% | Single agent + subagents | Interactive-first, not optimized for autonomous |
| OpenHands | 51.9% | CodeActAgent | General-purpose, no benchmark tuning |

## Implementation Priority for AutoCode

| Priority | Pattern | Estimated Impact | Effort |
|----------|---------|-----------------|--------|
| **P0** | Non-interactive mode | +13 pts | 1 day |
| **P0** | Mandatory planning | +10-15 pts | 1 day |
| **P1** | Pre-completion verification | +5-8 pts | 1 day |
| **P1** | Progressive reasoning budget | +5-10 pts | 1 day |
| **P1** | Doom-loop detection | +3-5 pts | 0.5 day |
| **P2** | Environment bootstrapping | +3-5 pts | 0.5 day |
| **P2** | Context hygiene (output caps) | +3-5 pts | 0.5 day |
| **P2** | Marker-based command sync | +2-5 pts | 1 day |
| **P3** | Tool schema optimization | +3-5 pts | 1 day |
| **P3** | Planner-Executor-Verifier | +5-10 pts | 3-5 days |

## Sources

- [ForgeCode Blog: Benchmarks Don't Matter](https://forgecode.dev/blog/benchmarks-dont-matter/)
- [ForgeCode Blog: GPT-5.4 Agent Improvements](https://forgecode.dev/blog/gpt-5-4-agent-improvements/)
- [ForgeCode GitHub](https://github.com/antinomyhq/forgecode)
- [TongAgents](https://tongagents.mybigai.ac.cn/en/)
- [OpenSage Paper](https://arxiv.org/html/2602.16891v2)
- [Droid Terminal-Bench](https://factory.ai/news/terminal-bench)
- [KIRA GitHub](https://github.com/krafton-ai/KIRA)
- [Meta-Harness GitHub](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact)
- [LangChain: Improving Deep Agents](https://blog.langchain.com/improving-deep-agents-with-harness-engineering/)
- [Skill Issue: Harness Engineering](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents)
- [Terminal-Bench Paper](https://arxiv.org/abs/2601.11868)
