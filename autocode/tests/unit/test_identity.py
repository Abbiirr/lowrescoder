"""Tests for agent identity: AgentCard, AgentRole, ModelSpec, AgentRegistry."""

from __future__ import annotations

from autocode.agent.identity import (
    AgentCard,
    AgentRegistry,
    AgentRole,
    ModelSpec,
)


def test_agent_role_values() -> None:
    """AgentRole has expected values."""
    assert AgentRole.COORDINATOR == "coordinator"
    assert AgentRole.SCOUT == "scout"
    assert len(AgentRole) == 6


def test_model_spec_l1_only() -> None:
    """L1-only spec has no LLM."""
    spec = ModelSpec.l1_only()
    assert spec.provider == "none"
    assert spec.layer == 1


def test_model_spec_l3_default() -> None:
    """L3 default uses llama-cpp with small model."""
    spec = ModelSpec.l3_default()
    assert spec.provider == "llama-cpp"
    assert spec.layer == 3
    assert "1.5b" in spec.model


def test_model_spec_l4_default() -> None:
    """L4 default uses Ollama with 8B model."""
    spec = ModelSpec.l4_default()
    assert spec.provider == "ollama"
    assert spec.layer == 4


def test_model_spec_cloud() -> None:
    """Cloud spec uses OpenRouter by default."""
    spec = ModelSpec.cloud()
    assert spec.provider == "openrouter"
    assert spec.layer == 4


def test_agent_card_scout() -> None:
    """Scout agent has L1-only model and search skills."""
    card = AgentCard.scout()
    assert card.role == AgentRole.SCOUT
    assert card.model.layer == 1
    assert "search_code" in card.skills
    assert not card.can_spawn_subagents


def test_agent_card_architect() -> None:
    """Architect agent has L4 model and can spawn subagents."""
    card = AgentCard.architect()
    assert card.role == AgentRole.ARCHITECT
    assert card.model.layer == 4
    assert card.can_spawn_subagents


def test_agent_card_engineer() -> None:
    """Engineer agent has L3 model and edit skills."""
    card = AgentCard.engineer()
    assert card.role == AgentRole.ENGINEER
    assert card.model.layer == 3
    assert "edit_file" in card.skills


def test_agent_registry_default() -> None:
    """Default registry has 3 agents."""
    registry = AgentRegistry.default()
    agents = registry.list_agents()
    assert len(agents) == 3
    assert registry.get("scout") is not None
    assert registry.get("architect") is not None
    assert registry.get("engineer") is not None


def test_agent_registry_by_role() -> None:
    """Can query agents by role."""
    registry = AgentRegistry.default()
    scouts = registry.by_role(AgentRole.SCOUT)
    assert len(scouts) == 1
    assert scouts[0].id == "scout"


def test_agent_registry_custom() -> None:
    """Can register custom agents."""
    registry = AgentRegistry()
    card = AgentCard(
        id="my-agent",
        name="My Agent",
        role=AgentRole.CUSTOM,
        skills=["special_tool"],
    )
    registry.register(card)
    assert registry.get("my-agent") is not None
    assert registry.get("my-agent").name == "My Agent"
