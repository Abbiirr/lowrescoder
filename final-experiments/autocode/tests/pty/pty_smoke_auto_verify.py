#!/usr/bin/env python3
"""Smoke coverage for post-edit auto-verify loop wiring.

Run: python3 autocode/tests/pty/pty_smoke_auto_verify.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

_HERE = Path(__file__).resolve().parent
_AUTOCODE_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_AUTOCODE_ROOT / "src"))

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    if os.environ.get("AUTOCODE_AUTO_VERIFY_SMOKE_UV") != "1":
        os.environ["AUTOCODE_AUTO_VERIFY_SMOKE_UV"] = "1"
        os.execvp("uv", ["uv", "run", "python3", str(Path(__file__).resolve())])
    raise

from autocode.agent.approval import ApprovalManager, ApprovalMode  # noqa: E402
from autocode.agent.auto_verify import AutoVerifyConfig, VerificationDiagnostic  # noqa: E402
from autocode.agent.loop import AgentLoop  # noqa: E402
from autocode.agent.tools import ToolDefinition, ToolRegistry  # noqa: E402
from autocode.layer4.llm import ToolCall  # noqa: E402
from autocode.session.store import SessionStore  # noqa: E402

ARTIFACT_DIR = _AUTOCODE_ROOT / "docs" / "qa" / "test-results"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


async def _exercise_loop(project_root: Path) -> str:
    import autocode.agent.loop as loop_module

    target = project_root / "hello.py"
    store = SessionStore(project_root / "sessions.db")
    try:
        session_id = store.create_session(
            title="auto-verify smoke",
            model="mock",
            provider="mock",
            project_dir=str(project_root),
        )
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="write_file",
            description="write",
            parameters={"type": "object", "properties": {}},
            handler=lambda path, content: "Wrote file",
            mutates_fs=True,
        ))

        async def fake_verify_after_edit(*args: Any, **kwargs: Any) -> Any:
            from autocode.agent.auto_verify import VerificationResult

            return VerificationResult(
                checked_files=[target],
                diagnostics=[
                    VerificationDiagnostic(
                        path=target,
                        line=1,
                        column=6,
                        severity="error",
                        message="smoke diagnostic",
                    )
                ],
            )

        loop_module.verify_after_edit = fake_verify_after_edit
        loop = AgentLoop(
            provider=None,
            tool_registry=registry,
            approval_manager=ApprovalManager(ApprovalMode.AUTO),
            session_store=store,
            session_id=session_id,
            project_root=project_root,
            verify_config=AutoVerifyConfig(enabled=True, max_iterations=1),
        )
        msg_id = store.add_message(session_id, "assistant", "")
        result = await loop._execute_tool_call(
            ToolCall(
                id="tc1",
                name="write_file",
                arguments={"path": str(target), "content": "print('broken'"},
            ),
            msg_id=msg_id,
        )
        return result.result
    finally:
        store.close()


async def main_async() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = ARTIFACT_DIR / f"{_timestamp()}-pty-smoke-auto-verify.md"
    with TemporaryDirectory(prefix="autocode-auto-verify-smoke-") as tmp:
        project_root = Path(tmp)
        try:
            result = await _exercise_loop(project_root)
        except Exception as exc:
            artifact.write_text(
                "# Auto-Verify Smoke\n\nStatus: FAIL\n\n"
                f"Error: `{type(exc).__name__}: {exc}`\n",
                encoding="utf-8",
            )
            print(f"[FAIL] auto-verify smoke: {type(exc).__name__}: {exc}")
            print(f"Artifact: {artifact}")
            return 1
    passed = (
        "Verification failed" in result
        and "smoke diagnostic" in result
        and "No automatic rollback was performed" in result
    )
    artifact.write_text(
        "# Auto-Verify Smoke\n\n"
        f"Status: {'PASS' if passed else 'FAIL'}\n\n"
        "Scope: AgentLoop post-edit verification hook with deterministic diagnostics.\n\n"
        f"Result excerpt:\n\n```\n{result}\n```\n",
        encoding="utf-8",
    )
    print("[PASS] auto-verify smoke" if passed else "[FAIL] auto-verify smoke")
    print(f"Artifact: {artifact}")
    return 0 if passed else 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
