"""Agent identity primitives: AgentCard, AgentRole, ModelSpec.

These define first-class agent identity for multi-agent orchestration.
Based on A2A-inspired descriptors adapted for local-first edge computing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AgentRole(StrEnum):
    """Agent roles for the orchestration system."""

    COORDINATOR = "coordinator"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    SCOUT = "scout"
    CUSTOM = "custom"


@dataclass
class ModelSpec:
    """Which LLM to use for this agent.

    Specifies provider, model name, intelligence layer, and generation params.
    """

    provider: str = "ollama"
    model: str = "qwen3:8b"
    layer: int = 4
    temperature: float = 0.7
    max_tokens: int = 4096

    @classmethod
    def l1_only(cls) -> ModelSpec:
        """No LLM — deterministic L1 tools only."""
        return cls(provider="none", model="none", layer=1)

    @classmethod
    def l3_default(cls) -> ModelSpec:
        """L3 constrained generation with small model."""
        return cls(
            provider="llama-cpp",
            model="qwen2.5-coder:1.5b",
            layer=3,
            temperature=0.0,
            max_tokens=2048,
        )

    @classmethod
    def l4_default(cls) -> ModelSpec:
        """L4 full reasoning with 8B model."""
        return cls(
            provider="ollama",
            model="qwen3:8b",
            layer=4,
        )

    @classmethod
    def cloud(cls, provider: str = "openrouter", model: str = "default") -> ModelSpec:
        """Cloud-based provider (opt-in, costs money)."""
        return cls(
            provider=provider,
            model=model,
            layer=4,
            max_tokens=8192,
        )


@dataclass
class AgentCard:
    """A2A-inspired agent identity descriptor.

    Describes an agent's identity, capabilities, model assignment,
    and operational constraints.
    """

    id: str
    name: str
    role: AgentRole
    model: ModelSpec = field(default_factory=ModelSpec.l4_default)
    skills: list[str] = field(default_factory=list)
    tool_filter: dict[str, bool] = field(default_factory=dict)
    system_prompt_template: str = ""
    priority: int = 1
    max_iterations: int = 50
    context_budget: int = 4096
    can_spawn_subagents: bool = False
    can_approve: bool = False

    @classmethod
    def scout(cls, agent_id: str = "scout") -> AgentCard:
        """Pre-configured scout agent (L1/L2 only, no LLM)."""
        return cls(
            id=agent_id,
            name="Scout",
            role=AgentRole.SCOUT,
            model=ModelSpec.l1_only(),
            skills=["find_definition", "find_references", "search_code", "list_symbols"],
            max_iterations=10,
        )

    @classmethod
    def architect(cls, agent_id: str = "architect") -> AgentCard:
        """Pre-configured architect agent (L4 reasoning)."""
        return cls(
            id=agent_id,
            name="Architect",
            role=AgentRole.ARCHITECT,
            model=ModelSpec.l4_default(),
            skills=["analyze_code", "plan_edits", "review_code"],
            can_spawn_subagents=True,
        )

    @classmethod
    def engineer(cls, agent_id: str = "engineer") -> AgentCard:
        """Pre-configured engineer agent (L3 constrained edits)."""
        return cls(
            id=agent_id,
            name="Engineer",
            role=AgentRole.ENGINEER,
            model=ModelSpec.l3_default(),
            skills=["write_file", "edit_file", "run_command"],
            max_iterations=20,
        )


class AgentRegistry:
    """Registry of available agent cards.

    Manages agent identity lookup and creation.
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentCard] = {}

    def register(self, card: AgentCard) -> None:
        """Register an agent card."""
        self._agents[card.id] = card

    def get(self, agent_id: str) -> AgentCard | None:
        """Get an agent card by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentCard]:
        """List all registered agents."""
        return list(self._agents.values())

    def by_role(self, role: AgentRole) -> list[AgentCard]:
        """Find agents by role."""
        return [a for a in self._agents.values() if a.role == role]

    @classmethod
    def default(cls) -> AgentRegistry:
        """Create registry with default agent cards."""
        registry = cls()
        registry.register(AgentCard.scout())
        registry.register(AgentCard.architect())
        registry.register(AgentCard.engineer())
        return registry
