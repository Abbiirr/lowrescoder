"""Tests for agent team persistence."""

from __future__ import annotations

from pathlib import Path

from autocode.agent.team import AgentTeam, TeamStore


def test_bugfix_team() -> None:
    """Pre-defined bugfix team has 3 agents and pipeline."""
    team = AgentTeam.bugfix_team()
    assert team.name == "bugfix"
    assert len(team.agents) == 3
    assert team.coordinator_id == "architect"
    assert team.pipeline is not None
    assert len(team.pipeline.steps) == 3


def test_team_serialization() -> None:
    """Team can be serialized and deserialized."""
    team = AgentTeam.bugfix_team()
    data = team.to_dict()

    restored = AgentTeam.from_dict(data)
    assert restored.name == team.name
    assert len(restored.agents) == len(team.agents)
    assert restored.coordinator_id == team.coordinator_id
    assert restored.pipeline is not None
    assert len(restored.pipeline.steps) == len(team.pipeline.steps)


def test_team_store_save_load(tmp_path: Path) -> None:
    """TeamStore saves and loads teams."""
    store = TeamStore(tmp_path / "teams")
    team = AgentTeam.bugfix_team()

    path = store.save(team)
    assert path.exists()

    loaded = store.load("bugfix")
    assert loaded is not None
    assert loaded.name == "bugfix"
    assert len(loaded.agents) == 3


def test_team_store_list(tmp_path: Path) -> None:
    """TeamStore lists available teams."""
    store = TeamStore(tmp_path / "teams")
    store.save(AgentTeam.bugfix_team())
    store.save(AgentTeam(name="custom", description="Custom team"))

    teams = store.list_teams()
    assert "bugfix" in teams
    assert "custom" in teams
    assert len(teams) == 2


def test_team_store_delete(tmp_path: Path) -> None:
    """TeamStore deletes teams."""
    store = TeamStore(tmp_path / "teams")
    store.save(AgentTeam.bugfix_team())

    assert store.delete("bugfix")
    assert store.load("bugfix") is None
    assert "bugfix" not in store.list_teams()


def test_team_store_load_missing(tmp_path: Path) -> None:
    """Loading non-existent team returns None."""
    store = TeamStore(tmp_path / "teams")
    assert store.load("nonexistent") is None


def test_team_agent_roles() -> None:
    """Team agents have correct roles."""
    team = AgentTeam.bugfix_team()
    roles = [a.role.value for a in team.agents]
    assert "scout" in roles
    assert "architect" in roles
    assert "engineer" in roles
