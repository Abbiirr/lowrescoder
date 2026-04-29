"""Tests for subprocess-based LSP client substrate."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from autocode.layer2.lsp_client import LSPClient, LSPServerConfig, UnsupportedLSPOperation
from autocode.layer2.lsp_servers import LSPAdapter, get_adapter_for_path, lsp_doctor_checks


FIXTURE_SERVER = Path(__file__).resolve().parents[1] / "fixtures" / "lsp" / "fake_server.py"


def _config(**kwargs: object) -> LSPServerConfig:
    return LSPServerConfig(
        language_id="fake",
        command=[sys.executable, str(FIXTURE_SERVER)],
        root_uri="file:///tmp/fake-root",
        **kwargs,
    )


@pytest.mark.asyncio()
async def test_lsp_client_starts_and_negotiates_capabilities() -> None:
    client = LSPClient(_config())
    await client.start()
    try:
        assert client.running
        assert client.capabilities["definitionProvider"] is True
    finally:
        await client.stop()


@pytest.mark.asyncio()
async def test_lsp_client_round_trips_all_nine_operations() -> None:
    client = LSPClient(_config())
    await client.start()
    try:
        uri = "file:///tmp/fake-root/example.fake"
        assert await client.goto_definition(uri, 1, 1)
        assert len(await client.find_references(uri, 1, 1)) == 2
        assert "fake hover" in str(await client.hover(uri, 1, 1))
        assert (await client.document_symbol(uri))[0]["name"] == "FakeSymbol"
        assert (await client.workspace_symbol("Fake"))[0]["name"] == "FakeWorkspaceSymbol"
        assert await client.implementations(uri, 1, 1)
        assert await client.type_definition(uri, 1, 1)
        assert (await client.call_hierarchy(uri, 1, 1))[0]["name"] == "FakeCallable"
        assert (await client.diagnostics(uri))["items"][0]["message"] == "fake diagnostic"
    finally:
        await client.stop()


@pytest.mark.asyncio()
async def test_lsp_client_restarts_after_server_crash() -> None:
    client = LSPClient(_config(env={"FAKE_LSP_CRASH_AFTER": "2"}, max_restarts=2))
    await client.start()
    try:
        uri = "file:///tmp/fake-root/example.fake"
        assert await client.goto_definition(uri, 1, 1)
        assert await client.goto_definition(uri, 1, 1)
        assert client.restart_count == 1
    finally:
        await client.stop()


@pytest.mark.asyncio()
async def test_lsp_client_degrades_when_capability_is_missing() -> None:
    client = LSPClient(_config(env={"FAKE_LSP_LIMITED_CAPS": "1"}))
    await client.start()
    try:
        with pytest.raises(UnsupportedLSPOperation):
            await client.goto_definition("file:///tmp/fake-root/example.fake", 1, 1)
    finally:
        await client.stop()


@pytest.mark.asyncio()
async def test_lsp_client_lazy_start_and_idle_shutdown() -> None:
    client = LSPClient(_config(idle_timeout_s=0.01))
    assert not client.running
    await client.goto_definition("file:///tmp/fake-root/example.fake", 1, 1)
    assert client.running
    await asyncio.sleep(0.05)
    await client.reap_idle()
    assert not client.running


def test_lsp_registry_resolves_extensions_and_doctor_does_not_spawn() -> None:
    class FakeAdapter(LSPAdapter):
        language_id = "fake"
        extensions = (".fake",)
        command = ("fake-lsp-that-is-not-installed",)

    adapter = get_adapter_for_path("example.fake", adapters=[FakeAdapter()])
    assert adapter is not None
    assert adapter.language_id == "fake"

    checks = lsp_doctor_checks(adapters=[FakeAdapter()])

    assert checks == [{
        "language": "fake",
        "available": False,
        "command": "fake-lsp-that-is-not-installed",
        "path": None,
    }]
