"""Integration test: verify Ollama models support native tool calling.

Run with: uv run python -m pytest tests/integration/test_ollama_tool_calling.py -v -s
Requires: OLLAMA_HOST env var pointing to a running Ollama server.

Models that fail tool calling should NOT be used as the AutoCode L4 model.
"""

from __future__ import annotations

import json
import os
import time

import pytest
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

MODELS_TO_TEST = [
    "qwen3:8b",
]

TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Run a shell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                },
                "required": ["command"],
            },
        },
    },
]

MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant. Use the provided tools."},
    {"role": "user", "content": "Run the command 'pwd' to show the current directory."},
]


def _check_ollama_reachable() -> bool:
    """Check if Ollama server is reachable."""
    import urllib.request

    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=30)
        return True
    except Exception:
        return False


def _list_available_models() -> list[str]:
    """Get list of models available on the Ollama server."""
    import urllib.request

    try:
        resp = urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=10)
        data = json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _test_tool_calling(model: str, timeout: int = 120) -> dict[str, object]:
    """Test if a model supports native Ollama tool calling.

    Returns dict with: model, success, has_tool_calls, content, duration_s, error
    """
    import urllib.request

    payload = json.dumps({
        "model": model,
        "messages": MESSAGES,
        "tools": TOOL_SCHEMA,
        "stream": False,
    }).encode()

    start = time.monotonic()
    try:
        req = urllib.request.Request(
            f"{OLLAMA_HOST}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        duration = time.monotonic() - start

        message = data.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls", [])

        # Check if model used native tool calling
        has_native_tool_calls = len(tool_calls) > 0
        correct_tool = False
        tool_args = {}

        if has_native_tool_calls:
            tc = tool_calls[0]
            func = tc.get("function", {})
            correct_tool = func.get("name") == "run_command"
            tool_args = func.get("arguments", {})

        # Check if model tried text-based tool calls (bad)
        text_based = any(
            marker in content
            for marker in ["<function=", "<tool_call>", "```tool", "<|tool_call|>"]
        )

        return {
            "model": model,
            "success": has_native_tool_calls and correct_tool,
            "has_tool_calls": has_native_tool_calls,
            "correct_tool": correct_tool,
            "tool_args": tool_args,
            "text_based_fallback": text_based,
            "content_preview": content[:200] if content else "(empty)",
            "duration_s": round(duration, 1),
            "error": None,
        }
    except Exception as e:
        duration = time.monotonic() - start
        return {
            "model": model,
            "success": False,
            "has_tool_calls": False,
            "correct_tool": False,
            "tool_args": {},
            "text_based_fallback": False,
            "content_preview": "",
            "duration_s": round(duration, 1),
            "error": str(e),
        }


@pytest.fixture(scope="module")
def ollama_available() -> bool:
    reachable = _check_ollama_reachable()
    if not reachable:
        pytest.skip(f"Ollama server not reachable at {OLLAMA_HOST}")
    return True


@pytest.fixture(scope="module")
def available_models(ollama_available: bool) -> list[str]:
    return _list_available_models()


@pytest.mark.integration()
class TestOllamaToolCalling:
    """Test each model's native tool calling capability."""

    @pytest.mark.parametrize("model", MODELS_TO_TEST)
    def test_model_tool_calling(
        self, model: str, available_models: list[str],
    ) -> None:
        """Test that a model supports native Ollama tool calling."""
        if model not in available_models:
            pytest.skip(f"{model} not available on {OLLAMA_HOST}")

        result = _test_tool_calling(model, timeout=180)

        print(f"\n{'='*60}")
        print(f"Model: {result['model']}")
        print(f"Duration: {result['duration_s']}s")
        print(f"Native tool calls: {result['has_tool_calls']}")
        print(f"Correct tool (run_command): {result['correct_tool']}")
        print(f"Tool args: {result['tool_args']}")
        print(f"Text-based fallback: {result['text_based_fallback']}")
        print(f"Content: {result['content_preview']}")
        if result["error"]:
            print(f"Error: {result['error']}")
        print(f"PASS: {result['success']}")
        print(f"{'='*60}")

        if result["error"]:
            pytest.fail(f"{model}: {result['error']}")

        assert result["has_tool_calls"], (
            f"{model} did not use native tool calling. "
            f"Content: {result['content_preview']}"
        )
        assert result["correct_tool"], (
            f"{model} called wrong tool. Expected 'run_command'."
        )


@pytest.mark.integration()
def test_summary_report(available_models: list[str]) -> None:
    """Run all models and print a summary comparison table."""
    results = []
    for model in MODELS_TO_TEST:
        if model not in available_models:
            results.append({"model": model, "success": False, "error": "not installed"})
            continue
        results.append(_test_tool_calling(model, timeout=180))

    print("\n" + "=" * 80)
    print(f"{'Model':<30} {'Native TC':<12} {'Correct':<10} {'Time':<8} {'Status'}")
    print("-" * 80)
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        err = f" ({r['error']})" if r.get("error") else ""
        tc = "Yes" if r.get("has_tool_calls") else "No"
        correct = "Yes" if r.get("correct_tool") else "No"
        dur = f"{r.get('duration_s', '?')}s"
        print(f"{r['model']:<30} {tc:<12} {correct:<10} {dur:<8} {status}{err}")
    print("=" * 80)

    passing = [r["model"] for r in results if r["success"]]
    print(f"\nRecommended models for AutoCode: {passing or 'NONE'}")
