# ailogd — Universal AI Tool Logger

## What This Is

A background daemon that captures all request-response data from every AI coding tool on this machine — Claude Code, Codex CLI, OpenCode, GitHub Copilot (VS Code + JetBrains), Ollama, and HTTPS API traffic — regardless of how or where they are launched.

All logs go to `~/logs/`. The daemon lives at `modules/ailogd/` with its own `uv`-managed venv.

## File Index

| File | Contents |
|------|----------|
| [01-architecture.md](01-architecture.md) | Capture tiers, module layout, overall design |
| [02-schema.md](02-schema.md) | Unified event contract (`ailogd.v1`), all normalization maps |
| [03-source-formats.md](03-source-formats.md) | Verified source formats — ground truth from actual files on this machine |
| [04-phase1-parsers.md](04-phase1-parsers.md) | All 5 log parsers: Claude Code, Codex, OpenCode, Copilot VS Code, Copilot JetBrains |
| [05-phase2-hooks.md](05-phase2-hooks.md) | Claude Code hooks — real-time capture, hook API reference, settings.json |
| [06-phase3-ollama-proxy.md](06-phase3-ollama-proxy.md) | Ollama reverse proxy — httpx async, streaming, body capture |
| [07-phase4-mitmproxy.md](07-phase4-mitmproxy.md) | mitmproxy HTTPS capture — addon API, domain filtering, CA cert |
| [08-daemon.md](08-daemon.md) | Daemon design — asyncio workers, file tailing, DB polling, checkpoints |
| [09-nitrite-extractor.md](09-nitrite-extractor.md) | JetBrains Copilot — Nitrite/H2 MVStore Java extractor, full details |
| [10-systemd-install.md](10-systemd-install.md) | systemd user service, install script, wrapper shims, shell injection |
| [11-testing.md](11-testing.md) | 17-test plan with validation details |
| [12-risks-security.md](12-risks-security.md) | Risks, mitigations, security, privacy, retention |

## Locked Defaults

| Setting | Value |
|---------|-------|
| Log sink | `~/logs/` |
| Module path | `modules/ailogd/` (in repo) |
| Package manager | `uv` |
| Daemon runtime | `systemd --user` |
| Source scope | CLI + VS Code + JetBrains |
| Thinking capture | Exposed full |
| Retention | Keep forever (compressed segments) |
| Redaction | Headers only |
| P4 mode | Always-on for targets |

## Quick Start (After Implementation)

```bash
cd modules/ailogd
./install.sh          # creates dirs, syncs venv, installs hooks/wrappers/service
systemctl --user status ailogd   # verify running
tail -f ~/logs/unified.jsonl     # watch events
```

## Implementation Order

1. **Phase 1** — Log parsers + unified store (Tier 1: universal file/DB tailers)
2. **Phase 2** — Claude Code hooks (Tier 2: real-time via hook system)
3. **Phase 3** — Ollama reverse proxy (Tier 3: HTTP traffic capture)
4. **Phase 4** — mitmproxy HTTPS capture (Tier 3: HTTPS API domains)

Each phase is independently useful. Phase 1 alone gives full historical + incremental capture from all tools.
