# Cross-cutting contracts

**Date:** 2026-06-23
**Scope:** the two integration contracts that span plan boundaries and that no
single plan owns. Both are *specifications*: they pin down a shape that several
components already implement independently, so the implementations don't drift.
Neither asks for a refactor — they document the contract the existing code must
keep honouring.

- §1 — **Trajectory schema contract** (PLAN_01 producer ↔ Anvil consumer).
- §2 — **Authorization-barrier spec** (the "untrusted-proposes / trusted-authorizes"
  pattern, reimplemented 3×).

---

## 1. Trajectory schema contract

### Why this exists

Anvil's evaluation flywheel (PLAN_04/05) depends on the runtime emitting
*trajectories*. The Anvil **consumer** parses a `layer_distribution` field;
PLAN_01 (the `harness-ide` runtime, the **producer**) never commits to emitting
it. This is the integration gap that passes every per-component test and fails
the moment the loop runs end-to-end. This section pins the schema on both sides.

### The two sides

| Side | Role | Where | Format |
|---|---|---|---|
| **Producer** | the harness runtime | `autocode/src/autocode/backend/headless_schema.py` (and the equivalent in `harness-ide/`, PLAN_01) | **headless NDJSON** event stream |
| **Consumer** | the Anvil recorder | `autocode/src/autocode/anvil/teacher/recorder.py` → `teacher/schemas.py::Trajectory` | typed `Trajectory` dataclass |

`recorder.from_autocode_ndjson()` parses the producer's NDJSON into a
`Trajectory`; `recorder.from_puku_stream()` does the same for a teacher run
(puku-cli `stream-json`). Both call `Trajectory.compute_layer_distribution()`.

### Producer contract — the NDJSON the runtime MUST emit

The recorder consumes these event types (`backend/headless_schema.py`). To feed
the flywheel, the runtime must emit, per task run:

- **`tool_call_started`** — `{ type, tool_call_id, tool_name, tool_family, args, started_at }`.
  `tool_call_id` MUST be non-empty and unique per call (used for dedupe).
  `tool_family` SHOULD be set; if blank the recorder back-fills it via
  `headless_schema.tool_family(tool_name)`.
- **`tool_call_completed`** — same id; carries the result/observation. The
  recorder digests the observation into `Step.observation_digest`.
- **`turn_completed`** — carries `usage: { input_tokens, output_tokens }`. Token
  totals are spread coarsely across steps.
- *(legacy fallback)* `item_started` with `kind == "tool_execution"` is still
  parsed, but the typed `tool_call_*` events are preferred.

`tool_family` is the contract's load-bearing field: it is what maps a tool call
to an **escalation layer**. The producer's `TOOL_FAMILY_MAP`
(`headless_schema.py:105`) classifies each tool name into a family
(`file_read`, `search`, `lsp`, `git`, `file_write`, `shell`, `planning`,
`subagent`, `user_interaction`, `cache`, or `unknown`).

### Consumer contract — the typed `Trajectory` (`teacher/schemas.py`)

```
Trajectory:
  trajectory_id: str
  task: Task { instruction, repo, commit, source }
  harness_version: str
  model: ModelInfo { alias, provider, is_local }
  steps: list[Step]
  final_diff: str | None
  outcome: Verdict
  cost: { usd, wall_s }
  layer_distribution: { L1, L2, L3, L4 }   # fractions, sum ≈ 1.0
  role: "student" | "teacher"

Step:
  i: int
  layer: "L1" | "L2" | "L3" | "L4"
  action: "retrieve" | "tool_call" | "plan" | "generate" | "escalate"
  tool: str
  args: dict
  observation_digest: str          # "sha256:<first16hex>"
  tokens: { in, out }
  latency_ms: int
  escalated_from: str | None
```

### `layer_distribution` — the shared field

`layer_distribution` is the fraction of steps spent at each escalation layer.
It is **derived** by `Trajectory.compute_layer_distribution()` (`schemas.py:242`)
— per-layer step counts divided by total steps, rounded to 4 dp. It is the basis
for the teacher-vs-student layer contrast (PLAN_05 Channel C) and one of the three
edge-cost guards (`layer_distribution.L4`, with `latency_p50` and
`tokens_per_task`).

The producer never emits `layer_distribution` directly; it falls out of the
**family → layer** mapping the recorder applies to each step:

| tool_family (producer) | layer | action |
|---|---|---|
| `file_read`, `search`, `lsp` | **L2** | retrieve |
| `git` | **L1** | tool_call |
| `file_write` | **L4** | edit |
| `shell`, `subagent`, `user_interaction`, `cache`, `unknown` | **L4** | tool_call |
| `planning` | **L4** | plan |

*(Source: `recorder.py::_AUTOCODE_FAMILY` and `_PUKU_TOOL`.)*

**The contract in one line:** the runtime emits `tool_call_started/completed` with
a correct `tool_family` (or a `tool_name` resolvable by `TOOL_FAMILY_MAP`) plus a
`turn_completed` usage block; the recorder turns those into `Step`s and derives
`layer_distribution`. If the producer changes a tool's family — or adds a tool
that lands in `unknown` — the layer distribution shifts silently, so
`TOOL_FAMILY_MAP` is part of this contract and must be kept in sync on both sides.

---

## 2. Authorization-barrier spec — "untrusted-proposes / trusted-authorizes"

### Why this exists

One pattern is reimplemented **three times across two languages**:

| Implementation | Component | Untrusted proposer | Trusted authorizer | Audit record |
|---|---|---|---|---|
| ClipMind | `video-agent/src/video_agent/compiler/validate.py` | the LLM planner → a typed `ChangeRequest` (`extra="forbid"` schema) | `validate_change_request()` / `validate_or_raise()` → `CompileError` | (render artifact + CR; egress gate is the open gap) |
| Station | `harness-ide/crates/station/src/approver.rs` | the agent's `ApprovalRequest` (tool call) | `StationApprover::request()` → `ApprovalOutcome::Approved/Denied`; maker/checker | `harness-ide` audit log (sha256-chained `AuditEntry`) |
| Anvil | `autocode/src/autocode/anvil/{gate,registry,promote}.py` | a proposed patch bundle | `gate()` (prediction + edge-cost) + `registry` reuse-scope/ToS + gate-component lockout → `GateError`/`RegistryError`/`GateComponentError` | `anvil/audit_log.jsonl` (append-only JSONL, `promote.py:92`) |

No single plan owns the shared model, and they have **already drifted**: ClipMind
has no egress gate, while the station has a full risk-framed approval card for the
same class of action. This spec is the shared reference. It does **not** force a
cross-language shared library (that is not free across Python/Rust) — it specifies
the threat model, approval semantics, and audit-log format the three should match.

### Threat model (shared)

The model / agent / planner is an **untrusted component** (OWASP dual-LLM /
DeepMind CaMeL). It MAY be prompt-injected, may hallucinate, may be steered by
untrusted input embedded in its evidence (OCR text, a file, a web page). It is
allowed to **propose** an action but never to **authorize** one. Authorization is
a deterministic, non-LLM chokepoint that:

1. accepts only a **closed, typed** proposal (no free-form shell/path/command can
   be smuggled — ClipMind's `extra="forbid"` op grammar is the reference);
2. evaluates the proposal against an explicit policy (sensitivity ceiling, reuse
   scope, risk class, gate-component lockout, edge-cost regression, …);
3. **fails closed** — on any error, missing field, or unmet predicate, it denies;
4. records the decision in an append-only audit log before the action runs.

### Approval semantics (shared)

- **Deny-by-default.** Absence of an explicit allow is a deny. (ClipMind's
  cloud-planner egress gap is exactly this rule missing — tracked as Tier-0 0b.)
- **Decision is a closed enum**, not a free-form boolean: `Approved` (optionally
  scoped: once / thread / session / project / policy) or `Denied(reason)`.
  *(Station: `ApprovalOutcome::Approved { .. } | Denied(String)`.)*
- **Scoped claims.** A proposal carries the narrowest claim it needs; the
  authorizer checks the claim is within the policy's allowed space (Anvil reuse
  scope; ClipMind CR sensitivity ≤ source sensitivity, `validate.py:64`).
- **Maker ≠ checker** for high/critical-risk actions (station `requires_checker`;
  a maker may not self-approve).
- **Gate-component lockout.** A proposal that targets the authorizer's own oracle
  (verifier / eval suite / metrics / registry / kill switches) is refused — "the
  single most important rule" (Anvil `assert_not_gate_component`,
  `registry.py:85`).

### Audit-log format (shared)

Every authorization decision is recorded before the action runs, append-only, with
at minimum:

- `timestamp`, `actor` (and `checker` if maker/checker applies),
- `action` / proposal id (Anvil bundle id; station tool name; ClipMind CR id),
- `decision` (`approved` / `denied`) + `reason` (required on deny, and on any
  override),
- `scope` (once / thread / session / project / policy, where applicable),
- the predicates that decided it (Anvil: `met`, `no_regression`,
  `edge_cost_measured`, `no_regression_on`; station: risk class + `requires_checker`),
- a tamper-evident link where the substrate supports it (the `harness-ide` audit
  log is **sha256-chained**, `hash_in`/`hash_out`; Anvil's is plain append-only
  JSONL — a candidate to upgrade to a chained format under this spec).

**The contract in one line:** untrusted proposes a closed typed artifact; a
deterministic authorizer evaluates it against an explicit, deny-by-default policy,
fails closed, and writes an append-only audit line (chained where possible) before
the action runs. The three implementations should each be readable against this
list — where one omits a row (e.g. ClipMind's egress gate, Anvil's chaining), that
omission is a tracked gap, not a silent divergence.

---

## References

- Trajectory: `autocode/src/autocode/anvil/teacher/recorder.py`,
  `teacher/schemas.py`, `backend/headless_schema.py`;
  `harness_copy_teacher/04_ARCHITECTURE.md` §4.2.1,
  `08_EVALUATION_AND_VERIFICATION.md` §8.2.
- Authorization: `video-agent/src/video_agent/compiler/validate.py`;
  `harness-ide/crates/station/src/approver.rs`;
  `autocode/src/autocode/anvil/{gate,registry,promote}.py`;
  `01-trust-domains.md` (ClipMind), `07_SELF_MAINTENANCE_ENGINE.md` §7.2 (Anvil).
