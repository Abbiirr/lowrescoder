"""Edge case tests across all modules."""

from __future__ import annotations

from pathlib import Path

from autocode.agent.bus import AgentBus, AgentMessage, MessageType
from autocode.agent.cost_dashboard import CostDashboard
from autocode.agent.identity import AgentCard, AgentRole, ModelSpec
from autocode.agent.llmloop import LLMLOOP, EditPlan, Edit, EditType
from autocode.agent.multi_edit import FileEdit, MultiEditPlan
from autocode.agent.policy_router import PolicyRouter
from autocode.agent.sop_runner import SOPPipeline, SOPRunner, SOPStep
from autocode.agent.token_tracker import TokenTracker
from autocode.eval.harness import compute_metrics, EvalReport, EvalResult
from autocode.external.mcp_server import MCPServer


# --- TokenTracker edge cases ---

def test_token_tracker_zero_tokens() -> None:
    """TokenTracker handles zero-token calls."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=0, completion_tokens=0)
    assert tracker.total.total_tokens == 0
    assert tracker.call_count == 1


def test_token_tracker_large_values() -> None:
    """TokenTracker handles large token counts."""
    tracker = TokenTracker()
    tracker.record(prompt_tokens=1_000_000, completion_tokens=500_000)
    assert tracker.total.total_tokens == 1_500_000
    summary = tracker.summary()
    assert "1,500,000" in summary


# --- AgentBus edge cases ---

def test_bus_empty_pending() -> None:
    """No pending messages for unknown agent."""
    bus = AgentBus()
    assert bus.get_pending("nonexistent") == []


def test_bus_empty_thread() -> None:
    """Empty thread for unknown task."""
    bus = AgentBus()
    assert bus.get_thread("no-task") == []


def test_bus_no_task_id_no_cap() -> None:
    """Messages without task_id aren't subject to cap."""
    bus = AgentBus()
    bus.MAX_MESSAGES_PER_TASK = 1
    # These should all succeed (no task_id)
    for _ in range(10):
        bus.send(AgentMessage(from_agent="a", to_agent="b"))
    assert bus.message_count == 10


# --- PolicyRouter edge cases ---

def test_router_unknown_task_type() -> None:
    """Unknown task types default to complexity-based routing."""
    router = PolicyRouter()
    decision = router.route("totally_unknown_task", complexity="low")
    assert decision.layer is not None


def test_router_empty_order() -> None:
    """Router with empty order still works."""
    router = PolicyRouter(order=[])
    assert not router.can_escalate(PolicyRouter.__dataclass_fields__["order"].default_factory()[0])


# --- CostDashboard edge cases ---

def test_cost_dashboard_empty_summary() -> None:
    """Empty dashboard produces valid summary."""
    dash = CostDashboard()
    summary = dash.summary()
    assert "Total tokens: 0" in summary
    assert "$0.0000" in summary


def test_cost_dashboard_many_entries() -> None:
    """Dashboard handles many entries."""
    dash = CostDashboard()
    for i in range(100):
        dash.record(f"agent-{i % 5}", f"task-{i}", "l4", tokens_in=100)
    assert dash.total_tokens == 10_000
    assert len(dash.by_agent()) == 5
    assert len(dash.by_task()) == 100


# --- compute_metrics edge cases ---

def test_metrics_no_overlap() -> None:
    """No overlap gives zero F1."""
    p, r, f1 = compute_metrics(["a.py"], ["b.py"])
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0


def test_metrics_superset() -> None:
    """Returning superset: recall=1, precision<1."""
    p, r, f1 = compute_metrics(["a.py", "b.py", "c.py", "d.py"], ["a.py"])
    assert r == 1.0
    assert p == 0.25
    assert 0 < f1 < 1


# --- LLMLOOP edge cases ---

def test_llmloop_zero_iterations() -> None:
    """LLMLOOP with 0 max_iterations returns immediately."""
    loop = LLMLOOP(max_iterations=0)
    result = loop.run("fix bug")
    assert not result.success
    assert result.iterations == 0


def test_llmloop_verify_nonexistent_file() -> None:
    """Verifier handles nonexistent files gracefully."""
    loop = LLMLOOP()
    result = loop.verify(["/nonexistent/file.py"])
    assert result.passed  # File doesn't exist, no syntax error to report


# --- EditPlan edge cases ---

def test_edit_plan_empty() -> None:
    """Empty edit plan."""
    plan = EditPlan(file="test.py")
    assert len(plan.edits) == 0
    assert plan.confidence == 0.0


# --- MultiEdit edge cases ---

def test_multi_edit_empty_plan(tmp_path: Path) -> None:
    """Empty edit plan is a no-op."""
    from autocode.agent.multi_edit import apply_multi_edit
    plan = MultiEditPlan()
    result = apply_multi_edit(plan, tmp_path)
    assert result.success
    assert len(result.files_modified) == 0


def test_file_edit_diff_lines_identical() -> None:
    """Identical content has 0 diff lines."""
    edit = FileEdit(path="a.py", old_content="same\n", new_content="same\n")
    assert edit.diff_lines == 0


# --- EvalReport edge cases ---

def test_eval_report_empty() -> None:
    """Empty report has 0 pass rate."""
    report = EvalReport()
    assert report.pass_rate == 0.0


# --- MCP edge cases ---

def test_mcp_path_traversal_blocked(tmp_path: Path) -> None:
    """Path traversal attempts are blocked."""
    config = MCPServerConfig(project_root=tmp_path)
    server = MCPServer(config)

    # Try various traversal patterns
    for evil_path in [
        "../../../etc/passwd",
        "/etc/shadow",
        str(tmp_path / ".." / ".." / "etc" / "passwd"),
    ]:
        result = server.handle_tool_call("read_file", {"path": evil_path})
        assert "error" in result


# --- ModelSpec edge cases ---

def test_model_spec_equality() -> None:
    """ModelSpec instances with same values are equal."""
    a = ModelSpec(provider="ollama", model="qwen3:8b", layer=4)
    b = ModelSpec(provider="ollama", model="qwen3:8b", layer=4)
    assert a == b


# Need this import for the MCP test
from autocode.external.mcp_server import MCPServerConfig
