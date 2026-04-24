#!/usr/bin/env python3
"""Minimal mock backend for Go TUI PTY regression tests.

Speaks JSON-RPC over stdin/stdout just enough to drive the TUI through
specific scenarios without a real LLM:
  - emits on_status on startup (lets TUI reach stageInput)
  - responds to chat requests with a short token stream + on_done
  - emits a WARNING to stderr (to test severity classification)
  - can emit an approval request modal for permission-surface capture
  - never opens a model list (C1 regression guard)
  - if chat body contains ``__ASK_USER__``, emit an on_ask_user request
    and wait for the TUI's answer before completing the turn (Phase 2
    Scenario 2)

Usage: set AUTOCODE_PYTHON_CMD to this script.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autocode.backend import schema as rpc_schema  # noqa: E402

# Pending ask_user request IDs → threading.Event + answer slot.
_ASK_LOCK = threading.Lock()
_PENDING_ASK: dict[int, dict] = {}
_NEXT_ASK_ID = 9000


def send(method: str, params: dict) -> None:
    msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def respond(id_: int, result: dict) -> None:
    msg = json.dumps({"jsonrpc": "2.0", "id": id_, "result": result})
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def request(method: str, params: dict, req_id: int) -> None:
    msg = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _ask_user_blocking(
    question: str,
    options: list,
    allow_text: bool = False,
    timeout: float = 15.0,
) -> str:
    """Send on_ask_user request and block until the TUI answers."""
    global _NEXT_ASK_ID
    with _ASK_LOCK:
        req_id = _NEXT_ASK_ID
        _NEXT_ASK_ID += 1
        evt = threading.Event()
        _PENDING_ASK[req_id] = {"event": evt, "answer": ""}

    request(rpc_schema.METHOD_ON_ASK_USER, {
        "question": question,
        "options": options,
        "allow_text": allow_text,
    }, req_id)

    if not evt.wait(timeout=timeout):
        with _ASK_LOCK:
            _PENDING_ASK.pop(req_id, None)
        return ""

    with _ASK_LOCK:
        entry = _PENDING_ASK.pop(req_id, {})
    return entry.get("answer", "")


def main() -> None:
    # Emit a WARNING to stderr — should appear as ⚠ dim, not red Error: banner
    if os.environ.get("AUTOCODE_MOCK_SUPPRESS_STARTUP_WARNING", "").strip() not in {
        "1",
        "true",
        "yes",
    }:
        print("WARNING: mock backend starting — this is a test warning", file=sys.stderr, flush=True)

    # Small delay then send on_status so TUI transitions stageInit → stageInput
    time.sleep(0.3)
    send(rpc_schema.METHOD_ON_STATUS, {
        "model": "tools",
        "provider": "openrouter",
        "mode": "suggest",
        "session_id": "mock-session-001",
    })

    # Read JSON-RPC requests/responses from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id")

        # Response to a mock-initiated request (on_ask_user answer)
        if method == "" and req_id is not None and "result" in req:
            with _ASK_LOCK:
                entry = _PENDING_ASK.get(req_id)
            if entry is not None:
                result = req.get("result") or {}
                entry["answer"] = result.get("answer", "") if isinstance(result, dict) else ""
                entry["event"].set()
            continue

        if method == "chat":
            params = req.get("params") or {}
            message = ""
            if isinstance(params, dict):
                message = params.get("message", "") or ""
            threading.Thread(
                target=_handle_chat,
                args=(req_id, message),
                daemon=True,
            ).start()

        elif method in ("session.resume", "steer", rpc_schema.METHOD_SESSION_FORK):
            if req_id is not None:
                respond(req_id, {"ok": True})

        elif method == rpc_schema.METHOD_MODEL_LIST:
            # CRITICAL: only respond if explicitly requested — never send unsolicited
            if req_id is not None:
                respond(req_id, {"models": ["tools", "coding", "fast"], "current": "tools"})

        elif method == rpc_schema.METHOD_PROVIDER_LIST:
            if req_id is not None:
                respond(req_id, {"providers": ["ollama", "openrouter"], "current": "openrouter"})

        elif method == rpc_schema.METHOD_SESSION_LIST:
            if req_id is not None:
                respond(
                    req_id,
                    {
                        "sessions": [
                            {
                                "id": "mock-session-001",
                                "title": "Mock session",
                                "model": "tools",
                                "provider": "openrouter",
                            }
                        ]
                    },
                )

        elif method == rpc_schema.METHOD_COMMAND_LIST:
            if req_id is not None:
                respond(
                    req_id,
                    {
                        "commands": [
                            {
                                "name": "help",
                                "aliases": ["h", "?"],
                                "description": "Show available commands",
                            },
                            {
                                "name": "model",
                                "aliases": ["m"],
                                "description": "Show or switch the LLM model",
                            },
                            {
                                "name": "plan",
                                "aliases": [],
                                "description": "Open the plan surface",
                            },
                            {
                                "name": "multi",
                                "aliases": [],
                                "description": "Open the multitasking surface",
                            },
                            {
                                "name": "review",
                                "aliases": [],
                                "description": "Open the review surface",
                            },
                            {
                                "name": "diff",
                                "aliases": [],
                                "description": "Open the diff surface",
                            },
                            {
                                "name": "grep",
                                "aliases": ["search"],
                                "description": "Open the search surface",
                            },
                            {
                                "name": "restore",
                                "aliases": [],
                                "description": "Open the restore browser",
                            },
                            {
                                "name": "cc",
                                "aliases": [],
                                "description": "Open the command center",
                            },
                            {
                                "name": "escalation",
                                "aliases": [],
                                "description": "Open the escalation surface",
                            },
                        ]
                    },
                )

        elif method == rpc_schema.METHOD_PLAN_SET:
            params = req.get("params") or {}
            mode = "planning"
            if isinstance(params, dict):
                mode = params.get("mode", "planning") or "planning"
            if req_id is not None:
                respond(req_id, {"mode": mode, "changed": True})

        elif req_id is not None:
            respond(req_id, {"ok": True})


def _handle_chat(req_id: int | None, message: str) -> None:
    time.sleep(0.1)

    # Phase 2 Scenario 2: ask_user trigger.
    if "__ASK_USER__" in message:
        answer = _ask_user_blocking(
            question="Please choose how to proceed:",
            options=["Continue", "Abort", "Retry"],
            allow_text=False,
        )
        tokens = [f"You chose: {answer or '(cancelled)'}"]
    elif "__APPROVAL__" in message:
        request(
            rpc_schema.METHOD_ON_TOOL_REQUEST,
            {
                "tool": "write_file",
                "args": "{\"path\":\"/tmp/demo.txt\",\"content\":\"example\"}",
            },
            9100,
        )
        tokens = []
    elif "__HALT_FAILURE__" in message:
        send(
            rpc_schema.METHOD_ON_ERROR,
            {
                "message": (
                    "halted after matrix shard failure; retry, inspect, restore, "
                    "rewind, compact, or planning are available"
                ),
            },
        )
        tokens = []
    elif "__WARNING__" in message:
        # Phase 2 Scenario 3: emit a WARNING to stderr mid-chat. The
        # TUI should render it as a dim scrollback line, NOT as a red
        # `Error:` banner.
        print(
            "WARNING: deliberate mid-session warning from mock backend",
            file=sys.stderr,
            flush=True,
        )
        time.sleep(0.1)
        tokens = ["Warning", " emitted", "."]
    elif (
        "__ACTIVE_FIXTURE__" in message
        or "refactor parser.ts to safely handle missing imports and run tests" in message
    ):
        send(
            rpc_schema.METHOD_ON_TASK_STATE,
            {
                "tasks": [
                    {"id": "task-1", "title": "Inspect parser flow", "status": "done"},
                    {"id": "task-2", "title": "Search extractImports references", "status": "done"},
                    {"id": "task-3", "title": "Update AST types", "status": "done"},
                    {"id": "task-4", "title": "Patch parser import handling", "status": "running"},
                    {"id": "task-5", "title": "Run targeted parser tests", "status": "running"},
                    {"id": "task-6", "title": "Write changelog note", "status": "pending"},
                ],
                "subagents": [
                    {"id": "agent-1", "role": "lint-scout", "status": "running"},
                    {"id": "agent-2", "role": "doc-writer", "status": "waiting"},
                ],
            },
        )
        scripted = [
            "Planning\n",
            "Will inspect parser flow, extend ASTNode with an optional imports field, patch extractImports to guard against undefined,\n",
            "then run the targeted parser tests.\n",
            "\n",
            "Read(src/utils/parser.ts)\n",
            "Search \"extractImports|ASTNode\" src\n",
            "Read(src/types.ts)\n",
            "Edit(src/types.ts)\n",
            "42 - imports: ImportNode[]\n",
            "42 + imports?: ImportNode[]\n",
            "Edit(src/utils/parser.ts)\n",
            "71 - const nodes = extractImports(ast.imports)\n",
            "71 + const nodes = ast.imports ? extractImports(ast.imports) : []\n",
            "Run(bun test ./tests/parser.test.ts)\n",
            "√ parsed simple ast\n",
            "√ extracted full imports\n",
        ]
        for tok in scripted:
            send("on_token", {"text": tok})
            time.sleep(0.05)
        time.sleep(3.5)
        tokens = [
            "[bun v1.1] √ parses optional import list\n",
            "[bun v1.1] √ extracts nested imports\n",
            "[bun v1.1] √ parser smoke path\n",
            "[bun v1.1] ● tests/parser.test.ts…\n",
        ]
    elif "__SLOW__" in message:
        # Phase 2 Scenario 5: hold the spinner for multiple ticks by
        # emitting one token immediately, then inserting a longer gap
        # mid-stream. This keeps the TUI in Stage::Streaming long enough
        # for spinner and queued-followup interactions to become visible.
        send("on_token", {"text": "Working"})
        time.sleep(2.0)
        tokens = [" done", " after", " a", " slow", " pause", "."]
    elif "__PANELS__" in message:
        send(
            rpc_schema.METHOD_ON_TASK_STATE,
            {
                "tasks": [
                    {
                        "id": "task-1",
                        "title": "Build release",
                        "status": "running",
                    }
                ],
                "subagents": [
                    {
                        "id": "agent-1",
                        "role": "coder",
                        "status": "running",
                    }
                ],
            },
        )
        send(
            rpc_schema.METHOD_ON_TOOL_CALL,
            {
                "name": "bash",
                "status": "running",
                "args": "ls -la",
            },
        )
        time.sleep(0.1)
        send(
            rpc_schema.METHOD_ON_TOOL_CALL,
            {
                "name": "write_file",
                "status": "completed",
                "args": "{\"path\":\"demo.txt\"}",
                "result": "ok",
            },
        )
        tokens = ["Panels", " ready", "."]
    else:
        tokens = ["Hello", " from", " the", " mock", " backend", "!"]

    for tok in tokens:
        send("on_token", {"text": tok})
        time.sleep(0.05)
    send("on_done", {
        "tokens_in": 5, "tokens_out": len(tokens),
        "cancelled": False, "layer_used": 4,
    })
    if req_id is not None:
        respond(req_id, {"ok": True})


if __name__ == "__main__":
    # findPythonBackend() appends "serve" as argv[1] — ignore it
    main()
