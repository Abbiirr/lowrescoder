"""Tests for Go and Rust LSP adapter slices."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from autocode.layer2.lsp_client import LSPClient
from autocode.layer2.lsp_servers import get_adapter_for_path, lsp_doctor_checks, registered_adapters
from autocode.layer2.lsp_servers.go import GoLSPAdapter
from autocode.layer2.lsp_servers.rust import RustLSPAdapter


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "lsp"
FIXTURE_SERVER = FIXTURE_ROOT / "fake_server.py"


def test_go_adapter_is_registered_for_go_extensions() -> None:
    adapter = get_adapter_for_path(FIXTURE_ROOT / "go" / "hello.go")

    assert isinstance(adapter, GoLSPAdapter)
    assert any(isinstance(adapter, GoLSPAdapter) for adapter in registered_adapters())


def test_rust_adapter_is_registered_for_rust_extensions() -> None:
    adapter = get_adapter_for_path(FIXTURE_ROOT / "rust" / "src" / "main.rs")

    assert isinstance(adapter, RustLSPAdapter)
    assert any(isinstance(adapter, RustLSPAdapter) for adapter in registered_adapters())


def test_go_adapter_config_discovers_go_mod(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "go.mod").write_text("module example.com/demo\n\ngo 1.21\n", encoding="utf-8")

    config = GoLSPAdapter().config_for_root(project_root.as_uri())

    assert config.language_id == "go"
    assert config.command == ("gopls",)
    assert config.initialization_options == {
        "autocode": {
            "config_files": ["go.mod"],
            "minimum_go_version": "1.16",
            "project_local_symbols_only": True,
        }
    }


def test_rust_adapter_config_discovers_cargo_toml_and_extends_timeout(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "Cargo.toml").write_text("[package]\nname = \"demo\"\n", encoding="utf-8")

    config = RustLSPAdapter().config_for_root(project_root.as_uri())

    assert config.language_id == "rust"
    assert config.command == ("rust-analyzer",)
    assert config.request_timeout_s == 30.0
    assert config.initialization_options == {
        "autocode": {
            "config_files": ["Cargo.toml"],
            "project_local_symbols_only": True,
            "rust_clippy_diagnostics": True,
        }
    }


def test_go_rust_doctor_reports_optional_servers_without_spawning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_which(command: str) -> Any:
        return None

    monkeypatch.setattr("autocode.layer2.lsp_servers.go.shutil.which", fake_which)
    monkeypatch.setattr("autocode.layer2.lsp_servers.rust.shutil.which", fake_which)
    checks = lsp_doctor_checks(adapters=[GoLSPAdapter(), RustLSPAdapter()])

    assert checks == [
        {
            "language": "go",
            "available": False,
            "command": "gopls",
            "path": None,
            "runtime": "go",
            "runtime_available": False,
            "runtime_path": None,
            "minimum_runtime_version": "1.16",
        },
        {
            "language": "rust",
            "available": False,
            "command": "rust-analyzer",
            "path": None,
            "runtime": "rustup",
            "runtime_available": False,
            "runtime_path": None,
            "component": "rust-analyzer",
        },
    ]


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("adapter", "fixture_dir", "fixture_name", "workspace_query"),
    [
        (GoLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER))), "go", "hello.go", "localAdd"),
        (
            RustLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER))),
            "rust",
            "src/main.rs",
            "local_add",
        ),
    ],
)
async def test_go_rust_fixtures_round_trip_against_fake_lsp_server(
    adapter: GoLSPAdapter | RustLSPAdapter,
    fixture_dir: str,
    fixture_name: str,
    workspace_query: str,
) -> None:
    root = FIXTURE_ROOT / fixture_dir
    client = LSPClient(adapter.config_for_root(root.as_uri()))
    uri = (root / fixture_name).as_uri()
    await client.start()
    try:
        assert await client.goto_definition(uri, 3, 5)
        assert len(await client.find_references(uri, 3, 5)) == 2
        assert "fake hover" in str(await client.hover(uri, 3, 5))
        assert (await client.document_symbol(uri))[0]["name"] == "FakeSymbol"
        assert (await client.workspace_symbol(workspace_query))[0]["name"] == "FakeWorkspaceSymbol"
        assert await client.implementations(uri, 3, 5)
        assert await client.type_definition(uri, 3, 5)
        assert (await client.call_hierarchy(uri, 3, 5))[0]["name"] == "FakeCallable"
        diagnostics = await client.diagnostics(uri)
        assert diagnostics["items"][0]["message"] == "fake diagnostic"
    finally:
        await client.stop()
