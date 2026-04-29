"""Subprocess-backed Language Server Protocol client."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


class LSPError(RuntimeError):
    """Base error for LSP client failures."""


class UnsupportedLSPOperation(LSPError):
    """Raised when the server did not advertise a required capability."""


@dataclass(frozen=True)
class LSPServerConfig:
    """Configuration for launching one LSP server process."""

    language_id: str
    command: Sequence[str]
    root_uri: str
    initialization_options: Mapping[str, Any] | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    max_restarts: int = 3
    request_timeout_s: float = 10.0
    idle_timeout_s: float = 600.0


class LSPClient:
    """Minimal JSON-RPC-over-stdio LSP client with lazy lifecycle."""

    _CAPABILITY_BY_METHOD = {
        "textDocument/definition": "definitionProvider",
        "textDocument/references": "referencesProvider",
        "textDocument/hover": "hoverProvider",
        "textDocument/documentSymbol": "documentSymbolProvider",
        "workspace/symbol": "workspaceSymbolProvider",
        "textDocument/implementation": "implementationProvider",
        "textDocument/typeDefinition": "typeDefinitionProvider",
        "textDocument/prepareCallHierarchy": "callHierarchyProvider",
        "textDocument/diagnostic": "diagnosticProvider",
    }

    def __init__(self, config: LSPServerConfig) -> None:
        self.config = config
        self.capabilities: dict[str, Any] = {}
        self.restart_count = 0
        self._process: asyncio.subprocess.Process | None = None
        self._next_id = 0
        self._last_used = 0.0

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def start(self) -> None:
        """Start the server and run the initialize handshake."""
        if self.running:
            return
        self._process = await self._spawn()
        result = await self._request_no_restart("initialize", {
            "processId": os.getpid(),
            "rootUri": self.config.root_uri,
            "capabilities": {},
            "initializationOptions": dict(self.config.initialization_options or {}),
        })
        self.capabilities = dict((result or {}).get("capabilities") or {})
        await self._notify("initialized", {})

    async def stop(self) -> None:
        """Gracefully stop the server, killing it if shutdown does not complete."""
        process = self._process
        self._process = None
        if process is None or process.returncode is not None:
            return
        try:
            await asyncio.wait_for(self._request_no_restart("shutdown", {}), timeout=1)
            await self._notify("exit", {})
        except Exception:
            pass
        try:
            await asyncio.wait_for(process.wait(), timeout=1)
        except TimeoutError:
            process.kill()
            await process.wait()

    async def reap_idle(self) -> None:
        """Stop the server if it has been idle beyond the configured threshold."""
        if not self.running:
            return
        if time.monotonic() - self._last_used >= self.config.idle_timeout_s:
            await self.stop()

    async def goto_definition(self, uri: str, line: int, character: int) -> Any:
        return await self._text_document_position("textDocument/definition", uri, line, character)

    async def find_references(self, uri: str, line: int, character: int) -> Any:
        params = self._position_params(uri, line, character)
        params["context"] = {"includeDeclaration": True}
        return await self._request("textDocument/references", params)

    async def hover(self, uri: str, line: int, character: int) -> Any:
        return await self._text_document_position("textDocument/hover", uri, line, character)

    async def document_symbol(self, uri: str) -> Any:
        return await self._request("textDocument/documentSymbol", {
            "textDocument": {"uri": uri},
        })

    async def workspace_symbol(self, query: str) -> Any:
        return await self._request("workspace/symbol", {"query": query})

    async def implementations(self, uri: str, line: int, character: int) -> Any:
        return await self._text_document_position("textDocument/implementation", uri, line, character)

    async def type_definition(self, uri: str, line: int, character: int) -> Any:
        return await self._text_document_position("textDocument/typeDefinition", uri, line, character)

    async def call_hierarchy(self, uri: str, line: int, character: int) -> Any:
        return await self._text_document_position(
            "textDocument/prepareCallHierarchy",
            uri,
            line,
            character,
        )

    async def diagnostics(self, uri: str) -> Any:
        return await self._request("textDocument/diagnostic", {
            "textDocument": {"uri": uri},
        })

    async def _text_document_position(
        self,
        method: str,
        uri: str,
        line: int,
        character: int,
    ) -> Any:
        return await self._request(method, self._position_params(uri, line, character))

    def _position_params(self, uri: str, line: int, character: int) -> dict[str, Any]:
        return {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        }

    async def _request(self, method: str, params: dict[str, Any]) -> Any:
        await self.start()
        self._ensure_capability(method)
        try:
            return await self._request_no_restart(method, params)
        except (EOFError, BrokenPipeError, ConnectionError):
            if self.restart_count >= self.config.max_restarts:
                raise
            self.restart_count += 1
            await self._force_stop()
            await self.start()
            return await self._request_no_restart(method, params)

    async def _request_no_restart(self, method: str, params: dict[str, Any]) -> Any:
        if not self.running:
            raise ConnectionError("LSP server is not running")
        assert self._process is not None
        self._next_id += 1
        request_id = self._next_id
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }
        await self._write(payload)
        while True:
            response = await asyncio.wait_for(
                self._read(),
                timeout=self.config.request_timeout_s,
            )
            if response.get("id") != request_id:
                continue
            self._last_used = time.monotonic()
            if "error" in response:
                raise LSPError(str(response["error"]))
            return response.get("result")

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        if not self.running:
            return
        await self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _ensure_capability(self, method: str) -> None:
        capability = self._CAPABILITY_BY_METHOD.get(method)
        if capability and not self.capabilities.get(capability):
            raise UnsupportedLSPOperation(
                f"{self.config.language_id} server does not support {method}"
            )

    async def _spawn(self) -> asyncio.subprocess.Process:
        env = os.environ.copy()
        env.update(self.config.env)
        return await asyncio.create_subprocess_exec(
            *self.config.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

    async def _write(self, payload: dict[str, Any]) -> None:
        assert self._process is not None and self._process.stdin is not None
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        self._process.stdin.write(header + body)
        await self._process.stdin.drain()

    async def _read(self) -> dict[str, Any]:
        assert self._process is not None and self._process.stdout is not None
        headers: dict[str, str] = {}
        while True:
            line = await self._process.stdout.readline()
            if not line:
                raise EOFError("LSP server closed stdout")
            if line in (b"\r\n", b"\n"):
                break
            name, value = line.decode("ascii").split(":", 1)
            headers[name.lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            raise EOFError("LSP response missing Content-Length")
        body = await self._process.stdout.readexactly(length)
        return json.loads(body.decode("utf-8"))

    async def _force_stop(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.returncode is None:
            process.kill()
            await process.wait()
