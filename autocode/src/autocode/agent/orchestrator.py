"""Orchestrator — the sole control plane for multi-agent task execution.

Wraps AgentLoop as an internal worker primitive and owns all task dispatch,
messaging, event emission, and policy enforcement. All frontends should
use Orchestrator (via create_orchestrator()) rather than constructing
AgentLoop directly.
"""

from __future__ import annotations

import logging
from typing import Any

from autocode.agent.bus import AgentBus, AgentMessage, MessageType
from autocode.agent.context import RuntimeState
from autocode.agent.cost_dashboard import CostDashboard
from autocode.agent.events import (
    EventSink,
    EventType,
    NullEventSink,
    OrchestratorEvent,
)
from autocode.agent.identity import AgentCard, AgentRegistry
from autocode.agent.policy_router import PolicyRouter, RoutingDecision, RoutingLayer
from autocode.agent.sop_runner import SOPPipeline, SOPResult, SOPRunner, SOPStep

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central orchestrator for multi-agent task execution.

    Ties together:
    - AgentLoop: the internal worker that handles LLM interactions
    - PolicyRouter: decides which layer/agent handles a task
    - AgentBus: in-memory message pub/sub (backward compat)
    - MessageStore: persistent mailbox (optional, Sprint 8B)
    - TaskStore: persistent task board (optional, Sprint 8C)
    - EventSink: canonical event emission (Sprint 8A)
    - SOPRunner: executes multi-step pipelines
    - CostDashboard: tracks all token costs
    - AgentRegistry: manages available agents
    - RuntimeState: canonical runtime state (Section 0.3)
    """

    def __init__(
        self,
        *,
        agent_loop: Any | None = None,
        task_store: Any | None = None,
        message_store: Any | None = None,
        bus: AgentBus | None = None,
        event_sink: EventSink | None = None,
        subagent_manager: Any | None = None,
        delegation_policy: Any | None = None,
        session_id: str = "",
        registry: AgentRegistry | None = None,
        router: PolicyRouter | None = None,
        cost_dashboard: CostDashboard | None = None,
        runtime_state: RuntimeState | None = None,
    ) -> None:
        self._agent_loop = agent_loop
        self._task_store = task_store
        self._message_store = message_store
        self._subagent_manager = subagent_manager
        self._delegation_policy = delegation_policy
        self._session_id = session_id
        self._event_sink = event_sink or NullEventSink()

        # Section 0.3: canonical runtime state
        self._runtime_state = runtime_state or RuntimeState(session_id=session_id)

        # Backward-compat: these were the original constructor params
        self.registry = registry or AgentRegistry.default()
        self.router = router or PolicyRouter()
        self.bus = bus or AgentBus()
        self.cost = cost_dashboard or CostDashboard()
        self._sop_runner = SOPRunner(gate_checker=self._check_gate)

    # ── Properties ──

    @property
    def agent_loop(self) -> Any | None:
        """Access the internal AgentLoop worker. Read-only."""
        return self._agent_loop

    @property
    def event_sink(self) -> EventSink:
        """The event sink for canonical event emission."""
        return self._event_sink

    @property
    def session_id(self) -> str:
        return self._session_id

    @session_id.setter
    def session_id(self, value: str) -> None:
        self._session_id = value
        self._runtime_state.session_id = value
        if self._agent_loop is not None:
            self._agent_loop.session_id = value

    @property
    def runtime_state(self) -> RuntimeState:
        """The canonical runtime state (Section 0.3)."""
        return self._runtime_state

    # ── AgentLoop delegation (drop-in frontend compatibility) ──

    async def run(self, user_input: str, **kwargs: Any) -> Any:
        """Delegate to the internal AgentLoop.run()."""
        if self._agent_loop is None:
            raise RuntimeError("No AgentLoop configured")
        return await self._agent_loop.run(user_input, **kwargs)

    def cancel(self) -> None:
        """Delegate to the internal AgentLoop.cancel()."""
        if self._agent_loop is not None:
            self._agent_loop.cancel()

    def set_mode(self, mode: Any) -> None:
        """Delegate to the internal AgentLoop.set_mode()."""
        if self._agent_loop is not None:
            self._agent_loop.set_mode(mode)
        self._runtime_state.agent_mode = str(mode)

    def get_mode(self) -> Any:
        """Delegate to the internal AgentLoop.get_mode()."""
        if self._agent_loop is None:
            from autocode.agent.loop import AgentMode

            return AgentMode.AUTO
        return self._agent_loop.get_mode()

    # ── Task Management ──

    def submit_task(
        self,
        title: str,
        description: str = "",
        priority: int = 0,
    ) -> str:
        """Create a task in TaskStore, emit TASK_CREATED event, return task_id."""
        if self._task_store is None:
            raise RuntimeError("No TaskStore configured")

        task_id = self._task_store.create_task(
            title=title,
            description=description,
        )

        self._event_sink.emit(
            OrchestratorEvent(
                event_type=EventType.TASK_CREATED,
                session_id=self._session_id,
                task_id=task_id,
                source_agent="orchestrator",
                payload={"title": title, "description": description, "priority": priority},
            )
        )

        return task_id

    # ── Routing ──

    def route_task(
        self,
        task_type: str,
        complexity: str = "low",
    ) -> RoutingDecision:
        """Route a task to the appropriate layer via PolicyRouter."""
        decision = self.router.route(task_type, complexity)
        logger.info(
            "Routed %s (complexity=%s) to %s: %s",
            task_type,
            complexity,
            decision.layer,
            decision.reason,
        )
        return decision

    def dispatch(
        self,
        task: str,
        task_type: str = "general",
        complexity: str = "low",
        task_id: str = "",
    ) -> dict[str, Any]:
        """Dispatch a task through the routing and execution pipeline.

        1. Route via PolicyRouter
        2. Select agent from registry
        3. Post to AgentBus
        4. Emit TASK_ROUTED event
        5. Return result
        """
        # Route
        decision = self.route_task(task_type, complexity)

        # Select agent based on layer
        agent = self._select_agent(decision.layer)
        if not agent:
            return {
                "success": False,
                "error": f"No agent available for layer {decision.layer}",
                "routing": decision,
            }

        # Post request to bus
        msg = AgentMessage(
            from_agent="orchestrator",
            to_agent=agent.id,
            message_type=MessageType.REQUEST,
            payload={"task": task, "task_type": task_type},
            task_id=task_id or f"dispatch-{id(task)}",
        )
        self.bus.send(msg)

        # Track cost
        self.cost.record(
            agent_id=agent.id,
            task_id=msg.task_id or "",
            layer=decision.layer.value,
            tokens_in=decision.estimated_tokens,
        )

        # Emit event
        self._event_sink.emit(
            OrchestratorEvent(
                event_type=EventType.TASK_ROUTED,
                session_id=self._session_id,
                task_id=msg.task_id or "",
                source_agent="orchestrator",
                payload={
                    "task_type": task_type,
                    "layer": decision.layer.value,
                    "agent": agent.id,
                    "estimated_tokens": decision.estimated_tokens,
                },
            )
        )

        return {
            "success": True,
            "agent": agent.id,
            "layer": decision.layer.value,
            "routing": decision,
            "message_id": msg.id,
            "task_id": msg.task_id,
        }

    def run_pipeline(
        self,
        pipeline: SOPPipeline,
        context: dict[str, Any] | None = None,
        task_id: str = "",
    ) -> SOPResult:
        """Execute an SOP pipeline with real agent dispatch."""

        def step_executor(step: SOPStep, ctx: dict[str, Any]) -> Any:
            complexity = "medium" if step.agent == "architect" else "low"
            result = self.dispatch(
                task=step.action.format(**ctx) if ctx else step.action,
                task_type=step.output_type,
                complexity=complexity,
                task_id=task_id,
            )
            self.bus.send(
                AgentMessage(
                    from_agent=step.agent,
                    to_agent="orchestrator",
                    message_type=MessageType.RESULT,
                    payload=result,
                    task_id=task_id,
                )
            )
            return result

        return self._sop_runner.run(
            pipeline,
            context=context,
            step_executor=step_executor,
        )

    # ── Internal ──

    def _select_agent(self, layer: RoutingLayer) -> AgentCard | None:
        """Select the best agent for a given layer."""
        layer_to_role = {
            RoutingLayer.L1: "scout",
            RoutingLayer.L2: "scout",
            RoutingLayer.L3_LOCAL: "engineer",
            RoutingLayer.L4_LOCAL: "architect",
            RoutingLayer.EXTERNAL: "architect",
        }
        role_name = layer_to_role.get(layer)
        if role_name:
            agent = self.registry.get(role_name)
            if agent:
                return agent
        agents = self.registry.list_agents()
        return agents[0] if agents else None

    def _check_gate(self, gate_name: str, step_output: Any) -> bool:
        """Check SOP gate conditions."""
        if gate_name == "syntax_valid":
            if isinstance(step_output, dict):
                return step_output.get("success", False)
            return True
        if gate_name == "tests_pass":
            if isinstance(step_output, dict):
                return step_output.get("success", False)
            return True
        return True

    @property
    def summary(self) -> str:
        """Get orchestrator summary including costs."""
        lines = [
            "Orchestrator Summary",
            f"Agents: {len(self.registry.list_agents())}",
            f"Messages: {self.bus.message_count}",
            f"Total tokens: {self.cost.total_tokens:,}",
            f"Estimated cost: ${self.cost.total_cost:.4f}",
        ]
        return "\n".join(lines)
