# Philosophy: Agent Benchmarks vs Model Benchmarks

## The Core Problem

Most coding benchmarks (HumanEval, MBPP, LiveCodeBench) measure **model intelligence** — can the LLM generate correct code from a prompt? But a coding agent is a system: model + tools + orchestration + error handling + context management. When you test only the model, you miss everything the agent adds.

## Evidence That Scaffolding Matters More Than Model Choice

| Finding | Source |
|---------|--------|
| Scaffold choice causes **up to 15% performance difference** on same model | SWE-bench Verified ablations |
| Weaker model (Sonnet) with strong scaffold beat stronger model (Opus) with weak scaffold: 52.7% vs 52.0% | Confucius Code Agent |
| GPT-4 varies from 2.7% to 28.3% on SWE-bench Lite depending on scaffold | CodeR vs early RAG comparison |
| Gemini-2.5-Pro achieved 50.8% on SWE-bench **without any tools** — pure model in context | Monolithic agent study |
| Gemini with tools scores 65%+ — the **15+ point delta is the agent's contribution** | Same study, with scaffold |
| Infrastructure configuration alone swings benchmarks by several percentage points | Anthropic engineering blog |

## What "Agent Quality" Actually Means

When we say "test the agent, not the model," we mean test these system capabilities:

### 1. Tool Orchestration Layer
The agent decides WHEN to use tools, WHICH tool to use, and HOW to interpret results. A great model that never calls `grep` and instead reads 50 files sequentially is a bad agent.

### 2. Error Recovery Layer
The agent detects failures and adapts. The model generates code; the agent notices it broke tests and feeds the error back. Recovery-Bench showed this is **orthogonal** to raw coding ability — the best coder is not the best recoverer.

### 3. Context Engineering Layer
The agent decides what context the model sees. Put garbage in the prompt, the model produces garbage. Put the perfect 3 functions in the prompt, even a small model produces correct patches. This is the L2 retrieval layer in HybridCoder's architecture.

### 4. Planning Layer
The agent breaks complex tasks into steps and executes them in order. The model generates each step; the agent sequences them, detects failures, and replans.

### 5. Edit Application Layer
The model proposes changes in natural language or diff format. The agent turns these into actual file modifications. Aider showed that edit format compliance varies wildly and is the #1 source of failures.

### 6. Deterministic Bypass Layer
HybridCoder's unique advantage: L1-L2 can solve many problems **without invoking the LLM at all**. Tree-sitter, LSP, and static analysis produce zero-token solutions. Tests should measure how much work gets done at zero token cost.

## The Scaffold Delta Test

The most powerful agent quality metric:

```
agent_quality = performance(model + agent) - performance(model alone)
```

Run the same model (e.g., Qwen3-8B) through:
1. HybridCoder's full 4-layer system
2. A naive single-prompt scaffold (just send the task to the model)

The delta IS the agent quality measurement. If HybridCoder's scaffold doesn't improve over naive prompting, the agent adds no value.

## Design Principles for Agent Tests

1. **Model-agnostic**: Every test must work with any model. Swap Qwen3-8B for GPT-4 — the test still measures agent quality.
2. **Deterministic grading**: "Choose deterministic graders where possible, LLM graders where necessary" (Anthropic). End with `make test` and binary pass/fail.
3. **Grade outcomes, not paths**: "Avoid checking that agents followed very specific steps" (Anthropic). The agent may find valid alternatives the test designer didn't anticipate.
4. **Isolate dimensions**: Each test should primarily stress ONE agent capability. Multi-file coordination tests should use simple code so the model isn't the bottleneck.
5. **pass^k over pass@1**: Measure consistency. pass^k = p^k requires ALL k runs to succeed. Deterministic agent layers should show pass^k close to pass^1.
6. **Cost matters**: Measure tokens per resolved task. Two agents that both pass at 80% but one uses 10x the tokens — the efficient one is better.

## Per-Lane Grader Policy

Graders must be explicitly constrained by lane to prevent token-cost creep:

| Lane | Primary Grader | Secondary Grader | LLM Grader |
|------|---------------|-----------------|------------|
| **PR Core** | Deterministic (build/test pass, binary checks) | OFF | **OFF** (opt-in via `--with-llm-grader`) |
| **Nightly Regression** | Deterministic | Heuristic (transcript patterns) | Sampled (10% of runs) |
| **Capability** | Deterministic | Heuristic | Active on all runs |
| **Stress** | Deterministic + fault metrics | Heuristic | OFF (no LLM grading under chaos) |

**Rationale:** The PR lane must be fast and cheap. Deterministic graders (build passes, tests pass, acceptance checks pass) provide sufficient signal for regression gating. LLM judges add noise and cost — reserve them for deeper nightly analysis where the extra signal justifies the token spend.

## HybridCoder's Natural Advantages to Measure

| Advantage | How to Test It |
|-----------|---------------|
| L1-L2 deterministic bypass | Count tasks resolved at zero LLM tokens |
| Local-first (no API noise) | pass^k consistency vs cloud-dependent agents |
| 4-layer escalation | Measure which layer resolves each task type |
| Constrained generation (L3) | Edit format compliance with Outlines grammar |
| Edge-native (fixed hardware) | Reproducible infrastructure conditions |
