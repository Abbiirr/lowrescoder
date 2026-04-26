# Phase 5 — Universal Orchestrator: Agent Teams, Multi-Model, External Integration

> Status: **PROVISIONAL_LOCKED** — Rev 6 (roadmap approved 2026-02-17, Rev 6 amendments applied 2026-02-18)
> Last updated: 2026-02-18
> Depends on: Phase 4 (Agent Orchestration) — COMPLETE
> Agreement trail: AGENTS_CONVERSATION.MD entries 424-489
> Rev 2 source: Entry 465-Claude (7 critical findings), Entry 468 (Codex blocker register), Entry 470-Claude (blocker resolution)
> Rev 3 source: Entry 471-Codex (B4/B5 amendments), Entry 472-Codex (vision-conformance audit, G1-G5 gates), Entry 473-Codex (user decisions D1-D3, waiver policy W1-W3)
> Rev 4 source: Entry 478-Codex (P1-P8 required inclusions), Entry 479-Codex (M1-M10 must-include + archival), Entry 480-Claude (comprehensive resolution + M9/M10 addition)
> Rev 5 source: Entry 484-Codex (B2 contradictions + R1-R6 deep-research deltas)
> Rev 6 source: Entry 487-Codex (Q1-Q5 adjudication), Entry 488-Claude (verdict acceptance + B2 fixes), Entry 489-Claude (archival + comprehensive reply)

---

## 1. Vision

Phase 5 transforms AutoCode from a single-agent coding assistant into a **feature-complete standalone AI coding tool** first, then a **universal orchestrator** that connects to Claude Code, Codex, OpenCode, and any future AI coding tool.

**Core strategy: "Standalone first, then interact."** AutoCode must have all the bells and whistles to stand on its own ground before building bridges. The standalone product (M1+M2) must be a fully functional, competitive AI coding assistant — with working LLMLOOP, proven context quality, agent orchestration, and cost intelligence. Only after the standalone MVP gate passes do we build external tool bridges (M3).

### 1.1 Design Principles (13 Locked)

1. **Zero setup** — Standalone by default, auto-detects external tools
2. **Bridges are additive** — Enhance external tools, never restrict them
3. **Agents talk to each other** — Real AgentBus with typed messages
4. **Local models reduce token cost** — Route cheap tasks to free local models
5. **Runtime tracking** — ExternalToolTracker discovers tools at runtime
6. **Can't compete on features** — Compete on integration + intelligence + cost
7. **Bidirectional** — HC orchestrates them AND they orchestrate HC (via MCP)
8. **AGENTS_CONVERSATION.MD as AgentBus reference** — Same semantics, programmatic runtime
9. **Robust but minimal** — 3 message types (REQUEST/RESULT/ISSUE), strict budget
10. **Easy first, optimize later** — Ship working bridges before perfecting them
11. **Inspect internals** — Understand tool mechanisms to build effective bridges
12. **LLM as last resort** — Deterministic tools first (tree-sitter, LSP, static analysis)
13. **Consumer hardware** — 8GB VRAM, 16GB RAM, max 2 models loaded

### 1.2 What AutoCode Becomes

```
┌─────────────────────────────────────────────────────────┐
│                     User / Go TUI                        │
├─────────────────────────────────────────────────────────┤
│                  AutoCode Core                        │
│   L1 (tree-sitter/LSP) → L2 (search) → L3 → L4         │
├──────────┬──────────┬──────────┬────────────────────────┤
│ LLMLOOP  │ AgentBus │ SOPRunner│  Policy Router         │
│ Arch→Edit│ REQ/RES  │ Pipelines│  L1→L3→L4→external     │
├──────────┴──────────┴──────────┴────────────────────────┤
│              External Tool Integration                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │Claude Code│  │  Codex   │  │ OpenCode │   ...more    │
│  │(via MCP + │  │(via MCP +│  │(via MCP+ │              │
│  │ CLAUDE.md)│  │AGENTS.md)│  │opencode. │              │
│  └──────────┘  └──────────┘  │  json)   │              │
│                               └──────────┘              │
├─────────────────────────────────────────────────────────┤
│ AgentCard │ Provider  │ Tool    │ Eval    │ Cost        │
│ Registry  │ Registry  │ Registry│ Harness │ Dashboard   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Industry Research Summary

> Full research: `docs/research/phase5-agent-teams-research.md`, `docs/research/claude-code-subagents.md`, `docs/research/opencode-and-competitors.md`, `docs/research/aider-architect-editor.md`, `docs/research/multi-agent-landscape-2026.md`

### 2.1 External Tool Configuration Surfaces

The primary integration path is through each tool's configuration surface — not CLI wrapping.

| | Claude Code | Codex | OpenCode |
|---|---|---|---|
| **MCP server** | `.claude/settings.json` | `mcp_servers` config | `opencode.json` → `mcp` |
| **Project rules** | `CLAUDE.md` | `codex.md` / instructions | `"instructions"` array |
| **Custom agents** | `.claude/agents/*.md` | Not first-class | `.opencode/agents/*.md` |
| **Custom commands** | `.claude/commands/*.md` | N/A | `.opencode/commands/*.md` |
| **Custom tools** | Via MCP only | Via MCP only | `.opencode/tools/` + MCP |
| **Per-agent model** | YAML frontmatter `model:` | N/A | `"agent": {"model": "..."}` |
| **Permissions** | `permissionMode` in agent def | Sandbox/approval flags | `"permission": {}` |
| **LSP** | Via extensions | N/A | 30+ built-in servers, `"lsp": {}` config |
| **Structured output** | N/A | `--json` flag | N/A |

### 2.2 OpenCode LSP Architecture

OpenCode has the most mature LSP integration of all three tools:
- 30+ pre-configured language servers (auto-launched on file detection)
- Full LSP client derived from `mcp-language-server` project
- **Only diagnostics exposed to the AI agent** — go-to-definition, find-references consumed internally but NOT passed to the LLM
- Community plugin `oh-my-opencode` adds `lsp_goto_definition`, `lsp_find_references`, `lsp_symbols`, `lsp_rename`

**Key architectural difference**: OpenCode uses LSP to make LLM better. AutoCode uses LSP to **avoid LLM entirely** (L1 deterministic). This is our competitive advantage.

### 2.3 Key Patterns from Aider

The Architect/Editor pattern (from Aider benchmarks) shows:
- Architect (strong model) plans → Editor (weak model) applies → 30-40% cost reduction
- Verification gate (syntax check, tests) catches Editor mistakes
- 2-3 feedback iterations sufficient for convergence

### 2.4 What Our Codebase Already Has (from Phase 4)

| Primitive | Location | Team Use |
|-----------|----------|----------|
| SubagentLoop | `subagent.py` | Isolated mini-loop per agent |
| SubagentType (EXPLORE/PLAN/EXECUTE) | `subagent.py` | Role-based capability filtering |
| LLMScheduler | `subagent.py` | Priority queue for multi-model scheduling |
| ToolRegistry + capability flags | `tools.py` | Per-agent tool access control |
| TaskStore (DAG) | `task_store.py` | Shared work tracking with dependencies |
| MemoryStore | `memory.py` | Cross-session learning |
| CheckpointStore | `checkpoint_store.py` | State snapshots for rollback |
| ApprovalManager | `approval.py` | Safety gates |
| Plan mode | `loop.py` | Read-only exploration phase |

---

## 3. Milestone & Sprint Plan

Three macro milestones, six sprints. **M1 + M2 = Standalone MVP Gate.** External integration (M3) only begins after the standalone product is feature-complete and proven. Sprint 5A0 (Quick Wins) delivers immediate user value before architecture work.

> **Rev 2 (2026-02-17):** Added Sprint 5A0, dropped Sprint 5E (A2A), replaced Outlines with llama.cpp native grammar, replaced multilspy with Jedi, fixed VRAM math (sequential loading only), extended soak testing, replaced recall/precision with F1 for M2 gate, added MCP security requirements to 5D.
>
> **Rev 3 (2026-02-17):** Applied Codex 471-473 amendments: B4 reliability gate strengthened (3 consecutive smoke passes, stored soak artifacts, fixed workload fixture), B5 adapter hardening expanded (golden transcript tests, strict version probe + fail-closed, JSON-only parsing), full edit command locked as Sprint 5B P0 non-deferrable, A2A reclassified from "dead" to WATCHLIST, Phase 6 entry criteria section added, document precedence contract added, waiver policy W1-W3 codified, user decision D1 (single-installable → Phase 6) applied.
>
> **Rev 4 (2026-02-18):** Codex Entry 478 P1-P8 inclusions: (P1) waiver governance as enforceable gate with auto-reopen rule, (P2) A2A normalized to WATCHLIST across all docs, (P3) artifact metadata standard (date/sha/platform/versions/command), (P4) deterministic acceptance per micro-sprint (no manual-only DoD), (P5) 5B.5 risk buffer + fail-fast criteria, (P6) 8GB hardware realism gate in 5C, (P7) slice-level independence contract, (P8) reproducible benchmark/eval policy with stored fixtures. Codex Entry 479 M9-M10 additions: (M9) lock-state table schema (OPEN/CONDITIONAL_CLOSED/CLOSED/CHECKLIST_READY), (M10) duplicate entry-ID handling rule (suffix policy).
>
> **Rev 5 (2026-02-18):** Codex Entry 484 B2 contradictions fixed + R1-R6 deep-research deltas: (R1) config/MCP-first integration contract — no regex/free-text CLI parsing, (R2) Codex capability framing — treat subagents as orchestrator-managed until official API, (R3) adapter capability probes with fail-closed behavior, (R4) MCP security gate — local-only default + path allowlist + audit log + explicit remote opt-in + tool-poisoning defense, (R5) eval additions — context-budget sweep, wrong-context negative control, routing-regret metric, (R6) comms regression guards for D2/D5 text. B2 doc contradictions resolved: Section 3.5 P2-compliant language, Section 10.2 aiohttp row struck, requirements_and_features.md P2-compliant.
>
> **Rev 6 (2026-02-18):** Entry 487 (Codex) audit — B2 final corrections: (1) Section 3.5 "negligible production deployment" replaced with P2-compliant framing; (2) Section 10.2 struck-through aiohttp row removed entirely; (3) requirements_and_features.md confirmed P2-compliant (no action needed). Entry 488 (Claude) response: Q1 editor bakeoff gate added to Sprint 5B pre-conditions; Q2 latency split gates (single-file/multi-file) and measured artifacts added to Sprint 5C; Q3 task bank freeze moved to pre-5A0 prerequisite; Q4 Ollama ctx corrected to adaptive policy (4096 min / 8192 target, pending user decision on hard floor); Q5 AgentBus kept in 5C with simulation harness, external-bridge contract tests deferred to 5D.

### 3.0 Overview

```
    M0: Quick Wins
    ┌──────────────────┐
    │ 5A0: Quick Wins  │   Immediate user-facing value
    │  diff preview     │   before architecture work
    │  doctor, tokens   │
    └────────┬─────────┘
             │
═══════════════════ STANDALONE MVP GATE ═══════════════════
║            ▼                                            ║
║  M1: Core Engine              M2: Quality + Teams       ║
║  ┌────────────────────┐       ┌──────────────────┐      ║
║  │ 5A: Identity+Eval  │       │ 5C: Evals+AgentBus│     ║
║  │ 5B: LLMLOOP v1     │ ───▶  │ 5C+: Policy Router│     ║
║  │     + Jedi tools    │       │     + Cost Control │     ║
║  └────────────────────┘       └──────────────────┘      ║
║  Working Architect/Editor      Proven context quality    ║
║  Local models, zero cost       Agent orchestration      ║
║  tree-sitter + Jedi intel.     Cost dashboard           ║
║                                                         ║
═══════════════════════════════════════════════════════════
                         │
                    MVP GATE CHECK
                    (feature-complete standalone)
                         │
                         ▼
              M3: External Integration
              ┌──────────────────┐
              │ 5D: MCP + Bridges│
              └──────────────────┘
              Only after standalone
              is proven & shipped
```

**MVP Gate Criteria (must pass before M3) — Numeric (from Codex Entry 448):**

| Gate | Metric | Target |
|------|--------|--------|
| **M1 Gate** | Internal task bank pass rate | >= 75% |
| | p95 single-file fast path | <= 60s (see Section 15.22 for split gates) |
| | p95 multi-file iterative path | <= 300s (see Section 15.22) |
| | Hard-fail regressions in syntax/LSP/test pipeline | 0 |
| **M2 Gate** | Context retrieval F1 (harmonic mean of recall and precision) | >= 0.65 |
| | Minimum absolute task success rate with curated context | >= 50% |
| | Token reduction vs raw dump (at equal-or-better success) | >= 30% |
| **M3 Gate** | Adapter health probes (installed/version/auth/dry-run) | All pass |
| | Setup/uninstall idempotent + rollback-safe | Verified |
| | Integration tests for supported tool versions | All pass |

---

### 3.05 Sprint 5A0 — Quick Wins (User-Facing Value First)

> Added in Rev 2 (2026-02-17). Rationale: Sprint 5A has no immediate user-visible output. 5A0 delivers quick wins that make AutoCode more useful TODAY before architecture work begins.

**Goal:** Immediate user-facing improvements. No architecture changes — focused on polishing what exists.

**Scope decision: `safe-scope`** — Full edit command deferred to Sprint 5A (10-16h estimated, not a quick win).

#### P0 (Must Ship)

| # | Task | Description | Est. Hours |
|---|------|-------------|------------|
| 1 | Write_file diff preview | Show diff after write_file (before/after comparison) | 2h |
| 2 | Git auto-commit + shell hardening | Auto-commit before edits, GIT_EDITOR blocking, timeout policy | 3h |
| 3 | Token counting | Ollama native token counts + session accumulation display | 2.5h |
| 4 | `autocode doctor` MVP | 8 readiness checks with remediation messages | 3.5h |
| 5 | Completion notifications | Enrich on_done with summary stats | 1h |

#### P1 (Can Defer)

| # | Task | Description | Est. Hours |
|---|------|-------------|------------|
| 6 | Large-repo safeguards | Warn/bail on repos > 10K files or > 1 GB | 1.5h |
| 7 | Model auto-download | Auto-pull Ollama L4 model if missing | 1.5h |
| 8 | Error recovery/retry | Retry transient failures in agent loop | 1h |
| 9 | Graceful Ollama disconnection | Detect disconnect, inform user, retry on reconnect | 1h |
| 10 | Benchmark runner expansion | Add matrix mode support to E2E runner | 0.5h |

#### Exit Criteria

- [ ] `autocode doctor` runs 8 checks and reports actionable fixes
- [ ] Diff preview displayed after every write_file call
- [ ] Token count visible in status bar and on_done summary
- [ ] Git auto-commit before edits (configurable)
- [ ] Shell hardening: GIT_EDITOR blocked, interactive prompts blocked, 30s default timeout
- [ ] All existing tests pass (982+), no regressions
- [ ] 5+ new tests for doctor, diff preview, token counting

---

### 3.1 Sprint 5A — Identity + Foundations + Eval Skeleton

**Goal:** First-class agent identity, multi-model provider registry, eval harness skeleton.

#### P0 (Must Ship)

| # | Task | Description |
|---|------|-------------|
| 1 | `AgentCard` dataclass | Identity, role, model spec, skills, tools, prompt |
| 2 | `AgentRole` enum | COORDINATOR, ARCHITECT, ENGINEER, REVIEWER, SCOUT, CUSTOM |
| 3 | `ModelSpec` dataclass | Provider + model + layer + temperature + max_tokens |
| 4 | `ProviderRegistry` | Multi-model provider management, lazy loading, max 2 loaded |
| 5 | Provider adapters | llama-cpp-python (L3), Ollama (L4), OpenRouter (cloud fallback) |
| 6 | Eval harness skeleton | Scenario format, deterministic grader, cost/latency capture |
| 7 | Context packer interfaces | L1, L2, L1+L2, LLM-curated baseline strategies |
| 8 | Agent identity in messages | Add `agent_id` to session messages and tool calls |

#### P1 (Can Defer)

| # | Task | Description |
|---|------|-------------|
| 9 | Dashboard/report formatting | Human-readable eval output |
| 10 | Extend SubagentLoop for AgentCard | Accept AgentCard, route to ProviderRegistry |
| 11 | Multi-language tree-sitter grammars | Add JS/TS, Go, Rust, Java grammars to L1 parser (grammars exist, need wiring) |
| 11 | `/agents` command | List registered agent cards |

#### New Files

| File | Purpose |
|------|---------|
| `src/autocode/agent/identity.py` | AgentCard, AgentRole, ModelSpec |
| `src/autocode/agent/provider_registry.py` | Multi-model provider management |
| `src/autocode/eval/harness.py` | Eval scenario format, grader, reporter |
| `src/autocode/eval/context_packer.py` | Context strategy interfaces |

#### Key Schemas

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
        return cls(provider="none", model="none", layer=1)

    @classmethod
    def l3_default(cls) -> ModelSpec:
        return cls(provider="llama-cpp", model="qwen2.5-coder:1.5b", layer=3)

    @classmethod
    def l4_default(cls) -> ModelSpec:
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
    priority: int = 1
    max_iterations: int = 5
    context_budget: int = 4096
    can_spawn_subagents: bool = False
    can_approve: bool = False


class ProviderRegistry:
    """Manages LLM providers. Constraint: max 2 models loaded (L3 + L4)."""

    def __init__(self, config: AutoCodeConfig):
        self._l4_provider: LLMProvider | None = None
        self._l3_provider: L3Provider | None = None
        self._config = config

    def get_provider(self, spec: ModelSpec) -> LLMProvider | L3Provider: ...
    def cleanup(self) -> None: ...
```

#### Eval Harness Skeleton

```python
@dataclass
class EvalScenario:
    """Single evaluation scenario."""
    id: str
    task_type: str           # "bug_fix", "feature_add", "code_review", "refactor"
    input_description: str
    gold_files: list[str]    # Expected relevant files
    gold_symbols: list[str]  # Expected relevant symbols

@dataclass
class ContextStrategy:
    """How to curate context for an LLM."""
    name: str                # "l1_only", "l2_only", "l1_l2", "llm_curated"
    curate: Callable[[str], CuratedContext]

class EvalHarness:
    """Runs context quality benchmarks."""
    def run(self, scenarios: list[EvalScenario],
            strategies: list[ContextStrategy]) -> EvalReport: ...
```

#### Exit Criteria

- [ ] AgentCard, AgentRole, ModelSpec implemented and tested
- [ ] ProviderRegistry manages L3 + L4 providers with lazy loading
- [ ] Provider adapters for llama-cpp, Ollama, OpenRouter
- [ ] Eval harness runs scenarios against context strategies
- [ ] Context packer interfaces for L1, L2, L1+L2, LLM-curated
- [ ] Messages tagged with agent_id
- [ ] ~25 new tests pass

---

### 3.2 Sprint 5B — Standalone LLMLOOP v1

**Goal:** The Architect/Editor pattern working end-to-end on local models. Highest standalone value — works without any external tools.

#### P0 (Must Ship)

| # | Task | Description |
|---|------|-------------|
| 1 | Architect agent (L4) | Plans edits, produces structured EditPlan. **Scoped narrowly:** single-function reasoning, not multi-file planning. L1/L2 identify exact files/functions first, Architect reasons about focused edits. Graceful degradation: when reasoning fails, present to user instead of burning 3 retries. |
| 2 | Editor agent (L3) | Applies edits using llama-cpp-python native grammar constraints (Outlines replaced — segfaults, 2-5x perf penalty) |
| 3 | Verification gate | tree-sitter syntax check + Jedi semantic validation + optional test run |
| 4 | LLMLOOP pipeline | Architect → Editor → Verify → feedback loop (max 3 iterations) |
| 5 | Budget policy | Local-only path costs $0; cloud path has hard token caps |
| 6 | Baseline regression suite | Measure LLMLOOP on internal task bank |
| 7 | Jedi semantic tools | `find_definition`, `find_references`, `list_symbols`, `get_type_info` via Jedi library (NOT multilspy — pure Python, <100ms, no LSP server) |
| 7b | Full edit command | LLM output parser with fuzzy matching (SequenceMatcher), whitespace normalization, diff preview + accept/reject flow. **NON-DEFERRABLE P0** (Rev 3): cannot slip past Sprint 5B without explicit user override per Codex Entry 471 constraint. |

#### P1 (Can Defer)

| # | Task | Description |
|---|------|-------------|
| 8 | SOP templates | Pre-defined pipelines for bugfix, review, refactor |
| 9 | Feedback channel | Editor sends compile errors back to Architect |
| 10 | Escalation to user | After max iterations, present partial result + diagnostics |

#### LLMLOOP Architecture

```
     ┌──────────┐
     │ Architect │ (L4: plans edits)
     │  Qwen3-8B │
     └─────┬─────┘
           │ structured EditPlan (JSON)
           ▼
     ┌──────────┐
     │  Editor   │ (L3: applies edits)
     │ Qwen2.5  │ (constrained generation via llama.cpp native grammar)
     └─────┬─────┘
           │ modified files
           ▼
     ┌──────────────┐
     │ Verify (L1)  │ tree-sitter parse + Jedi semantic check
     └─────┬────────┘
           │ errors?
     ┌─────┴─────┐
     │  Yes  │ No │
     ▼       ▼
  Feedback  DONE
  to Arch.  (commit-ready)
  (max 3×)
```

#### Key Schemas

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
    type: Literal["replace", "insert", "delete"]
    location: str          # Symbol path or line range
    old_content: str
    new_content: str
    context: str

class LLMLOOP:
    """Architect/Editor feedback loop."""
    def __init__(self, architect: AgentCard, editor: AgentCard,
                 provider_registry: ProviderRegistry,
                 tool_registry: ToolRegistry,
                 max_iterations: int = 3): ...

    async def run(self, task: str, context: CuratedContext) -> LLMLOOPResult: ...
```

#### Exit Criteria

- [ ] Architect produces valid EditPlan from task description
- [ ] Editor applies EditPlan using L3 constrained generation
- [ ] tree-sitter validates syntax after each edit
- [ ] LSP diagnostics fed back to Architect on failure
- [ ] Loop converges within 3 iterations on test cases
- [ ] Budget policy enforced (local = $0, cloud = capped)
- [ ] `find_definition`, `find_references`, `list_symbols`, `get_type_info` working via Jedi
- [ ] Regression suite baseline established
- [ ] ~30 new tests pass

---

### 3.3 Sprint 5C — Context Quality + AgentBus + Policy Router (MVP Completion)

**Goal:** Prove context quality, wire agent orchestration, add cost intelligence. **This sprint completes the standalone MVP.**

#### P0 (Must Ship)

| # | Task | Description |
|---|------|-------------|
| 1 | Retrieval relevance/completeness | File-set precision/recall, symbol coverage |
| 2 | End-to-end fix success | Internal task bank + SWE-bench-style slice |
| 3 | Cost/latency metrics | Per strategy (L1, L2, L1+L2, LLM-curated) |
| 4 | Failure taxonomy | Missing context, noisy context, serialization loss, policy violations |
| 5 | AgentBus | Typed messaging (REQUEST, RESULT, ISSUE) tied to Task IDs |
| 6 | MessageStore (SQLite) | Persistent message log |
| 7 | SOPRunner | Deterministic pipeline executor |
| 8 | Deterministic policy router | L1/L2 → L3 local → L4 local (escalation chain) |
| 9 | Cost dashboard | Token breakdown: local vs cloud, per-agent, per-task |
| 10 | Delegation hard caps | 2 agents default, 3 messages/task-edge, no recursion |

#### P1 (Can Defer)

| # | Task | Description |
|---|------|-------------|
| 8 | Ablation studies | Which L1/L2 component contributes most |
| 9 | Threshold tuning | Optimal similarity cutoffs for vector search |
| 10 | Team lifecycle commands | `/team`, Go TUI team panel |

#### Context Quality Eval Framework

```python
class ContextQualityBenchmark:
    """Proves L1+L2 matches L4-curated at zero cost."""
    scenarios: list[EvalScenario]
    strategies: list[ContextStrategy]

    def run(self) -> BenchmarkReport:
        for scenario, strategy in product(scenarios, strategies):
            context = strategy.curate(scenario.input)
            relevance = jaccard(context.files, scenario.gold.files)
            completeness = recall(context.files, scenario.gold.files)
            efficiency = len(context.tokens) / len(scenario.gold.tokens)
            # Also measure: symbol coverage, false positive rate
```

**Hypothesis**: L1+L2 matches L4-curated quality at zero cost. This is testable and provable.

| Scenario Type | Input | Gold Standard |
|---|---|---|
| Bug Fix | Error + stack trace | Files/functions needed to fix |
| Feature Add | Feature description | Related modules, interfaces, patterns |
| Code Review | Diff / PR | Affected callers, tests, constraints |
| Refactor | Refactor goal | Full dependency graph |

| Strategy | Tokens | Expected Relevance | Cost |
|---|---|---|---|
| Raw file dump | High | Low | $0 |
| L1 (tree-sitter symbols) | Low | High | $0 |
| L2 (BM25 + vector) | Medium | High | $0 |
| **L1 + L2 combined** | **Low** | **Highest** | **$0** |
| L4 curated (ask LLM) | High | Variable | $$ |

#### AgentBus Design

```python
class MessageType(StrEnum):
    REQUEST = "request"     # "Do this task"
    RESULT = "result"       # "Here's the output"
    ISSUE = "issue"         # "Something went wrong"

@dataclass
class AgentMessage:
    id: str
    from_agent: str
    to_agent: str | None     # None = broadcast
    message_type: MessageType
    payload: dict[str, Any]
    task_id: str | None
    timestamp: datetime

class AgentBus:
    """Runtime equivalent of AGENTS_CONVERSATION.MD."""

    def send(self, message: AgentMessage) -> str: ...
    def subscribe(self, agent_id: str, callback: Callable) -> None: ...
    def get_pending(self, agent_id: str) -> list[AgentMessage]: ...
    def get_thread(self, task_id: str) -> list[AgentMessage]: ...
```

#### SOPRunner Design

```python
@dataclass
class SOPStep:
    agent: str             # Agent ID
    action: str            # Prompt template
    input_from: str | None # Previous step's output
    output_type: str       # Expected output format
    gate: str | None       # Condition to proceed

class SOPRunner:
    """Deterministic pipeline executor."""
    async def run(self, team: AgentTeam) -> SOPResult:
        for step in team.sop:
            result = await self._execute_step(step)
            if step.gate and not self._check_gate(step.gate, result):
                return SOPResult(status="gate_failed", step=step)
        return SOPResult(status="completed")
```

#### Exit Criteria

- [ ] Eval suite runs on internal task bank (10+ scenarios)
- [ ] L1+L2 vs L4-curated comparison with precision/recall metrics
- [ ] Cost/latency breakdown per strategy
- [ ] Failure taxonomy documented with examples
- [ ] AgentBus sends/receives typed messages
- [ ] MessageStore persists to SQLite
- [ ] SOPRunner executes multi-step workflows
- [ ] Policy router escalates L1 → L2 → L3 → L4 correctly
- [ ] Cost dashboard shows per-agent, per-task token breakdown
- [ ] Delegation caps enforced (2 agents, 3 messages default)
- [ ] **MVP GATE: AutoCode solves real coding tasks standalone** (no external tools needed)
- [ ] **Reliability smoke test** (30-minute, per sprint): memory growth < 200 MB, VRAM ± 500 MB, p95 ≤ 60s single-file / ≤ 300s multi-file (see Section 15.22), zero crashes, Ollama recovery within 60s, SQLite WAL < 50 MB, stable open FDs
- [ ] **3 consecutive smoke passes required** before advancing to next sprint (Rev 3, per Codex Entry 471 B4 amendment)
- [ ] **Extended soak test** (4-hour, per milestone at M2 boundary): memory < 100 MB/hour, VRAM ± 200 MB, no latency degradation > 20% hour 1→4, zero unrecoverable hangs, Ollama recovery within 30s, SQLite WAL < 100 MB, stable open FDs
- [ ] **1 stored soak artifact per milestone** with output saved to `docs/qa/test-results/` (Rev 3)
- [ ] **Fixed workload fixture** used for all smoke/soak runs to ensure comparable results (Rev 3)
- [ ] Soak metrics tracked: Python RSS (psutil), GPU VRAM (nvidia-smi/pynvml), SQLite file sizes, open FD count, p50/p95/p99 latency
- [ ] ~40 new tests pass

---

### 3.4 Sprint 5D — External Tool Interaction v1

**Goal:** AutoCode bridges to Claude Code, Codex, and OpenCode through MCP and configuration surfaces.

#### P0 (Must Ship)

| # | Task | Description |
|---|------|-------------|
| 1 | Read-only MCP server | `search_code`, `find_definition`, `find_references`, `list_symbols`, `read_file`, `get_diagnostics` |
| 2 | ExternalToolTracker | Runtime discovery — detect Claude Code, Codex, OpenCode on PATH |
| 3 | Safe config merge generator | Generate tool-specific configs with `# managed-by: autocode` markers |
| 4 | `autocode setup` command | One-shot: detect installed tools → generate configs → register MCP |
| 5 | `autocode uninstall` command | Clean removal of all managed config sections |
| 6 | Minimal CLIBroker | Opt-in, bounded, structured output parsing (Codex `--json`) |

#### P1 (Can Defer)

| # | Task | Description |
|---|------|-------------|
| 7 | OpenCode custom commands | `/hc-search`, `/hc-analyze` |
| 8 | Richer bridge features | Write MCP tools, agent delegation |
| 9 | OpenCode LSP server reuse | Read `opencode.json` → `"lsp"` to discover running servers |

#### MCP Server Tools

```python
# Read-only tools exposed to external agents
MCP_TOOLS = {
    "search_code": "BM25 + vector search across codebase (L2)",
    "find_definition": "Go-to-definition via LSP/tree-sitter (L1)",
    "find_references": "Find all references via LSP/tree-sitter (L1)",
    "list_symbols": "List symbols in a file via tree-sitter (L1)",
    "read_file": "Read file contents with optional line range",
    "get_diagnostics": "Get LSP diagnostics for a file (L1)",
}
```

These tools expose AutoCode's L1/L2 intelligence to external tools. Claude Code and OpenCode get `find_definition`, `find_references`, `list_symbols` for free — tools that OpenCode's base product doesn't even expose to its own agent.

#### Config Generation

```python
def setup_claude_code(project_dir: Path) -> None:
    """Register HC as MCP server + add integration rules."""
    # 1. Merge MCP server into .claude/settings.json
    # 2. Append integration rules to CLAUDE.md (with markers)
    # 3. Place custom subagent in .claude/agents/autocode.md

def setup_opencode(project_dir: Path) -> None:
    """Register HC as MCP server + add agents/commands."""
    # 1. Merge MCP server into opencode.json
    # 2. Add instructions reference
    # 3. Place custom agent in .opencode/agents/autocode.md
    # 4. Place custom commands in .opencode/commands/

def setup_codex(project_dir: Path) -> None:
    """Register HC as MCP server + add instructions."""
    # 1. Merge MCP server into codex config
    # 2. Add project instructions to codex.md
```

#### Safe Config Merge Policy

**NEVER overwrite user config.** Always:
1. Read existing config file
2. Parse and merge HC section only
3. Add `# managed-by: autocode` markers to all injected content
4. Backup original to `.autocode/backups/<tool>-<timestamp>.json`
5. `autocode uninstall` removes ONLY sections with HC markers
6. If config file doesn't exist, create it (no merge needed)

#### ExternalToolTracker

```python
class ExternalToolTracker:
    """Runtime discovery of external AI coding tools."""

    def discover(self) -> list[ExternalTool]:
        """Check PATH for known tools."""
        tools = []
        for name, binary in KNOWN_TOOLS.items():
            if shutil.which(binary):
                version = self._get_version(binary)
                tools.append(ExternalTool(name=name, binary=binary, version=version))
        return tools

KNOWN_TOOLS = {
    "claude_code": "claude",
    "codex": "codex",
    "opencode": "opencode",
}
```

#### MCP Security Requirements (Rev 2 — CRITICAL)

> Added based on Entry 465-Claude Finding 4: 6+ CVEs, real exploits (WhatsApp exfiltration, GitHub prompt injection, Anthropic MCP Inspector RCE, mcp-remote CVSS 9.6). 82% of analyzed MCP implementations have path traversal risks.

| Requirement | Implementation |
|-------------|---------------|
| Input validation | Validate every tool parameter — no raw path passthrough |
| Path allowlist | Only permit paths under project root |
| No auto-run | MCP tools require explicit user opt-in, not auto-discovered |
| Content filtering | Block secrets patterns (API keys, passwords) in search results |
| Audit logging | Log every MCP call: tool name, params hash, result summary |
| SDK version pin | Pin MCP SDK to v1.x in pyproject.toml — v2 transport-layer breaking changes expected |
| Defensive JSON | Schema version detection, graceful degradation on unknown fields |
| Atomic writes | Write-temp-rename pattern for config merge (no partial writes) |

#### Version Compatibility Matrix (Rev 2)

| External Tool | Minimum Tested Version | Config Surface | Contract Test |
|---------------|----------------------|----------------|---------------|
| Claude Code | TBD (test before ship) | `.claude/settings.json` | Real binary invocation |
| Codex CLI | TBD (watch for JSON breakage post-v0.44) | `mcp_servers` config | Real binary invocation |
| OpenCode | TBD (stable releases) | `opencode.json` | Real binary invocation |
| Gemini CLI | TBD (evaluate free tier) | TBD | Real binary invocation |

#### Exit Criteria

- [ ] MCP server exposes 6 read-only tools
- [ ] Claude Code can use HC tools via MCP (verified with contract test)
- [ ] OpenCode can use HC tools via MCP (verified with contract test)
- [ ] `autocode setup` detects and configures all installed tools
- [ ] `autocode uninstall` cleanly removes all HC config
- [ ] Config merge never overwrites user content (deep merge, atomic writes)
- [ ] Backups created before every config modification
- [ ] CLIBroker can invoke Codex `--json` and parse output (**JSON/schema parsing ONLY — no regex free-text parsing**, Rev 3 B5 amendment)
- [ ] ExternalToolTracker discovers tools on PATH
- [ ] MCP input validation: path allowlist enforced, no raw passthrough
- [ ] MCP audit logging: every call logged
- [ ] MCP SDK pinned to v1.x
- [ ] Version compatibility matrix documented with tested minimum versions
- [ ] Contract tests pass against real tool binaries (not mocked)
- [ ] **Golden transcript tests** per adapter: known-good JSON IO fixtures for each external tool (Rev 3 B5 amendment)
- [ ] **Strict version probe + fail-closed**: unsupported tool versions trigger graceful error, not silent degradation (Rev 3 B5 amendment)
- [ ] Manual fallback installation docs for every supported tool
- [ ] Deep merge config: conflict detection raises error, never silently drops (Rev 3)
- [ ] ~35 new tests pass (increased from 30 due to golden transcript + version probe tests)

---

### 3.5 Sprint 5E — DROPPED (Rev 2)

> **A2A has been dropped from Phase 5 scope. Reclassified as WATCHLIST (Rev 3).** A2A is not a Phase 5 dependency; reclassified as WATCHLIST for Phase 6+ re-evaluation. MCP has 16,000+ servers and universal tool support across target tools (Claude Code, Codex, OpenCode); A2A remains an evolving protocol (v0.3.0, pre-1.0) that is not required for same-machine orchestration. A2A requires HTTP server, DNS, OAuth — antithetical to edge-native local CLI. A2A remains active upstream (Codex Entry 471 correction). **Status: WATCHLIST** — re-evaluate if adoption changes in Phase 6+.
>
> See `AGENTS_CONVERSATION.MD` Entry 465-Claude (Finding C6) and Entry 464-OpenCode for evidence.
>
> Original content preserved in Section 16.3 (Future Roadmap).

---

## 4. Model Assignment Strategy

| Role | Model | VRAM | Cost | When Used |
|------|-------|------|------|-----------|
| **Scout** | None (L1/L2 only) | 0 | $0 | File discovery, symbol lookup, search |
| **Engineer/Editor** | Qwen2.5-Coder-1.5B (L3) | ~1 GB | $0 | Constrained edits, structured output |
| **Architect** | Qwen3-8B (L4) | ~5 GB | $0 | Planning, reasoning, review |
| **External** | Claude/GPT via cloud | 0 | $$ | Complex multi-file tasks (opt-in) |

**VRAM budget — CORRECTED (Rev 2):** Dual-model loading on 8GB VRAM is **not feasible**. Actual math: Qwen3-8B weights (~5-6 GB) + Qwen2.5-Coder-1.5B weights (~1-1.5 GB) + KV cache for both at 4K context (~0.9 GB) + CUDA overhead (~0.5-1 GB) = **7.9-9.4 GB**, exceeding 8 GB. At 8K context: ~9.3 GB. Windows reserves 0.5-1.5 GB for desktop compositor.

**Strategy: Sequential model loading ONLY.** Load Architect (L4), unload, then load Editor (L3), unload. Each swap adds 5-15s latency. For 3-iteration LLMLOOP: ~36-102s of pure swap overhead. Ollama `num_ctx` must be set explicitly (Ollama defaults to 4096 and silently truncates — see Section 15.24 for adaptive policy: 4096 min / 8192 target).

**Future:** Track Qwen3-Coder-Next (80B total, 3B active MoE — 70.6% SWE-bench). If a smaller MoE variant ships (e.g., 14B-A3B), it could dramatically improve quality within 8GB VRAM.

---

## 5. Integration Opportunities

### 5.1 AutoCode as MCP Server (they use us)

External tools get free access to our L1/L2 intelligence:
- `find_definition` — better than OpenCode's base (which doesn't expose this to its agent)
- `find_references` — cross-file reference tracking
- `list_symbols` — AST-aware symbol enumeration
- `search_code` — BM25 + vector hybrid search

### 5.2 AutoCode as Orchestrator (we use them)

For tasks beyond local model capability:
- Delegate complex reasoning to Claude Code via config surface
- Delegate code generation to Codex via CLIBroker (`--json`)
- Delegate parallel research to OpenCode agents

### 5.3 OpenCode LSP Bridge

- Read `opencode.json` → `"lsp"` section to discover running language servers
- Avoid duplicate server launches (resource savings on consumer hardware)
- MCP tools compatible with `oh-my-opencode` interface (`lsp_goto_definition`, etc.)

---

## 6. Configuration

```yaml
# .autocode.yaml additions
agents:
  provider_registry:
    max_loaded_models: 2
    auto_unload: true
    unload_timeout: 300

  llmloop:
    max_iterations: 3
    architect_model: { provider: ollama, model: "qwen3:8b", layer: 4 }
    editor_model: { provider: llama-cpp, model: "qwen2.5-coder:1.5b", layer: 3 }

  bus:
    max_messages_per_task: 3
    max_delegated_agents: 2

  policy_router:
    order: [l1, l2, l3_local, l4_local, external]
    external_enabled: false    # Opt-in
    external_budget: 10000     # Max tokens per task

  external:
    auto_discover: true        # ExternalToolTracker
    strict_mode: false         # --strict: 1 agent, 2 messages

  mcp_server:
    enabled: false             # `autocode setup` enables this
    tools: [search_code, find_definition, find_references, list_symbols, read_file, get_diagnostics]

  # a2a: DROPPED in Rev 2 / WATCHLIST in Rev 3 — not a Phase 5 dependency
```

---

## 7. Test Strategy

### 7.1 Test Counts

| Sprint | New Tests | Cumulative (from 978) |
|--------|-----------|----------------------|
| 5A0 | ~10 | ~1013 |
| 5A | ~25 | ~1038 |
| 5B | ~30 | ~1068 |
| 5C | ~40 | ~1108 |
| 5D | ~30 | ~1138 |

### 7.2 Test Categories

- **Unit:** AgentCard, ModelSpec, ProviderRegistry, AgentBus, MessageStore, SOPRunner, LLMLOOP, EvalHarness, ContextPacker, ExternalToolTracker, ConfigGenerator
- **Integration:** Multi-agent LLMLOOP execution, MCP server tool calls, config merge/uninstall
- **Eval/Benchmark:** Context quality suite (precision/recall/cost/latency), LLMLOOP regression
- **Contract:** MCP protocol compliance, AgentBus message format validation
- **E2E:** LLMLOOP bug fix scenario, `autocode setup` with mock tools

---

## 8. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| VRAM contention — dual model impossible on 8GB | OOM, 5x slowdown | **Confirmed** | Sequential loading only (Rev 2). Each model swap adds 5-15s. Set `num_ctx` explicitly. |
| L3 model quality insufficient for Editor | Bad edits, loop doesn't converge | Medium | Max 3 iterations then escalate to user; baseline regression catches regressions |
| Qwen3-8B Architect quality (~35-45% pass rate) | Multi-file edits fail 40-60% of the time | **High** | Scope Architect narrowly (single-function). Track Qwen3-Coder-Next MoE (70.6% SWE-bench, 3B active/80B total). |
| Config merge breaks user setup | User loses config | High if careless | NEVER overwrite; deep merge; atomic writes; markers; backup; uninstall path |
| External tool APIs change | Bridge breaks | **High** (Codex v0.44 broke JSON, Claude Code MCP hangs) | Version compat matrix; contract tests against real binaries; defensive JSON parsing |
| MCP security exposure | Data exfiltration, RCE | **Critical** (6+ CVEs, 82% path traversal risk) | Path allowlist, input validation, audit logging, no auto-run, pin SDK v1.x |
| Scope explosion | Never ships | High | Ruthless P0-only per sprint; 5A0 quick wins first for user value |
| Gemini CLI free tier undermines "zero cost" positioning | Users choose free cloud over local | Medium | Monitor Gemini CLI capabilities; lean into LLM-as-last-resort differentiator; consider as cloud fallback |
| Context evals too late | Optimize on weak context | Medium | Start eval harness in 5A, not 5C (Codex recommendation) |
| SOP rigidity | Poor results for novel tasks | Medium | SOPs are templates with LLM-filled slots; coordinator can override |
| AgentBus message storms | Queue flooding | Low | Hard cap: 3 messages/task-edge, max 2 delegated agents |

---

## 9. Open Questions

1. **Jedi vs LSP**: Jedi chosen as primary Python semantic backend (Rev 2). LSP server reuse from OpenCode/VS Code is a future optimization, not required for standalone MVP.
2. **MCP tool naming**: Use our own names (`find_definition`) since MCP tools are namespaced per server anyway. Compatibility with `oh-my-opencode` via documentation, not naming.
3. **Team persistence**: Session-scoped for v1; project-scoped in `.autocode/teams/` as P1.
4. **Agent memory isolation**: Shared project memory with agent-tagged entries.
5. **Qwen3-Coder-Next tracking** (Rev 2): 80B total params, 3B active (MoE). 70.6% SWE-bench Verified. On 8GB VRAM with RAM offloading: ~1.2 t/s. If a smaller variant (14B-A3B) ships, it could replace Qwen3-8B as Architect.
6. **Gemini CLI as cloud fallback** (Rev 2): Free (1000 req/day), 78% SWE-bench, 1M context, web search. Consider as opt-in cloud fallback alongside OpenRouter. Does not undermine edge-native positioning if opt-in.

---

## 10. Dependencies

### 10.1 Sprint Dependencies

```
5A0 (Quick Wins) ──blocks──▶ 5A (Identity + Eval)
                                      │
                                blocks ▼
                               5B (LLMLOOP)
                                      │
                                blocks ▼
                               5C (Evals + AgentBus)
                                      │
                              MVP GATE CHECK
                                      │
                                blocks ▼
                               5D (External Interaction)
```

### 10.2 External Dependencies

| Dependency | Sprint | Required | Notes |
|-----------|--------|----------|-------|
| Ollama | 5A+ | Yes | L4 provider (already integrated) |
| llama-cpp-python | 5A+ | Optional | L3 provider (graceful degradation) |
| llama-cpp-python native grammar | 5B | Required | Constrained generation for EditPlan (Outlines replaced — segfaults, perf penalty) |
| Jedi | 5B | Required | Python semantic intelligence — cross-file goto, refs, types (replaces multilspy) |
| mcp-sdk | 5D | Required | MCP server implementation |

---

## 11. References

- [A2A Protocol Specification v0.3](https://a2a-protocol.org/latest/specification/)
- [Claude Code Subagents](https://docs.claude.com/en/docs/claude-code/sub-agents)
- [Claude Code Agent Teams](https://docs.claude.com/en/docs/claude-code/team)
- [Claude Code Settings](https://code.claude.com/docs/en/settings)
- [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Codex MCP](https://developers.openai.com/codex/mcp)
- [Codex Non-Interactive Output](https://developers.openai.com/codex/noninteractive)
- [OpenCode Config](https://opencode.ai/docs/config/)
- [OpenCode Agents](https://opencode.ai/docs/agents/)
- [OpenCode LSP](https://opencode.ai/docs/lsp/)
- [Aider Architect/Editor Benchmarks](https://aider.chat/2024/09/26/architect.html)
- [SWE-bench](https://github.com/swe-bench/SWE-bench)
- [MetaGPT](https://github.com/FoundationAgents/MetaGPT)
- AutoCode research: `docs/research/phase5-agent-teams-research.md`
- AutoCode research: `docs/research/claude-code-subagents.md`
- AutoCode research: `docs/research/opencode-and-competitors.md`
- AutoCode research: `docs/research/aider-architect-editor.md`
- AutoCode research: `docs/research/multi-agent-landscape-2026.md`

---

## 12. Document Precedence Contract (Rev 3)

When documents conflict, the following authority order applies:

| Priority | Document | Scope | Updates |
|----------|----------|-------|---------|
| 1 (highest) | `docs/plan/phase5-agent-teams.md` | Phase 5 sprint scope, gates, exit criteria, tech decisions | Canonical for Phase 5 implementation |
| 2 | `PLAN.md` (repo root) | Project-wide roadmap, milestone summaries, cross-phase gates. Absorbed `docs/plan.md` on 2026-04-18 (§6 carries the MVP Acceptance checklist). | References Phase 5 plan, does not override it |
| 3 | `docs/requirements_and_features.md` | Feature catalog, sprint listing, status tracking | Derived from Phase 5 plan |
| 4 | `CLAUDE.md` | Agent instructions, tech stack summary, testing rules | Summarizes; defers to Phase 5 plan on conflict |

**Rule:** If a sprint scope, gate metric, or tech decision conflicts between documents, `docs/plan/phase5-agent-teams.md` is authoritative. Other documents must be updated to match, not the other way around.

---

## 13. Phase 6 Entry Criteria (Rev 3, per User Decision D1)

> **User decision D1 (2026-02-17):** "Single-installable file" is delegated to Phase 6. Phase 5 delivers standalone MVP; Phase 6 delivers packaging and distribution.
> **User decision D2 (2026-02-17):** Risky/advanced features deferred to Phase 6 if they endanger Phase 5 MVP delivery.

### 13.1 Phase 5 Exit Gate (= Phase 6 Entry Prerequisites)

Phase 6 cannot begin until ALL of these pass:

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Phase 5 MVP gate (M2) passes | >= 75% task bank pass, p95 <= 60s single-file / 300s multi-file (Section 15.22), 0 hard-fail regressions |
| 2 | External bridges (M3) working | MCP server + at least 1 adapter passing contract tests |
| 3 | Full edit command shipped | Sprint 5B item 7b complete (non-deferrable P0) |
| 4 | Context quality proven | F1 >= 0.65 on eval suite |
| 5 | Reliability soak passed | 4-hour extended soak with stored artifact |
| 6 | Documentation locked | All Phase 5 docs reconciled, regression tests green |

### 13.2 Phase 6 Scope (Preliminary)

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 1 | Single-installable file | PyInstaller/Nuitka packaging, zero-setup first-run | P0 |
| 2 | First-run model bootstrap | Auto-download Ollama + models on first launch | P0 |
| 3 | Offline mode | Full operation without network (local models only) | P0 |
| 4 | Clean uninstall/rollback | `autocode uninstall` removes everything cleanly | P0 |
| 5 | Advanced edit features | Multi-file editing, cross-file refactoring, rename | P1 |
| 6 | Team persistence | Project-scoped agent teams in `.autocode/teams/` | P1 |
| 7 | Routing quality benchmark | Success/latency/cost benchmark validating multi-model delegation | P1 |

### 13.3 Minimum Reliable Edit Capability (Phase 5 Boundary)

Per Codex Entry 473 constraint: deferring risky items must not hollow out standalone MVP value. Phase 5 MUST ship:
- Full edit command (Sprint 5B P0 7b) — single-file fuzzy matching, diff preview, accept/reject
- 3-iteration LLMLOOP with Architect → Editor → Verify
- Graceful degradation when edit fails (present to user, don't loop forever)

Advanced/risky edit features that may move to Phase 6:
- Multi-file editing (requires cross-file dependency graph)
- Rename refactoring (requires project-wide symbol resolution)
- Auto-apply without user confirmation (safety concern)

---

## 14. Waiver Policy (Rev 3, per Codex Entry 473 W1-W3)

### W1: mypy Baseline Waiver (Conditional)

Acceptable for roadmap-lock progression if ALL conditions hold:
1. Baseline count frozen at **<= 52 errors**
2. No new mypy error categories introduced beyond the 7 documented in Entry 470
3. Ownership assigned: Sprint 5A0 for type annotation cleanup (cosmetic items)
4. Any regression above 52 **auto-reopens blocker B1**

### W2: Go N/A Waiver (Conditional)

Acceptable for planning-only lock if:
1. No Go code changed during the lock period
2. Go TUI tests (275 passing) remain at Phase 4 gate parity
3. Waiver **automatically revokes** when Phase 5 implementation touches Go/TUI/runtime boundaries

### W3: No Blanket Waivers

- Any future regression above the documented baseline auto-reopens the relevant blocker
- Each waiver is scoped to the specific lock phase (planning-only); implementation phases require full QA

---

## 15. Execution Policies (Rev 4, per Codex Entry 478 P1-P8)

### P1: Waiver Governance (Enforceable Gate)

Waivers (W1-W3 in Section 14) are **enforceable gates**, not narrative suggestions:
- mypy baseline cap: **<= 52 errors**. Any count > 52 auto-reopens blocker B1.
- Named owner: **Claude** (test execution). Target: <= 30 by end of 5A0, <= 10 by end of 5A.
- No new mypy categories beyond the 7 documented.
- Go N/A auto-revokes when implementation touches Go.

### P2: A2A Terminology Policy

All authority documents must use: **"Not a Phase 5 dependency; WATCHLIST for Phase 6+ re-evaluation."**
The terms "dead", "effectively dead", or "zero adoption" are prohibited in active docs.

### P3: Artifact Metadata Standard

Every QA/eval artifact in `docs/qa/test-results/` MUST include:

```markdown
## Metadata
| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Commit SHA | `<sha>` |
| Python | X.Y.Z |
| Package Manager | uv X.Y.Z |
| Platform | <OS version> |
| Command | `<exact command>` |
```

### P4: Deterministic Acceptance Per Micro-Sprint

Every micro-sprint slice MUST have at least one **deterministic** acceptance assertion. Manual-only Definition of Done is prohibited. Even "manual verification" slices must have a scripted smoke check.

### P5: 5B.5 Full-Edit Risk Controls

- **Risk buffer:** If 5B.5 exceeds 2x estimated hours (> 20h), halt and escalate to user.
- **Fail-fast criteria:** If fuzzy matching success rate < 50% on test fixtures after first 3 TDD tests, reassess approach.
- **User escalation trigger:** Any schedule slip in 5B.5 must be communicated to user before consuming buffer from other slices.

### P6: 8GB Hardware Realism Gate (Sprint 5C)

Sprint 5C exit criteria include: "Soak test on 8GB VRAM machine (or simulated VRAM cap) with fixed workload fixture, 3 consecutive 30-min smoke runs, zero OOM/hangs." Soak artifacts stored in `docs/qa/test-results/`.

### P7: Slice-Level Independence Contract

Each micro-sprint slice MUST declare:
1. **Dependencies:** Which prior slices must be complete (or "None").
2. **Standalone evidence:** Pass/fail test results that prove the slice works independently.
3. **Artifact path:** Where stored in `docs/qa/test-results/`.

### P8: Reproducible Benchmark/Eval Policy

- Same fixtures used across runs for comparability.
- Same commands documented in artifact metadata.
- Stored artifacts enable re-scoring without re-running.
- Eval results include: pass rate, latency, token cost, and failure breakdown.

### 15.9 M9: Lock-State Table Schema

Blocker status uses exactly one of these values:

| Status | Meaning |
|--------|---------|
| `OPEN` | Blocker is unresolved; blocks progression |
| `CONDITIONAL_CLOSED` | Spec accepted, awaits implementation evidence or final reviewer acknowledgment |
| `CLOSED` | Blocker fully resolved with evidence |
| `CHECKLIST_READY` | Pass/fail criteria defined, awaits implementation-phase execution |

Lock-state tables must be published in comms for every plan revision and use this schema consistently.

### 15.10 M10: Duplicate Entry-ID Handling

When multiple agents claim the same entry number, use `-Agent` suffix in archive references (e.g., `449-Claude`, `449-Codex`). Future entries start from the next unclaimed sequential ID. All archive comments must use the suffixed form to prevent audit ambiguity. This rule applies to all comms archival operations.

### 15.11 D1: B1/B2 Transition Conditions

| Blocker | Current Status | Transition Trigger | Target Status |
|---------|---------------|-------------------|---------------|
| B1 QA Lock Pack | CONDITIONAL_CLOSED | User confirms waiver acceptance OR Sprint 5A0-1 implementation starts (implicit acceptance) | CLOSED |
| B2 Cross-doc Consistency | CONDITIONAL_CLOSED | Codex posts explicit "no contradictions remain" acknowledgment | CLOSED |

Both triggers are testable: B1 via comms entry or first implementation commit; B2 via explicit Codex comms entry.

### 15.12 D2: Archival Count Audit Correction

Entry 477 declared archival of 12 Claude entries. The archive file summary listed 11. Correction: the archive file at `docs/communication/old/2026-02-17-claude-phase5-planning-superseded.md` covers all 12 entries (428, 431-435, 438-439, 443-444, 449-Claude, 450-Claude) as confirmed by the archive comment on line 92 of AGENTS_CONVERSATION.MD. No entries are missing.

### 15.13 D3: 5B.5 Fail-Fast Hard Gate

The following thresholds are **hard gates** (not advisory):

- **Budget overrun threshold:** If 5B.5 exceeds 2x estimated hours (>20h), HALT and escalate to user.
- **Fuzzy-match threshold:** If after first 3 TDD test implementations, fuzzy matching success rate is <50% on test fixtures, HALT and reassess approach.
- **User escalation:** Both triggers require an explicit comms entry with options (scope reduction, sprint extension, or user override to continue). No silent absorption of time from adjacent slices.

### 15.14 D4: G5 Eval Gate — First Evidence Bundle

G5 remains **OPEN**. First evidence bundle required to transition to CLOSED:

- **Fixture:** >= 30-task internal task bank (frozen before 5A0 per Section 15.23 prerequisite).
- **Report:** End-to-end task success rate, context F1, token cost breakdown.
- **Storage:** `docs/qa/test-results/sprint-5c-eval-baseline.md` with metadata per P3 template.
- **Pass condition:** Task bank pass rate >= 75%, context F1 >= 0.65, all metrics reproducible per P8.

### 15.15 R1: Integration Contract — Config/MCP-First Adapters

External tool integration uses config-surface and MCP-surface adapters as primary integration paths. CLI fallback is permitted ONLY when the tool provides machine-readable output (e.g., `codex exec --json`, `--output-schema`). **No regex or free-text parsing of CLI output — JSON/schema only.** This applies to all Sprint 5D adapter implementations.

### 15.16 R2: Codex Capability Framing

Codex currently exposes MCP server support and background agents/workflows, but does NOT provide a Claude-style first-class markdown subagent surface with per-agent model override. The plan treats Codex "subagents" as orchestrator-managed roles until an official per-agent API surface exists. Sprint 5D adapters must not assume capabilities beyond what is documented and version-probed.

### 15.17 R3: Adapter Capability Probes

Each external tool adapter must implement versioned capability probes:

| Probe | Description |
|-------|-------------|
| `supports_mcp_server` | Tool can serve as MCP client connecting to AutoCode's MCP server |
| `supports_json_schema_output` | Tool supports structured JSON output via CLI flags |
| `supports_background_tasks` | Tool supports background/async task execution |

**Fail-closed behavior:** If a probe returns false or the tool version is unsupported, the adapter must raise a graceful error and disable that integration path. Silent degradation is not permitted.

### 15.18 R4: MCP Security Gate

MCP server defaults to **local-only transport** (stdio for local process integration). Network scenarios use Streamable HTTP (SSE is deprecated per MCP spec 2025-03-26). Security requirements:

- **Project-root path allowlist:** MCP tools can only access files within the project root.
- **Audit log:** Every MCP tool invocation is logged with timestamp, tool name, arguments, and caller identity.
- **Explicit remote opt-in:** Remote/network MCP transport requires explicit user configuration. Not enabled by default.
- **Input sanitization:** MCP tool results must sanitize patterns that resemble system prompt injections before returning to the client (defense against tool poisoning via adversarial search results).

Rationale: Active 2025 MCP CVEs (CVE-2025-6514, CVE-2025-68144, CVE-2025-68145) demonstrate real attack surface.

### 15.19 R5: Eval Additions (Sprint 5C)

Sprint 5C evaluation suite must include:

- **Context-budget sweep:** Test context quality at small (2k tokens), medium (8k tokens), and large (16k tokens) budgets to validate L1/L2 retrieval scales appropriately.
- **Wrong-context negative control:** Include tasks where deliberately incorrect context is provided; verify the system does NOT pass these (proving context quality matters, not just model capability).
- **Routing-regret metric:** Compare actual routing decisions against an oracle (which layer would have been optimal) to measure routing accuracy. Target: routing regret < 15%.

### 15.20 R6: Comms Regression Guards

Add deterministic regression tests to `test_roadmap_lock_regression.py`:

- Verify D2 archival-correction text exists in plan (Section 15.12).
- Verify D5 "applies to all comms archival operations" phrase exists in plan (Section 15.10).

### 15.21 Q1: Editor Model Bakeoff Gate (Pre-5B)

Before Sprint 5B implementation begins, run a model bakeoff evaluating at least 3 editor candidates on the same edit fixtures:

| Candidate | Description |
|-----------|-------------|
| L3 baseline (Qwen2.5-Coder-1.5B Q4_K_M) | Current plan default |
| Stronger local fallback (e.g., Qwen2.5-Coder-3B or 7B quantized) | Higher capability, more VRAM |
| L4-only path (Qwen3-8B for both Architect and Editor) | Zero swap overhead, best quality, single model |

**Bakeoff protocol:** Run each candidate on the pre-committed task bank edit fixtures. Measure: format compliance rate, patch-apply success rate, semantic correctness rate.

**Promotion rule:** If L3 fails threshold (format-valid >= 80% AND patch-apply >= 70% AND semantic-pass >= 60%), auto-promote to stronger editor tier for Sprint 5B. This is a hard gate, not advisory.

### 15.22 Q2: Measured Latency Budget with Split Gates

The p95 latency gate must be measured empirically, not assumed. Before locking p95 gate values:

1. Run measured latency profiling on target hardware (8GB VRAM consumer GPU).
2. Record both `first_token_latency` and `end_to_end_latency` in eval artifacts.
3. Split latency gates by task class:

| Task Class | Description | p95 Target |
|-----------|-------------|------------|
| Single-file fast path | L1/L2 + single Architect pass, no model swap | <= 60s |
| Multi-file iterative path | Full LLMLOOP with up to 3 iterations | <= 300s |

Gate values are provisional until measured artifacts are stored. Adjust based on empirical evidence, not estimates.

### 15.23 Q3: Task Bank as Upfront Lock Prerequisite

The 75% task bank pass rate gate (M1) requires a pre-committed task bank. **This is a lock prerequisite, not a Sprint 5B deliverable.**

**Required before Sprint 5A0 starts:**
- Commit >= 30 concrete task scenarios to the repo with gold-standard answers.
- Each scenario specifies: input (files, symbols, user request), expected output (specific edits, references, classifications), and scoring rubric.
- Fixture IDs and gold labels are frozen before implementation begins.
- Task bank composition must be locked so it cannot be unconsciously tuned during implementation.

**Task bank composition guideline:** ~60-70% of tasks should be solvable by L1/L2 deterministic tools (reflecting the architecture's "LLM as last resort" principle), ~20-30% require L3/L4 intervention, ~10% are negative controls (should NOT trigger LLM).

### 15.24 Q4: Adaptive Context Policy

Ollama default context window is 4096 tokens (corrected from 2048). Policy:

| Parameter | Value |
|-----------|-------|
| `minimum_supported_ctx` | 4096 (hard floor — below this, refuse to start) |
| `target_ctx` | 8192 (set by default when hardware budget permits) |
| Downgrade behavior | If VRAM insufficient for 8192, fall back to 4096 with telemetry warning |
| User override | Configurable via `autocode.toml` provider settings |

ProviderRegistry enforces this policy for all Ollama calls. Silent truncation is never acceptable — if context exceeds the window, raise an explicit error.

### 15.25 Q5: AgentBus 5C Simulation Harness

AgentBus core (including persistence) stays in Sprint 5C. However, external-adapter validation requires Sprint 5D bridges. To close the testing gap:

- Sprint 5C includes a **simulation harness** with synthetic internal agents and deterministic message fixtures.
- Simulation harness tests: message routing, typed message serialization, persistence round-trip, concurrent access.
- External-bridge **contract tests** are reserved for Sprint 5D where real external agents validate the messaging.

This ensures AgentBus is testable in 5C without depending on unbuilt 5D infrastructure.

### 15.26 R7: Codex JSONL Event-Stream Contract Tests (Sprint 5D)

`codex exec --json` emits newline-delimited JSON events (not one final JSON object). Parser requirements:

- Line-by-line streaming decode of JSONL events.
- Unknown-event tolerance: ignore unrecognized event types without error.
- Deterministic extraction of final assistant payload from the event stream.

**Golden fixtures required:** Cover at least `thread.started`, `turn.started`, `turn.completed`, `item.started`, `item.completed`, and `error` event types. Fixtures stored in `tests/fixtures/codex-events/`.

### 15.27 R8: `--output-schema` Semantics Guard

`--output-schema` constrains the **final response shape only**. Intermediate stream events do NOT match the output schema.

**Implementation requirement:** Maintain separate validation paths:
1. **Stream-events parser** — parses each JSONL line by event type, tolerates unknown fields.
2. **Final-schema validator** — applies `--output-schema` JSON Schema to the extracted final payload only.

Do not assume intermediate events conform to the output schema.

### 15.28 R9: MCP Transport/Security Compatibility Details

Transport priority:

| Transport | Use Case | Status |
|-----------|----------|--------|
| stdio | Local process integration (default) | Primary |
| Streamable HTTP | Network scenarios | Secondary |
| HTTP+SSE (legacy) | Backwards-compat fallback | Deprecated — document only |

For Streamable HTTP mode:
- Explicit Origin validation on all requests.
- Localhost bind by default (`127.0.0.1`, not `0.0.0.0`).
- `Mcp-Session-Id` lifecycle handling: persist header across requests; restart flow on 404.
- Backwards-compat fallback: if connecting to a legacy HTTP+SSE server, detect via initial handshake and fall back gracefully. Document behavior but do not optimize for it.

### 15.29 R10: Delegation Budget Controls (Hard Gate)

Multi-agent delegation (Claude Code subagents, Codex parallel tasks) can cause materially higher token burn. Hard caps required:

- **Max teammates per task:** configurable, default 3.
- **Per-turn delegation cap:** maximum tokens delegated per agent turn.
- **Per-role token ceilings:** each AgentRole has a max token budget per task.
- **Stop conditions:** if delegation budget is exhausted, halt delegation and surface to user.

These are hard gates, not advisory limits. Violation triggers a user-visible warning and task pause.

### 15.30 R11: External Capability Matrix (Executable Contract)

Maintain a tool/version/capability probe matrix per external adapter:

| Tool | Min Version | Probes | Fail Behavior |
|------|-------------|--------|---------------|
| Claude Code | >= 1.0 | `claude --version`, MCP server list | Fail closed — disable adapter |
| Codex CLI | >= 0.1 | `codex --version`, `codex exec --json` health check | Fail closed — disable adapter |
| OpenCode | >= 0.1 | `opencode --version`, config probe | Fail closed — disable adapter |

Matrix stored as data (not hardcoded logic). Adapter refuses to activate if probes fail. Matrix updated per release.

### 15.31 R12: Context Handoff Benchmark Pack

Before enabling aggressive multi-agent delegation defaults, add explicit evals for context transfer quality:

- **Too-little context:** Task fails because delegated agent lacks necessary context.
- **Too-much context:** Task succeeds but with excessive token usage (> 2x optimal).
- **Wrong-context:** Task fails because delegated agent receives irrelevant context.
- **Routing-regret tracking:** Compare delegation routing decisions against oracle to measure routing accuracy.

These evals must pass before any multi-agent delegation defaults are enabled in production.

### 15.32 R13: Benchmark Pyramid Gate (Phase-Scoped)

Evaluations must include suites from the benchmark pyramid (see `docs/research/coding-agent-testing.md`), **scoped by phase to prevent scope explosion:**

- **Phase 5 minimum:** SWE-bench Verified subset + SWT-Bench subset + internal full-system task seed (small).
- **Phase 5C extension:** Add Terminal-Bench subset + anti-gaming controls.
- **Phase 6 expansion:** Add goal-oriented lane, multilingual lane, adversarial lane, larger full-system track.

No single-benchmark pass is sufficient for gate closure at any phase.

### 15.33 R14: Verifiability Contract

Every eval task must have a deterministic oracle (command + expected exit/state). No LLM-as-judge for pass/fail decisions. Acceptable oracles: test suite pass/fail, compilation success, linter clean, exact string match, AST diff, exit code.

### 15.34 R15: Anti-Gaming Controls

Eval integrity controls:
- Hidden test cases (not visible to agent during development)
- Paraphrased prompts (same task, different wording — verify consistency)
- Private holdout split (tasks never seen during development)
- Benchmark freeze hashes (detect if task bank was modified after lock)

### 15.35 R16: Cost/Latency/Quality Triplet

All eval reports must include three metrics together: `resolve@1` (quality), `cost per resolved task` (cost), and `p95 wall-clock` (latency). No quality-only reporting is acceptable.

### 15.36 R17: Full-System Build Track

Include at least 10 internal greenfield tasks (API + DB + tests + CI) with fully executable acceptance harness. These are not patches — they test whether the agent can build a complete working system from scratch.

### 15.37 R18: TDD Enforcement Mode

In benchmark mode, bug-fix tasks require the agent to write a failing test that reproduces the bug FIRST, then apply the fix. If the agent cannot reproduce the bug via test, it must document the reason. This validates the TDD workflow.

### 15.38 P9: Sub-Sprint Start Gate (Mandatory)

Before starting any sub-sprint, the following must be satisfied:

1. **Clear goals:** Scope, non-goals, and acceptance criteria defined.
2. **Clear tests:** TDD tests written that define what success looks like.
3. **Two-state summary presented to user:**
   - **Current state** (what exists now)
   - **Expected state** (what will exist after the sub-sprint completes)
4. **Explicit user approval** to proceed.

If any of the above is missing, the sub-sprint remains `BLOCKED`. No implementation begins without this ceremony.

### 15.39 D1: Reproducibility Bundle (Mandatory per Benchmark Report)

Every reported benchmark result must store: task set hash/version, harness commit SHA, container image digest (if applicable), random seed(s), exact command, wall-clock time, and cost telemetry. Without this bundle, scores are not comparable across runs.

### 15.40 D2: Flakiness & Uncertainty Policy

Single-run numbers are insufficient for agentic systems. Require multi-seed reruns for headline metrics, confidence intervals in reports, and an explicit flaky-task quarantine threshold.

### 15.41 D4: Temporal Holdout

Extend R15 anti-gaming controls with time-based holdout: include post-training-cutoff tasks to reduce contamination/memorization effects (LiveCodeBench principle).

### 15.42 E3: Environment Determinism Gate

Default eval runs: network-off, pinned dependency versions, benchmark-specific exceptions documented. Deviations require explicit justification in the reproducibility bundle.

### 15.43 F4: Versioned Benchmark Manifest

Each reported score must include a benchmark-manifest version (task list, hashes, excludes) and harness version to prevent silent drift between evaluation runs.

### 15.44 H5: Protocol Decision Gate

**MCP is the Phase 5 interoperability backbone.** A2A remains on WATCHLIST for Phase 6+ (remote/organization-to-organization agent exchange only). A2A is complementary to MCP, not a replacement.

### 15.45 Governance Backlog (Deferred to 5C / Phase 6)

The following proposals are tracked but not blocking implementation. They will be locked during Sprint 5C (Evals + Cost + Policy) or Phase 6 as appropriate:

D3 (stronger-test augmentation), D5 (scaffold-neutrality check), E1 (fixed-scaffold control lane), E2 (goal-oriented eval lane), E4 (test-integrity policy), E5 (difficulty-sliced reporting), F1 (attempt-inflation guard), F2 (difficulty-sliced gates), F3 (periodic human audit), H1 (tool-surface contract), H2 (dual-mode product contract), H3 (multi-model delegation safety), H4 (cross-agent message envelope), H6 (hard-eval additions).

---

## 16. Future Roadmap (Post-Phase 5 — Previously Planned Features)

> These features were in the original Phase 5 draft (2026-02-14). They remain valid goals but are deferred until the standalone MVP is proven and external bridges are working. Preserved here for continuity.

### 16.1 Built-in Team Templates

Pre-defined agent team configurations for common workflows:

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

### 16.2 Full Team Lifecycle

- `/team` command — Create/list/manage agent teams from CLI
- Go TUI team panel — Show team members, active agent, SOP progress
- Team persistence — Project-scoped in `.autocode/teams/`
- Context isolation — Per-agent context windows (private vs shared)
- Handoff protocol — Structured context transfer between agents

### 16.3 A2A Full Implementation

- A2A Agent Card endpoint — Serve `/.well-known/agent-card.json` over HTTP
- A2A task lifecycle — Full state machine (submitted → working → completed/failed)
- A2A JSON-RPC server — HTTP wrapper with SSE streaming
- A2A client — Connect to and delegate to external A2A agents
- Push notifications — Webhook-based event delivery for long-running tasks

### 16.4 Extended Configuration

```yaml
# Future .autocode.yaml extensions
teams:
  default_team: "solo"
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

agents:
  a2a:
    enabled: false
    port: 8642
    auth: null
```

### 16.5 Relationship to AGENT_COMMUNICATION_RULES.md

The current markdown protocol (`AGENTS_CONVERSATION.MD`) is essentially a human-readable precursor to the AgentBus:

| AGENT_COMMUNICATION_RULES.md | Phase 5 Runtime |
|-------------------------------|----------------|
| Identity header (`Agent: X \| Role: Y`) | `AgentCard` dataclass |
| Message types (Concern, Review, Handoff) | `MessageType` enum |
| Entry numbers | `AgentMessage.id` |
| `Directed to:` | `AgentMessage.to_agent` |
| `Replying to:` | `AgentMessage.context_id` |
| `AGENTS_CONVERSATION.MD` file | `AgentBus` + `MessageStore` (SQLite) |
| Resolution rules | Task state transitions |
| Archival to `docs/communication/old/` | Message retention + cleanup |
