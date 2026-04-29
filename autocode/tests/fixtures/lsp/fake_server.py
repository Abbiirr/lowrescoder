#!/usr/bin/env python3
"""Deterministic stdio LSP server fixture for unit tests."""

from __future__ import annotations

import json
import os
import sys


def _read_message() -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        name, value = line.decode("ascii").split(":", 1)
        headers[name.lower()] = value.strip()

    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def _write_message(payload: dict) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def _capabilities() -> dict:
    if os.environ.get("FAKE_LSP_LIMITED_CAPS") == "1":
        return {"hoverProvider": True}
    return {
        "definitionProvider": True,
        "referencesProvider": True,
        "hoverProvider": True,
        "documentSymbolProvider": True,
        "workspaceSymbolProvider": True,
        "implementationProvider": True,
        "typeDefinitionProvider": True,
        "callHierarchyProvider": True,
        "diagnosticProvider": {"interFileDependencies": False, "workspaceDiagnostics": False},
    }


def _location(uri: str = "file:///fixture.py") -> dict:
    return {
        "uri": uri,
        "range": {
            "start": {"line": 1, "character": 2},
            "end": {"line": 1, "character": 8},
        },
    }


def _result(method: str, params: dict) -> object:
    uri = params.get("textDocument", {}).get("uri", "file:///fixture.py")
    if method == "initialize":
        return {"capabilities": _capabilities()}
    if method == "textDocument/definition":
        return [_location(uri)]
    if method == "textDocument/references":
        return [_location(uri), _location(uri)]
    if method == "textDocument/hover":
        return {"contents": {"kind": "markdown", "value": "fake hover"}}
    if method == "textDocument/documentSymbol":
        return [{"name": "FakeSymbol", "kind": 12, "range": _location(uri)["range"]}]
    if method == "workspace/symbol":
        return [{"name": "FakeWorkspaceSymbol", "kind": 12, "location": _location(uri)}]
    if method == "textDocument/implementation":
        return [_location(uri)]
    if method == "textDocument/typeDefinition":
        return [_location(uri)]
    if method == "textDocument/prepareCallHierarchy":
        return [{"name": "FakeCallable", "kind": 12, "uri": uri, "range": _location(uri)["range"], "selectionRange": _location(uri)["range"]}]
    if method == "textDocument/diagnostic":
        return {"kind": "full", "items": [{"message": "fake diagnostic", "severity": 1, "range": _location(uri)["range"]}]}
    if method == "shutdown":
        return None
    return None


def main() -> int:
    requests_seen = 0
    crash_after = int(os.environ.get("FAKE_LSP_CRASH_AFTER", "0"))
    while True:
        message = _read_message()
        if message is None:
            return 0
        if "id" not in message:
            continue
        requests_seen += 1
        if crash_after and requests_seen > crash_after:
            return 2
        method = message.get("method", "")
        _write_message({"jsonrpc": "2.0", "id": message["id"], "result": _result(method, message.get("params") or {})})
        if method == "shutdown":
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
