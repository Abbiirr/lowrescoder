# Gateway Complaint Template

Use this format when reporting an LLM-gateway issue to the user. Post it as a fenced block in chat, so the user can scan it and fix without extra questions. Per `feedback_no_gateway_restart.md`, agents never restart the gateway themselves — this template is the hand-off.

---

## Format

```
## Gateway complaint
- Host: <BENCH_HOST> (e.g. http://localhost:4000/v1)
- Alias tested: <alias> (e.g. coding)
- Command (exact, with key redacted):
    curl -sS -X POST <host>/chat/completions \
      -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
      -H 'Content-Type: application/json' \
      --max-time 30 \
      -d '{"model":"<alias>","messages":[{"role":"user","content":"hi"}],"max_tokens":20,"stream":false}'
- Observed: <timeout | error-body | provider error | partial stream | ...>
- Elapsed: <Ns until failure>
- Comparison aliases I already tested:
    - fast: <ok | Ns | error>
    - tools: <ok | Ns | error>
    - default: <ok | Ns | error>
    - <alias>: <result>
- Health endpoint result (curl <host-root>/health/readiness with bearer):
    <paste one-line excerpt>
- Impact: <what user-visible behavior breaks — e.g., autocode chat stuck on simple questions>
- Ask: please check <alias> upstream provider list / rate limit / cache key, then tell me to resume.
- Not done: no gateway restart, no docker start, no provider swap. Waiting.
```

## Rules

1. **Never** run `docker start llm-gateway` or equivalent — the memory says so.
2. Always compare the broken alias against `fast` + `tools` + `default` in the same complaint so the user can see the scope.
3. Always show the exact curl with the key redacted (reference `$LITELLM_MASTER_KEY`, don't paste it).
4. Report the `--max-time` used, so the user knows your patience bound, not the actual provider timeout.
5. Include the health-readiness check result if the complaint is a timeout (so the user knows if the gateway itself is down vs the alias alone).
6. End with an explicit "not done" line listing what you did *not* try, so the user has the full picture.

## Example

```
## Gateway complaint
- Host: http://localhost:4000/v1
- Alias tested: coding
- Command: curl -sS -X POST http://localhost:4000/v1/chat/completions -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' --max-time 45 -d '{"model":"coding","messages":[{"role":"user","content":"hi"}],"max_tokens":20,"stream":false}'
- Observed: operation timed out, 0 bytes received
- Elapsed: 45s (--max-time cap)
- Comparison:
    - fast: ok, ~2s, returned "Hello, how can I assist you today?"
    - tools: ok, ~2s, returned "It's nice to meet you..."
    - default: ok (maps to fast), ~2s
    - thinking: timed out at 15s (expected for reasoning but still concerning)
- Health: `/health/readiness` returned "healthy"
- Impact: `autocode chat` is stuck on every message because ~/.autocode/config.yaml has `model: coding` and the TUI faithfully waits on the first token.
- Ask: please check `coding` upstream provider list (OpenRouter / Cerebras / Groq), then tell me to resume.
- Not done: no gateway restart, no docker start, no provider swap. Waiting.
```

That complaint gets a gateway fix fast because the user has everything they need without follow-up questions.
