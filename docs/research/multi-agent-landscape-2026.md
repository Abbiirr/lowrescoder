# Multi-Agent & Agent Orchestration Landscape — 2026 Research Notes

> Researched: 2026-02-17
> Sources: Multiple web searches, official docs, arXiv papers

---

## 1. A2A Protocol (Agent2Agent) — Current Status

### Linux Foundation Transfer
Google Cloud donated A2A to Linux Foundation on June 23, 2025. Founding members: AWS, Cisco, Google, Microsoft, Salesforce, SAP, ServiceNow.

### Current Version: v0.3
Key v0.3 features:
- **gRPC support** alongside JSON-RPC 2.0 and HTTP/REST
- **Security**: TLS 1.3+ recommended for production
- **Multi-transport consistency** requirements
- **Draft v1.0** in progress at `a2a-protocol.org/dev/specification/`

### Core Concepts
- **AgentCard**: JSON metadata declaring capabilities, transports, auth
- **Task lifecycle**: submitted → working → input-required → completed/failed/canceled
- **JSON-RPC 2.0** over HTTP(S) with SSE streaming
- **Parts**: text, fileReference, structuredData, html
- **Artifacts**: Structured outputs from completed tasks

### Fit for AutoCode
- A2A's JSON-RPC transport matches our Go TUI ↔ Python backend protocol
- Task lifecycle maps to our TaskStore states
- Agent Cards provide discovery mechanism
- We need lightweight local adaptation (A2A designed for HTTP networked agents)

---

## 2. MCP (Model Context Protocol) — Latest

### Governance
Anthropic donated MCP to **Agentic AI Foundation (AAIF)** under Linux Foundation in December 2025. Co-founded by Anthropic, Block, OpenAI.

### Spec Update: Streamable HTTP
March 2025 spec replaced dual SSE+HTTP with single endpoint supporting both POST and GET. Eliminates complexity of maintaining two connections.

### Industry Adoption
MCP is now **de facto standard for tool interop**: OpenAI Agents SDK, Google DeepMind, Zed, Sourcegraph, JetBrains, Cloudflare all support it.

### MCP vs A2A
- **MCP**: Agent-to-tool (vertical — giving agents access to tools/data)
- **A2A**: Agent-to-agent (horizontal — agents discovering and collaborating)
- **Complementary, not competing**

---

## 3. Multi-Agent Frameworks — 2026 State

### 3a. MetaGPT / MGX
- Launched **MGX** (Feb 2025) — world's first AI agent development team
- Core pattern: **SOPs (Standard Operating Procedures)** as prompt chains
- Assembly line: PM → Architect → Project Manager → Engineer
- **AFlow** paper accepted ICLR 2025 (top 1.8%)

### 3b. AutoGen → Microsoft Agent Framework
- **Major shift**: Microsoft merged AutoGen + Semantic Kernel into unified **Microsoft Agent Framework** (GA Q1 2026)
- AutoGen and Semantic Kernel now in **maintenance mode**
- AG2 (open-source fork) continues independently

### 3c. CrewAI
- Version 1.1.0 (Jan 2026)
- **Flows**: Production-grade event-driven orchestration, 12M+ executions/day
- **Native A2A support**: Async chain for agent-to-agent
- **HITL** for Flows
- 100,000+ developers certified

### 3d. LangGraph
- LangChain's clear message: "Use LangGraph for agents, not LangChain"
- **Graph-based architecture**: agents as nodes, connections as edges
- Key patterns: Supervisor, Peer-to-peer, Pipeline, Scatter-gather, HITL

### 3e. OpenAI Agents SDK
- Released March 2025, production evolution of Swarm
- **Core primitives** (intentionally minimal):
  - **Agents**: LLMs with instructions, tools, behavior
  - **Handoffs**: One-way transfer of control to another agent
  - **Guardrails**: Validation of agent inputs/outputs
  - **Runner**: Orchestrates execution
  - **Sessions**: Built-in session memory
- **Two patterns**: Handoff (decentralized, peer agents) and Manager (centralized, sub-agents as tools)
- Provider-agnostic (100+ LLMs), MCP support

### 3f. Google ADK (Agent Development Kit)
- Released at Google Cloud NEXT 2025
- Python, TypeScript, Go, Java
- **Three workflow agents**:
  - **SequentialAgent**: Execute in order
  - **ParallelAgent**: Run simultaneously with shared state
  - **LoopAgent**: Repeat until termination condition
- 8 documented design patterns
- Native A2A support, model-agnostic

---

## 4. Cost-Optimized Multi-Model Patterns

### Key Patterns

**a) Model Routing (Static)**
Select model per-query based on predicted complexity. IDC predicts by 2028, 70% of top AI enterprises will use multi-model routing.

**b) Model Cascading (Dynamic)**
Process through increasingly larger models, stopping when answer is sufficient.

**c) Cascade Routing (Hybrid)**
Combines routing + cascading. Research shows it **consistently outperforms both pure approaches**.

**d) OI-MAS Framework (January 2026, arXiv)**
- **State-dependent routing**: dynamically selects agent roles AND model scales
- Confidence mechanism: high confidence → small model; low confidence → large model
- **Up to 12.88% accuracy improvement + 79.78% cost reduction**

### Tiered Architecture Economics
```
Tier 1: Small models (1.5B-3B) — High-frequency execution
Tier 2: Mid-tier models (7B-14B) — Standard reasoning
Tier 3: Frontier models (70B+) — Complex planning
```
Combined with semantic caching: **90% cost reduction, 15x response time improvement**.

---

## 5. Claude Code's Tiered Model Pattern

### How It Works
- **Haiku** powers Explore subagent (rapid context gathering)
- Simple tasks auto-routed to Haiku: file reads, quick edits, boilerplate
- Complex reasoning stays on main Sonnet/Opus context

### Planner-Worker Pattern
```
Orchestrator (Opus/Sonnet) — plans, reasons, decides
    |
    +-- Worker (Haiku) — implements small parallelizable tasks
    +-- Worker (Haiku) — rapid, cheap execution
    +-- Worker (Haiku) — file reads, searches, boilerplate
```

### claude-router (Community Tool)
Automatic complexity-based routing:
- Simple queries → Haiku (~$0.01)
- Moderate tasks → Sonnet (~$0.03)
- Complex tasks → Opus (~$0.06)
- Claims ~40% cost reduction on complex workflows, ~80% overall

---

## 6. Key Takeaways for AutoCode

1. **Our 4-layer architecture is ahead of the curve.** Industry converging on tiered intelligence. Our L1→L2→L3→L4 is essentially cascade routing.

2. **OI-MAS validates our approach.** Confidence-aware routing across multi-scale models reduces cost by ~80% while improving accuracy.

3. **MCP is the tool interop standard.** A2A is the agent-to-agent standard. Both under Linux Foundation. We should support both.

4. **OpenAI's Manager pattern** = our agent loop orchestrating subagents. Their Handoff pattern = our inter-agent delegation.

5. **Google ADK's Sequential/Parallel/LoopAgent** = primitives we need for SOPRunner.

6. **Plan-and-Execute** (expensive plans, cheap executes) = our L4→L3 architecture. 90% cost reduction validates our approach.

---

## Sources

- [A2A Protocol Specification v0.3](https://a2a-protocol.org/v0.3.0/specification/)
- [A2A GitHub](https://github.com/a2aproject/A2A)
- [Linux Foundation A2A Launch](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project)
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MetaGPT GitHub](https://github.com/FoundationAgents/MetaGPT)
- [AG2 GitHub](https://github.com/ag2ai/ag2)
- [CrewAI Docs](https://docs.crewai.com/en/changelog)
- [LangGraph Multi-Agent](https://blog.langchain.com/langgraph-multi-agent-workflows/)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [Google ADK Docs](https://google.github.io/adk-docs/)
- [OI-MAS Paper](https://arxiv.org/abs/2601.04861)
- [Cascade Routing Paper](https://arxiv.org/abs/2410.10347)
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [claude-router GitHub](https://github.com/0xrdan/claude-router)
