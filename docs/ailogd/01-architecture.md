# Architecture

## Capture Universality Model

Two-tier capture — not all tiers are universal:

| Tier | Scope | Mechanism | Universal? |
|------|-------|-----------|-----------:|
| **Tier 1: Parsers** | All tools, all launches | File/DB tailers watching `~/.claude/`, `~/.codex/`, etc. | **Yes** — tools write logs regardless of how launched |
| **Tier 2: Hooks** | Claude Code only | Claude Code hook system via `~/.claude/settings.json` | **Yes** — global user settings, any project |
| **Tier 3: Deep capture** | CLI tools launched via wrappers | Ollama proxy + mitmproxy via env vars | **Conditional** — only when launched through wrapper shims |

**Fallback guarantee:** Even without wrappers or hooks, Tier 1 parsers capture everything from local logs. Tiers 2 and 3 add real-time and network-level capture on top.

## Sources Captured

| Source | Storage | Format | Size on Disk |
|--------|---------|--------|-------------|
| Claude Code | `~/.claude/projects/**/*.jsonl` | JSONL (session files + subagent files) | ~560MB |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | JSONL (`{timestamp, type, payload}`) | ~51MB |
| OpenCode | `~/.local/share/opencode/opencode.db` | SQLite (session/message/part tables) | ~5.6MB |
| Copilot VS Code | `~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl` | Multi-kind JSONL (kind: 0/1/2) | varies |
| Copilot JetBrains | `~/.config/github-copilot/db/` | H2 MVStore / Nitrite (Java-serialized) | ~92KB |
| Ollama / Gateway | `http://localhost:4000/v1` (gateway) / `:11434` (direct) | HTTP JSON API | real-time |
| API HTTPS | `api.anthropic.com`, `api.openai.com`, `api.openrouter.ai` | HTTPS | real-time |

## Output Structure

```
~/logs/                        <- global sink (chmod 700)
├── claude-code/
│   ├── live.jsonl             <- real-time from hooks (normalized ailogd.v1)
│   └── parsed.jsonl           <- parsed from projects/**/*.jsonl
├── codex/
│   ├── live.jsonl             <- real-time from session file watching
│   └── parsed.jsonl           <- parsed from sessions/**/*.jsonl
├── opencode/
│   ├── live.jsonl             <- real-time from DB polling
│   └── parsed.jsonl           <- parsed from opencode.db
├── copilot/
│   ├── vscode-parsed.jsonl    <- parsed from chatSessions
│   └── jetbrains-parsed.jsonl <- parsed from Nitrite via Java extractor
├── ollama/
│   └── traffic.jsonl          <- full HTTP request/response (plaintext)
├── api-traffic/
│   └── https.jsonl            <- full HTTPS payloads via mitmproxy
└── unified.jsonl              <- merged normalized stream from all sources
```

## Module Layout

```
modules/ailogd/
├── pyproject.toml                     <- uv project (name=ailogd, python>=3.11)
├── uv.lock
├── .python-version
├── src/
│   └── ailogd/
│       ├── __init__.py
│       ├── daemon.py                  <- main daemon entry point
│       ├── config.py                  <- config loading from config.yaml
│       ├── schema.py                  <- ailogd.v1 event dataclasses + validation
│       ├── normalize.py               <- hook/source event normalization mappers
│       ├── state.py                   <- checkpoint store (per-source strategies)
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py               <- BaseParser ABC with incremental tailing
│       │   ├── claude_code.py        <- projects/**/*.jsonl parser
│       │   ├── codex.py              <- sessions/**/*.jsonl parser
│       │   ├── opencode.py           <- SQLite (session/message/part) parser
│       │   ├── copilot_vscode.py     <- chatSessions/*.jsonl (kind:0/1/2)
│       │   └── copilot_jetbrains.py  <- Java subprocess -> Nitrite -> JSONL
│       └── capture/
│           ├── __init__.py
│           ├── ollama_proxy.py       <- HTTP reverse proxy (localhost:11435 -> Ollama)
│           └── mitm_addon.py         <- mitmproxy addon for HTTPS API domains
├── java/
│   └── NitriteExtractor.java         <- ~50-line Java program for Nitrite -> JSONL
├── hooks/
│   └── claude_hook.sh                 <- Claude Code hook (installed to ~/.local/bin/ailogd-hook)
├── wrappers/
│   ├── claude.sh                      <- wrapper shim for Claude Code CLI
│   └── codex.sh                       <- wrapper shim for Codex CLI
├── config.yaml                        <- default config (source paths, ports, domains, resolved paths)
├── install.sh                         <- one-shot installer
├── analyze.py                         <- pattern analysis CLI tool
└── tests/
    ├── fixtures/                      <- sample JSONL/DB per source format
    ├── test_parsers.py
    ├── test_schema.py
    ├── test_normalize.py
    ├── test_state.py
    ├── test_ollama_proxy.py
    ├── test_nitrite_extractor.py
    └── test_hook_latency.py
```

## Data Flow

```
[Claude Code]  ──writes──>  ~/.claude/projects/**/*.jsonl  ──tailer──>  ~/logs/claude-code/parsed.jsonl
                             ~/.claude/settings.json hooks  ──hook──>   ~/logs/claude-code/live.jsonl

[Codex CLI]    ──writes──>  ~/.codex/sessions/**/*.jsonl   ──tailer──>  ~/logs/codex/parsed.jsonl

[OpenCode]     ──writes──>  ~/.local/share/opencode/opencode.db  ──poller──>  ~/logs/opencode/parsed.jsonl

[Copilot VSC]  ──writes──>  workspaceStorage/*/chatSessions/*.jsonl  ──tailer──>  ~/logs/copilot/vscode-parsed.jsonl

[Copilot JB]   ──writes──>  ~/.config/github-copilot/db/*.db  ──java+poller──>  ~/logs/copilot/jetbrains-parsed.jsonl

[Any tool]     ──HTTP──>   localhost:11435 (ollama proxy)  ──capture──>  ~/logs/ollama/traffic.jsonl
                ──HTTPS──>  localhost:8080 (mitmproxy)     ──capture──>  ~/logs/api-traffic/https.jsonl

All per-source sinks  ──merger──>  ~/logs/unified.jsonl
```
