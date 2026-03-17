# Phase 4: mitmproxy HTTPS Capture

Phase 4 adds HTTPS traffic capture for AI API domains. This is Tier 3 — conditional capture via wrapper shims that set `HTTPS_PROXY`.

---

## Design

A mitmproxy addon that intercepts HTTPS traffic to AI API domains, captures full request/response bodies (with auth headers redacted), and logs to `~/logs/api-traffic/https.jsonl`.

**Addon file:** `modules/ailogd/src/ailogd/capture/mitm_addon.py`
**Execution:** `{venv}/bin/mitmdump -s {addon_path} --listen-port 8080 --set confdir=~/.mitmproxy`
**Output:** `~/logs/api-traffic/https.jsonl`

---

## Target Domains

| Domain | Provider | Traffic Type |
|--------|----------|-------------|
| `api.anthropic.com` | Anthropic | Claude API calls |
| `api.openai.com` | OpenAI | GPT/Codex API calls |
| `api.openrouter.ai` | OpenRouter | Multi-model routing |

---

## mitmproxy Addon Implementation

### Addon Class

```python
import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from mitmproxy import http, flowfilter

REDACT_HEADERS = {"authorization", "x-api-key", "proxy-authorization", "cookie", "set-cookie"}
TARGET_DOMAINS = {"api.anthropic.com", "api.openai.com", "api.openrouter.ai"}
LOG_FILE = Path.home() / "logs" / "api-traffic" / "https.jsonl"

logger = logging.getLogger("ailogd.mitm")

class AilogdMitmAddon:
    def __init__(self):
        self.filter = None

    def configure(self, updated):
        """Build domain filter on startup."""
        filter_expr = " | ".join(f"~d {d}" for d in TARGET_DOMAINS)
        self.filter = flowfilter.parse(filter_expr)

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when full response (headers + body) is received."""
        if not flowfilter.match(self.filter, flow):
            return

        # Redact sensitive headers
        req_headers = dict(flow.request.headers)
        resp_headers = dict(flow.response.headers)
        for h in REDACT_HEADERS:
            if h in req_headers:
                req_headers[h] = "[REDACTED]"
            if h in resp_headers:
                resp_headers[h] = "[REDACTED]"

        # Parse bodies
        req_body = None
        resp_body = None
        try:
            if flow.request.content:
                req_body = json.loads(flow.request.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            req_body = flow.request.content.decode("utf-8", errors="replace")
        try:
            if flow.response.content:
                resp_body = json.loads(flow.response.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            resp_body = flow.response.content.decode("utf-8", errors="replace")

        event = {
            "schema_version": "ailogd.v1",
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": "api-https",
            "event": "api_request",
            "event_id": str(uuid.uuid4()),
            "capture_mode": "proxy_https",
            "redaction_applied": "headers_only",
            "data": {
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "host": flow.request.host,
                "request_headers": req_headers,
                "request_body": req_body,
                "response_status": flow.response.status_code,
                "response_headers": resp_headers,
                "response_body": resp_body,
                "latency_ms": int((flow.response.timestamp_end - flow.request.timestamp_start) * 1000),
            },
            "provider": _domain_to_provider(flow.request.host),
            "model": _extract_model(req_body),
        }

        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(event) + "\n")

        logger.info(f"Captured {flow.request.method} {flow.request.pretty_url} -> {flow.response.status_code}")

def _domain_to_provider(host: str) -> str:
    return {
        "api.anthropic.com": "anthropic",
        "api.openai.com": "openai",
        "api.openrouter.ai": "openrouter",
    }.get(host, "unknown")

def _extract_model(body) -> str | None:
    if isinstance(body, dict):
        return body.get("model")
    return None

addons = [AilogdMitmAddon()]
```

### mitmproxy API Reference

| Property | Type | Description |
|----------|------|-------------|
| `flow.request.host` | str | Hostname |
| `flow.request.pretty_url` | str | Full URL |
| `flow.request.method` | str | HTTP method |
| `flow.request.content` | bytes | Request body |
| `flow.request.text` | str | Request body (decoded) |
| `flow.request.headers` | Headers | Mutable headers dict |
| `flow.response.status_code` | int | Response status |
| `flow.response.content` | bytes | Response body |
| `flow.response.headers` | Headers | Response headers |
| `flow.request.timestamp_start` | float | Request start time |
| `flow.response.timestamp_end` | float | Response end time |

### Flow Filter Syntax

| Expression | Meaning |
|-----------|---------|
| `~d domain` | Match by domain |
| `~u regex` | Match by URL pattern |
| `~m method` | Match by HTTP method |
| `~s` | Match responses |
| `~q` | Match requests |
| `expr1 \| expr2` | OR |
| `expr1 & expr2` | AND |
| `!expr` | NOT |

### Event Hooks Available

| Hook | When | Body Available? |
|------|------|----------------|
| `requestheaders()` | Request headers read | No |
| `request()` | Full request read | Yes |
| `responseheaders()` | Response headers read | No |
| `response()` | Full response read | Yes |
| `error()` | Connection error | N/A |

**ailogd uses `response()`** — both request and response bodies are available at this point.

---

## CA Certificate Setup

mitmproxy uses a self-signed CA to intercept HTTPS. Tools must trust this CA.

### First-time setup

```bash
# Generate CA cert (run mitmdump once)
mitmdump --listen-port 8080 &
sleep 2
kill %1

# Install system-wide
sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt
sudo update-ca-certificates

# For Python (requests/httpx)
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# For Node.js
export NODE_EXTRA_CA_CERTS=$HOME/.mitmproxy/mitmproxy-ca-cert.pem
```

### CA cert location

- Generated at: `~/.mitmproxy/mitmproxy-ca-cert.pem`
- Config dir: `~/.mitmproxy/` (specified via `--set confdir=~/.mitmproxy`)

---

## Integration with Daemon

The daemon manages mitmproxy as a subprocess:

```python
# In daemon.py
import subprocess

async def start_mitmproxy(config):
    """Start mitmproxy as a managed subprocess."""
    mitmdump_path = config["resolved_paths"]["mitmdump"]  # from config.yaml
    addon_path = config["resolved_paths"]["mitm_addon"]

    proc = await asyncio.create_subprocess_exec(
        mitmdump_path,
        "-s", addon_path,
        "--listen-port", "8080",
        "--set", f"confdir={Path.home() / '.mitmproxy'}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return proc
```

---

## Caveats

### IDE Extensions Cannot Be Proxied

VS Code and JetBrains extensions make HTTPS requests directly — they don't respect `HTTPS_PROXY` env var. This is a known limitation. Parser capture (Phase 1) covers these tools.

### TLS Pinning

Some tools may use TLS certificate pinning, which blocks mitmproxy interception. In this case:
- mitmproxy will show a TLS handshake error
- The request will fail through the proxy
- **Mitigation:** Rely on parser capture (Tier 1) for tools with TLS pinning
- Log a warning and continue

### Streaming Responses

When `flow.response.stream = True` is set in `responseheaders()`, the response body will be **empty** in `response()`. ailogd does NOT set streaming — it buffers the full response for capture. This means large responses are held in memory briefly.

### Body Size

AI API responses can be large (especially with long completions). The addon captures the full body. For very large responses, this may use significant memory momentarily.

### Redaction

Only headers are redacted. Request/response bodies are kept raw — this is the whole point of ailogd (observing prompt patterns, tool definitions, etc.). The following headers are redacted:
- `Authorization`
- `x-api-key`
- `proxy-authorization`
- `cookie`
- `set-cookie`

### mitmproxy Logging

Since mitmproxy 9+, use standard Python `logging` module. The old `ctx.log` / `log` hook is deprecated.

### Port 8080 Conflict

If another service uses port 8080, mitmproxy fails to start. The daemon should handle this gracefully (log error, continue without HTTPS capture).
