# Risks, Security & Privacy

---

## Security Model

### Data at Rest

- `~/logs/` directory mode `700` — owner-only access
- Local-only storage — no uploads, no cloud sync, no network exposure
- No encryption at rest (files are plaintext JSONL + gzip)

### Redaction Policy

**Headers only** — the following headers are redacted to `[REDACTED]` in `api-traffic/https.jsonl`:
- `Authorization`
- `x-api-key`
- `proxy-authorization`
- `cookie`
- `set-cookie`

**Bodies are kept raw.** This is intentional — the entire point of ailogd is observing prompt patterns, tool definitions, conversation flows, and model outputs. Redacting bodies would defeat the purpose.

### Sensitive Data Warning

The installer prints:
```
WARNING: ailogd captures full request/response bodies from AI tools.
This includes prompts, code, and model outputs. Logs are stored at
~/logs/ with mode 700 (owner-only). Do not share log files.
```

### Nitrite DB Temp Files

When extracting from JetBrains Copilot databases, temp copies are created and deleted immediately after extraction. Temp files inherit the system tmp directory permissions.

---

## Risk Matrix

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | GUI clients/IDEs bypass proxy env | High | Medium | Tier 1 parsers always on as universal fallback; wrapper shims cover CLI launches |
| 2 | TLS pinning blocks mitmproxy | Medium | Low | Rely on parser capture; log warning and continue |
| 3 | Keep-forever disk growth | High | Medium | Gzip rotated segments (100MB trigger); `analyze.py --disk-usage` reports growth |
| 4 | Vendor format drift breaks parsers | Medium | Medium | Tolerant parsers (skip unknown fields); versioned test fixtures per source |
| 5 | Hook script stale after venv rebuild | Low | Medium | `install.sh` re-resolves paths; systemd `ExecStartPre` could run path check |
| 6 | Wrapper shim PATH ordering | Low | High | Install to `~/.local/bin/` (first in PATH); `install.sh` verifies |
| 7 | OpenCode DB locked during writes | Medium | Low | `PRAGMA journal_mode=WAL` read connection; retry on `SQLITE_BUSY` |
| 8 | Nitrite DB locked by running IDE | High | Low | Copy to temp file before extraction; use MVStore read-only mode |
| 9 | JetBrains JARs move on IDE upgrade | Medium | Medium | `config.yaml` stores resolved path; `install.sh --doctor` detects and warns |
| 10 | h2-mvstore version mismatch | Low | High | Pin to 2.2.224 exactly; verify at install time by checking DB file header |
| 11 | Python startup latency in hook | Medium | Low | Minimal stdlib-only script; target < 100ms median |
| 12 | mitmproxy CA cert not trusted | Medium | Medium | Print install instructions; test during doctor checks |
| 13 | Port 8080/11435 conflict | Low | Medium | Check ports at startup; log clear error; continue other workers |
| 14 | Partial JSONL lines from unflushed writes | Medium | Low | Skip empty/partial lines; retry on next read cycle |

---

## Detailed Risk Analysis

### Risk 1: IDE Extensions Bypass Proxy

VS Code extensions and JetBrains plugins make HTTPS requests directly using their runtime's HTTP client. They do not respect `HTTPS_PROXY` environment variables. This means Tier 3 (mitmproxy) cannot capture their API traffic.

**Impact:** No real-time HTTPS capture for IDE-based tools.
**Mitigation:** Tier 1 parsers read the IDE's local log files, which contain the full conversation data. This is actually more complete than proxy capture (includes thinking blocks, tool results, etc.).

### Risk 3: Disk Growth

With keep-forever retention and 5+ active AI tools, disk usage can grow quickly:
- Claude Code alone produces ~560MB of session data
- Ollama traffic logs can grow with frequent local model usage

**Mitigation:**
- Gzip compression at 100MB rotation trigger (~10:1 ratio for JSONL)
- `analyze.py --disk-usage` reports per-source sizes and daily growth rate
- Future: configurable retention policy per source

### Risk 4: Vendor Format Drift

AI tools frequently update and may change their log formats without notice. For example:
- Claude Code could change JSONL event types
- Codex could restructure `response_item` payloads
- Copilot could change response part kinds

**Mitigation:**
- Parsers use tolerant parsing: unknown fields are preserved in `data`, not rejected
- Test fixtures are versioned per source format — when a format changes, add a new fixture version
- Schema validation logs warnings for unknown fields but does not reject events

### Risk 6: Wrapper Shim PATH Ordering

If `~/.local/bin/` is not first in `$PATH`, the wrapper shims won't intercept tool launches. The real binary would be called directly, bypassing proxy env vars.

**Mitigation:**
- Most Linux distributions put `~/.local/bin/` first in `$PATH` by default
- `install.sh` checks PATH ordering and warns if `~/.local/bin/` is not before the real binary
- Doctor check verifies wrapper resolution

### Risk 10: h2-mvstore Version Mismatch

The Copilot JetBrains databases use H2 MVStore format version 3. If the JARs are updated to h2-mvstore 2.4.x (format version 4), the extractor will fail with:

```
org.h2.mvstore.MVStoreException: The file format is not supported
```

**Mitigation:**
- Pin to the exact JARs from the installed Copilot plugin (which match the DB format)
- Install script verifies JAR versions match DB format
- If mismatch detected, warn and skip JetBrains capture (other sources unaffected)

---

## Privacy Considerations

### What ailogd Captures

- Full prompts submitted to AI tools
- Full assistant responses (including code, explanations, plans)
- Full thinking/reasoning blocks
- Tool calls and results (including file contents, terminal output)
- API request/response bodies (including model parameters, system prompts)
- Token usage and timing data
- Session metadata (project paths, git branches, model selections)

### What ailogd Does NOT Capture

- Keystrokes or screen content outside of AI tool interactions
- File system activity unrelated to AI tools
- Network traffic to non-AI domains
- User credentials (auth headers are redacted)

### Recommendations

1. **Do not share `~/logs/` contents** — they contain your code, prompts, and model outputs
2. **Review logs before sharing snippets** for debugging — redact project-specific information
3. **Consider encryption** if the machine is shared or at risk of theft
4. **Audit periodically** — run `analyze.py --disk-usage` to understand what's being stored
