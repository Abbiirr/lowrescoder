# Post-C7 Telemetry Spec (P1a + P3d Reference)

> **Status:** P1a implemented; P3d eval-gate strictness remains deferred until the eval suite ships.
> **User direction:** "what kind of telemetry make a file on the plan we shall dig in later" (post-commit decision #5).
> **Authoritative phase definition:** `docs/plan/post-c7-stable-commit-roadmap.md` §"P1a — Telemetry Plumbing (Tier 8.1)".
> **Source spec:** `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` §"Tier 8.1 — Telemetry plumbing".

This file is the agreed-on home for telemetry detail. P1a implementation references this spec; P3d eval suite consumes events declared here.

---

## Scope

What gets captured, where it's stored, what schema it follows, how long it's retained, and what privacy guarantees apply.

**Non-goals** (intentionally out of scope at v1):
- Off-machine reporting — all telemetry stays local, never sent anywhere.
- Per-user identity — events tag session/thread/turn IDs only, no PII.
- Real-time streaming dashboards — JSONL files + CLI aggregator only.

---

## Storage

- **Path:** `~/.autocode/telemetry/events-YYYY-MM-DD.jsonl` (daily file rotation)
- **Format:** newline-delimited JSON (one event per line)
- **Append-only.** Daily files immutable after rollover.
- **Backup writer:** background thread + bounded `queue.Queue(maxsize=10_000)`. Queue full → increment `dropped_count`, never block agent loop.
- **`.gitignore`** entry covers `~/.autocode/telemetry/` from any project worktree.

## Privacy switches

- **`AUTOCODE_TELEMETRY_DISABLED=true`** — emission no-op, hot path zero overhead.
- **`autocode telemetry purge`** — deletes all under `~/.autocode/telemetry/`.
- **CI guard:** unit test asserts no network calls from `autocode/src/autocode/telemetry/` modules.
- **README** documents privacy posture.

---

## Event schema (common envelope)

```json
{
  "ts": "2026-04-30T12:34:56.789Z",
  "session_id": "01HXY...",
  "thread_id": "01HXZ...",
  "turn_id": "01HW0...",
  "kind": "tool_call_completed",
  "data": { /* event-specific */ }
}
```

All fields except `data` are required. `session_id` may be `null` for global/init events.

---

## Event kinds (catalog — to be expanded during P1a)

### Session lifecycle

| Kind | When emitted | `data` fields |
|---|---|---|
| `session_start` | New session created | `model`, `provider`, `cwd` |
| `session_end` | Session closed cleanly | `duration_ms`, `turn_count` |
| `session_resumed` | Existing session reopened | `prior_turn_count` |
| `thread_start` | Thread within session begins | `parent_thread_id` (nullable) |
| `thread_fork` | `/fork` invoked | `parent_session_id`, `parent_turn_id` |
| `thread_archive` | Thread archived | (none) |
| `turn_start` | User message begins a turn | `input_chars` |
| `turn_completed` | Turn ends successfully | `duration_ms`, `tools_called`, `usage` (full block from C6.G5 NDJSON shape) |
| `turn_interrupted` | User aborts mid-turn | `reason` |
| `turn_steered` | Mid-turn steer applied | `steer_chars` |

### Tool execution

| Kind | When emitted | `data` fields |
|---|---|---|
| `tool_call_started` | Mutating or expensive tool begins | `tool_name`, `args_hash` |
| `tool_call_completed` | Tool returns success | `tool_name`, `args_hash`, `duration_ms`, `result_bytes` |
| `tool_call_failed` | Tool returns error | `tool_name`, `args_hash`, `error_class` |
| `tool_output_offloaded` | Tier 7.1 scratch threshold hit (P2a) | `tool_name`, `result_bytes`, `scratch_path` |
| `tool_drift_detected` | Tier 5.1 detector fires (P3a) | `tool_name`, `drift_kind` (schema/staleness/inconsistency), `severity` |

### Cost & cache

| Kind | When emitted | `data` fields |
|---|---|---|
| `llm_call_completed` | Every provider response | `provider`, `model`, `prompt_tokens`, `completion_tokens`, `cached_input_tokens`, `cache_creation_tokens`, `reasoning_tokens` |
| `cache_breakpoint_applied` | Tier 1.1 cache_control attached (P2) | `breakpoint_count`, `stable_prefix_bytes` |
| `compaction_event` | Compaction triggered | `path` (A or B), `tokens_before`, `tokens_after`, `duration_ms` |
| `cost_limit_warning` | Configured cap approached | `total_usd`, `limit_usd`, `provider` |

### Approval & permissions

| Kind | When emitted | `data` fields |
|---|---|---|
| `approval_requested` | Tool needs human OK | `tool_name`, `risk_level` |
| `approval_granted` | User says yes | `tool_name`, `decision_ms` |
| `approval_denied` | User says no | `tool_name`, `decision_ms` |
| `permission_escalation` | Sandbox elevated | `from_profile`, `to_profile`, `reason` |

### Reliability events

| Kind | When emitted | `data` fields |
|---|---|---|
| `ralph_recovery_fired` | Tier 5.3 recovery triggers (P3b) | `trigger_kind` (give_up/stagnation/context_saturation), `context_fraction` |
| `entropy_audit_completed` | Tier 7.2 audit run (P3c) | `severity_max`, `incident_count` |
| `pev_step_failed` | Tier 5.2 verifier rejects step (P3b) | `plan_step_id`, `verdict` |

### User actions

| Kind | When emitted | `data` fields |
|---|---|---|
| `slash_command_invoked` | Any `/<cmd>` runs | `command`, `args_present` (bool, no content) |
| `feature_flag_toggled` | Env var or `/flag` sets a flag | `flag_name`, `new_value` |

---

## Retention

- **Daily files:** kept indefinitely on disk; user can `purge` or manually delete
- **In-memory aggregator:** rolling 7-day window for `autocode telemetry summary --last 7d` default
- **No automatic deletion** — disk usage estimates ~5-50 KB/day per active session

---

## CLI surfaces (P1a)

```bash
autocode telemetry summary [--last 7d|30d|all]
autocode telemetry events --kind <name> [--last <window>] [--session <id>]
autocode telemetry session <session_id>
autocode telemetry export [--since <date>] [--format jsonl|csv]
autocode telemetry purge
```

`autocode telemetry summary` output example documented in `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` §"`autocode telemetry summary` output".

---

## Performance budgets

- `emit()` call: < 5 µs (queue put)
- Background writer flush: < 50 ms per batch
- `summary --last 7d` aggregation: < 500 ms over ~50k events
- Background writer thread: < 1% CPU at steady state

---

## Cross-tier dependencies

| Phase | Consumes telemetry kinds | Emits new kinds |
|---|---|---|
| P1a | (foundational; no consumption) | All session/turn/tool/llm/approval/slash kinds |
| P2 | `cache_breakpoint_applied`, `llm_call_completed` (cache fields) | (no new kinds) |
| P2a | (no consumption) | `tool_output_offloaded` |
| P3 | `compaction_event` | (no new kinds) |
| P3a | (no consumption) | `tool_drift_detected` |
| P3b | (no consumption) | `ralph_recovery_fired`, `pev_step_failed` |
| P3c | `tool_drift_detected` (correlation) | `entropy_audit_completed` |
| P3d | All event kinds (eval scoring, drift-derived eval generation) | (no new kinds) |

P3d's drift-derived eval generator (Tier 8.4) groups `tool_drift_detected` events by `(tool_name, drift_kind)` over 30-day windows; ≥3 occurrences proposes a new eval case.

---

## CI gate strictness — DEFERRED until this spec is fleshed

Per User decision #5: telemetry CI gate strictness for P3d is **TBD**. The eval suite (P3d) will:

- **v1 default:** soft gate (warn-only) for first 2 weeks of stability
- **v2:** promote to hard gate (merge-blocking) on baseline drift > 10%

Final strictness will be locked when P1a + P3d are about to ship. Until then, this spec stays in skeleton form.

---

## Resolved P1a decisions

1. **Bytes vs tokens for `result_bytes`:** bytes. Token estimation would require extra model/tokenizer work; bytes is exact and cheap.
2. **`args_hash` algorithm:** SHA-256 over sorted-key compact JSON, truncated to 16 hex chars.
3. **`risk_level` enum for approval events:** P1a emits coarse `"write"` or `"shell"` risk labels from the existing approval path. A richer approval-risk enum remains future tightening.
4. **PII redaction in `tool_call_failed`:** only exception class name is emitted as `error_class`; exception messages are intentionally excluded.
5. **Cross-session aggregation:** P1a aggregates globally across the local telemetry root with date/kind/session filters. Project-scoped aggregation can be added later if needed.

---

## Provenance

- Tier 8.1 source: `docs/plan/roadmaps/2026-04-30-tier-roadmap/10-tier8-observability-evals.md` §"Tier 8.1 — Telemetry plumbing"
- Phase definition: `docs/plan/post-c7-stable-commit-roadmap.md` §"P1a — Telemetry Plumbing"
- Created in response to: `AGENTS_CONVERSATION.MD` Entry 1698 user decision #5
- Cross-tier event consumption: `docs/plan/post-c7-stable-commit-roadmap.md` §"Cross-cutting concerns" → "Telemetry per phase" table
