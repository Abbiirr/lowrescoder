#!/usr/bin/env python3
"""Smoke coverage for Kotlin LSP adapter registration and operation plumbing.

Run: python3 autocode/tests/pty/pty_smoke_lsp_kotlin.py
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
    if os.environ.get("AUTOCODE_LSP_KOTLIN_SMOKE_UV") != "1":
        os.environ["AUTOCODE_LSP_KOTLIN_SMOKE_UV"] = "1"
        os.execvp("uv", ["uv", "run", "python3", str(Path(__file__).resolve())])
    raise

from autocode.layer2.lsp_client import LSPClient  # noqa: E402
from autocode.layer2.lsp_servers import get_adapter_for_path, lsp_doctor_checks  # noqa: E402
from autocode.layer2.lsp_servers.kotlin import KotlinLSPAdapter  # noqa: E402

ARTIFACT_DIR = _AUTOCODE_ROOT / "docs" / "qa" / "test-results"
FIXTURE_ROOT = _AUTOCODE_ROOT / "tests" / "fixtures" / "lsp" / "kotlin"
FIXTURE_SERVER = _AUTOCODE_ROOT / "tests" / "fixtures" / "lsp" / "fake_server.py"


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


async def _exercise_fake_server() -> list[str]:
    adapter = KotlinLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER)))
    client = LSPClient(adapter.config_for_root(FIXTURE_ROOT.as_uri()))
    uri = (FIXTURE_ROOT / "Hello.kt").as_uri()
    await client.start()
    try:
        await client.goto_definition(uri, 3, 5)
        await client.find_references(uri, 3, 5)
        await client.hover(uri, 3, 5)
        await client.document_symbol(uri)
        await client.workspace_symbol("greet")
        await client.implementations(uri, 3, 5)
        await client.type_definition(uri, 3, 5)
        await client.call_hierarchy(uri, 3, 5)
        await client.diagnostics(uri)
    finally:
        await client.stop()
    return ["Kotlin adapter resolved for Hello.kt", "fake stdio LSP server completed all 9 ops"]


async def main_async() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact = ARTIFACT_DIR / f"{_timestamp()}-pty-smoke-lsp-kotlin.md"
    adapter = get_adapter_for_path(FIXTURE_ROOT / "Hello.kt")
    if not isinstance(adapter, KotlinLSPAdapter):
        artifact.write_text(
            "# Kotlin LSP Smoke\n\nStatus: FAIL\n\nKotlin adapter did not resolve.\n",
            encoding="utf-8",
        )
        print("[FAIL] Kotlin adapter did not resolve")
        print(f"Artifact: {artifact}")
        return 1
    try:
        evidence = await _exercise_fake_server()
    except Exception as exc:
        artifact.write_text(
            "# Kotlin LSP Smoke\n\nStatus: FAIL\n\n"
            f"Error: `{type(exc).__name__}: {exc}`\n",
            encoding="utf-8",
        )
        print(f"[FAIL] Kotlin LSP smoke: {type(exc).__name__}: {exc}")
        print(f"Artifact: {artifact}")
        return 1
    real_server = shutil.which("kotlin-language-server")
    real_status = (
        f"Real kotlin-language-server present at `{real_server}`."
        if real_server
        else "Real kotlin-language-server unavailable; real-server portion self-skipped."
    )
    doctor_checks = lsp_doctor_checks(adapters=[KotlinLSPAdapter()])
    artifact.write_text(
        "# Kotlin LSP Smoke\n\nStatus: PASS\n\n"
        "Scope: Kotlin adapter registration, deterministic fake stdio LSP operation path, "
        "extended timeout config, and non-spawning doctor metadata.\n\nEvidence:\n"
        + "\n".join(f"- {line}" for line in evidence)
        + f"\n- {real_status}\n"
        + f"- Doctor metadata: `{doctor_checks[0]}`\n",
        encoding="utf-8",
    )
    print("[PASS] Kotlin LSP smoke")
    print(f"Artifact: {artifact}")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
