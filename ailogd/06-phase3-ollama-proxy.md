# Phase 3: Ollama Reverse Proxy

Phase 3 adds HTTP traffic capture for Ollama/LLM Gateway requests. This is Tier 3 — conditional capture via wrapper shims and shell profile injection.

---

## Design

An async `httpx`-based HTTP reverse proxy on `localhost:11435` that forwards to the configured Ollama/Gateway host (default `localhost:4000`). Captures full request and response bodies while streaming responses through transparently.

**File:** `modules/ailogd/src/ailogd/capture/ollama_proxy.py`
**Output:** `~/logs/ollama/traffic.jsonl`

---

## Implementation Approach

### httpx Async Reverse Proxy with Body Capture (Tee Pattern)

The proxy must stream responses through to the client while simultaneously capturing the body for logging. This requires a "tee" pattern:

```python
import httpx
import json
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM = "http://localhost:4000"
LISTEN_PORT = 11435
LOG_FILE = Path.home() / "logs" / "ollama" / "traffic.jsonl"

client = httpx.AsyncClient(base_url=UPSTREAM, timeout=None)

async def tee_response(response: httpx.Response, captured: list[bytes]):
    """Yield chunks to client while accumulating for capture."""
    async for chunk in response.aiter_raw():
        captured.append(chunk)
        yield chunk

async def handle_request(request_method, path, headers, body):
    """Forward request to upstream, capture and log both directions."""
    # Build upstream request
    url = httpx.URL(path=path)
    rp_req = client.build_request(
        request_method,
        url,
        headers=[(k, v) for k, v in headers if k.lower() != "host"],
        content=body,
    )

    # Send with streaming
    rp_resp = await client.send(rp_req, stream=True)

    # Tee response for capture
    captured_chunks: list[bytes] = []

    async def log_after_response():
        await rp_resp.aclose()
        response_body = b"".join(captured_chunks)
        event = {
            "schema_version": "ailogd.v1",
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "ollama",
            "event": "api_request",
            "event_id": str(uuid.uuid4()),
            "capture_mode": "proxy_http",
            "redaction_applied": "none",
            "data": {
                "method": request_method,
                "path": path,
                "request_body": json.loads(body) if body else None,
                "response_status": rp_resp.status_code,
                "response_body": json.loads(response_body) if response_body else None,
            },
        }
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")

    return rp_resp, captured_chunks, log_after_response
```

### Key httpx Details

| Method | Description |
|--------|-------------|
| `response.aiter_raw()` | Raw bytes, no decoding — preserves original encoding. Use for proxying. |
| `response.aiter_bytes()` | Decoded bytes — handles content-encoding. Do NOT use for proxying (breaks Content-Encoding header). |
| `response.aiter_text()` | Decoded text |
| `response.aiter_lines()` | Line-by-line text |

### ASGI/Starlette Integration

For production, wrap in a Starlette/FastAPI app:

```python
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.routing import Route
from starlette.background import BackgroundTask

async def proxy(request: Request):
    body = await request.body()
    rp_resp, captured, cleanup = await handle_request(
        request.method,
        request.url.path,
        request.headers.raw,
        body,
    )
    return StreamingResponse(
        tee_response(rp_resp, captured),
        status_code=rp_resp.status_code,
        headers=dict(rp_resp.headers),
        background=BackgroundTask(cleanup),
    )

app = Starlette(routes=[Route("/{path:path}", proxy, methods=["GET","POST","PUT","DELETE","PATCH"])])
```

Run with: `uvicorn ailogd.capture.ollama_proxy:app --host 0.0.0.0 --port 11435`

Or integrate as an asyncio task within `daemon.py`.

---

## Activation

### Wrapper Shims (CLI tools)

`~/.local/bin/claude` wrapper:
```bash
#!/bin/bash
export HTTPS_PROXY=http://localhost:8080
export OLLAMA_HOST=http://localhost:11435
exec /home/bs01763/.local/share/claude/versions/current/claude "$@"
```

`~/.local/bin/codex` wrapper:
```bash
#!/bin/bash
export HTTPS_PROXY=http://localhost:8080
exec /home/bs01763/.nvm/versions/node/v24.13.1/bin/codex "$@"
```

### Shell Profile Injection

Added to `~/.bashrc` / `~/.zshrc` (idempotent, guarded by `# ailogd:` marker):
```bash
# ailogd: route Ollama traffic through logging proxy
export OLLAMA_HOST=http://localhost:11435
# HTTPS_PROXY set per-tool via wrappers to avoid breaking non-AI HTTPS
```

**Why not set HTTPS_PROXY globally?** Because it would break all HTTPS traffic system-wide. Only AI CLI tools need the proxy, so it's set per-tool via wrappers.

---

## Caveats

### Streaming Responses

Ollama supports `"stream": true` which returns newline-delimited JSON chunks. The proxy must handle this correctly:
- Forward chunks as they arrive (non-blocking)
- Accumulate chunks for logging
- Log the complete response after streaming finishes

### Timeout

Set `timeout=None` on `httpx.AsyncClient`. Ollama responses can take 30+ seconds for large generations. Default httpx timeout is 5 seconds — will cause failures.

### Host Header

When proxying, remove or don't forward the original `Host` header. The upstream server may reject requests with the wrong Host.

### Connection Management

Use a single `httpx.AsyncClient` instance (connection pooling). Do NOT create a new client per request.

### Response Body Assembly

For streaming responses, the captured chunks are individual JSON objects (one per line). The assembled body is all chunks concatenated. For non-streaming, it's a single JSON object.

### Port Conflict

If port 11435 is already in use, the proxy fails to start. The daemon should:
1. Check if the port is free at startup
2. Log a clear error message if not
3. Continue running other workers (parsers, etc.)
