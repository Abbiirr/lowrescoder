"""Tests for JavaScript and TypeScript LSP adapter slices."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from autocode.layer2.lsp_client import LSPClient
from autocode.layer2.lsp_servers import get_adapter_for_path, lsp_doctor_checks, registered_adapters
from autocode.layer2.lsp_servers.javascript import JavaScriptLSPAdapter
from autocode.layer2.lsp_servers.typescript import TypeScriptLSPAdapter


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "lsp"
FIXTURE_SERVER = FIXTURE_ROOT / "fake_server.py"


def test_javascript_adapter_is_registered_for_js_extensions() -> None:
    for name in ("hello.js", "component.jsx", "module.mjs"):
        adapter = get_adapter_for_path(FIXTURE_ROOT / "javascript" / name)
        assert isinstance(adapter, JavaScriptLSPAdapter)

    assert any(isinstance(adapter, JavaScriptLSPAdapter) for adapter in registered_adapters())


def test_typescript_adapter_is_registered_for_ts_extensions() -> None:
    for name in ("hello.ts", "component.tsx", "types.d.ts"):
        adapter = get_adapter_for_path(FIXTURE_ROOT / "typescript" / name)
        assert isinstance(adapter, TypeScriptLSPAdapter)

    assert any(isinstance(adapter, TypeScriptLSPAdapter) for adapter in registered_adapters())


def test_javascript_adapter_config_discovers_project_config(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "jsconfig.json").write_text("{}\n", encoding="utf-8")

    config = JavaScriptLSPAdapter().config_for_root(project_root.as_uri())

    assert config.language_id == "javascript"
    assert config.command == ("typescript-language-server", "--stdio")
    assert config.initialization_options == {
        "autocode": {
            "config_files": ["jsconfig.json"],
            "project_local_symbols_only": True,
        }
    }


def test_typescript_adapter_config_discovers_tsconfig(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "tsconfig.json").write_text("{}\n", encoding="utf-8")

    config = TypeScriptLSPAdapter().config_for_root(project_root.as_uri())

    assert config.language_id == "typescript"
    assert config.command == ("typescript-language-server", "--stdio")
    assert config.initialization_options == {
        "autocode": {
            "config_files": ["tsconfig.json"],
            "project_local_symbols_only": True,
            "typescript_type_diagnostics": True,
        }
    }


def test_typescript_language_server_doctor_reports_peer_dependency_without_spawning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_which(command: str) -> Any:
        return None

    monkeypatch.setattr("autocode.layer2.lsp_servers.javascript.shutil.which", fake_which)
    checks = lsp_doctor_checks(adapters=[JavaScriptLSPAdapter(), TypeScriptLSPAdapter()])

    assert checks == [
        {
            "language": "javascript",
            "available": False,
            "command": "typescript-language-server",
            "path": None,
            "peer_dependency": "typescript",
            "peer_available": False,
            "peer_path": None,
        },
        {
            "language": "typescript",
            "available": False,
            "command": "typescript-language-server",
            "path": None,
            "peer_dependency": "typescript",
            "peer_available": False,
            "peer_path": None,
        },
    ]


@pytest.mark.asyncio()
async def test_javascript_fixture_operations_round_trip_against_fake_lsp_server() -> None:
    adapter = JavaScriptLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER)))
    client = LSPClient(adapter.config_for_root((FIXTURE_ROOT / "javascript").as_uri()))
    uri = (FIXTURE_ROOT / "javascript" / "hello.js").as_uri()
    await client.start()
    try:
        assert await client.goto_definition(uri, 7, 9)
        assert len(await client.find_references(uri, 7, 9)) == 2
        assert "fake hover" in str(await client.hover(uri, 3, 16))
        assert (await client.document_symbol(uri))[0]["name"] == "FakeSymbol"
        assert (await client.workspace_symbol("greet"))[0]["name"] == "FakeWorkspaceSymbol"
        assert await client.implementations(uri, 13, 9)
        assert await client.type_definition(uri, 13, 9)
        assert (await client.call_hierarchy(uri, 7, 9))[0]["name"] == "FakeCallable"
        assert (await client.diagnostics(uri))["items"][0]["message"] == "fake diagnostic"
    finally:
        await client.stop()


@pytest.mark.asyncio()
async def test_typescript_fixture_operations_round_trip_against_fake_lsp_server() -> None:
    adapter = TypeScriptLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER)))
    client = LSPClient(adapter.config_for_root((FIXTURE_ROOT / "typescript").as_uri()))
    uri = (FIXTURE_ROOT / "typescript" / "hello.ts").as_uri()
    await client.start()
    try:
        assert await client.goto_definition(uri, 11, 9)
        assert len(await client.find_references(uri, 11, 9)) == 2
        assert "fake hover" in str(await client.hover(uri, 3, 17))
        assert (await client.document_symbol(uri))[0]["name"] == "FakeSymbol"
        assert (await client.workspace_symbol("Greeter"))[0]["name"] == "FakeWorkspaceSymbol"
        assert await client.implementations(uri, 6, 17)
        assert await client.type_definition(uri, 17, 15)
        assert (await client.call_hierarchy(uri, 11, 9))[0]["name"] == "FakeCallable"
        assert (await client.diagnostics(uri))["items"][0]["message"] == "fake diagnostic"
    finally:
        await client.stop()
