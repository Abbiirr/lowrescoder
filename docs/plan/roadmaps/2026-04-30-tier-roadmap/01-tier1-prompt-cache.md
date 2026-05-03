# Tier 1 — Prompt Cache Plumbing

**Goal:** cut OpenRouter free-tier cost ≥ 40% on any agent run > 2 turns.

**Total cost:** ~3 days engineering, ~210 LOC across 3 files.

**Core insight (from arXiv 2601.06007 "Don't Break the Cache"):** caching only the system prompt while excluding dynamic tool results gives more consistent benefits than naive full-context caching, which can sometimes hurt. The single biggest mistake is putting variable content (timestamps, request IDs, current date) inside the cached prefix — every request invalidates the cache and you pay the 25% cache-write premium for nothing.

---

## Tier 1.1 — Prompt cache breakpoint injection

### Files touched

- `src/autocode/layer4/llm.py` (line 1024+, `OpenRouterProvider`)
- `src/autocode/layer4/llm.py` (line 639+, `OllamaProvider` — no-op for Ollama, but ensure no crash)

### Behavior change

For every chat completion request:
1. Detect whether target model supports prompt caching
2. If yes, attach `cache_control: {"type": "ephemeral", "ttl": "1h"}` to the **last block of the stable prefix** (system prompt + tool definitions)
3. For OpenRouter routing to Anthropic models, also inject `extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}`
4. Read response's `usage.prompt_tokens_details.cached_tokens` and `cache_creation_input_tokens` and `cache_read_input_tokens`; pass to existing `TokenTracker`

### Detection rules

```python
def _supports_explicit_cache(provider: str, model: str) -> bool:
    """Returns True for models supporting explicit cache_control breakpoints."""
    if provider == "anthropic":
        return True  # all current Anthropic models
    if provider == "openrouter":
        # OpenRouter passes cache_control through for Anthropic and Gemini
        return model.startswith("anthropic/") or model.startswith("google/gemini-")
    if provider == "openai":
        return False  # OpenAI uses automatic prefix caching, no cache_control needed
    return False


def _supports_implicit_cache(provider: str, model: str) -> bool:
    """Returns True for providers with automatic prefix caching (no markup needed)."""
    if provider == "openai":
        return True
    if provider == "openrouter":
        return model.startswith("openai/") or model.startswith("deepseek/")
    return False
```

### Implementation skeleton

```python
# In OpenRouterProvider.chat_completion (around line 1024)

async def chat_completion(self, messages, tools=None, **kwargs):
    extra_headers = kwargs.get("extra_headers", {})
    extra_body = kwargs.get("extra_body", {})

    if _supports_explicit_cache(self.provider_name, self.model):
        # 1. Inject anthropic-beta header for OpenRouter→Anthropic
        if self.provider_name == "openrouter" and self.model.startswith("anthropic/"):
            extra_headers["anthropic-beta"] = "prompt-caching-2024-07-31"

        # 2. Mark the LAST block of system prompt with cache_control
        messages = self._inject_cache_breakpoint(messages)

    response = await self._client.chat.completions.create(
        model=self.model,
        messages=messages,
        tools=tools,
        extra_headers=extra_headers,
        extra_body=extra_body,
        **kwargs,
    )

    # 3. Capture cache metrics
    self._capture_cache_usage(response)

    return self._build_response(response)


def _inject_cache_breakpoint(self, messages: list[dict]) -> list[dict]:
    """Mark the last block of the stable prefix with cache_control.

    The 'stable prefix' is the system message PLUS all assistant/user
    messages BEFORE the dynamic boundary marker (see Tier 1.2).
    """
    if not messages:
        return messages

    BOUNDARY_MARKER = "# === DANGEROUS_uncachedSystemPromptSection_BELOW ==="

    # Find the system message
    system_msg = next((m for m in messages if m["role"] == "system"), None)
    if not system_msg:
        return messages

    content = system_msg["content"]

    # Split system message at the boundary
    if BOUNDARY_MARKER in content:
        stable, dynamic = content.split(BOUNDARY_MARKER, 1)
        # Convert system message to multipart content
        system_msg["content"] = [
            {
                "type": "text",
                "text": stable,
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            },
            {
                "type": "text",
                "text": dynamic,
            },
        ]
    else:
        # No boundary marker — cache the entire system message (less optimal)
        system_msg["content"] = [
            {
                "type": "text",
                "text": content,
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            },
        ]

    return messages


def _capture_cache_usage(self, response) -> None:
    """Extract cache hit/miss tokens from response and pass to tracker."""
    usage = getattr(response, "usage", None)
    if not usage:
        return

    # Anthropic-direct format
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0

    # OpenRouter / OpenAI-style nested format
    details = getattr(usage, "prompt_tokens_details", None)
    if details:
        cache_read = max(cache_read, getattr(details, "cached_tokens", 0) or 0)

    if self._token_tracker:
        self._token_tracker.record_cache(
            provider=self.provider_name,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
        )
```

### Edge cases

- **First call to a fresh prefix:** `cache_creation_input_tokens > 0`, `cache_read_input_tokens == 0`. This is the 25% premium; budget for it.
- **Cache hit:** `cache_read_input_tokens > 0`, charged at 10% of base price (Anthropic) or 50% (OpenAI).
- **TTL expiry:** silent — next call after 5 min (or 1 h with extended TTL) will be a cache write again.
- **Multi-block messages:** explicit cache breakpoints have a hard limit of **4 per request**. Reserve them: system, tool defs, RulesLoader output, optional CLAUDE.md.
- **Workspace isolation (Anthropic, since Feb 5 2026):** caches are per-workspace, not per-org. If you switch workspaces (different API key), expect a cold cache.
- **Provider sticky routing:** OpenRouter automatically routes subsequent requests to the same provider once it sees a cache hit. Don't manually override `provider.order` — that disables sticky routing.

### Acceptance test

```python
# tests/integration/test_prompt_cache.py
async def test_cache_hit_on_repeat_call():
    # Use a 1500+ token system prompt to clear the 1024 minimum
    long_prompt = "You are a helpful assistant. " * 100  # ~3000 chars

    # First call — write
    r1 = await provider.chat_completion(
        messages=[
            {"role": "system", "content": long_prompt},
            {"role": "user", "content": "Hi"},
        ]
    )
    cache_write_1 = r1.usage.cache_creation_input_tokens or 0
    cache_read_1 = r1.usage.cache_read_input_tokens or 0
    assert cache_write_1 > 0
    assert cache_read_1 == 0

    # Second call within 5 min — read
    r2 = await provider.chat_completion(
        messages=[
            {"role": "system", "content": long_prompt},
            {"role": "user", "content": "What's 2+2?"},
        ]
    )
    cache_read_2 = r2.usage.cache_read_input_tokens or 0
    assert cache_read_2 >= 1024  # at least the system prompt block
```

### Risk & mitigation

| Risk | Mitigation |
|---|---|
| Provider rejects cache_control because model doesn't support it | Wrap call in try/except, fall back to non-cached request |
| Cache_control causes silent provider switch on OpenRouter (anthropic-only) | Log the actual provider returned in `response.provider` field |
| Tool definitions change between turns and bust cache | Keep tool definitions sorted alphabetically and serialized identically — see Tier 1.2 |
| User has no CLAUDE.md → tool defs change at runtime | Tier 1.2 handles this via stable boundary |

---

## Tier 1.2 — Stable / dynamic prompt boundary

### File touched

- `src/autocode/agent/prompts.py` (currently 193 lines, will grow to ~270)

### What changes

The current `SYSTEM_PROMPT` is a single concatenated string. Refactor so the system prompt is **assembled from parts**, with a literal sentinel separating cacheable from per-request content.

### New structure

```python
# src/autocode/agent/prompts.py

CACHE_BOUNDARY_MARKER = "# === DANGEROUS_uncachedSystemPromptSection_BELOW ==="


# --- STABLE PREFIX (cacheable, identical across turns within a session) ---

STABLE_INSTRUCTIONS = (
    "You are AutoCode, an AI coding assistant running locally "
    "on the user's machine.\n\n"
    "You help with software development tasks: writing code, debugging, "
    "explaining code, refactoring, and answering questions about codebases.\n\n"
    # ... rest of current SYSTEM_PROMPT body ...
)


def build_stable_prefix(
    *,
    tool_definitions_json: str,
    rules_text: str | None,
    skill_catalog_index: str | None,
) -> str:
    """Assemble the cacheable portion of the system prompt.

    EVERYTHING here MUST be deterministic — no timestamps, no random
    IDs, no current date. If it changes between turns, the cache breaks.
    """
    parts = [STABLE_INSTRUCTIONS]

    if tool_definitions_json:
        parts.append("## Available tools\n\n" + tool_definitions_json)

    if rules_text:
        parts.append("## Project rules (CLAUDE.md / AGENTS.md)\n\n" + rules_text)

    if skill_catalog_index:
        parts.append("## Skills available\n\n" + skill_catalog_index)

    return "\n\n".join(parts)


# --- DYNAMIC TAIL (per-request, must NOT be cached) ---

def build_dynamic_tail(
    *,
    cwd: str,
    git_status_summary: str | None,
    current_iso_date: str,
    current_todo_state: str | None,
    open_tasks_summary: str | None,
) -> str:
    """Assemble the per-request portion. Re-built on every turn."""
    parts = [f"## Current context\n\nWorking directory: {cwd}",
             f"Date: {current_iso_date}"]

    if git_status_summary:
        parts.append("## Git status\n\n" + git_status_summary)

    if current_todo_state:
        parts.append("## Current plan / todos\n\n" + current_todo_state)

    if open_tasks_summary:
        parts.append("## Open tasks\n\n" + open_tasks_summary)

    return "\n\n".join(parts)


# --- ASSEMBLY ---

def assemble_system_prompt(
    *,
    tool_definitions_json: str,
    rules_text: str | None = None,
    skill_catalog_index: str | None = None,
    cwd: str,
    git_status_summary: str | None = None,
    current_iso_date: str,
    current_todo_state: str | None = None,
    open_tasks_summary: str | None = None,
) -> str:
    """Build the full system prompt with cache boundary marker.

    Returns a single string with CACHE_BOUNDARY_MARKER between
    the stable prefix and the dynamic tail. The LLM provider layer
    splits at this marker to apply cache_control to the prefix only.
    """
    stable = build_stable_prefix(
        tool_definitions_json=tool_definitions_json,
        rules_text=rules_text,
        skill_catalog_index=skill_catalog_index,
    )

    dynamic = build_dynamic_tail(
        cwd=cwd,
        git_status_summary=git_status_summary,
        current_iso_date=current_iso_date,
        current_todo_state=current_todo_state,
        open_tasks_summary=open_tasks_summary,
    )

    return f"{stable}\n\n{CACHE_BOUNDARY_MARKER}\n\n{dynamic}"
```

### What goes where — definitive table

| Content | Stable prefix | Dynamic tail | Why |
|---|---|---|---|
| Core instructions (the current SYSTEM_PROMPT body) | ✅ | | Identical every turn |
| Tool definitions JSON | ✅ | | Stable for a session unless tools change |
| RulesLoader output (CLAUDE.md, AGENTS.md, .rules/*.md) | ✅ | | Stable per session |
| SkillCatalog frontmatter index | ✅ | | Stable per session |
| Current working directory | | ✅ | Can change with cd |
| Current ISO date | | ✅ | Changes constantly |
| Git status summary | | ✅ | Changes per file save |
| Current todo / plan state | | ✅ | Changes every iteration |
| Open tasks summary | | ✅ | Changes per task |
| Recent tool call results | | ✅ (in messages, not system) | Always fresh |

### Tool definitions stability rule

Tool definitions get serialized to JSON and embedded in the stable prefix. **They must serialize identically every turn** or the cache breaks. Enforce this:

```python
def serialize_tool_defs_stable(tools: list[ToolDefinition]) -> str:
    """Deterministic JSON serialization of tool definitions for caching."""
    sorted_tools = sorted(tools, key=lambda t: t.name)
    return json.dumps(
        [t.to_openai_schema() for t in sorted_tools],
        sort_keys=True,
        separators=(",", ":"),  # no whitespace variability
    )
```

### Test that nothing dynamic leaks above the boundary

```python
# tests/unit/test_prompt_cache_boundary.py
def test_no_dynamic_content_above_boundary():
    prompt = assemble_system_prompt(
        tool_definitions_json="<dummy>",
        rules_text="some rules",
        cwd="/home/user/proj",
        current_iso_date="2026-04-30T12:00:00Z",
        current_todo_state="[ ] do thing",
    )

    stable, dynamic = prompt.split(CACHE_BOUNDARY_MARKER, 1)

    # Stable must NOT contain any time/date/path strings
    forbidden_in_stable = [
        "2026", "T12:00", "/home/user/proj", "do thing",
        "Date:", "Working directory:",
    ]
    for token in forbidden_in_stable:
        assert token not in stable, f"Dynamic content '{token}' leaked into cached prefix"

    # Dynamic must contain them
    assert "2026" in dynamic
    assert "/home/user/proj" in dynamic
    assert "do thing" in dynamic
```

### Migration from current SYSTEM_PROMPT

The current code does this somewhere (in `loop.py` or `context.py`):

```python
system_prompt = SYSTEM_PROMPT  # single string
```

Replace with:

```python
from datetime import datetime, UTC
from autocode.agent.prompts import assemble_system_prompt, serialize_tool_defs_stable

system_prompt = assemble_system_prompt(
    tool_definitions_json=serialize_tool_defs_stable(self.tool_registry.get_all()),
    rules_text=self._rules_text,  # already loaded by RulesLoader
    skill_catalog_index=self._skill_index,  # already exists
    cwd=str(self.cwd),
    git_status_summary=await self._summarize_git_status(),
    current_iso_date=datetime.now(UTC).isoformat(),
    current_todo_state=self._render_todos(),
    open_tasks_summary=self._task_summary(),
)
```

---

## Tier 1.3 — Reasoning-token usage capture and reporting

### Files touched

- `src/autocode/agent/token_tracker.py` (currently 138 lines, +40)
- `src/autocode/tui/commands.py` (the `/cost` handler — already exists)
- `src/autocode/backend/server.py` (cost_update notification — already exists)
- `rtui/src/render/view.rs` (status bar token display)

### What changes

`TokenUsage` dataclass currently has `prompt_tokens`, `completion_tokens`, `cached_input_tokens`. Add:

```python
@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_input_tokens: int = 0       # already exists — read tokens
    cache_creation_tokens: int = 0     # NEW — write tokens (25% premium)
    reasoning_tokens: int = 0          # NEW — for thinking models

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def billable_input_cost_factor(self) -> float:
        """Effective input cost factor accounting for cache.

        Cache reads cost 0.10x, cache writes cost 1.25x, regular 1.0x.
        Returns weighted average of input price multiplier.
        """
        non_cached = self.prompt_tokens - self.cached_input_tokens - self.cache_creation_tokens
        if self.prompt_tokens == 0:
            return 1.0
        weighted = (
            non_cached * 1.0
            + self.cached_input_tokens * 0.10
            + self.cache_creation_tokens * 1.25
        )
        return weighted / self.prompt_tokens
```

### Tracker method to record cache events

```python
def record_cache(
    self,
    *,
    provider: str,
    cache_read_tokens: int,
    cache_write_tokens: int,
) -> None:
    """Record cache hit/miss tokens from a single API call."""
    self._totals.cached_input_tokens += cache_read_tokens
    self._totals.cache_creation_tokens += cache_write_tokens

    per_provider = self._per_provider.setdefault(provider, TokenUsage())
    per_provider.cached_input_tokens += cache_read_tokens
    per_provider.cache_creation_tokens += cache_write_tokens
```

### `/cost` slash command upgrade

Current `/cost` shows messages, estimated tokens, characters. Add cache breakdown:

```
**Session Usage:**
- Messages: 47 (12 user, 28 assistant, 7 tool)
- Total tokens: 84,231 (61,420 input / 22,811 output)
- Cache reads:   42,108 tokens  (saved ≈ 75% on input)
- Cache writes:  3,210 tokens   (one-time write premium paid)
- Reasoning:     1,847 tokens   (Claude 4.7 thinking)
- Provider: openrouter / anthropic/claude-opus-4-7
- Effective cost multiplier: 0.31x  (vs no caching)
```

### Status bar display in Rust TUI

Current status bar: `model · provider · mode · 1.2k tokens`

Add cache hit indicator:

```
qwen3-coder:free · openrouter · auto · 1.2k tokens · ⚡73% cached
```

The `⚡73%` is `cached_input_tokens / prompt_tokens * 100`. Only show when > 0.

### Persistence

`TokenTracker` is currently per-session in memory. To match Codex's resumed-thread token replay (#18023), persist to SQLite when session is paused:

```sql
-- Add to schema
CREATE TABLE IF NOT EXISTS session_token_usage (
    session_id TEXT PRIMARY KEY,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    per_provider_json TEXT,  -- JSON dict
    updated_at TEXT NOT NULL
);
```

On `session_resume`: read row, hydrate `TokenTracker`. On `session_pause` / new turn: write row.

### Acceptance test

```python
async def test_cost_command_shows_cache_breakdown():
    # Run a session that does 3 turns with same long system prompt
    # First turn: cache write
    # Turns 2-3: cache reads
    # Then run /cost
    output = await router.dispatch("/cost")
    assert "Cache reads:" in output
    assert "Cache writes:" in output
    assert "Effective cost multiplier:" in output
    # Multiplier should be < 1.0 (caching helped)
    assert "0." in output and "x" in output
```
