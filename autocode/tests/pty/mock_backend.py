#!/usr/bin/env python3
"""Minimal mock backend for Go TUI PTY regression tests.

Speaks JSON-RPC over stdin/stdout just enough to drive the TUI through
specific scenarios without a real LLM:
  - emits on_status on startup (lets TUI reach stageInput)
  - responds to chat requests with a short token stream + on_done
  - emits a WARNING to stderr (to test severity classification)
  - never opens a model list (C1 regression guard)

Usage: set AUTOCODE_PYTHON_CMD to this script.
"""
from __future__ import annotations

import json
import sys
import threading
import time


def send(method: str, params: dict) -> None:
    msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params})
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def respond(id_: int, result: dict) -> None:
    msg = json.dumps({"jsonrpc": "2.0", "id": id_, "result": result})
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def main() -> None:
    # Emit a WARNING to stderr — should appear as ⚠ dim, not red Error: banner
    print("WARNING: mock backend starting — this is a test warning", file=sys.stderr, flush=True)

    # Small delay then send on_status so TUI transitions stageInit → stageInput
    time.sleep(0.3)
    send("on_status", {
        "model": "tools",
        "provider": "openrouter",
        "mode": "suggest",
        "session_id": "mock-session-001",
    })

    # Read JSON-RPC requests from stdin and respond
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

        if method == "chat":
            # Simulate a chat turn: token stream + done
            threading.Thread(target=_handle_chat, args=(req_id,), daemon=True).start()

        elif method in ("session.resume", "steer", "fork_session", "session.fork"):
            # Acknowledge without side effects
            if req_id is not None:
                respond(req_id, {"ok": True})

        elif method in ("model_list", "model.list"):
            # CRITICAL: only respond if explicitly requested — never send unsolicited
            if req_id is not None:
                respond(req_id, {"models": ["tools", "coding", "fast"], "current": "tools"})

        elif req_id is not None:
            respond(req_id, {"ok": True})


def _handle_chat(req_id: int | None) -> None:
    time.sleep(0.1)
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
