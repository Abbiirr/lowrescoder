#!/usr/bin/env python3
"""Smoke coverage for Go subprocess LSP adapter registration.

Run: python3 autocode/tests/pty/pty_smoke_lsp_go.py
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AUTOCODE_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_AUTOCODE_ROOT / "src"))

try:
    import dotenv  # noqa: F401
except ModuleNotFoundError:
    if os.environ.get("AUTOCODE_LSP_GO_SMOKE_UV") != "1":
        os.environ["AUTOCODE_LSP_GO_SMOKE_UV"] = "1"
        os.execvp("uv", ["uv", "run", "python3", str(Path(__file__).resolve())])
    raise

from autocode.layer2.lsp_client import LSPClient  # noqa: E402
from autocode.layer2.lsp_servers import get_adapter_for_path, lsp_doctor_checks  # noqa: E402
from autocode.layer2.lsp_servers.go import GoLSPAdapter  # noqa: E402

ARTIFACT_DIR = _AUTOCODE_ROOT / "docs" / "qa" / "test-results"
FIXTURE_ROOT = _AUTOCODE_ROOT / "tests" / "fixtures" / "lsp" / "go"
FIXTURE_SERVER = _AUTOCODE_ROOT / "tests" / "fixtures" / "lsp" / "fake_server.py"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


async def _exercise_fake_server() -> list[str]:
    adapter = GoLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER)))
    client = LSPClient(adapter.config_for_root(FIXTURE_ROOT.as_uri()))
    uri = (FIXTURE_ROOT / "hello.go").as_uri()
    await client.start()
    try:
        await client.goto_definition(uri, 3, 5)
        await client.find_references(uri, 3, 5)
        await client.hover(uri, 3, 5)
        await client.document_symbol(uri)
        await client.workspace_symbol("localAdd")
        await client.implementations(uri, 3, 5)
        await client.type_definition(uri, 3, 5)
        await client.call_hierarchy(uri, 3, 5)
        await client.diagnostics(uri)
    finally:
        await client.stop()
    return ["Go adapter resolved for hello.go", "fake stdio LSP server completed all 9 ops"]


async def main_async() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = ARTIFACT_DIR / f"{_timestamp()}-pty-smoke-lsp-go.md"
    adapter = get_adapter_for_path(FIXTURE_ROOT / "hello.go")
    if not isinstance(adapter, GoLSPAdapter):
        artifact.write_text(
            "# Go LSP Smoke\n\nStatus: FAIL\n\nGo adapter did not resolve.\n",
            encoding="utf-8",
        )
        print("[FAIL] Go adapter did not resolve")
        print(f"Artifact: {artifact}")
        return 1
    try:
        evidence = await _exercise_fake_server()
    except Exception as exc:
        artifact.write_text(
            "# Go LSP Smoke\n\nStatus: FAIL\n\n"
            f"Error: `{type(exc).__name__}: {exc}`\n",
            encoding="utf-8",
        )
        print(f"[FAIL] Go LSP smoke: {type(exc).__name__}: {exc}")
        print(f"Artifact: {artifact}")
        return 1
    real_server = shutil.which("gopls")
    real_status = (
        f"Real gopls present at `{real_server}`."
        if real_server
        else "Real gopls unavailable; real-server portion self-skipped."
    )
    doctor_checks = lsp_doctor_checks(adapters=[GoLSPAdapter()])
    artifact.write_text(
        "# Go LSP Smoke\n\nStatus: PASS\n\n"
        "Scope: Go subprocess LSP adapter registration and deterministic fake stdio LSP "
        "operation path.\n\nEvidence:\n"
        + "\n".join(f"- {line}" for line in evidence)
        + f"\n- {real_status}\n"
        + f"- Doctor metadata: `{doctor_checks[0]}`\n",
        encoding="utf-8",
    )
    print("[PASS] Go LSP smoke")
    print(f"Artifact: {artifact}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
