# Agent Orchestration & Context Intelligence Research

> **Research Date:** 2026-02-06
> **Purpose:** Inform Phase 4 design — context management, task systems, subagents, memory, checkpoints
> **Scope:** Modern AI coding agent architectures (2024-2026)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Claude Code Architecture](#2-claude-code-architecture)
3. [SWE-agent](#3-swe-agent)
4. [Aider](#4-aider)
5. [OpenCode](#5-opencode)
6. [Kimi K2.5](#6-kimi-k25)
7. [Devin 2.0 / Devon](#7-devin-20--devon)
8. [Codex CLI](#8-codex-cli)
9. [Cross-System Patterns](#9-cross-system-patterns)
10. [Context Management Techniques](#10-context-management-techniques)
11. [Memory Architectures](#11-memory-architectures)
12. [Checkpoint & Recovery](#12-checkpoint--recovery)
13. [Token Budget Economics](#13-token-budget-economics)
14. [Implications for HybridCoder](#14-implications-for-hybridcoder)
15. [References](#15-references)

---

## 1. Executive Summary

Modern AI coding agents have converged on several architectural patterns:

| Pattern | Adopted By | Key Insight |
|---------|-----------|-------------|
| **Orchestrator-Worker** | Claude Code, OpenCode, Devin | One coordinator delegates to specialized workers |
| **Plan-First** | Devin, Cursor, Claude Code | Planning phase before execution reduces failures |
| **Context Isolation** | Claude Code, SWE-agent | Subagents get isolated context to prevent pollution |
| **Observation Collapse** | SWE-agent, Acon | Compress old observations to fit more iterations |
| **Task-Driven** | Claude Code, OpenCode | External task lists reduce context load |
| **3-Layer Memory** | Langmem, MemGPT | Semantic + Episodic + Procedural memory |
| **Durable Execution** | LangGraph, Devon | Checkpoint/restore for crash recovery |

**Key takeaway for HybridCoder:** We operate under a single-LLM constraint (one 7B model, 8GB VRAM). This means we cannot run parallel LLM inference like cloud-based tools. Instead, we need:
- **Sequential LLM access** via asyncio.Lock (subagents share the model)
- **Aggressive context compaction** (auto-summarize at 75% budget)
- **External state** (SQLite tasks, memories) to reduce context pressure
- **Non-LLM parallelism** (file I/O, search, parsing run concurrently)

---

## 2. Claude Code Architecture

### 2.1 Subagent System

Claude Code uses a flat orchestrator-worker pattern:

- **Main agent** (Claude Opus 4.5) coordinates the conversation
- **Subagents** (Claude Sonnet 4) handle delegated tasks in isolated contexts
- **Built-in types**: Explore (read-only), Plan (research + design), General-purpose
- **Custom subagents**: Users define domain-specific agents with custom system prompts and restricted tool access
- **Flat hierarchy**: Subagents cannot spawn other subagents (prevents recursive explosion)

### 2.2 Context Forking

Subagents receive a **forked context** — they see the conversation history up to the fork point but run in isolation. This prevents "context pollution" from exploratory work (testing, debugging, diff application). The orchestrator receives only a clean summary from the subagent.

### 2.3 Todo Lists (Task Tool)

Claude Code provides a native `TodoWrite` tool with three states:
- `pending` — not yet started
- `in_progress` — currently being worked on
- `completed` — done

Tasks are stored **outside the context window** (in the tool's state), which reduces context pressure. The LLM reads the current task list each iteration but doesn't need to maintain it in conversation history.

### 2.4 Memory & Hooks

- **CLAUDE.md files**: Project-specific instructions loaded at startup
- **Hooks system**: Event-driven pre-tool gating and post-tool logging
- **No persistent episodic memory across sessions** (each conversation starts fresh)

### 2.5 Relevance to HybridCoder

| Feature | Claude Code | HybridCoder Adaptation |
|---------|------------|----------------------|
| Subagents | Parallel on different models | Sequential via LLM lock (single model) |
| Context isolation | Full fork per subagent | Separate message lists per subagent |
| Todo lists | SQLite-backed | SQLite tasks table with DAG dependencies |
| Flat hierarchy | Yes | Yes (subagents cannot spawn subagents) |
| Memory | Per-project CLAUDE.md | Per-project memory.md + episodic memory DB |

**Sources:**
- https://code.claude.com/docs/en/sub-agents
- https://medium.com/@georgesung/tracing-claude-codes-llm-traffic-agentic-loop-sub-agents-tool-use-prompts-7796941806f5

---

## 3. SWE-agent

### 3.1 Observation-Action-Thought Cycle

SWE-agent uses a continuous loop embedded in the architecture:
1. **Thought** — LLM reasons about what to do next
2. **Action** — Execute a command via Agent-Computer Interface (ACI)
3. **Observation** — Collect output, feed back to LLM

Each iteration produces a verifiable `(thought, action, observation)` triplet recorded as a JSON trajectory.

### 3.2 Agent-Computer Interface (ACI)

The ACI is an LLM-friendly abstraction that exposes minimal, unambiguous shell-like actions. Instead of raw shell commands, the LLM uses structured actions like `open_file`, `edit_file`, `search_dir`. This reduces hallucination and improves action quality.

### 3.3 History Compression (Critical Pattern)

SWE-agent's `HistoryProcessor` compresses context before passing to the LLM:

- **Observation collapse**: Observations before the last 5 are collapsed into a single line (just the action + success/failure status)
- **Content removal**: Older observations stripped to essential metadata
- **Sliding window**: Only recent N observations retain full content

This compression enables **far more iterations** within a fixed context window. Without it, agents exhaust their context in 5-10 iterations. With it, 50+ iterations are possible.

### 3.4 Relevance to HybridCoder

The observation collapse pattern is directly applicable:
- Tool results older than the last 4-5 iterations → collapse to one-line summaries
- Keep full content only for recent tool results
- This multiplies effective iterations within our 8192-token context

**Sources:**
- https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf
- https://swe-agent.com/latest/background/architecture/

---

## 4. Aider

### 4.1 Architect/Editor Pattern

Aider's most significant contribution is the two-pass editing system:

1. **Architect phase**: A reasoning model (e.g., o1, Claude) analyzes the problem and produces a plain-text plan with specific steps
2. **Editor phase**: A smaller/faster model translates the plan into well-formed code edits

This separation reduces hallucination and improves editing quality. The Architect doesn't need to produce syntactically valid edits; it just needs to reason clearly. The Editor doesn't need to reason about the problem; it just needs to translate instructions to code.

### 4.2 Repository Map

Aider generates a **concise graph representation** of the entire Git repository:
- Includes important classes, functions, types, and call signatures
- Uses node-edge dependencies to determine which portions to include
- Configurable token budget (`--map-tokens`, default 1024 tokens)
- Only sends the most relevant repository portions based on file dependency graph

This is a Layer 2 concern but informs how context assembly should work.

### 4.3 Relevance to HybridCoder

| Feature | Aider | HybridCoder Adaptation |
|---------|-------|----------------------|
| Architect/Editor | Two models, two passes | Single model, two-prompt (plan then execute) |
| Repo map | Graph-based, token-budgeted | Future Phase 4/5 (Layer 2 retrieval) |
| Edit format | Search/replace, whole-file | Currently whole-file; search/replace in Phase 3 |

**Sources:**
- https://aider.chat/docs/usage/modes.html
- https://aider.chat/docs/repomap.html

---

## 5. OpenCode

### 5.1 Primary/Subagent System

OpenCode implements a two-tier agent architecture:
- **Primary agents** (Build, Plan): User-facing agents that coordinate work
- **Subagents** (Librarian, Explore): Background agents for research and exploration
- **TaskManager**: Breaks features into atomic, verifiable subtasks with smart agent suggestions

### 5.2 Provider-Agnostic Design

OpenCode supports 75+ LLM providers, enabling different models for different agent roles. This is relevant because HybridCoder could assign different tasks to L3 (1.5B) vs L4 (8B) models.

### 5.3 Parallel Execution

Research agents (Librarian, Explore) are designed for parallel launches (`run_in_background=true`). They perform file I/O and search operations concurrently, only blocking on LLM calls.

### 5.4 Relevance to HybridCoder

- Subagent types (explore, plan, execute) map well to our needs
- Background parallel execution for non-LLM work
- Atomic subtask decomposition for task system

**Sources:**
- https://opencode.ai/docs/agents/
- https://deepwiki.com/code-yeongyu/oh-my-opencode/4.1-sisyphus-orchestrator

---

## 6. Kimi K2.5

### 6.1 Dynamic Agent Swarms

Kimi K2.5 (Moonshot AI) demonstrates the most aggressive multi-agent approach:
- **Self-directed decomposition**: Agent decides when to parallelize and how many sub-agents to spawn
- **Up to 100 sub-agents** managed dynamically per task
- **Up to 1,500 total tool calls** across a swarm
- **200-300 sequential tool call stability** without drift

### 6.2 Architecture

- Mixture-of-Experts: 1T parameters, 32B activated per request
- Trainable orchestrator that decomposes work into parallelizable chunks
- Frozen workers spawned on demand (no predefined roles)
- Built-in result merging for aggregating parallel outputs

### 6.3 Relevance to HybridCoder

Kimi's scale is not applicable to a single 8B model, but the **self-directed decomposition** pattern is useful: the LLM decides when a task is complex enough to warrant subtask creation. We don't impose a fixed decomposition strategy.

**Sources:**
- https://www.kimi.com/blog/kimi-k2-5.html
- https://www.datacamp.com/tutorial/kimi-k2-agent-swarm-guide

---

## 7. Devin 2.0 / Devon

### 7.1 Planner + Executor Separation

Devin 2.0 implements a clean separation:
- **High-level planner** (powered by reasoning model like o1): Creates executable plans
- **Executor** (powered by Claude/GPT): Implements step-by-step actions
- **Interactive planning**: Scans codebase, suggests refinable plans before autonomous execution
- **Approval gate**: Humans review and refine plans before execution begins

### 7.2 Multi-Agent Components

- **Code Editor Agent**: File manipulation and composition
- **Command Line Agent**: Shell execution and CLI operations
- **Error Handling Agent**: Identifies issues and suggests modifications
- **Parallel execution**: Multiple instances with isolated cloud-based IDEs

### 7.3 Relevance to HybridCoder

The planner-executor pattern aligns with our Architect/Editor split (Phase 5). For Phase 4, the **approval gate on plans** is key: before executing a multi-step task, show the user the plan and get approval.

**Sources:**
- https://medium.com/@takafumi.endo/agent-native-development-a-deep-dive-into-devin-2-0s-technical-design-3451587d23c0
- https://cognition.ai/blog/devin-2

---

## 8. Codex CLI

### 8.1 Agent Loop Architecture

Codex CLI uses an iterative tool invocation loop:
1. Build messages from system prompt + conversation history + tool definitions
2. Call LLM with tool schemas
3. If tool calls → execute, append results, repeat
4. If text-only → return response
5. MCP server pattern enables multi-agent system composition

### 8.2 Prompt Caching (Critical Optimization)

Codex optimizes inference cost via systematic prompt caching:
- **Cache hierarchy**: System prompt → Tool definitions → Conversation history → Query
- **Each level cached independently**: Changes at one level don't invalidate deeper levels
- **Result**: Inference cost becomes linear instead of quadratic in conversation length
- **Cached tokens are 75% cheaper** than non-cached tokens

### 8.3 Relevance to HybridCoder

Prompt caching is critical for our efficiency targets. Ollama supports KV cache reuse for common prefixes. We should structure our prompts to maximize cache hits:
1. System prompt (static per session)
2. Tool definitions (static per session)
3. Memory/tasks (changes infrequently)
4. Conversation history (changes each iteration)

**Sources:**
- https://developers.openai.com/codex/cli/
- https://cookbook.openai.com/examples/codex/codex_mcp_agents_sdk/

---

## 9. Cross-System Patterns

### 9.1 TDAG (Task-Directed Acyclic Graph)

A framework for dynamically decomposing complex tasks into subtasks:
- Each task node has dependencies (blocks/blockedBy)
- Subagents are generated per subtask with tailored system prompts
- DAG structure prevents circular dependencies
- Enables parallel execution of independent subtasks

### 9.2 Context Isolation

All major agent frameworks isolate subagent contexts:
- Subagents receive a **subset** of the main conversation
- Subagent output is **summarized** before returning to the orchestrator
- This prevents context pollution from exploratory work

### 9.3 Plan-First Workflow

The dominant pattern across tools:
1. Agent analyzes the codebase
2. Proposes an implementation plan
3. Human reviews and approves (approval gate)
4. Agent executes the plan step-by-step
5. Each step is independently verifiable

Benefits: Reduces LLM call failures, enables human oversight, identifies parallelizable steps upfront.

### 9.4 Streaming Architecture

All production agents use streaming:
- Progressive token streaming (not spinner-wait)
- Bidirectional: agents process while user inputs
- Interruptibility: users can stop agents mid-action
- HybridCoder already has this via `on_chunk` callbacks

---

## 10. Context Management Techniques

### 10.1 Compaction Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Observation collapse** | Old tool results → one-line summaries | Every N iterations |
| **LLM summarization** | LLM summarizes conversation history | At token threshold |
| **Sliding window** | Keep last N messages, drop older | Simple conversations |
| **Tool result clearing** | Remove verbose tool outputs entirely | Low-importance tools |
| **Structured summarization** | Maintain sections: intent, modifications, decisions, next steps | Complex workflows |

### 10.2 Acon Framework

Optimal context compression with guideline optimization:
- Compresses while preserving task-critical information
- Uses natural language guidelines (not hard rules)
- Achieves better compression ratios than naive summarization

### 10.3 Auto-Compaction Triggers

Best practice: trigger compaction at **75% of context budget**:
- Leaves 25% headroom for the next LLM response + tool calls
- Compaction itself requires an LLM call (to summarize), so budget accordingly
- After compaction, context should be <50% of budget

### 10.4 Tool Result Truncation

A lightweight optimization before full compaction:
- Tool results >500 tokens: keep first 200 + last 100 + "[truncated N tokens]"
- Applies to: `read_file` (large files), `search_text` (many matches), `run_command` (verbose output)
- Does NOT require an LLM call

### 10.5 Hierarchical Summarization

For long sessions, use multi-level summarization:
1. **Level 0**: Raw messages (most recent)
2. **Level 1**: Summarized batches of 10-20 messages
3. **Level 2**: Summary of summaries (session overview)

Each level is progressively more compressed but retains key decisions and outcomes.

**Sources:**
- https://google.github.io/adk-docs/context/compaction/
- https://arxiv.org/html/2510.00615v1
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

---

## 11. Memory Architectures

### 11.1 Three-Layer Memory Model

Modern agent memory systems use three layers (formalized by Langmem):

| Layer | Type | Content | Storage |
|-------|------|---------|---------|
| **Semantic** | Facts & knowledge | "This project uses pytest" | Vector embeddings |
| **Episodic** | Past actions & experiences | "User prefers snake_case" | Event logs, trajectories |
| **Procedural** | How-to knowledge | "To run tests: `uv run pytest`" | Few-shot examples, patterns |

### 11.2 Episodic Memory in Practice

Most coding agents focus on episodic memory:
- **What worked**: Tool sequences that solved similar problems
- **User preferences**: Coding style, tool preferences, approval patterns
- **Error resolutions**: How specific errors were fixed
- **Project facts**: Architecture decisions, key file locations

### 11.3 Memory Extraction

After a session completes, an LLM analyzes the conversation to extract memories:
- **Automatic extraction**: LLM identifies patterns and preferences
- **Categories**: tool_pattern, user_preference, project_fact, error_resolution
- **Relevance scoring**: Memories decay over time if not accessed
- **Deduplication**: New memories merged with existing if similar

### 11.4 Memory Injection

At session start, relevant memories are loaded into the system prompt:
- **Budget**: 300-500 tokens for memory context
- **Selection**: Most relevant memories by category + recency
- **Format**: Concise bullet points, not full conversation excerpts

### 11.5 Relevance to HybridCoder

| Aspect | Cloud Agents | HybridCoder |
|--------|-------------|-------------|
| Memory storage | Vector DB + LLM | SQLite + token budget |
| Extraction | LLM after each session | LLM on `/memory save` or auto |
| Injection | Semantic search | Top-N by relevance score |
| Decay | Per-access refresh | 0.95x decay per session |
| Max entries | Thousands | 50 per project (token budget) |

**Sources:**
- https://langchain-ai.github.io/langmem/concepts/conceptual_guide/
- https://arxiv.org/abs/2310.08560 (MemGPT)

---

## 12. Checkpoint & Recovery

### 12.1 Durable Execution Pattern

LangGraph and similar frameworks implement durable execution:
- **Checkpoints** saved after each completed step
- On failure, restore to last checkpoint and retry (or reflect-and-retry)
- Enables **resumable workflows** across crashes/restarts
- Thread-scoped checkpoints enable replay and localized repair

### 12.2 Reflect-and-Retry

A sophisticated error recovery pattern:
1. Agent encounters an error
2. Agent **reflects** on the error (what went wrong, why)
3. Agent retries with a corrected approach
4. If retry fails, escalate to user

This triples LLM calls but dramatically improves success rates.

### 12.3 Checkpoint Contents

For a coding agent, a checkpoint includes:
- **Session state**: Current messages, active files
- **Task state**: Task list snapshot (which tasks are done, in progress, pending)
- **Plan state**: Current plan text (if using plan-first workflow)
- **Context summary**: Compressed summary of conversation so far
- **Tool state**: Active file contents, search results cache

### 12.4 Relevance to HybridCoder

Checkpoints are valuable for:
- **Resumable multi-file edits**: Save progress after each file
- **Error recovery**: Restore to last good state on failure
- **Session continuity**: Resume interrupted sessions with full context
- **Storage**: SQLite table with JSON-serialized state

**Sources:**
- https://google.github.io/adk-docs/plugins/reflect-and-retry/
- https://agentsarcade.com/blog/error-handling-agentic-systems-retries-rollbacks-graceful-failure/
- https://blog.langchain.com/planning-agents/

---

## 13. Token Budget Economics

### 13.1 Context Budget Allocation

For a 8192-token context window (Qwen3-8B default):

| Component | Tokens | % |
|-----------|--------|---|
| System prompt | 800 | 10% |
| Tool definitions | 600 | 7% |
| Memory context | 500 | 6% |
| Task summary | 300 | 4% |
| Compact summary | 600 | 7% |
| Recent messages | 3400 | 41% |
| LLM response headroom | 2000 | 24% |
| **Total** | **8200** | **100%** |

### 13.2 Cost of Compaction

Each auto-compaction requires one LLM call (~500 input tokens, ~300 output tokens). At our context size, this is:
- ~1-2 seconds latency
- Amortized over every 5-10 iterations
- Net positive: enables 3x more iterations per session

### 13.3 Prefix Caching Benefits

For Ollama with KV cache reuse:
- System prompt + tool definitions: cached across iterations (~1400 tokens saved)
- First-token latency improvement: ~40-60% for repeated prefixes
- HybridCoder should structure prompts to maximize cache hits

### 13.4 Production Economics (For Reference)

Cloud agents process 100:1 input-output token ratio in production:
- 10,000 conversations/day without optimization = $255,000/year
- Basic compression reduces 60% of tokens without information loss
- Cached tokens are 75% cheaper than non-cached
- **HybridCoder**: $0/year (local inference), but latency matters

**Sources:**
- https://www.getmaxim.ai/articles/context-engineering-ai-agents-token-optimization/
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

---

## 14. Implications for HybridCoder

### 14.1 What We Should Build (Phase 4)

Based on this research, the Phase 4 priorities are:

1. **ContextEngine** — Automatic context management
   - Token counting for all messages
   - Auto-compaction at 75% budget (LLM summarization)
   - Tool result truncation (>500 tokens)
   - Observation collapse for old iterations

2. **TaskStore** — SQLite-backed task DAG
   - Tasks with dependencies (blocks/blockedBy)
   - LLM tools: create_task, update_task, list_tasks
   - Task summary injected into system prompt each iteration
   - `/tasks` slash command for user visibility

3. **SubagentLoop** — Isolated context execution
   - Shares LLM via asyncio.Lock (sequential access)
   - Restricted tool sets per subagent type
   - Max 5 iterations (vs 10 for main agent)
   - Returns summary to orchestrator

4. **MemoryStore** — Episodic memory in SQLite
   - Categories: tool_pattern, user_preference, project_fact, error_resolution
   - Relevance decay (0.95x per session)
   - LLM extraction after sessions
   - Memory injection into system prompt

5. **CheckpointStore** — Resumable state
   - Save/restore session state
   - Task list snapshot
   - Context summary

### 14.2 What We Should NOT Build (Yet)

- **Vector memory** (requires embedding infrastructure — Phase 4 Layer 2)
- **Dynamic agent swarms** (requires parallel LLM — not feasible on single GPU)
- **Recursive subagents** (flat hierarchy only)
- **MCP server** (useful but out of scope for Phase 4)
- **Architect/Editor split** (Phase 5, depends on Layer 3)

### 14.3 Single-LLM Constraint Adaptations

| Cloud Pattern | HybridCoder Adaptation |
|---------------|----------------------|
| Parallel LLM calls | asyncio.Lock for sequential access |
| Model routing | L3 (1.5B) vs L4 (8B) based on task complexity |
| 200k context | 8k context with aggressive compaction |
| Vector search for memory | SQLite with relevance scoring |
| Cloud checkpoints | SQLite checkpoint table |

---

## 15. References

### Agent Architectures
1. Claude Code Subagent Docs — https://code.claude.com/docs/en/sub-agents
2. Tracing Claude Code's LLM Traffic — https://medium.com/@georgesung/tracing-claude-codes-llm-traffic-agentic-loop-sub-agents-tool-use-prompts-7796941806f5
3. SWE-agent NeurIPS Paper — https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf
4. SWE-agent Architecture — https://swe-agent.com/latest/background/architecture/
5. Aider Architect Pattern — https://aider.chat/docs/usage/modes.html
6. Aider Repository Map — https://aider.chat/docs/repomap.html
7. OpenCode Agents — https://opencode.ai/docs/agents/
8. OpenCode Orchestration — https://deepwiki.com/code-yeongyu/oh-my-opencode/4.1-sisyphus-orchestrator
9. Kimi K2.5 Blog — https://www.kimi.com/blog/kimi-k2-5.html
10. Kimi K2.5 Agent Swarm Guide — https://www.datacamp.com/tutorial/kimi-k2-agent-swarm-guide
11. Devin 2.0 Technical Design — https://medium.com/@takafumi.endo/agent-native-development-a-deep-dive-into-devin-2-0s-technical-design-3451587d23c0
12. Devin 2.0 Blog — https://cognition.ai/blog/devin-2
13. Codex CLI Docs — https://developers.openai.com/codex/cli/
14. Building with Codex MCP — https://cookbook.openai.com/examples/codex/codex_mcp_agents_sdk/

### Context Management
15. Context Compaction (Google ADK) — https://google.github.io/adk-docs/context/compaction/
16. Acon Context Compression — https://arxiv.org/html/2510.00615v1
17. Context Engineering (Anthropic) — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
18. Token Optimization Strategies — https://www.getmaxim.ai/articles/context-engineering-ai-agents-token-optimization/

### Memory
19. Langmem Conceptual Guide — https://langchain-ai.github.io/langmem/concepts/conceptual_guide/
20. MemGPT Paper — https://arxiv.org/abs/2310.08560

### Error Handling & Recovery
21. Reflect and Retry (Google ADK) — https://google.github.io/adk-docs/plugins/reflect-and-retry/
22. Error Handling in Agentic Systems — https://agentsarcade.com/blog/error-handling-agentic-systems-retries-rollbacks-graceful-failure/
23. Reflection Pattern — https://agent-patterns.readthedocs.io/en/stable/patterns/reflection.html

### Planning
24. Plan-and-Execute Agents (LangChain) — https://blog.langchain.com/planning-agents/
25. Plan-and-Act Guide — https://forgecode.dev/docs/plan-and-act-guide/

### Streaming & MCP
26. AG-UI Real-time Streaming — https://medium.datadriveninvestor.com/production-grade-agentic-apps-with-ag-ui-real-time-streaming-guide-2026-5331c452684a
27. Bidirectional Streaming Multi-Agent — https://developers.googleblog.com/en/beyond-request-response-architecting-real-time-bidirectional-streaming-multi-agent-system/
28. Model Context Protocol — https://modelcontextprotocol.io/
29. MCP Announcement — https://www.anthropic.com/news/model-context-protocol

---

*Research compiled from web searches, documentation review, and academic papers. All sources accessed February 2026.*
