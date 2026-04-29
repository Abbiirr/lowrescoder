"""Tests for the Java LSP adapter slice."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from autocode.layer2.lsp_client import LSPClient
from autocode.layer2.lsp_servers import get_adapter_for_path, lsp_doctor_checks, registered_adapters
from autocode.layer2.lsp_servers.java import JavaLSPAdapter


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "lsp" / "java"
FIXTURE_SERVER = Path(__file__).resolve().parents[1] / "fixtures" / "lsp" / "fake_server.py"


def test_java_adapter_is_registered_for_java_files() -> None:
    adapter = get_adapter_for_path(FIXTURE_ROOT / "Hello.java")

    assert isinstance(adapter, JavaLSPAdapter)
    assert any(isinstance(registered, JavaLSPAdapter) for registered in registered_adapters())
    assert adapter.language_id == "java"
    assert adapter.extensions == (".java",)


def test_java_adapter_config_uses_jdtls_workspace_and_project_local_init_options(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pom.xml").write_text("<project />\n", encoding="utf-8")
    root_uri = project_root.as_uri()

    config = JavaLSPAdapter().config_for_root(root_uri)

    assert config.language_id == "java"
    assert config.command[0] == "jdtls"
    assert "-data" in config.command
    workspace_dir = Path(config.command[config.command.index("-data") + 1])
    assert workspace_dir.name == "jdtls-workspace"
    assert str(project_root) in str(workspace_dir)
    assert config.initialization_options == {
        "autocode": {
            "build_files": ["pom.xml"],
            "project_local_symbols_only": True,
        }
    }


def test_java_lsp_doctor_reports_jdtls_and_java_runtime_without_spawning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_which(command: str) -> Any:
        return None

    monkeypatch.setattr("autocode.layer2.lsp_servers.java.shutil.which", fake_which)
    checks = lsp_doctor_checks(adapters=[JavaLSPAdapter()])

    assert checks == [{
        "language": "java",
        "available": False,
        "command": "jdtls",
        "path": None,
        "runtime": "java",
        "runtime_available": False,
        "runtime_path": None,
        "minimum_runtime_version": 17,
    }]


@pytest.mark.asyncio()
async def test_java_fixture_operations_round_trip_against_fake_lsp_server() -> None:
    adapter = JavaLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER)))
    client = LSPClient(adapter.config_for_root(FIXTURE_ROOT.as_uri()))
    uri = (FIXTURE_ROOT / "Hello.java").as_uri()
    await client.start()
    try:
        assert await client.goto_definition(uri, 10, 23)
        assert len(await client.find_references(uri, 10, 23)) == 2
        assert "fake hover" in str(await client.hover(uri, 5, 13))
        assert (await client.document_symbol(uri))[0]["name"] == "FakeSymbol"
        assert (await client.workspace_symbol("Hello"))[0]["name"] == "FakeWorkspaceSymbol"
        assert await client.implementations(uri, 20, 17)
        assert await client.type_definition(uri, 30, 20)
        assert (await client.call_hierarchy(uri, 10, 23))[0]["name"] == "FakeCallable"
        assert (await client.diagnostics(uri))["items"][0]["message"] == "fake diagnostic"
    finally:
        await client.stop()
