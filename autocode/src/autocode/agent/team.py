"""Agent team persistence — save/load teams to .autocode/teams/.

Project-scoped agent team definitions with SOPs and model assignments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autocode.agent.identity import AgentCard, AgentRole, ModelSpec
from autocode.agent.sop_runner import SOPPipeline, SOPStep


@dataclass
class AgentTeam:
    """A team of agents with a defined workflow."""

    name: str
    description: str = ""
    agents: list[AgentCard] = field(default_factory=list)
    coordinator_id: str = ""
    pipeline: SOPPipeline | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON storage."""
        return {
            "name": self.name,
            "description": self.description,
            "coordinator_id": self.coordinator_id,
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "role": a.role.value,
                    "model": {
                        "provider": a.model.provider,
                        "model": a.model.model,
                        "layer": a.model.layer,
                    },
                    "skills": a.skills,
                }
                for a in self.agents
            ],
            "pipeline": {
                "name": self.pipeline.name,
                "steps": [
                    {
                        "agent": s.agent,
                        "action": s.action,
                        "output_type": s.output_type,
                        "gate": s.gate,
                    }
                    for s in self.pipeline.steps
                ],
            } if self.pipeline else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentTeam:
        """Deserialize from dict."""
        agents = [
            AgentCard(
                id=a["id"],
                name=a["name"],
                role=AgentRole(a["role"]),
                model=ModelSpec(
                    provider=a["model"]["provider"],
                    model=a["model"]["model"],
                    layer=a["model"]["layer"],
                ),
                skills=a.get("skills", []),
            )
            for a in data.get("agents", [])
        ]
        pipeline = None
        if data.get("pipeline"):
            p = data["pipeline"]
            pipeline = SOPPipeline(
                name=p["name"],
                steps=[
                    SOPStep(
                        agent=s["agent"],
                        action=s["action"],
                        output_type=s.get("output_type", "text"),
                        gate=s.get("gate"),
                    )
                    for s in p.get("steps", [])
                ],
            )
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            agents=agents,
            coordinator_id=data.get("coordinator_id", ""),
            pipeline=pipeline,
        )

    @classmethod
    def bugfix_team(cls) -> AgentTeam:
        """Pre-defined bugfix team."""
        return cls(
            name="bugfix",
            description="Scout → Architect → Engineer bug fix workflow",
            agents=[
                AgentCard.scout(),
                AgentCard.architect(),
                AgentCard.engineer(),
            ],
            coordinator_id="architect",
            pipeline=SOPPipeline.bugfix(),
        )


class TeamStore:
    """Persistent storage for agent teams.

    Saves/loads teams to/from .autocode/teams/ directory.
    """

    def __init__(self, teams_dir: Path | None = None) -> None:
        self._dir = teams_dir or Path(".autocode") / "teams"

    def save(self, team: AgentTeam) -> Path:
        """Save a team definition to disk."""
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{team.name}.json"
        path.write_text(
            json.dumps(team.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def load(self, name: str) -> AgentTeam | None:
        """Load a team by name."""
        path = self._dir / f"{name}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return AgentTeam.from_dict(data)

    def list_teams(self) -> list[str]:
        """List available team names."""
        if not self._dir.exists():
            return []
        return [
            p.stem for p in self._dir.glob("*.json")
        ]

    def delete(self, name: str) -> bool:
        """Delete a team definition."""
        path = self._dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False
