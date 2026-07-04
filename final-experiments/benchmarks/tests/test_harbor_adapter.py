"""Focused regressions for the Harbor / Terminal-Bench adapter."""

from __future__ import annotations

import importlib
import logging
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

# benchmarks/ is not a package — add project root to sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_harbor_adapter() -> types.ModuleType:
    """Import harbor_adapter with minimal Harbor stubs installed."""
    for name in [
        "benchmarks.adapters.harbor_adapter",
        "harbor",
        "harbor.agents",
        "harbor.agents.base",
        "harbor.environments",
        "harbor.environments.base",
        "harbor.models",
        "harbor.models.agent",
        "harbor.models.agent.context",
    ]:
        sys.modules.pop(name, None)

    harbor = types.ModuleType("harbor")
    harbor_agents = types.ModuleType("harbor.agents")
    harbor_agents_base = types.ModuleType("harbor.agents.base")
    harbor_env = types.ModuleType("harbor.environments")
    harbor_env_base = types.ModuleType("harbor.environments.base")
    harbor_models = types.ModuleType("harbor.models")
    harbor_models_agent = types.ModuleType("harbor.models.agent")
    harbor_models_agent_context = types.ModuleType("harbor.models.agent.context")

    class BaseAgent:
        SUPPORTS_ATIF = False

        def __init__(self) -> None:
            self.logger = logging.getLogger("test.harbor")
            self.model_name: str | None = None

    class BaseEnvironment:
        pass

    class AgentContext:
        def __init__(self) -> None:
            self.n_input_tokens = 0
            self.n_output_tokens = 0
            self.cost_usd = 0.0

    harbor_agents_base.BaseAgent = BaseAgent
    harbor_env_base.BaseEnvironment = BaseEnvironment
    harbor_models_agent_context.AgentContext = AgentContext

    sys.modules["harbor"] = harbor
    sys.modules["harbor.agents"] = harbor_agents
    sys.modules["harbor.agents.base"] = harbor_agents_base
    sys.modules["harbor.environments"] = harbor_env
    sys.modules["harbor.environments.base"] = harbor_env_base
    sys.modules["harbor.models"] = harbor_models
    sys.modules["harbor.models.agent"] = harbor_models_agent
    sys.modules["harbor.models.agent.context"] = harbor_models_agent_context

    return importlib.import_module("benchmarks.adapters.harbor_adapter")


class _FakeExecResult:
    def __init__(
        self,
        stdout: str = "",
        stderr: str = "",
        return_code: int = 0,
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code


class _FakeEnvironment:
    def __init__(self) -> None:
        self.commands: list[tuple[str, int]] = []

    async def exec(self, command: str, timeout_sec: int = 0) -> _FakeExecResult:
        self.commands.append((command, timeout_sec))
        if "which python3" in command:
            return _FakeExecResult(stdout="/usr/bin/python3\n")
        if "=== PWD ===" in command:
            return _FakeExecResult(stdout="/tmp/task\n")
        if command == "echo hi":
            return _FakeExecResult(stdout="hi\n")
        return _FakeExecResult(stdout="ok\n")


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def post(self, *_args, **_kwargs) -> _FakeResponse:
        if not self._responses:
            raise AssertionError("No fake Harbor responses left")
        return _FakeResponse(self._responses.pop(0))


@pytest.mark.asyncio
async def test_provider_errors_do_not_consume_turn_budget(
    monkeypatch: pytest.MonkeyPatch,
):
    """Provider errors should not exhaust max_iterations before a real turn lands."""
    module = _load_harbor_adapter()
    import httpx

    responses = [
        {"error": {"message": "gateway timeout"}},
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "tc1",
                                "type": "function",
                                "function": {
                                    "name": "run_command",
                                    "arguments": '{"command":"echo hi"}',
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        },
    ]
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(responses),
    )
    monkeypatch.setenv("AUTOCODE_TBENCH_MAX_ITER", "1")

    agent = module.AutoCodeHarborAgent()
    environment = _FakeEnvironment()
    context = SimpleNamespace(n_input_tokens=0, n_output_tokens=0, cost_usd=0.0)

    await agent.run("Fix the task", environment, context)

    assert any(command == "echo hi" for command, _timeout in environment.commands)
    assert context.n_input_tokens == 11
    assert context.n_output_tokens == 7


@pytest.mark.asyncio
async def test_text_only_turns_can_recover_into_tool_use(
    monkeypatch: pytest.MonkeyPatch,
):
    """Three text-only turns should nudge, not terminate, before a tool turn."""
    module = _load_harbor_adapter()
    import httpx

    responses = [
        {
            "choices": [
                {"message": {"content": "Plan the fix first.", "tool_calls": []}}
            ],
            "usage": {},
        },
        {
            "choices": [
                {"message": {"content": "Inspecting mentally.", "tool_calls": []}}
            ],
            "usage": {},
        },
        {
            "choices": [
                {
                    "message": {
                        "content": "Need to use a tool next.",
                        "tool_calls": [],
                    },
                }
            ],
            "usage": {},
        },
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "tc1",
                                "type": "function",
                                "function": {
                                    "name": "run_command",
                                    "arguments": '{"command":"echo hi"}',
                                },
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        },
    ]
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(responses),
    )
    monkeypatch.setenv("AUTOCODE_TBENCH_MAX_ITER", "4")

    agent = module.AutoCodeHarborAgent()
    environment = _FakeEnvironment()
    context = SimpleNamespace(n_input_tokens=0, n_output_tokens=0, cost_usd=0.0)

    await agent.run("Fix the task", environment, context)

    assert any(command == "echo hi" for command, _timeout in environment.commands)


def test_compact_messages_keeps_tool_pairs_and_drops_orphans():
    """Compaction should preserve valid recent tool pairs and remove orphaned tool rows."""
    module = _load_harbor_adapter()
    agent = module.AutoCodeHarborAgent()

    messages = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u"},
    ]
    messages.extend(
        {"role": "assistant", "content": f"filler-{i}" * 500} for i in range(60)
    )
    messages.extend(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc-keep",
                        "type": "function",
                        "function": {
                            "name": "run_command",
                            "arguments": '{"command":"echo hi"}',
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "tc-keep", "content": "hi"},
            {"role": "tool", "tool_call_id": "tc-orphan", "content": "bad"},
        ]
    )

    compacted = agent._compact_messages(messages)

    assert any(
        m.get("role") == "tool" and m.get("tool_call_id") == "tc-keep"
        for m in compacted
    )
    assert not any(
        m.get("role") == "tool" and m.get("tool_call_id") == "tc-orphan"
        for m in compacted
    )


def test_strategy_overlay_classifies_html_task():
    """HTML_OUTPUT task should get HTML-specific overlay guidance."""
    module = _load_harbor_adapter()
    overlay = module.get_overlay("break-filter-js-from-html")
    assert overlay.family.value == "html_output"
    assert "read_file" in overlay.preferred_tools
    assert overlay.additional_prompt_guidance != ""


def test_strategy_overlay_classifies_python_build_task():
    """PYTHON_BUILD task should get build-specific overlay guidance."""
    module = _load_harbor_adapter()
    overlay = module.get_overlay("build-cython-ext")
    assert overlay.family.value == "python_build"
    assert "bash" in overlay.preferred_tools


def test_stagnation_detector_integrated():
    """StagnationDetector should flag repeated identical results."""
    module = _load_harbor_adapter()
    detector = module.StagnationDetector(max_identical_results=3)
    assert detector.check("run_command", "same output") is None
    assert detector.check("run_command", "same output") is None
    result = detector.check("run_command", "same output")
    assert result is not None
    assert "STAGNATION" in result


def test_verifier_aware_retry_integrated():
    """verifier_aware_retry_guidance should guide on error signals."""
    module = _load_harbor_adapter()
    guidance = module.verifier_aware_retry_guidance(
        "run_command",
        "error: build failed",
        1,
        3,
    )
    assert guidance is not None
    assert "extract" in guidance.lower()

    max_guidance = module.verifier_aware_retry_guidance(
        "run_command",
        "error: build failed",
        3,
        3,
    )
    assert "MAX RETRIES" in max_guidance
