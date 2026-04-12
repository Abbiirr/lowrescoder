"""Cross-module integration tests — verify components work together.

Tests that span multiple Phase 5/6 modules to catch interface issues.
"""

from __future__ import annotations

from pathlib import Path

from autocode.agent.bus import AgentBus, AgentMessage, MessageType
from autocode.agent.completion import SessionStats
from autocode.agent.cost_dashboard import CostDashboard
from autocode.agent.identity import AgentCard, AgentRegistry, AgentRole, ModelSpec
from autocode.agent.llmloop import LLMLOOP, EditPlan, Edit, EditType
from autocode.agent.multi_edit import FileEdit, MultiEditPlan, apply_multi_edit
from autocode.agent.policy_router import PolicyRouter, RoutingLayer
from autocode.agent.sop_runner import SOPPipeline, SOPRunner, SOPStatus
from autocode.agent.team import AgentTeam, TeamStore
from autocode.agent.token_tracker import TokenTracker
from autocode.eval.harness import EvalHarness, EvalScenario
from autocode.eval.context_packer import ALL_STRATEGIES
from autocode.external.mcp_server import MCPServer, MCPServerConfig
from autocode.external.tracker import ExternalToolTracker
from autocode.doctor import run_doctor


def test_team_with_bus_and_sop() -> None:
    """Team agents communicate via AgentBus and execute SOP pipeline."""
    team = AgentTeam.bugfix_team()
    bus = AgentBus()

    # Coordinator sends task to scout
    bus.send(AgentMessage(
        from_agent=team.coordinator_id,
        to_agent="scout",
        message_type=MessageType.REQUEST,
        payload={"task": "find the bug"},
        task_id="bug-123",
    ))

    # Scout responds
    bus.send(AgentMessage(
        from_agent="scout",
        to_agent=team.coordinator_id,
        message_type=MessageType.RESULT,
        payload={"files": ["src/app.py"]},
        task_id="bug-123",
    ))

    thread = bus.get_thread("bug-123")
    assert len(thread) == 2
    assert thread[0].message_type == MessageType.REQUEST
    assert thread[1].message_type == MessageType.RESULT


def test_policy_router_with_cost_dashboard() -> None:
    """Policy router decisions tracked in cost dashboard."""
    router = PolicyRouter()
    dash = CostDashboard()

    # Route a task
    decision = router.route("find_definition")
    assert decision.layer == RoutingLayer.L1

    # Track the cost
    dash.record("scout", "task-1", decision.layer.value, tokens_in=100)
    assert dash.total_cost == 0.0  # L1 is free
    assert dash.by_layer()["l1"] == 100


def test_session_stats_with_token_tracker() -> None:
    """SessionStats integrates TokenTracker for completion summary."""
    stats = SessionStats()
    stats.token_tracker.record(prompt_tokens=1000, completion_tokens=500, provider="ollama")
    stats.token_tracker.record(prompt_tokens=2000, completion_tokens=800, provider="openrouter")
    stats.record_file_change("src/app.py")
    stats.record_tool_use("edit_file")
    stats.record_tool_use("read_file")
    stats.record_tool_use("edit_file")

    summary = stats.summary()
    assert "4,300" in summary  # total tokens
    assert "Files changed: 1" in summary
    assert "Tool calls: 3" in summary
    assert "edit_file(2)" in summary


def test_eval_harness_with_all_strategies() -> None:
    """EvalHarness runs full scenario suite with all 4 strategies."""
    scenarios = [
        EvalScenario(
            id="s1", task_type="bug_fix",
            input_description="Fix the database query",
            gold_files=["src/database.py", "src/models.py"],
            gold_symbols=["Database.query"],
        ),
        EvalScenario(
            id="s2", task_type="feature_add",
            input_description="Add user authentication",
            gold_files=["src/auth.py"],
            gold_symbols=["Auth.login"],
        ),
    ]

    harness = EvalHarness()
    report = harness.run(scenarios, ALL_STRATEGIES)

    assert len(report.results) == 8  # 2 scenarios x 4 strategies
    assert len(report.strategy_summaries) == 4
    # LLM strategy should have best recall (returns gold)
    assert report.strategy_summaries["oracle_llm_baseline"]["avg_recall"] == 1.0


def test_mcp_server_with_tracker(tmp_path: Path) -> None:
    """MCP server works alongside tool tracker."""
    tracker = ExternalToolTracker()
    tracker.discover()

    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    # MCP call
    result = server.handle_tool_call("search_code", {"query": "def main"})
    assert result["status"] == "ok"
    assert len(server.audit_log) == 1


def test_llmloop_with_verification(tmp_path: Path) -> None:
    """LLMLOOP verifier catches syntax errors."""
    valid = tmp_path / "good.py"
    valid.write_text("def hello():\n    return 'world'\n")

    invalid = tmp_path / "bad.py"
    invalid.write_text("def broken(\n")

    loop = LLMLOOP(max_iterations=3)
    good_result = loop.verify([str(valid)])
    assert good_result.passed

    bad_result = loop.verify([str(invalid)])
    assert not bad_result.passed


def test_multi_edit_with_team(tmp_path: Path) -> None:
    """Multi-edit plan can be created from team workflow."""
    team = AgentTeam.bugfix_team()
    plan = MultiEditPlan(
        description=f"Fix by team {team.name}",
        edits=[
            FileEdit(path="src/app.py", old_content="", new_content="# fixed\n"),
            FileEdit(path="tests/test_app.py", old_content="", new_content="# test\n"),
        ],
    )

    result = apply_multi_edit(plan, tmp_path)
    assert result.success
    assert len(result.files_created) == 2


def test_doctor_with_platform_detect() -> None:
    """Doctor integrates with platform detection."""
    results = run_doctor()
    # Should have 9 checks (includes autocode command PATH check)
    assert len(results) == 9
    # Python check should pass
    py_check = next(r for r in results if r.name == "python_version")
    assert py_check.passed


def test_agent_registry_with_provider_registry() -> None:
    """AgentRegistry agents reference valid ModelSpecs."""
    registry = AgentRegistry.default()
    for agent in registry.list_agents():
        assert agent.model is not None
        assert agent.model.provider in ("none", "ollama", "llama-cpp", "openrouter")
        assert agent.model.layer in (1, 2, 3, 4)


def test_team_store_roundtrip(tmp_path: Path) -> None:
    """Full team save/load/list/delete cycle."""
    store = TeamStore(tmp_path / "teams")
    team = AgentTeam.bugfix_team()

    # Save
    store.save(team)
    assert "bugfix" in store.list_teams()

    # Load
    loaded = store.load("bugfix")
    assert loaded is not None
    assert loaded.name == team.name
    assert len(loaded.agents) == 3
    assert loaded.pipeline is not None

    # Delete
    store.delete("bugfix")
    assert "bugfix" not in store.list_teams()
