# Test Plan

17 tests covering all features across all phases.

---

## Test Matrix

| # | Test | Phase | Validates |
|---|------|-------|-----------|
| 1 | Parser fixture tests | P1 | Each parser's format handling — known JSONL snippets → normalized output |
| 2 | Claude historical replay | P1 | Claude backfill including thinking + tool_use + tool_result |
| 3 | Codex session replay | P1 | function_call/reasoning extraction + token_count |
| 4 | OpenCode DB query | P1 | session/message/part extraction with `time_created` checkpoint |
| 5 | Copilot VS Code parse | P1 | Full Copilot parser — `kind:0` requests[], `kind:2` toolInvocationSerialized + thinking |
| 6 | Copilot JetBrains extract | P1 | Java subprocess + entity deserialization via NitriteExtractor |
| 7 | Claude hook normalization | P2 | Schema compliance — `UserPromptSubmit`→`user_prompt`, `PreToolUse`→`tool_call`, etc. |
| 8 | Claude hook latency | P2 | Hook performance — time 100 invocations → median < 100ms |
| 9 | Ollama proxy e2e | P3 | Ollama capture — `curl` through proxy → `traffic.jsonl` has full payload |
| 10 | mitmproxy domain filter | P4 | HTTPS capture — filtered + non-filtered requests → only filtered logged |
| 11 | Header redaction | P4 | Privacy — Authorization/x-api-key → `[REDACTED]` in api-traffic only |
| 12 | Daemon restart + dedup | All | Reliability — stop, restart → no duplicate events per source type |
| 13 | DB checkpoint recovery | P1 | OpenCode — restart after inserts → no duplicates, no missed rows |
| 14 | Nitrite checkpoint | P1 | JetBrains — restart after session → no duplicates |
| 15 | Unified schema validation | All | Contract — validate every event in unified.jsonl against ailogd.v1 |
| 16 | Wrapper shim validation | P3/P4 | P3/P4 universality — `~/.local/bin/claude` sets proxy and delegates to real binary |
| 17 | Rotation + gzip | All | Retention — write >100MB → segment rotated and compressed |

---

## Test Details

### Test 1: Parser Fixture Tests

**Location:** `tests/test_parsers.py`

For each parser, provide a fixture file with known JSONL content and verify normalized output:

```python
def test_claude_code_parser_user_prompt():
    fixture = '{"type":"user","message":{"role":"user","content":"hello"},"sessionId":"s1","cwd":"/tmp","timestamp":"2026-01-15T10:00:00Z"}'
    events = claude_code_parser.parse_line(json.loads(fixture))
    assert len(events) == 1
    assert events[0].event == "user_prompt"
    assert events[0].session_id == "s1"
    assert events[0].data["prompt"] == "hello"

def test_claude_code_parser_assistant_with_tool():
    fixture = '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","name":"Bash","input":{"command":"ls"},"id":"t1"},{"type":"tool_result","tool_use_id":"t1","content":"file.txt"}]}}'
    events = claude_code_parser.parse_line(json.loads(fixture))
    assert len(events) == 2
    assert events[0].event == "tool_call"
    assert events[0].tool_name == "Bash"
    assert events[1].event == "tool_result"
```

Fixtures stored in `tests/fixtures/` — one sample file per source format.

### Test 2: Claude Historical Replay

Parse real `~/.claude/projects/` directory. Verify:
- All events have `schema_version: "ailogd.v1"`
- `thinking` blocks produce `reasoning_exposed` events
- `tool_use` blocks produce `tool_call` events with correct `tool_name`
- `tool_result` blocks produce `tool_result` events with matching `tool_use_id`
- Session IDs are consistent within a file

### Test 3: Codex Session Replay

Parse real `~/.codex/sessions/` directory. Verify:
- `function_call` events are paired with `function_call_output`
- `reasoning` events contain thinking text
- `token_count` events have valid `total_usage_tokens` > 0
- `session_meta` produces a `session_start` event with `cwd`

### Test 4: OpenCode DB Query

Read real `~/.local/share/opencode/opencode.db`. Verify:
- Messages are extracted with correct roles
- Parts are joined to messages
- `time_created` checkpoint prevents re-reading old rows
- `tool` parts produce both `tool_call` and `tool_result`
- `step-finish` parts produce `token_usage` with token counts

### Test 5: Copilot VS Code Parse

Parse real workspace JSONL files. Verify:
- `kind:0` session state is correctly read
- `thinking` response parts → `reasoning_exposed`
- `toolInvocationSerialized` → `tool_call` + `tool_result` (when `isComplete: true`)
- Model family extracted from `inputState.selectedModel.metadata.family`
- `inlineReference`, `reference`, `undoStop` are skipped

### Test 6: Copilot JetBrains Extract

Run `NitriteExtractor` on real DB. Verify:
- Output is valid JSONL
- Each line has `_collection` field
- `NtTurn` documents have `request` and `response` fields
- `NtChatSession` documents have `id`, `name`, `createdAt`

### Test 7: Claude Hook Normalization

Feed sample hook payloads through the hook script. Verify:
- Each hook event maps to the correct `ailogd.v1` event
- `SubagentStart` → `session_start` with `data.is_subagent: true`
- `PostToolUseFailure` → `error`
- All events have required schema fields

### Test 8: Claude Hook Latency

Time 100 hook invocations:
```bash
for i in $(seq 100); do
    echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"ls"}}' | \
    time ~/.local/bin/ailogd-hook
done
```
Assert: median < 100ms, p99 < 200ms.

### Test 9: Ollama Proxy E2E

1. Start proxy on `localhost:11435`
2. `curl -X POST http://localhost:11435/api/chat -d '{"model":"test","messages":[{"role":"user","content":"hi"}]}'`
3. Verify `~/logs/ollama/traffic.jsonl` contains the request + response

### Test 10: mitmproxy Domain Filter

1. Start mitmproxy addon
2. Send request to `api.anthropic.com` (should be logged)
3. Send request to `example.com` (should NOT be logged)
4. Verify only the Anthropic request appears in `~/logs/api-traffic/https.jsonl`

### Test 11: Header Redaction

1. Send request with `Authorization: Bearer sk-xxx` header through mitmproxy
2. Verify `~/logs/api-traffic/https.jsonl` shows `Authorization: [REDACTED]`
3. Verify request body is NOT redacted (preserved raw)

### Test 12: Daemon Restart + Dedup

1. Run daemon, let it process some events
2. Stop daemon
3. Restart daemon
4. Verify no duplicate events in any sink file
5. Check per-source: JSONL files (inode+offset), SQLite (time_created), Nitrite (modifiedAt)

### Test 13: DB Checkpoint Recovery (OpenCode)

1. Record OpenCode checkpoint (max time_created)
2. Insert new messages into OpenCode (via tool usage)
3. Restart daemon
4. Verify new messages are captured, old ones not duplicated

### Test 14: Nitrite Checkpoint

1. Record JetBrains checkpoint (max modifiedAt)
2. Use Copilot in JetBrains (creates new turns)
3. Restart daemon
4. Verify new turns captured, old ones not duplicated

### Test 15: Unified Schema Validation

Read every event in `~/logs/unified.jsonl` and validate:
- `schema_version` is `"ailogd.v1"`
- `ts` is valid ISO 8601
- `source` is one of the defined source enums
- `event` is one of the defined event enums
- `event_id` is a valid UUID
- `capture_mode` is one of the defined capture modes

### Test 16: Wrapper Shim Validation

1. Run `~/.local/bin/claude --version` (or similar non-destructive command)
2. Verify `HTTPS_PROXY` and `OLLAMA_HOST` are set in the subprocess environment
3. Verify the real Claude binary is executed (correct version output)

### Test 17: Rotation + Gzip

1. Write > 100MB to a test JSONL file
2. Trigger rotation worker
3. Verify original file is rotated to `<name>.<timestamp>.jsonl.gz`
4. Verify new empty JSONL file is created
5. Verify gzipped file is valid and contains original content
