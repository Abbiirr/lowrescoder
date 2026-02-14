# Phase 5 — Agent Teams & A2A Communication

> Status: DRAFT (research phase)
> Last updated: 2026-02-14
> Depends on: Phase 4 (Agent Orchestration) — COMPLETE

---

## 1. Vision

Phase 5 transforms HybridCoder from a single-agent assistant with background subagents into a **multi-agent team** where specialized agents collaborate on complex tasks — each potentially running a different model, communicating through a structured protocol, and discoverable by other agents.

**Core idea:** Generalize the markdown-based agent communication protocol used in this project (`AGENT_COMMUNICATION_RULES.md`) into a runtime agent-to-agent system, drawing from Google's A2A protocol and MetaGPT's role-based SOP patterns, while staying true to HybridCoder's edge-native, local-first principles.

### 1.1 Design Principles (carry forward from Phase 0)

1. **Local-first** — All agents run on the user's machine. No cloud dependency required.
2. **Consumer hardware** — Agent teams must function within 8GB VRAM / 16GB RAM.
3. **LLM as last resort** — Deterministic coordination where possible; LLM only for reasoning.
4. **Different models for different roles** — Small models (1.5B-3B) for focused tasks, larger models (7B-8B) for complex reasoning.
5. **Run anywhere** — Protocol is transport-agnostic. Works in-process, over stdio, over HTTP.
6. **Generic protocol** — Not HybridCoder-specific. Reusable across any agent system.

---

## 2. Industry Landscape (Research Summary)

### 2.1 Google A2A Protocol

The Agent2Agent (A2A) protocol (v0.3, donated to Linux Foundation) is the emerging interoperability standard for agent-to-agent communication.

**Key concepts:**
- **Agent Card** — JSON metadata at `/.well-known/agent.json` describing identity, capabilities, skills, auth requirements
- **Task lifecycle** — `submitted → working → input-required → completed/failed/canceled/rejected`
- **JSON-RPC 2.0** — All communication over HTTP(S) with SSE streaming
- **Parts** — Messages contain typed parts (text, fileReference, structuredData, html)
- **Artifacts** — Structured outputs from completed tasks
- **Push notifications** — Webhook-based event delivery for long-running tasks

**Fit for HybridCoder:**
- A2A's JSON-RPC transport matches our existing Go TUI ↔ Python backend protocol
- Task lifecycle maps cleanly to our TaskStore states
- Agent Cards provide discovery mechanism we currently lack
- However: A2A is designed for **HTTP-based networked agents**, not in-process teams
- We need a **lightweight local adaptation** that preserves the protocol semantics but works in-process

### 2.2 MCP vs A2A — Complementary Protocols

| Aspect | MCP (Model Context Protocol) | A2A (Agent-to-Agent) |
|--------|-----|-----|
| Direction | Vertical — agent ↔ tools/data | Horizontal — agent ↔ agent |
| Focus | Tool invocation, context injection | Task delegation, capability discovery |
| Transport | JSON-RPC over stdio/SSE | JSON-RPC over HTTP/gRPC/SSE |
| State | Stateless tool calls | Stateful task lifecycle |

**For HybridCoder:** MCP is for Phase 5b (external tool integration). A2A is the core of Phase 5a (agent teams).

### 2.3 Multi-Agent Frameworks

| Framework | Architecture | Multi-Model | Local Support | Maturity |
|-----------|-------------|-------------|---------------|----------|
| **MetaGPT** | Role-based SOP (PM → Architect → Engineer → QA) | Yes (per role) | Yes (Ollama) | Production |
| **AutoGen/AG2** | Conversational agents, async, human-in-loop | Yes | Yes (local models) | Production |
| **CrewAI** | Role-based crews with tasks | Yes (per agent) | Yes (Ollama) | Production |
| **LangGraph** | Graph-based state machines | Yes (per node) | Yes | Production |
| **OpenAI Swarm → Agents SDK** | Handoff functions, routines | Limited (OpenAI models) | No | Experimental→Production |

**Key insight from MetaGPT:** SOPs (Standard Operating Procedures) encoded as prompt chains produce far better multi-agent results than free-form agent conversations. This aligns with our layered intelligence model — deterministic coordination first, LLM reasoning second.

### 2.4 What Our Codebase Already Has

From Phase 4, we have these primitives that directly support agent teams:

| Primitive | Location | Team Use |
|-----------|----------|----------|
| SubagentLoop | `subagent.py` | Isolated mini-loop per agent team member |
| SubagentType (EXPLORE/PLAN/EXECUTE) | `subagent.py` | Role-based capability filtering |
| LLMScheduler | `subagent.py` | Priority queue for multi-model scheduling |
| ToolRegistry + capability flags | `tools.py` | Per-agent tool access control |
| TaskStore (DAG) | `task_store.py` | Shared work tracking with dependencies |
| MemoryStore | `memory.py` | Cross-session learning (project-scoped) |
| CheckpointStore | `checkpoint_store.py` | State snapshots for rollback |
| ApprovalManager | `approval.py` | Safety gates for destructive operations |
| Plan mode | `loop.py` | Read-only exploration phase |
| AGENT_COMMUNICATION_RULES.md | Root | Protocol template for structured agent messages |

**Gap analysis — what's missing:**

1. **Agent identity** — No first-class agent identity system (messages are just `role: assistant`)
2. **Agent discovery** — No way for agents to discover each other's capabilities
3. **Inter-agent messaging** — Subagents communicate only via task state; no direct messaging
4. **Multi-model support** — Single LLM provider instance shared by all agents
5. **Agent lifecycle** — No persistent agent definitions; subagents are ephemeral
6. **Team definitions** — No way to define a team of agents with roles and SOPs
7. **Context isolation** — All agents share the same context; no private context per agent
8. **Handoff protocol** — No structured way for one agent to delegate to another with context

---

## 3. Architecture

### 3.1 Layer Diagram

```
┌─────────────────────────────────────────────────────┐
│                   User / Go TUI                      │
├─────────────────────────────────────────────────────┤
│                  Team Coordinator                    │
│         (orchestrates agents, routes messages)       │
├──────────┬──────────┬──────────┬────────────────────┤
│ Architect│ Engineer │ Reviewer │  Scout (Explorer)  │
│  (L4:7B) │ (L3:1.5B)│ (L4:7B) │   (L1/L2 only)    │
├──────────┴──────────┴──────────┴────────────────────┤
│              Agent Message Bus (AgentBus)            │
│        (pub/sub, structured messages, routing)       │
├─────────────────────────────────────────────────────┤
│ Agent Card │ Provider  │ Tool      │ Task     │ Mem │
│ Registry   │ Registry  │ Registry  │ Store    │ Stre│
└─────────────────────────────────────────────────────┘
```

### 3.2 Core Concepts

**AgentCard** — A2A-inspired JSON descriptor for each agent:
```python
@dataclass
class AgentCard:
    id: str                    # Unique agent identifier
    name: str                  # Human-readable name (e.g., "Architect")
    role: AgentRole            # ARCHITECT, ENGINEER, REVIEWER, SCOUT, COORDINATOR
    model: ModelSpec           # Which LLM to use (provider + model name)
    skills: list[str]          # What this agent can do
    tools: list[str]           # Allowed tool names (or capability filter)
    system_prompt: str         # Role-specific system prompt
    priority: int              # LLM scheduler priority (0=highest)
    max_iterations: int        # Per-turn iteration limit
    context_budget: int        # Max tokens for this agent's context
```

**AgentTeam** — A named collection of agents with an SOP:
```python
@dataclass
class AgentTeam:
    id: str
    name: str                  # e.g., "Code Review Team"
    agents: list[AgentCard]    # Team members
    coordinator: str           # Agent ID that orchestrates
    sop: list[SOPStep]         # Standard Operating Procedure
    shared_memory: bool        # Whether agents share MemoryStore
    shared_tasks: bool         # Whether agents share TaskStore
```

**SOPStep** — Deterministic workflow step:
```python
@dataclass
class SOPStep:
    agent: str                 # Agent ID to execute this step
    action: str                # What to do (prompt template)
    input_from: str | None     # Previous step's output (artifact ID)
    output_type: str           # Expected output format
    gate: str | None           # Condition to proceed (e.g., "all_tests_pass")
```

**AgentMessage** — Structured inter-agent message (A2A-inspired):
```python
@dataclass
class AgentMessage:
    id: str
    from_agent: str            # Sender agent ID
    to_agent: str | None       # Recipient (None = broadcast to team)
    message_type: MessageType  # TASK_HANDOFF, CONCERN, REVIEW, STATUS_UPDATE
    parts: list[MessagePart]   # Text, structured data, file references
    task_id: str | None        # Associated task
    context_id: str | None     # Conversation thread
    timestamp: datetime
```

### 3.3 Model Assignment Strategy

Different agents use different models based on their role:

| Role | Model | VRAM | Rationale |
|------|-------|------|-----------|
| **Scout** | None (L1/L2 only) | 0 | Tree-sitter + embeddings, no LLM needed |
| **Engineer** | Qwen2.5-Coder-1.5B (L3) | ~1 GB | Constrained generation for edits |
| **Architect** | Qwen3-8B (L4) | ~5 GB | Complex reasoning for planning |
| **Reviewer** | Qwen3-8B (L4) | ~5 GB | Deep analysis for review |
| **Coordinator** | Qwen3-8B (L4) or rules-only | 0-5 GB | Can be deterministic SOP runner |

**VRAM budget:** Scout (0) + Engineer (1 GB) + one L4 agent (5 GB) = **6 GB** — fits in 8 GB VRAM with headroom. L4 agents time-share via LLMScheduler.

### 3.4 Provider Registry (Multi-Model)

Extend the current single-provider design to a registry:

```python
class ProviderRegistry:
    """Maps model specs to LLM provider instances."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._l3_provider: L3Provider | None = None  # Shared L3 instance

    def register(self, spec: ModelSpec, provider: LLMProvider) -> None: ...
    def get(self, spec: ModelSpec) -> LLMProvider: ...
    def get_l3(self) -> L3Provider | None: ...  # For constrained gen
```

**Key constraint:** Only one L3 model and one L4 model loaded at a time (VRAM). L4 agents share the Ollama instance. L3 agents share the llama-cpp instance. LLMScheduler serializes access.

---

## 4. Sprint Plan

### 4.1 Sprint 5A — Agent Identity & Multi-Model (Foundation)

**Goal:** First-class agent identity, multi-model provider registry, agent cards.

| Task | Priority | Description |
|------|----------|-------------|
| AgentCard dataclass | P0 | Identity, role, model spec, skills, tools, prompt |
| AgentRole enum | P0 | ARCHITECT, ENGINEER, REVIEWER, SCOUT, COORDINATOR |
| ModelSpec dataclass | P0 | Provider + model name + layer (L3/L4) |
| ProviderRegistry | P0 | Multi-model provider management, lazy loading |
| Agent identity in messages | P0 | Add `agent_id` to session messages and tool calls |
| Extend SubagentLoop | P1 | Accept AgentCard, use card's model/tools/prompt |
| Extend LLMScheduler | P1 | Route to correct provider based on ModelSpec |
| AgentConfig extensions | P1 | Team definitions in YAML config |
| `/agents` command | P2 | List registered agent cards |

### 4.2 Sprint 5B — Agent Message Bus & Teams

**Goal:** Structured inter-agent communication, team definitions, SOP runner.

| Task | Priority | Description |
|------|----------|-------------|
| AgentBus | P0 | Pub/sub message bus for inter-agent communication |
| AgentMessage dataclass | P0 | Structured message with parts, types, routing |
| MessageStore (SQLite) | P0 | Persistent message log (replaces markdown AGENTS_CONVERSATION) |
| AgentTeam dataclass | P0 | Team definition with agents and SOP |
| SOPRunner | P0 | Deterministic SOP executor — runs steps in sequence |
| Team lifecycle | P1 | Create team, assign agents, start SOP, monitor |
| Handoff protocol | P1 | Structured context transfer between agents |
| Context isolation | P1 | Per-agent context windows, shared vs private |
| `/team` command | P2 | Create/list/manage teams |
| Go TUI team panel | P2 | Show team members, active agent, SOP progress |

### 4.3 Sprint 5C — Architect/Editor Pattern & Feedback Loops

**Goal:** Implement the canonical multi-agent coding pattern.

| Task | Priority | Description |
|------|----------|-------------|
| Architect agent | P0 | Plans edits using L4, produces structured edit plan |
| Editor agent | P0 | Applies edits using L3 constrained generation |
| LLMLOOP | P0 | edit → compile → fix cycle using tree-sitter diagnostics |
| Feedback channel | P1 | Editor sends compile errors back to Architect |
| Verification gate | P1 | Automated test run as SOP gate condition |
| Built-in SOPs | P1 | Pre-defined SOPs: CodeReview, BugFix, FeatureImpl |
| MCP server (basic) | P2 | Expose HybridCoder tools via MCP for external agents |

### 4.4 Sprint 5D — A2A Compatibility & External Agents

**Goal:** Make HybridCoder agents discoverable and interoperable via A2A.

| Task | Priority | Description |
|------|----------|-------------|
| A2A Agent Card endpoint | P1 | Serve `/.well-known/agent.json` over HTTP |
| A2A task lifecycle | P1 | Map TaskStore states to A2A states |
| A2A JSON-RPC server | P1 | HTTP server implementing A2A SendMessage/GetTask |
| A2A client | P1 | Connect to external A2A agents |
| A2A streaming (SSE) | P2 | Real-time task updates via Server-Sent Events |
| MCP server (full) | P2 | Complete MCP tool exposure for external consumption |
| External agent handoff | P2 | Delegate tasks to external A2A agents |

---

## 5. Detailed Design — Sprint 5A

### 5.1 New Files

| File | Purpose |
|------|---------|
| `src/hybridcoder/agent/identity.py` | AgentCard, AgentRole, ModelSpec dataclasses |
| `src/hybridcoder/agent/provider_registry.py` | Multi-model provider management |
| `src/hybridcoder/agent/team.py` | AgentTeam, SOPStep, SOPRunner |
| `src/hybridcoder/agent/bus.py` | AgentBus, AgentMessage, MessageStore |

### 5.2 Modified Files

| File | Change |
|------|--------|
| `src/hybridcoder/agent/subagent.py` | SubagentLoop accepts AgentCard; route to ProviderRegistry |
| `src/hybridcoder/agent/loop.py` | Accept agent_id; tag messages with identity |
| `src/hybridcoder/session/store.py` | Add `agent_id` column to messages table |
| `src/hybridcoder/session/models.py` | DDL for agent_cards, agent_messages tables |
| `src/hybridcoder/config.py` | AgentTeamConfig, ModelSpec in YAML |
| `src/hybridcoder/backend/server.py` | ProviderRegistry creation, agent routing |
| `src/hybridcoder/tui/commands.py` | `/agents`, `/team` commands |

### 5.3 AgentCard Schema

```python
class AgentRole(StrEnum):
    COORDINATOR = "coordinator"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    SCOUT = "scout"
    CUSTOM = "custom"


@dataclass
class ModelSpec:
    """Which LLM to use for this agent."""
    provider: str          # "ollama", "openrouter", "llama-cpp", "none"
    model: str             # "qwen3:8b", "qwen2.5-coder:1.5b", etc.
    layer: int = 4         # Which intelligence layer (1-4)
    temperature: float = 0.7
    max_tokens: int = 4096

    @classmethod
    def l1_only(cls) -> ModelSpec:
        """No LLM — deterministic tools only."""
        return cls(provider="none", model="none", layer=1)

    @classmethod
    def l3_default(cls) -> ModelSpec:
        """L3 constrained generation."""
        return cls(provider="llama-cpp", model="qwen2.5-coder:1.5b", layer=3)

    @classmethod
    def l4_default(cls) -> ModelSpec:
        """L4 full reasoning."""
        return cls(provider="ollama", model="qwen3:8b", layer=4)


@dataclass
class AgentCard:
    """A2A-inspired agent identity descriptor."""
    id: str
    name: str
    role: AgentRole
    model: ModelSpec
    skills: list[str] = field(default_factory=list)
    tool_filter: dict[str, bool] = field(default_factory=dict)
    system_prompt_template: str = ""
    priority: int = 1              # LLM scheduler priority
    max_iterations: int = 5
    context_budget: int = 4096
    can_spawn_subagents: bool = False
    can_approve: bool = False      # Can this agent approve tool calls?
```

### 5.4 ProviderRegistry Design

```python
class ProviderRegistry:
    """Manages LLM providers for multi-model agent teams.

    Constraint: Only one L3 and one L4 model loaded at a time.
    Agents time-share via LLMScheduler.
    """

    def __init__(self, config: HybridCoderConfig):
        self._l4_provider: LLMProvider | None = None
        self._l3_provider: L3Provider | None = None
        self._config = config

    def get_provider(self, spec: ModelSpec) -> LLMProvider | L3Provider:
        """Get or create provider for the given model spec."""
        if spec.layer == 3:
            return self._ensure_l3(spec)
        elif spec.layer == 4:
            return self._ensure_l4(spec)
        else:
            raise ValueError(f"Layers 1-2 don't use LLM providers")

    def _ensure_l4(self, spec: ModelSpec) -> LLMProvider:
        """Lazy-load L4 provider (Ollama or OpenRouter)."""
        ...

    def _ensure_l3(self, spec: ModelSpec) -> L3Provider:
        """Lazy-load L3 provider (llama-cpp-python)."""
        ...

    def cleanup(self) -> None:
        """Release all model resources."""
        ...
```

### 5.5 How SubagentLoop Changes

Current SubagentLoop takes `provider`, `tool_registry`, `subagent_type`. After 5A:

```python
class SubagentLoop:
    def __init__(
        self,
        agent_card: AgentCard,           # NEW: replaces subagent_type
        provider_registry: ProviderRegistry,  # NEW: replaces provider
        tool_registry: ToolRegistry,
        scheduler: LLMScheduler,
        ...
    ):
        # Resolve provider from card's model spec
        self._provider = provider_registry.get_provider(agent_card.model)
        # Filter tools based on card's tool_filter + role capabilities
        self._registry = self._build_filtered_registry(tool_registry, agent_card)
        # Use card's system prompt template
        self._system_prompt = agent_card.system_prompt_template
        # Use card's priority for scheduler
        self._priority = agent_card.priority
```

---

## 6. Detailed Design — Sprint 5B

### 6.1 AgentBus — Inter-Agent Communication

The AgentBus is the runtime equivalent of `AGENTS_CONVERSATION.MD`. It provides structured, typed, routed messaging between agents.

```python
class AgentBus:
    """Pub/sub message bus for agent-to-agent communication.

    Generalizes the AGENT_COMMUNICATION_RULES.md protocol into runtime:
    - Identity headers → AgentCard references
    - Message types → MessageType enum
    - Entry numbers → message IDs
    - Directed to → routing
    - Resolution → task state updates
    """

    def __init__(self, conn: sqlite3.Connection, session_id: str):
        self._store = MessageStore(conn, session_id)
        self._subscribers: dict[str, list[Callable]] = {}

    def send(self, message: AgentMessage) -> str:
        """Send a message. Returns message ID."""
        msg_id = self._store.save(message)
        self._notify_subscribers(message)
        return msg_id

    def subscribe(self, agent_id: str, callback: Callable) -> None:
        """Subscribe to messages directed to this agent."""
        ...

    def get_pending(self, agent_id: str) -> list[AgentMessage]:
        """Get unread messages for an agent."""
        ...

    def get_thread(self, context_id: str) -> list[AgentMessage]:
        """Get all messages in a conversation thread."""
        ...
```

### 6.2 SOPRunner — Deterministic Workflow Execution

```python
class SOPRunner:
    """Executes Standard Operating Procedures (SOPs) — deterministic
    multi-agent workflows inspired by MetaGPT's assembly line pattern.

    Each SOP step assigns work to a specific agent, feeds it the
    previous step's output, and gates on success conditions.
    """

    def __init__(self, team: AgentTeam, bus: AgentBus,
                 subagent_manager: SubagentManager):
        self._team = team
        self._bus = bus
        self._manager = subagent_manager
        self._current_step: int = 0
        self._artifacts: dict[str, Any] = {}

    async def run(self) -> SOPResult:
        """Execute SOP steps in sequence."""
        for step in self._team.sop:
            # 1. Get agent card for this step
            card = self._get_agent(step.agent)
            # 2. Build input from previous artifacts
            input_context = self._build_input(step)
            # 3. Spawn agent with this step's task
            result = await self._execute_step(card, step, input_context)
            # 4. Store output artifact
            self._artifacts[step.output_type] = result
            # 5. Check gate condition
            if step.gate and not self._check_gate(step.gate, result):
                return SOPResult(status="gate_failed", step=step)
        return SOPResult(status="completed", artifacts=self._artifacts)
```

### 6.3 Built-in Team Templates

```yaml
# config/teams/code-review.yaml
team:
  name: "Code Review"
  agents:
    - id: scout
      role: scout
      model: { provider: none, layer: 1 }
      skills: [find_references, search_code, list_symbols]
    - id: reviewer
      role: reviewer
      model: { provider: ollama, model: "qwen3:8b", layer: 4 }
      skills: [analyze_code, find_issues, suggest_fixes]
  coordinator: reviewer
  sop:
    - agent: scout
      action: "Find all files related to {target}"
      output_type: relevant_files
    - agent: reviewer
      action: "Review these files for {criteria}"
      input_from: relevant_files
      output_type: review_report
      gate: null  # No gate — always produce review

# config/teams/bug-fix.yaml
team:
  name: "Bug Fix"
  agents:
    - id: scout
      role: scout
      model: { provider: none, layer: 1 }
    - id: architect
      role: architect
      model: { provider: ollama, model: "qwen3:8b", layer: 4 }
    - id: engineer
      role: engineer
      model: { provider: llama-cpp, model: "qwen2.5-coder:1.5b", layer: 3 }
  coordinator: architect
  sop:
    - agent: scout
      action: "Find the bug location using error message: {error}"
      output_type: bug_location
    - agent: architect
      action: "Analyze the bug and plan the fix"
      input_from: bug_location
      output_type: fix_plan
    - agent: engineer
      action: "Apply the fix according to the plan"
      input_from: fix_plan
      output_type: code_changes
      gate: all_tests_pass
```

---

## 7. Detailed Design — Sprint 5C (Architect/Editor)

### 7.1 LLMLOOP — Edit-Compile-Fix Cycle

```
     ┌──────────┐
     │ Architect │ (L4: plans edits)
     │  Qwen3-8B │
     └─────┬─────┘
           │ structured edit plan
           ▼
     ┌──────────┐
     │ Engineer  │ (L3: applies edits)
     │ Qwen2.5  │
     └─────┬─────┘
           │ modified files
           ▼
     ┌──────────┐
     │ tree-sitter│ (L1: parse + check)
     │ diagnostics│
     └─────┬─────┘
           │ errors?
     ┌─────┴─────┐
     │  Yes  │ No │
     │       │    │
     ▼       ▼    ▼
  Feedback  PASS  Done
  to Arch.
```

The LLMLOOP implements the Architect/Editor split from the Phase 5 requirements:

1. **Architect** (L4) receives the task and produces a structured edit plan
2. **Engineer** (L3) applies edits using constrained generation
3. **tree-sitter** (L1) parses the result for syntax errors
4. **If errors:** Feed diagnostics back to Architect for plan revision
5. **Max 3 iterations** of the loop, then escalate to user

### 7.2 Structured Edit Plan

```python
@dataclass
class EditPlan:
    """Structured output from Architect agent."""
    file: str
    edits: list[Edit]
    reasoning: str
    test_command: str | None

@dataclass
class Edit:
    """Single edit operation."""
    type: Literal["replace", "insert", "delete"]
    location: str          # Symbol path or line range
    old_content: str       # For replace: what to find
    new_content: str       # What to write
    context: str           # Why this edit
```

The Architect outputs a JSON-schema-constrained EditPlan. The Engineer applies it using L3's grammar-constrained generation (Outlines). Tree-sitter validates the result is syntactically correct.

---

## 8. Detailed Design — Sprint 5D (A2A Compatibility)

### 8.1 A2A Agent Card Endpoint

```python
# Serve at /.well-known/agent.json
{
    "id": "hybridcoder-instance-uuid",
    "name": "HybridCoder",
    "provider": {
        "name": "HybridCoder",
        "url": "https://github.com/user/hybridcoder"
    },
    "capabilities": {
        "streaming": true,
        "pushNotifications": false
    },
    "skills": [
        {"name": "code_review", "description": "Review code for issues"},
        {"name": "bug_fix", "description": "Diagnose and fix bugs"},
        {"name": "refactor", "description": "Refactor code structures"}
    ],
    "interfaces": [
        {"protocol": "jsonrpc", "url": "http://localhost:8642/a2a"}
    ]
}
```

### 8.2 Task State Mapping

| HybridCoder TaskStore | A2A Task State |
|----------------------|----------------|
| `pending` | `submitted` |
| `in_progress` | `working` |
| `blocked` (has unmet deps) | `input-required` |
| `completed` | `completed` |

### 8.3 A2A Server (HTTP)

A thin HTTP wrapper around the existing JSON-RPC backend:

```python
class A2AServer:
    """HTTP server implementing A2A protocol for external agent interop."""

    def __init__(self, backend: BackendServer, port: int = 8642):
        self._backend = backend
        self._port = port

    async def handle_send_message(self, request: A2AMessage) -> A2ATask:
        """A2A SendMessage → create task + run agent."""
        ...

    async def handle_get_task(self, task_id: str) -> A2ATask:
        """A2A GetTask → read TaskStore."""
        ...

    async def handle_cancel_task(self, task_id: str) -> A2ATask:
        """A2A CancelTask → cancel subagent."""
        ...
```

---

## 9. Relationship to AGENT_COMMUNICATION_RULES.md

The current `AGENT_COMMUNICATION_RULES.md` protocol used in this project is essentially a **human-readable precursor** to what Phase 5 builds programmatically:

| AGENT_COMMUNICATION_RULES.md | Phase 5 Runtime |
|-------------------------------|----------------|
| Identity header (`Agent: X | Role: Y`) | `AgentCard` dataclass |
| Message types (Concern, Review, Handoff) | `MessageType` enum |
| Entry numbers | `AgentMessage.id` |
| `Directed to:` | `AgentMessage.to_agent` |
| `Replying to:` | `AgentMessage.context_id` |
| `AGENTS_CONVERSATION.MD` file | `AgentBus` + `MessageStore` (SQLite) |
| Resolution rules | Task state transitions |
| Archival to `docs/communication/old/` | Message retention + cleanup |
| Tools Used footer | Message metadata |

**The key generalization:** Instead of agents reading/writing a shared markdown file, they publish typed messages to a bus with structured routing, automatic delivery, and programmatic resolution — while preserving the same semantic model (identity, types, threading, resolution).

---

## 10. Test Strategy

### 10.1 Test Counts

| Sprint | New Tests | Cumulative |
|--------|-----------|------------|
| 5A | ~25 | 1000+ |
| 5B | ~30 | 1030+ |
| 5C | ~20 | 1050+ |
| 5D | ~15 | 1065+ |

### 10.2 Test Categories

- **Unit:** AgentCard, ModelSpec, ProviderRegistry, AgentBus, MessageStore, SOPRunner
- **Integration:** Multi-agent team execution, handoff sequences, LLMLOOP cycles
- **Contract:** A2A protocol compliance, message format validation
- **E2E:** Team-based bug fix scenario, team-based code review scenario

---

## 11. Configuration

```yaml
# .hybridcoder.yaml additions
teams:
  default_team: "solo"  # or "code-review", "bug-fix", "feature-impl"

  definitions:
    solo:
      agents:
        - { id: main, role: coordinator, model: { provider: ollama, model: "qwen3:8b" } }

    code-review:
      agents:
        - { id: scout, role: scout, model: { provider: none, layer: 1 } }
        - { id: reviewer, role: reviewer, model: { provider: ollama, model: "qwen3:8b" } }
      coordinator: reviewer
      sop: [scout-gather, reviewer-analyze]

    bug-fix:
      agents:
        - { id: scout, role: scout, model: { provider: none, layer: 1 } }
        - { id: architect, role: architect, model: { provider: ollama, model: "qwen3:8b" } }
        - { id: engineer, role: engineer, model: { provider: llama-cpp, model: "qwen2.5-coder:1.5b" } }
      coordinator: architect
      sop: [scout-locate, architect-plan, engineer-apply, verify-tests]

agents:
  a2a:
    enabled: false          # Enable A2A HTTP server
    port: 8642
    auth: null              # No auth for local-only

  provider_registry:
    max_loaded_models: 2    # Max models in VRAM simultaneously
    auto_unload: true       # Unload unused models after timeout
    unload_timeout: 300     # Seconds before auto-unload
```

---

## 12. Exit Criteria

### Sprint 5A
- [ ] AgentCard, AgentRole, ModelSpec dataclasses implemented
- [ ] ProviderRegistry manages L3 + L4 providers
- [ ] SubagentLoop accepts AgentCard (backward-compatible)
- [ ] Messages tagged with agent_id in SessionStore
- [ ] `/agents` command lists registered cards
- [ ] 25 new tests pass

### Sprint 5B
- [ ] AgentBus pub/sub messaging works
- [ ] MessageStore persists messages (SQLite)
- [ ] AgentTeam + SOPRunner execute multi-step workflows
- [ ] Handoff protocol transfers context between agents
- [ ] `/team` command manages teams
- [ ] Go TUI team panel shows active agents
- [ ] 30 new tests pass

### Sprint 5C
- [ ] Architect agent produces structured EditPlan
- [ ] Engineer agent applies edits via L3 constrained gen
- [ ] LLMLOOP: edit → tree-sitter check → feedback cycle
- [ ] Max 3 loop iterations with escalation
- [ ] Built-in SOPs: CodeReview, BugFix
- [ ] 20 new tests pass

### Sprint 5D
- [ ] A2A Agent Card served at `/.well-known/agent.json`
- [ ] A2A SendMessage/GetTask/CancelTask implemented
- [ ] External agents can discover and delegate to HybridCoder
- [ ] MCP server exposes tools to external consumers
- [ ] 15 new tests pass

---

## 13. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| VRAM contention with multiple models | OOM crashes | Medium | Max 2 models loaded; auto-unload; sequential not parallel |
| SOP rigidity — agents can't adapt | Poor results for novel tasks | Medium | SOPs are templates with LLM-filled slots; coordinator can override |
| Inter-agent message storms | Queue flooding, latency | Low | Rate limiting on AgentBus; max messages per turn |
| A2A spec changes (still pre-1.0) | Protocol breakage | Medium | Abstract A2A behind adapter; version-pin to v0.3 |
| L3 model quality insufficient for Engineer | Bad edits, loop doesn't converge | Medium | LLMLOOP max 3 iterations then escalate to L4 |
| Team coordination overhead exceeds benefit | Slower than single agent | Medium | Solo team as default; teams only for complex multi-file tasks |

---

## 14. Dependencies

### 14.1 Sprint Dependencies

```
5A (Identity + Multi-Model) ─── blocks ──→ 5B (Bus + Teams)
                                                    │
                                             blocks ▼
                                          5C (Architect/Editor)
                                                    │
                                             blocks ▼
                                          5D (A2A + External)
```

### 14.2 External Dependencies

| Dependency | Sprint | Required | Notes |
|-----------|--------|----------|-------|
| Ollama | 5A+ | Yes | L4 provider (already integrated) |
| llama-cpp-python | 5A+ | Optional | L3 provider (graceful degradation) |
| Outlines | 5C | Optional | Structured output for EditPlan |
| aiohttp | 5D | Optional | A2A HTTP server |
| mcp-sdk | 5D | Optional | MCP server implementation |

---

## 15. Open Questions

1. **Team persistence:** Should team definitions persist across sessions, or be session-scoped? (Recommendation: project-scoped, stored in `.hybridcoder/teams/`)
2. **Agent memory isolation:** Should each agent in a team have its own MemoryStore, or share the project's? (Recommendation: shared project memory, with agent-tagged entries)
3. **Coordinator model:** Should the coordinator always be an LLM agent, or can it be a pure SOP runner (no LLM)? (Recommendation: both — deterministic SOP runner for defined workflows, LLM coordinator for ad-hoc tasks)
4. **A2A auth:** For local-only use, auth is unnecessary. If exposing to network, what auth model? (Recommendation: defer to 5D, start with localhost-only)
5. **Sprint 4C review fixes:** Codex identified 7 concerns in Sprint 4C (Entry 400). These should be addressed before starting Phase 5. (Recommendation: fix as pre-5A cleanup sprint)

---

## 16. References

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [A2A GitHub Repository](https://github.com/a2aproject/A2A)
- [A2A and MCP — Complementary Protocols](https://a2a-protocol.org/latest/topics/a2a-and-mcp/)
- [MCP vs A2A Guide](https://auth0.com/blog/mcp-vs-a2a/)
- [MetaGPT: Meta Programming for Multi-Agent Collaborative Framework](https://arxiv.org/abs/2308.00352)
- [MetaGPT GitHub](https://github.com/FoundationAgents/MetaGPT)
- [CrewAI vs LangGraph vs AutoGen Comparison](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [AI Agent Frameworks Comparison 2026](https://www.turing.com/resources/ai-agent-frameworks)
- [OpenAI Swarm → Agents SDK](https://github.com/openai/swarm)
- [Linux Foundation A2A Project](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
