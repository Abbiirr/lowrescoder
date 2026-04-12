# Context Window Management & Auto-Compaction — Deep Research

> Date: 2026-03-29
> Sources: 11 repos in research-components/ (Goose, Pi-mono, Codex, Aider, OpenCode, Claude Code, T3Code, Stripe, Open-SWE)
> Scope: Compaction strategies, token counting, budget allocation, truncation, sliding windows, priority, triggers, prompts, tool results

---

## 1. Compaction Strategies

### Goose (Rust) — Most Sophisticated

**File:** `research-components/goose/crates/goose/src/context_mgmt/mod.rs`

- Default threshold: `DEFAULT_COMPACTION_THRESHOLD = 0.8` (80% of context window)
- Progressive tool response removal with percentages: `[0%, 10%, 20%, 50%, 100%]`
- Middle-out removal strategy (preserves start/end, removes middle)
- Message visibility system: compacted messages marked `agent_only()`, originals marked user-visible but agent-invisible
- Continuation messages inserted after compaction ("don't mention compaction happened")
- Background tool pair summarization in batches of 10

### Pi-mono (TypeScript) — Best Documented

**File:** `research-components/pi-mono/packages/coding-agent/src/core/compaction/compaction.ts`

Thresholds:
```typescript
CompactionSettings {
  enabled: true,
  reserveTokens: 16384,    // reserved for LLM response
  keepRecentTokens: 20000,  // recent context never summarized
}
```

Decision: `contextTokens > contextWindow - reserveTokens`

Split turn handling: if single turn exceeds `keepRecentTokens`, generates two separate summaries.

Cumulative file tracking across multiple compactions:
```typescript
CompactionDetails { readFiles: string[], modifiedFiles: string[] }
```

### OpenAI Codex (Rust) — Two-Stage

**File:** `research-components/openai-codex/codex-rs/core/src/codex.rs`

- Pre-sampling compact (line 5396): before context updates
- Post-turn compact (line 5910): after response, compares `total_usage_tokens > auto_compact_limit`
- Model-specific `auto_compact_token_limit` (per model config)
- Remote compaction endpoint in codex-api crate

### Aider (Python) — Recursive

**File:** `research-components/aider/aider/history.py`

- Recursive summarization: walks backwards to find split points fitting `half_max_tokens`
- Safety buffer: `max_input_tokens - 512`
- Uses `prompts.summarize` constant + `prompts.summary_prefix`

---

## 2. Token Counting

### Goose — Tiktoken with LRU Cache

**File:** `research-components/goose/crates/goose/src/token_counter.rs`

```rust
// Uses tiktoken o200k_base BPE tokenizer
// LRU cache: max 10,000 entries
// Overhead constants:
FUNC_INIT: 7, PROP_INIT: 3, PROP_KEY: 3, ENUM_INIT: -3, ENUM_ITEM: 3, FUNC_END: 12
// Per-message: 4 tokens wrapper
// System prompt: +4 tokens
// Reply primer: +3 tokens
```

### Pi-mono — Heuristic Fallback

```typescript
// Prefers actual usage.totalTokens from API responses
// Fallback: Math.ceil(chars / 4)
// Tracks post-usage message tokens separately
```

### Our Current Approach

```python
# autocode/src/autocode/agent/context.py
def count_tokens(self, text: str) -> int:
    return max(1, len(text) // 4)  # ~4 chars per token
```

**Gap:** No tiktoken, no caching, no overhead constants for tool schemas.

---

## 3. Context Budget Allocation

### Goose — Dynamic Tool Call Cutoff

```rust
fn compute_tool_call_cutoff(context_limit: usize, threshold: f64) -> usize {
    let effective_limit = (context_limit as f64 * threshold) as usize;
    (3 * effective_limit / 20_000).clamp(10, 500)
}
// 128k context @ 0.8 → 15 tool calls before summarization
```

### Pi-mono — Three-Way Budget

```
context_window (128k)
├── reserveTokens (16,384) — for LLM response
├── keepRecentTokens (20,000) — never summarized
└── compactable (91,616) — can be summarized
```

### Our Current Approach

```python
# Flat threshold: 75% of context_length
threshold_tokens = int(budget * self._compaction_threshold)
if total_msg_tokens > threshold_tokens and len(stored_messages) > 4:
    # compact everything except last 3 messages
```

**Gap:** No separate budget for response, recent context, or tool results.

---

## 4. Tool Result Management

### Goose — Progressive Removal + Background Summarization

```rust
// Tool pair summarization prompt:
"Your task is to summarize a tool call & response pair to save tokens.
 Reply with a single message that describes what happened."

// Protects current turn, summarizes older calls in batches of 10
// Background async processing
```

### Codex — Configurable Token Limits

```rust
tool_output_token_limit = Some(100_000)  // per-tool output cap
// Truncation with marker when exceeding
```

### Pi-mono — Character Limit

```typescript
TOOL_RESULT_MAX_CHARS = 2000
// Appends "[... N more characters truncated]"
```

### Our Current Approach

```python
# autocode/src/autocode/agent/context.py
def truncate_tool_result(self, result: str) -> str:
    # Fixed truncation, no progressive removal
```

**Gap:** No progressive removal, no background summarization, no per-tool budgets.

---

## 5. Compaction Prompts

### Pi-mono — Structured Summary Format

```
System: "You are a context summarization assistant. Your task is to read a
conversation between a user and an AI coding assistant, then produce a
structured summary following the exact format specified.

Do NOT continue the conversation. Do NOT respond to any questions.
ONLY output the structured summary."

Format:
- Goal
- Constraints
- Progress
- Key Decisions
- Next Steps
- Critical Context
- File lists (read/modified)
```

### Goose — Template-Based

Uses `compaction.md` template with `{{ messages }}` placeholder via Tera templating.

### Our Current Approach

```python
messages_for_provider = [
    {"role": "system", "content": "Summarize concisely. Preserve key decisions, file paths, action items."},
    {"role": "user", "content": summary_text},
]
```

**Gap:** No structured format, no file tracking, no separation of goal/progress/decisions.

---

## 6. Compaction Triggers

| Framework | Trigger | Threshold | Additional |
|-----------|---------|-----------|------------|
| Goose | Token ratio | 80% of context | Env var configurable |
| Pi-mono | Budget check | `contextTokens > window - reserve` | Per-turn |
| Codex | Token count | Model-specific limit | Pre + post turn |
| Aider | Recursive | `half_max_tokens` | On history overflow |
| AutoCode | Token ratio | 75% of context | Single threshold |

---

## 7. Key Patterns We Should Adopt

### P0: Three-Way Budget Allocation (Pi-mono pattern)

Split context budget into:
1. **Response reserve** (16k tokens) — never consumed by history
2. **Recent context** (20k tokens) — never compacted
3. **Compactable history** (remaining) — summarized when full

### P0: Progressive Tool Result Removal (Goose pattern)

Instead of all-or-nothing compaction:
1. Try with 0% tool removal
2. If still too large: remove 10% of middle tool results
3. Then 20%, 50%, 100%
4. Only then summarize the conversation itself

### P1: Structured Summary Format (Pi-mono pattern)

Replace our generic "summarize concisely" with structured output:
- Goal, Constraints, Progress, Key Decisions, Next Steps
- Cumulative file lists (readFiles, modifiedFiles)

### P1: Background Tool Pair Summarization (Goose pattern)

Summarize old tool call+response pairs in background:
- Batch size: 10 pairs
- Protect current turn
- Replace pair with single summary message

### P2: Tiktoken Token Counting (Goose pattern)

Replace `len(text) // 4` with actual tokenizer:
- Use `tiktoken` for accurate counting
- LRU cache (10k entries) for performance
- Include tool schema overhead in budget

### P2: Message Visibility (Goose pattern)

After compaction:
- Summary: visible to agent only
- Original messages: visible to user only (for history display)
- Insert continuation: "conversation was compacted, don't mention it"

---

## 8. Comparison Matrix

| Feature | Goose | Pi-mono | Codex | Aider | AutoCode |
|---------|-------|---------|-------|-------|----------|
| Compaction threshold | 80% | Dynamic | Model-specific | Recursive | 75% |
| Token counting | tiktoken + cache | char/4 + API | Model config | tiktoken | char/4 |
| Budget allocation | Dynamic cutoff | 3-way split | Model limit | Half-max | Flat |
| Tool result handling | Progressive removal | 2k char limit | 100k token limit | None | Fixed truncation |
| Summary format | Template | Structured | Prompt file | Basic | Basic |
| Background compaction | Yes (async) | No | Yes (remote) | No | No |
| File tracking | No | Yes (cumulative) | No | No | No |
| Message visibility | Agent-only/user-only | Yes | Injection modes | No | No |
| Continuation message | 3 variants | Yes | 2 modes | No | No |
