"""Tests for C, Kotlin, and Python LSP adapter slices."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from autocode.agent import lsp_tools
from autocode.layer2.lsp_client import LSPClient
from autocode.layer2.lsp_servers import get_adapter_for_path, lsp_doctor_checks, registered_adapters
from autocode.layer2.lsp_servers.c import CLSPAdapter
from autocode.layer2.lsp_servers.kotlin import KotlinLSPAdapter
from autocode.layer2.lsp_servers.python import PythonLSPAdapter


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "lsp"
FIXTURE_SERVER = FIXTURE_ROOT / "fake_server.py"


def test_c_adapter_is_registered_for_c_extensions() -> None:
    for name in ("hello.c", "hello.h"):
        adapter = get_adapter_for_path(FIXTURE_ROOT / "c" / name)
        assert isinstance(adapter, CLSPAdapter)

    assert any(isinstance(adapter, CLSPAdapter) for adapter in registered_adapters())


def test_kotlin_adapter_is_registered_for_kotlin_extensions() -> None:
    for name in ("Hello.kt", "build.kts"):
        adapter = get_adapter_for_path(FIXTURE_ROOT / "kotlin" / name)
        assert isinstance(adapter, KotlinLSPAdapter)

    assert any(isinstance(adapter, KotlinLSPAdapter) for adapter in registered_adapters())


def test_python_adapter_is_registered_for_python_extensions() -> None:
    for name in ("hello.py", "hello.pyi"):
        adapter = get_adapter_for_path(FIXTURE_ROOT / "python" / name)
        assert isinstance(adapter, PythonLSPAdapter)

    assert any(isinstance(adapter, PythonLSPAdapter) for adapter in registered_adapters())


def test_c_adapter_config_discovers_compile_commands(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "compile_commands.json").write_text("[]\n", encoding="utf-8")

    config = CLSPAdapter().config_for_root(project_root.as_uri())

    assert config.language_id == "c"
    assert config.command == ("clangd", "--compile-commands-dir", str(project_root))
    assert config.initialization_options == {
        "autocode": {
            "config_files": ["compile_commands.json"],
            "project_local_symbols_only": True,
        }
    }


def test_kotlin_adapter_config_uses_extended_timeout_and_build_file_discovery(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "build.gradle.kts").write_text("plugins {}\n", encoding="utf-8")

    config = KotlinLSPAdapter().config_for_root(project_root.as_uri())

    assert config.language_id == "kotlin"
    assert config.command == ("kotlin-language-server",)
    assert config.request_timeout_s == 30.0
    assert config.initialization_options == {
        "autocode": {
            "build_files": ["build.gradle.kts"],
            "project_local_symbols_only": True,
        }
    }


def test_python_adapter_config_uses_pylsp_and_preserves_jedi_fallback(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")

    config = PythonLSPAdapter().config_for_root(project_root.as_uri())

    assert config.language_id == "python"
    assert config.command == ("pylsp",)
    assert config.initialization_options == {
        "autocode": {
            "config_files": ["pyproject.toml"],
            "project_local_symbols_only": True,
            "jedi_fallback": True,
            "preferred_server": "pylsp",
        }
    }
    assert callable(lsp_tools._handle_lsp_goto_definition)
    assert callable(lsp_tools._handle_lsp_find_references)
    assert callable(lsp_tools._handle_lsp_get_type)
    assert callable(lsp_tools._handle_lsp_symbols)


def test_c_kotlin_python_doctor_reports_optional_servers_without_spawning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_which(command: str) -> Any:
        return None

    monkeypatch.setattr("autocode.layer2.lsp_servers.c.shutil.which", fake_which)
    monkeypatch.setattr("autocode.layer2.lsp_servers.kotlin.shutil.which", fake_which)
    monkeypatch.setattr("autocode.layer2.lsp_servers.python.shutil.which", fake_which)
    checks = lsp_doctor_checks(
        adapters=[CLSPAdapter(), KotlinLSPAdapter(), PythonLSPAdapter()],
    )

    assert checks == [
        {
            "language": "c",
            "available": False,
            "command": "clangd",
            "path": None,
        },
        {
            "language": "kotlin",
            "available": False,
            "command": "kotlin-language-server",
            "path": None,
            "runtime": "java",
            "runtime_available": False,
            "runtime_path": None,
        },
        {
            "language": "python",
            "available": False,
            "command": "pylsp",
            "path": None,
            "fallback": "jedi",
            "fallback_available": lsp_tools._JEDI_OK,
            "fallback_error": lsp_tools._JEDI_ERR,
        },
    ]


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("adapter", "fixture_dir", "fixture_name", "workspace_query"),
    [
        (CLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER))), "c", "hello.c", "local_add"),
        (
            KotlinLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER))),
            "kotlin",
            "Hello.kt",
            "greet",
        ),
        (
            PythonLSPAdapter(command=(sys.executable, str(FIXTURE_SERVER))),
            "python",
            "hello.py",
            "Greeter",
        ),
    ],
)
async def test_c_kotlin_python_fixtures_round_trip_against_fake_lsp_server(
    adapter: CLSPAdapter | KotlinLSPAdapter | PythonLSPAdapter,
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
        assert (await client.diagnostics(uri))["items"][0]["message"] == "fake diagnostic"
    finally:
        await client.stop()
