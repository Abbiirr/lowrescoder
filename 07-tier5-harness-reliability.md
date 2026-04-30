# Tier 5 — Harness Reliability

**Goal:** address the dominant failure mode of agent harnesses in 2026 — context drift, schema misalignment, and state degradation — with sensors and recovery loops.

**Total cost:** ~3 weeks engineering, ~1400 LOC.

**Why this matters now:** the 2026 research is unambiguous. 65% of enterprise AI agent failures trace back to harness defects, not model defects (MemU/Atlan). Context degrades 2% per step in multi-step workflows. After 5 cycles, less than 60% of original context remains reliably accessible. AutoCode currently has zero sensors for any of this. Every long session is silently degrading and there's no signal.

The Mitchell Hashimoto rule (Feb 2026): *whenever an agent makes a mistake, build the solution that ensures it never makes that specific mistake again.* Tiers 5–8 operationalize that rule. Tier 5 ships the sensor infrastructure.

---

## Tier 5.1 — Drift detectors

### Files touched

- `src/autocode/agent/drift.py` — NEW (~400 LOC)
- `src/autocode/agent/loop.py` — sensor invocation hooks (~50 LOC)
- `src/autocode/agent/tools.py` — wrap tool handlers in drift checks
- `tests/unit/test_drift.py` — NEW

### What this is

A drift detector is a lightweight check that runs *between* agent turns to verify the context the agent is operating against is still accurate. Three classes of detector to ship:

#### Schema drift detector

Tracks the shape of structured tool outputs (file lists, git status, JSON responses). When shape changes between consecutive runs, raises a structured warning that gets injected into the next turn's context.

```python
# src/autocode/agent/drift.py

@dataclass
class SchemaSnapshot:
    """Hash of the structural shape of a tool output."""
    tool_name: str
    args_hash: str
    schema_hash: str  # hash of (sorted keys, types) — not values
    captured_at: datetime
    sample_size: int


class SchemaDriftDetector:
    """Detect when the structural shape of tool outputs changes.

    Stores per-(tool, args) shape fingerprints. When the same call
    returns a different shape, raises a drift warning.
    """

    def __init__(self, *, sensitivity: str = "medium"):
        self._snapshots: dict[tuple[str, str], SchemaSnapshot] = {}
        # sensitivity: "low" → only alert on missing top-level keys
        #              "medium" → also alert on type changes
        #              "high" → also alert on new keys
        self.sensitivity = sensitivity

    def observe(self, tool_name: str, args: dict, result: Any) -> DriftWarning | None:
        args_hash = self._hash_args(args)
        new_shape = self._compute_shape(result)
        new_hash = hashlib.sha256(json.dumps(new_shape, sort_keys=True).encode()).hexdigest()[:16]

        key = (tool_name, args_hash)
        prior = self._snapshots.get(key)

        snapshot = SchemaSnapshot(
            tool_name=tool_name,
            args_hash=args_hash,
            schema_hash=new_hash,
            captured_at=datetime.now(UTC),
            sample_size=1 if prior is None else prior.sample_size + 1,
        )
        self._snapshots[key] = snapshot

        if prior is None or prior.schema_hash == new_hash:
            return None

        # Drift detected
        diff = self._diff_shapes(self._cached_shape(prior), new_shape)
        if not self._meets_sensitivity_threshold(diff):
            return None

        return DriftWarning(
            kind="schema_drift",
            tool_name=tool_name,
            args=args,
            prior_seen_at=prior.captured_at,
            diff=diff,
            severity=self._severity(diff),
            recommendation=(
                f"The shape of {tool_name} results has changed since "
                f"{prior.captured_at.isoformat()}. Verify your assumptions "
                f"about the data structure before proceeding."
            ),
        )

    def _compute_shape(self, value: Any, depth: int = 0, max_depth: int = 3) -> Any:
        """Recursively summarize structure: keys + types, no values."""
        if depth > max_depth:
            return {"__truncated": True}
        if isinstance(value, dict):
            return {k: self._compute_shape(v, depth+1) for k, v in sorted(value.items())}
        if isinstance(value, list):
            if not value:
                return ["__empty"]
            # Sample first 3 to detect mixed types
            return [self._compute_shape(v, depth+1) for v in value[:3]]
        return type(value).__name__
```

#### Context staleness detector

Tracks the age of remembered facts (from MEMORY.md / topic files / earlier turns). When a fact is referenced that's older than the staleness threshold, warns the agent to re-verify.

```python
class ContextStalenessDetector:
    """Detect when agent acts on stale remembered information.

    Watches for tool calls that reference facts the agent could have
    learned in a prior session. If the source of that fact is older
    than the threshold, suggests verification.
    """

    DEFAULT_THRESHOLD = timedelta(days=7)

    def __init__(self, memory_fs: MemoryFS, threshold: timedelta = DEFAULT_THRESHOLD):
        self._memory_fs = memory_fs
        self._threshold = threshold

    def check_fact_freshness(self, fact_topic: str) -> DriftWarning | None:
        """Called when agent tries to use a fact from a topic file."""
        topic_path = self._memory_fs.topics_dir / f"{fact_topic}.md"
        if not topic_path.exists():
            return None
        age = datetime.now(UTC) - datetime.fromtimestamp(topic_path.stat().st_mtime, UTC)
        if age <= self._threshold:
            return None
        return DriftWarning(
            kind="context_staleness",
            fact_source=fact_topic,
            age_days=age.days,
            severity="medium",
            recommendation=(
                f"Topic '{fact_topic}' was last updated {age.days} days ago. "
                "Verify against current code before acting on remembered facts."
            ),
        )
```

#### Tool output inconsistency detector

Compares tool outputs that *should* be deterministic across calls within a turn. If `read_file` returns different content for the same path twice in one turn, something changed underneath the agent.

```python
class ToolConsistencyDetector:
    """Detect when supposedly-deterministic tool calls return different results."""

    DETERMINISTIC_TOOLS = {"read_file", "list_files", "git_status", "list_symbols"}

    def __init__(self):
        self._turn_observations: dict[tuple[str, str], Any] = {}

    def reset_turn(self):
        self._turn_observations.clear()

    def observe(self, tool_name: str, args: dict, result: Any) -> DriftWarning | None:
        if tool_name not in self.DETERMINISTIC_TOOLS:
            return None
        args_hash = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16]
        key = (tool_name, args_hash)

        if key in self._turn_observations:
            prior = self._turn_observations[key]
            if prior != result:
                return DriftWarning(
                    kind="tool_inconsistency",
                    tool_name=tool_name,
                    args=args,
                    severity="high",
                    recommendation=(
                        f"{tool_name} returned different results within the "
                        "same turn. The underlying state may have changed "
                        "(file edited externally, git refresh, etc.)."
                    ),
                )
        self._turn_observations[key] = result
        return None
```

### Wiring into the agent loop

```python
# src/autocode/agent/loop.py

class AgentLoop:
    def __init__(self, ..., drift_detector: DriftDetector | None = None):
        self._drift = drift_detector or DriftDetector()

    async def run(self, ...):
        for iteration in range(self.MAX_ITERATIONS):
            # ... existing turn logic ...

            for tc in response.tool_calls:
                outcome = await self._execute_tool_call(tc)

                # NEW: drift checks after every tool call
                warnings = self._drift.observe(
                    tool_name=tc.name,
                    args=tc.args,
                    result=outcome.result,
                )
                for w in warnings:
                    self._inject_drift_warning(messages, w)
                    self._metrics.drift_incidents.append(w)
```

### Drift warning injection

```python
def _inject_drift_warning(self, messages: list, w: DriftWarning) -> None:
    """Inject drift warning as a system-role message before next turn."""
    messages.append({
        "role": "system",
        "content": (
            f"[Drift detected — {w.kind}, severity {w.severity}]\n"
            f"{w.recommendation}\n"
            f"Diff: {json.dumps(w.diff, indent=2) if w.diff else '(none)'}\n"
            "Acknowledge this warning in your next response and adjust accordingly."
        ),
    })
```

### Telemetry

Each drift detection writes to `~/.autocode/telemetry/drift.jsonl`:

```json
{"ts": "2026-04-30T12:34:56Z", "session_id": "01HXY...", "kind": "schema_drift", "tool_name": "git_status", "severity": "medium"}
```

Aggregate via `autocode telemetry drift --last 7d`:

```
Drift incidents in last 7 days: 23

By kind:
  schema_drift           14
  context_staleness       7
  tool_inconsistency      2

By tool:
  git_status              8
  list_files              5
  read_file               3

Most stale topic files:
  api-patterns.md         32 days old
  legacy-auth.md          18 days old
```

---

## Tier 5.2 — Plan-Execute-Verify (PEV) loop

### Files touched

- `src/autocode/agent/pev.py` — NEW (~350 LOC)
- `src/autocode/agent/loop.py` — PEV wrapping (~60 LOC)
- `src/autocode/agent/prompts.py` — verifier system prompt
- `src/autocode/agent/verification_profiles.py` — already exists; flesh out

### Concept

Rather than a single agent that plans-and-executes-and-checks in one stream, the PEV pattern breaks the work into three distinct phases, each potentially using a different model:

1. **Plan** (high-reasoning model, e.g. Claude Opus 4.7) — produces a structured plan with explicit verification predicates
2. **Execute** (cheap fast model, e.g. qwen3-coder:free) — runs each plan step
3. **Verify** (high-reasoning model again, but with limited context) — checks each step against its predicate before allowing the next

The "Reasoning Sandwich" — expensive cognition at the boundaries, cheap execution in the middle.

### Plan format

```python
@dataclass
class PlanStep:
    id: str
    description: str
    tools_allowed: list[str]      # restrict tool surface for this step
    success_predicate: str         # natural-language assertion
    failure_predicate: str | None  # what counts as failure (optional)
    max_iterations: int = 5


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
    overall_success_criteria: str
    rollback_strategy: str         # "checkpoint", "revert", "abort"
```

### Plan example

```yaml
goal: Fix the OAuth callback bug where state cookie is lost on redirect

steps:
  - id: 1
    description: Read auth/callback.py and auth/state.py to understand current flow
    tools_allowed: [read_file, list_files]
    success_predicate: |
      Agent has produced a 5-sentence summary of the callback flow,
      identifying where state cookie is set and where it might be lost.

  - id: 2
    description: Identify root cause and propose fix
    tools_allowed: [grep_content, search_code]
    success_predicate: |
      Agent has produced a written hypothesis with file/line references.
      Hypothesis must explain WHY state cookie disappears.

  - id: 3
    description: Implement the fix
    tools_allowed: [read_file, edit_file, apply_patch]
    success_predicate: |
      Code change applied. Diff is < 50 lines.
      No edit_file calls modify files outside src/auth/.

  - id: 4
    description: Verify with test
    tools_allowed: [run_command, write_file]
    success_predicate: |
      A test exists that reproduces the original bug and now passes.
      run_command output contains "PASSED" or equivalent green indicator.
      No previously-passing tests fail.

overall_success_criteria: |
  All 4 steps complete. Bug-reproducing test passes. No diff in unrelated files.

rollback_strategy: checkpoint  # restore checkpoint if step 4 fails
```

### Verifier prompt template

```python
VERIFIER_PROMPT = """
You are the Verifier in a Plan-Execute-Verify pipeline. Your only job:
look at the work the Executor just did, and decide if step {step_id}
succeeded.

You have read-only access to a small set of tools to check the result.
Do NOT modify anything.

Step description: {step_description}
Success predicate: {success_predicate}
Failure predicate: {failure_predicate}

Executor's work for this step:
{executor_log}

Files modified (if any):
{modified_files}

Your output MUST be valid JSON matching this shape:

{{
  "verdict": "pass" | "fail" | "uncertain",
  "evidence": "1-3 sentences citing what you checked",
  "next_action": "proceed" | "retry_step" | "rollback" | "abort_plan"
}}

Be strict. If the success predicate isn't clearly met, return "fail".
If you can't verify either way, return "uncertain" and explain why.
"""
```

### PEV runner

```python
class PEVRunner:
    """Execute a Plan via Plan-Execute-Verify with model role separation."""

    def __init__(
        self,
        plan_model: LLMProvider,
        execute_model: LLMProvider,
        verify_model: LLMProvider,
        agent_loop_factory,
    ):
        self.plan_model = plan_model
        self.execute_model = execute_model
        self.verify_model = verify_model
        self.agent_loop_factory = agent_loop_factory

    async def execute_plan(self, plan: Plan, *, on_step_complete=None) -> PlanResult:
        results = []
        for step in plan.steps:
            executor = self.agent_loop_factory(
                model=self.execute_model,
                max_iterations=step.max_iterations,
                tool_allowlist=step.tools_allowed,
            )
            execution = await executor.run(step.description)

            verdict = await self._verify(step, execution)

            if verdict.verdict == "pass":
                results.append(StepResult.success(step, execution, verdict))
            elif verdict.verdict == "fail":
                if verdict.next_action == "retry_step":
                    # One retry with verifier feedback
                    retry_execution = await executor.run(
                        f"{step.description}\n\nPrevious attempt failed because: "
                        f"{verdict.evidence}\nTry again."
                    )
                    retry_verdict = await self._verify(step, retry_execution)
                    if retry_verdict.verdict == "pass":
                        results.append(StepResult.success(step, retry_execution, retry_verdict))
                        continue
                # Either no retry or retry also failed
                if plan.rollback_strategy == "checkpoint":
                    await self._restore_last_checkpoint()
                results.append(StepResult.failure(step, execution, verdict))
                return PlanResult(plan, results, "failed", verdict.evidence)
            else:  # uncertain
                # Escalate to user
                user_decision = await self._ask_user_about_uncertainty(step, verdict)
                if user_decision == "skip":
                    continue
                if user_decision == "abort":
                    return PlanResult(plan, results, "user_aborted", "User aborted at step " + step.id)
                # else proceed

        return PlanResult(plan, results, "succeeded", "")
```

### When to use PEV vs straight-line agent loop

| Use straight-line | Use PEV |
|---|---|
| Single-tool tasks (`read this file`) | Multi-step refactors |
| User said "just do it" | User invoked `/plan` first |
| Trivial fixes (typo, formatting) | Anything touching auth/security/data |
| Conversational responses | Tasks with explicit success criteria |
| < 3 expected tool calls | > 5 expected tool calls |

Auto-detect: if the agent (in straight-line mode) calls `todo_write` with > 3 items, automatically wrap subsequent execution in PEV.

### Cost analysis

PEV adds two extra LLM calls per step (plan creation, per-step verification). For a 4-step plan:
- Without PEV: ~10 LLM calls (planning + execution intertwined)
- With PEV: 1 plan + 4 execute + 4 verify = 9 LLM calls
- But: plan and verify use cheaper models or shorter context, often net cost is the *same*

The win isn't cost — it's reliability. PEV catches errors at step boundaries instead of letting them compound.

---

## Tier 5.3 — Ralph Loop for long-horizon recovery

### Files touched

- `src/autocode/agent/ralph_loop.py` — NEW (~250 LOC)
- `src/autocode/agent/context.py` — recovery hook (~30 LOC)
- `src/autocode/session/intent_store.py` — NEW (~150 LOC)

### Concept (verified from harness research)

The Ralph Loop is a recovery pattern named after the agent's tendency to try to give up when context anxiety hits. The pattern intercepts that giving-up signal, takes a snapshot of original intent, clears the dirty context, and re-injects the intent into a clean context. The agent resumes from a fresh start with full memory of the goal.

This is what enables long-horizon continuity — sessions that survive network crashes, context window saturation, model timeouts, or "I'm exhausted, I'm stopping" moments.

### Implementation

```python
# src/autocode/agent/ralph_loop.py

@dataclass
class Intent:
    """Crystallized statement of what the user wanted, captured at session start."""
    session_id: str
    original_goal: str
    captured_at: datetime
    success_criteria: list[str]
    constraints: list[str]
    progress_so_far: list[str]  # appended each compaction


class IntentStore:
    """SQLite-backed store of original user intent per session.

    Captured once at the START of a session (when the user first speaks)
    and never overwritten — only appended-to.
    """

    def capture(self, session_id: str, user_message: str, agent_loop) -> Intent:
        """First message in a session. Crystallize what the goal is."""
        # Use a high-reasoning model with a focused prompt to extract intent
        intent_text = await agent_loop.summarize(
            "Restate the user's goal in a single paragraph. Identify "
            "explicit success criteria. List any constraints (deadlines, "
            "scope limits, technologies to avoid).",
            user_message,
        )
        # Parse into structured form via JSON output mode
        # ...
        return Intent(...)


class RalphRecoveryDetector:
    """Detect when an agent is about to give up due to context anxiety.

    Triggers:
    - Agent produces text containing 'I'll stop here', 'this is too complex',
      'unable to continue', etc. without a tool call
    - Three consecutive turns with zero progress (no file changes, no new info)
    - Context approaching emergency threshold (90%) with no successful tool calls
    """

    GIVE_UP_PHRASES = [
        "i'll stop here",
        "this is too complex",
        "unable to continue",
        "i don't think i can",
        "let me know if you'd like me to try again",
        "i'm not sure how to proceed",
    ]

    def check(self, agent_state: AgentState) -> bool:
        # Phrase detection
        last_msg = agent_state.last_assistant_message or ""
        if any(p in last_msg.lower() for p in self.GIVE_UP_PHRASES):
            if not agent_state.last_turn_had_tool_calls:
                return True

        # Stagnation detection
        if agent_state.consecutive_zero_progress_turns >= 3:
            return True

        # Approaching context limit
        if (
            agent_state.context_fraction > 0.85
            and agent_state.tool_calls_in_last_3_turns == 0
        ):
            return True

        return False


class RalphLoop:
    def __init__(self, intent_store: IntentStore, agent_loop, detector: RalphRecoveryDetector):
        self._intents = intent_store
        self._agent = agent_loop
        self._detector = detector

    async def maybe_recover(self) -> bool:
        """Check if recovery should fire. Return True if recovery happened."""
        state = self._agent.snapshot_state()
        if not self._detector.check(state):
            return False

        intent = self._intents.get(state.session_id)
        if not intent:
            return False

        await self._recover(intent, state)
        return True

    async def _recover(self, intent: Intent, state: AgentState) -> None:
        """Execute the recovery: clear context, re-inject intent."""
        logger.warning(
            "Ralph Loop firing for session %s — context anxiety detected",
            state.session_id,
        )

        # 1. Snapshot what's been done so far
        progress_summary = await self._summarize_progress(state)
        intent.progress_so_far.append(progress_summary)
        self._intents.update(intent)

        # 2. Aggressive compaction (FullCompact)
        await self._agent.compact_full(keep_messages=2)

        # 3. Re-inject intent as a fresh user message
        recovery_message = (
            f"[Ralph recovery — session resumed after context exhaustion]\n\n"
            f"Original goal: {intent.original_goal}\n\n"
            f"Success criteria:\n"
            + "\n".join(f"- {c}" for c in intent.success_criteria)
            + f"\n\nProgress so far (from prior context, may be stale):\n"
            + "\n".join(f"- {p}" for p in intent.progress_so_far)
            + "\n\nContinue working toward the goal. Verify state before "
              "acting — the previous context was discarded."
        )
        await self._agent.enqueue_user_message(recovery_message)

        # 4. Telemetry
        self._metrics.ralph_recoveries.append({
            "session_id": state.session_id,
            "ts": datetime.now(UTC).isoformat(),
            "trigger": self._detector.last_trigger_reason,
            "context_fraction_at_trigger": state.context_fraction,
        })
```

### Hooking into the agent loop

```python
# src/autocode/agent/loop.py

class AgentLoop:
    async def run(self, ...):
        for iteration in range(self.MAX_ITERATIONS):
            # ... existing turn logic ...

            # NEW: after each turn, check Ralph
            if self._ralph_loop:
                recovered = await self._ralph_loop.maybe_recover()
                if recovered:
                    # Reset iteration counter; the agent has effectively restarted
                    iteration = 0
                    continue
```

### Edge cases

- **Don't fire on first turn:** the agent hasn't "given up" if it's the first response.
- **Don't fire more than 3 times per session:** if Ralph has already fired three times and still no progress, the original goal might be ill-defined. Surface to user.
- **Preserve checkpoints:** even after Ralph fires, the SQLite session_store still has the original messages. They're just not in the LLM context anymore.
- **User can disable:** `AUTOCODE_DISABLE_RALPH=true` for users who prefer the agent fail loudly.

---

## Acceptance tests

```python
async def test_schema_drift_detected_on_column_rename():
    detector = SchemaDriftDetector()
    # First call returns shape A
    detector.observe("query_db", {"q": "SELECT * FROM users"}, [
        {"id": 1, "name": "Alice", "email_certified": "a@x.com"},
    ])
    # Second call same query returns shape B (column renamed)
    warning = detector.observe("query_db", {"q": "SELECT * FROM users"}, [
        {"id": 1, "name": "Alice", "email_verified": "a@x.com"},
    ])
    assert warning is not None
    assert warning.kind == "schema_drift"
    assert "email_certified" in str(warning.diff) or "email_verified" in str(warning.diff)


async def test_pev_aborts_on_unverifiable_step():
    plan = Plan(
        goal="Test plan",
        steps=[
            PlanStep(
                id="1",
                description="Pretend to fix bug",
                tools_allowed=["read_file"],
                success_predicate="A bug-reproducing test exists and passes",
            ),
        ],
        overall_success_criteria="All steps pass",
        rollback_strategy="abort",
    )

    # Mock executor that does nothing useful
    runner = PEVRunner(...)
    result = await runner.execute_plan(plan)
    assert result.status == "failed"


async def test_ralph_recovers_from_context_anxiety():
    # Simulate agent producing "I don't know how to proceed" with zero tool calls
    state = AgentState(
        session_id="test",
        last_assistant_message="I'm not sure how to proceed with this complex change.",
        last_turn_had_tool_calls=False,
        context_fraction=0.7,
    )
    detector = RalphRecoveryDetector()
    assert detector.check(state) is True

    intent_store = InMemoryIntentStore()
    intent_store.capture("test", "Fix the auth bug", mock_agent_loop)

    ralph = RalphLoop(intent_store, mock_agent_loop, detector)
    recovered = await ralph.maybe_recover()
    assert recovered is True
    assert mock_agent_loop.message_queue[-1].startswith("[Ralph recovery")
```

---

## Telemetry summary

After Tier 5 ships, `autocode telemetry summary --last 7d` produces:

```
Sessions: 142     Successful: 121 (85%)
Drift incidents: 23 (16% of sessions)
  schema_drift: 14   context_staleness: 7   tool_inconsistency: 2
PEV invocations: 18 sessions  Plans completed: 14 (78%)
Ralph recoveries: 6 (4.2% of sessions)
  Trigger: give_up_phrase=4  stagnation=2

Top drifty tools:
  git_status     8 incidents
  list_files     5

Top stale topics:
  api-patterns.md  (32 days)
  legacy-auth.md   (18 days)
```

These numbers are the *raw signal* the team needs to know what to fix next. Without them, the team is flying blind on what's actually breaking in production.
