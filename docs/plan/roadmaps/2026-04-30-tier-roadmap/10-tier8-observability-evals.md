# Tier 8 — Observability and Evals

**Goal:** make AutoCode's behavior measurable, regressions catchable, and improvements provable.

**Total cost:** ~2 weeks engineering, ~700 LOC + ongoing eval-writing discipline.

**Why this is last:** evals only catch what they were designed to catch, and you don't know your failure modes until you've run in production for a while. Tier 5 (drift detectors) and Tier 7 (entropy audits) generate the raw signal. Tier 8 turns that signal into a regression suite.

The cycle this tier closes: a user reports a bug → you find the failure mode → you write an eval that reproduces it → the eval runs in CI → that bug never returns. This is Mitchell Hashimoto's harness rule operationalized.

---

## Tier 8.1 — Telemetry plumbing

### Files touched

- `src/autocode/telemetry/store.py` — NEW (~200 LOC)
- `src/autocode/telemetry/aggregator.py` — NEW (~150 LOC)
- `src/autocode/cli.py` — `autocode telemetry` subcommands (~100 LOC)
- `src/autocode/agent/loop.py` — emit events (~50 LOC scattered)

### Event schema

Single append-only JSONL store under `~/.autocode/telemetry/events.jsonl`. Each event:

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

### Event kinds

```python
# src/autocode/telemetry/store.py

EVENT_KINDS = {
    # Session lifecycle
    "session_start", "session_end", "session_resumed",
    "thread_start", "thread_fork", "thread_archive",
    "turn_start", "turn_completed", "turn_interrupted", "turn_steered",
    
    # Tool execution
    "tool_call_started", "tool_call_completed", "tool_call_failed",
    "tool_output_offloaded",   # Tier 7.1
    "tool_drift_detected",     # Tier 5.1
    
    # Cost & cache
    "llm_call_completed",      # tokens in/out, cache hit/miss
    "cache_breakpoint_applied", # Tier 1.1
    "compaction_event",        # path A or B, tokens before/after
    
    # Approval & permissions
    "approval_requested", "approval_granted", "approval_denied",
    "permission_escalation",
    
    # Reliability events
    "ralph_recovery_fired",    # Tier 5.3
    "entropy_audit_completed", # Tier 7.2
    "pev_step_failed",         # Tier 5.2
    
    # User actions
    "slash_command_invoked",
    "feature_flag_toggled",
}
```

### Implementation

```python
# src/autocode/telemetry/store.py

from datetime import datetime, UTC
from pathlib import Path
import json
import queue
import threading

class TelemetryStore:
    """Append-only JSONL event log with background flush."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or (Path.home() / ".autocode" / "telemetry")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=10_000)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._thread.start()
        self._enabled = True

    def emit(
        self,
        kind: str,
        *,
        session_id: str | None = None,
        thread_id: str | None = None,
        turn_id: str | None = None,
        **data,
    ) -> None:
        if not self._enabled or kind not in EVENT_KINDS:
            return
        evt = {
            "ts": datetime.now(UTC).isoformat(),
            "session_id": session_id,
            "thread_id": thread_id,
            "turn_id": turn_id,
            "kind": kind,
            "data": data,
        }
        try:
            self._queue.put_nowait(evt)
        except queue.Full:
            # Drop event under back-pressure; log to stderr
            pass

    def disable(self) -> None:
        self._enabled = False

    def shutdown(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5.0)

    def _writer_loop(self):
        # Daily file rotation: events-2026-04-30.jsonl
        current_date = None
        current_path = None
        current_fp = None
        while not self._stop.is_set():
            try:
                evt = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            today = datetime.now(UTC).date().isoformat()
            if today != current_date:
                if current_fp:
                    current_fp.close()
                current_date = today
                current_path = self.base_dir / f"events-{today}.jsonl"
                current_fp = current_path.open("a", encoding="utf-8")
            current_fp.write(json.dumps(evt) + "\n")
            current_fp.flush()
```

### CLI

```bash
# Show summary for last 7 days
autocode telemetry summary --last 7d

# Drill into a specific kind
autocode telemetry events --kind ralph_recovery_fired --last 30d

# Per-session breakdown
autocode telemetry session 01HXY... 

# Export as CSV for spreadsheet analysis
autocode telemetry export --since 2026-04-01 --format csv > events.csv

# Clear all telemetry (privacy)
autocode telemetry purge
```

### `autocode telemetry summary` output

```
AutoCode Telemetry Summary — last 7 days
═══════════════════════════════════════════

Sessions:                  142
  successful:              121 (85.2%)
  user_aborted:              8 (5.6%)
  errored:                  13 (9.2%)

Turns:                     1,847
  avg per session:           13.0
  avg duration:              42 sec

Tools (top 5):
  read_file               2,431  (avg 0.4s)
  edit_file                 891  (avg 0.7s)
  run_command               412  (avg 8.2s)
  todo_write                273
  search_code               198

LLM cost:
  total tokens:        4,212,847
  cache reads:         2,891,243  (68.6% hit ratio)
  cache writes:           87,432  (2.1% of input)
  effective cost:           ≈ $3.42 (vs $11.30 without caching)

Reliability events:
  drift_detected:           23  (16.2% of sessions)
    schema_drift:           14
    context_staleness:       7
    tool_inconsistency:      2
  ralph_recovery_fired:      6  (4.2% of sessions)
  pev_step_failed:           4  (33.3% of PEV plans)
  entropy_audit_high:        2

Top failure correlates:
  Sessions with web_fetch  → 23% drift incidents
  Sessions > 50 turns       → 41% require Ralph recovery
  Sessions with apply_patch → 8% rollback rate

Slash commands (top 5):
  /diff                     94
  /undo                     38
  /cost                     27
  /compact                  18
  /memory                   14
```

### Privacy

- Telemetry is **local only**. Never sent off-machine.
- README says so prominently. Repo CI tests no network call from telemetry path.
- `~/.autocode/telemetry/` is in `.gitignore` everywhere.
- `autocode telemetry purge` deletes everything.
- `AUTOCODE_TELEMETRY_DISABLED=true` skips emission entirely.

---

## Tier 8.2 — Eval suite

### Files touched

- `evals/` directory at repo root — NEW
- `evals/cases/` — individual eval cases as YAML
- `evals/runner.py` — eval execution engine (~300 LOC)
- `evals/judge.py` — LLM-as-judge for non-deterministic outputs (~150 LOC)
- `.github/workflows/evals.yml` or equivalent CI config — gating rule

### Anatomy of an eval case

```yaml
# evals/cases/auth-bug-fix.yaml

id: auth-bug-fix-001
name: "Fix OAuth callback state cookie loss"
provenance:
  source: bug_report
  bug_id: 2026-04-15-001
  recorded_at: 2026-04-15T14:32:00Z

setup:
  fixture_repo: fixtures/oauth-bug-repo/
  initial_files:
    - src/auth/callback.py
    - src/auth/state.py
    - tests/auth/test_callback.py
  
input:
  user_message: |
    The OAuth login flow is broken. Users get redirected back to login
    after authenticating. State cookie seems to disappear.

expected_outcomes:
  must_have:
    - "agent reads src/auth/callback.py"
    - "agent reads src/auth/state.py"
    - "agent identifies the root cause (state cookie SameSite or path issue)"
    - "agent edits src/auth/callback.py or src/auth/state.py"
    - "agent runs the failing test and shows it passing"
  must_not_have:
    - "agent edits files outside src/auth/ or tests/auth/"
    - "agent calls run_command with destructive flags (rm -rf, --force)"
    - "agent makes the diff > 100 lines"
  
  judge_criteria:
    correctness: |
      Does the fix actually address the state cookie issue (not a workaround)?
    minimality: |
      Is the change scoped tightly to the bug, or does it sprawl?
    test_quality: |
      Does the test actually verify the bug doesn't recur?

config:
  model: openrouter/anthropic/claude-opus-4-7
  max_turns: 15
  timeout_sec: 600

baseline:
  # Recorded score from prior runs; CI fails if score drops more than 10%
  correctness_score: 0.92
  minimality_score: 0.85
  test_quality_score: 0.78
  cost_usd_p50: 0.04
```

### Eval runner

```python
# evals/runner.py

class EvalCase:
    @classmethod
    def load(cls, path: Path) -> "EvalCase":
        return cls(yaml.safe_load(path.read_text()))

    async def run(self, harness_config: dict) -> EvalResult:
        # 1. Set up isolated fixture
        with tempfile.TemporaryDirectory() as workdir:
            self._copy_fixture(workdir)
            
            # 2. Run AutoCode against the fixture
            session = await launch_autocode_session(
                workdir=workdir,
                config=harness_config,
                timeout=self.config["timeout_sec"],
            )
            
            # 3. Send the user message
            result = await session.send_message(self.input["user_message"])
            
            # 4. Collect telemetry events
            events = await session.collect_telemetry()
            
            # 5. Verify must-have conditions
            must_have_pass = self._check_must_have(events)
            must_not_have_pass = self._check_must_not_have(events)
            
            # 6. Run LLM judge for qualitative scoring
            scores = await self._judge(workdir, result, events)
            
            return EvalResult(
                case_id=self.id,
                passed=must_have_pass and must_not_have_pass,
                scores=scores,
                events=events,
                cost_usd=session.total_cost(),
            )
```

### LLM judge

For qualitative criteria (correctness, minimality, test quality), use a judge model with structured output:

```python
# evals/judge.py

JUDGE_PROMPT = """
You are evaluating an AI coding agent's solution to a problem.

ORIGINAL PROBLEM:
{user_message}

THE AGENT'S WORK:
- Files modified: {files_modified}
- Final diff:
```
{diff}
```
- Test output:
```
{test_output}
```

EVALUATION CRITERIA:
{criteria}

For each criterion, give:
1. A score from 0.0 to 1.0
2. A 1-2 sentence justification
3. Specific evidence (line numbers, output excerpts)

Output ONLY valid JSON:
{
  "<criterion_name>": {"score": 0.85, "justification": "...", "evidence": "..."},
  ...
}
"""
```

The judge is a different model than the agent (Codex's pattern: judge with a stronger model than agent). For AutoCode: agent runs on `qwen3-coder:free`, judge runs on `claude-opus-4-7` (or whatever's strongest at eval time).

### CI gating

```yaml
# .github/workflows/evals.yml

name: Evals
on:
  pull_request:
    branches: [main]

jobs:
  evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          uv sync --extra dev
          # Run a stratified sample of evals (not all 200)
          uv run python -m evals.runner \
            --cases evals/cases/regression-set.yaml \
            --baseline-tolerance 0.10 \
            --max-budget-usd 5.00 \
            --report evals/results/$(git rev-parse HEAD).json
      - uses: actions/upload-artifact@v4
        with:
          name: eval-report
          path: evals/results/
```

Pre-merge gate: each PR must keep eval scores within 10% of baseline. Score drops require justification.

---

## Tier 8.3 — Regression discipline

The discipline that makes evals work over time:

### Rule 1: every fixed bug becomes an eval case

When a user reports a bug:
1. Engineer reproduces it
2. **Before** writing the fix, write an eval case that fails on current `main`
3. Land the fix
4. The eval should now pass
5. Commit eval and fix together

This is non-negotiable. PR template includes:

```
- [ ] Bug reproducer eval case added at `evals/cases/<id>.yaml`
- [ ] Eval fails on `main` (run `evals.runner --case <id> --commit main`)
- [ ] Eval passes on this branch
```

### Rule 2: drift detector incidents become eval cases

If `autocode telemetry summary` shows a recurring drift kind, write an eval that exercises it. Use the actual production session as the seed.

### Rule 3: baseline updates require justification

Eval baseline scores live in version control. Updating them (especially upward) is a code change requiring review. "I made the agent better" is fine; the PR description must explain *what* you changed and why scores went up.

### Rule 4: eval cases never delete

Eval cases are append-only. If a case becomes obsolete (the feature it tested was removed), mark it `archived: true` in the YAML, but keep the file. Restoration of the feature later finds the eval already there.

### Rule 5: eval execution must be reproducible

Each case fixes:
- Model + version
- Temperature (0.0 by default for evals)
- Random seed where applicable
- Fixture state via git commit hash

If you can't get the same score twice in a row, the eval is broken, not the model.

---

## Tier 8.4 — Drift-derived eval generation

A specific automation: take production drift detection events and turn them into eval cases automatically.

```python
# evals/scripts/generate_evals_from_drift.py

def generate_evals_from_drift(days: int = 30) -> list[EvalCase]:
    """Read recent drift events, propose eval cases that would catch them."""
    events = read_telemetry(kind="tool_drift_detected", days=days)
    
    # Group by tool + drift kind
    by_pattern = {}
    for evt in events:
        key = (evt["data"]["tool_name"], evt["data"]["kind"])
        by_pattern.setdefault(key, []).append(evt)
    
    proposed = []
    for (tool, kind), occurrences in by_pattern.items():
        if len(occurrences) < 3:
            continue  # not a pattern, just noise
        # Use the original session as fixture
        seed_session = occurrences[0]["session_id"]
        proposed.append(propose_eval_case(
            tool=tool,
            drift_kind=kind,
            seed_session=seed_session,
            count=len(occurrences),
        ))
    
    return proposed
```

Run weekly. Engineer reviews each proposed eval, accepts or rejects. Accepted ones become files in `evals/cases/`.

---

## Tier 8.5 — Public dashboards (optional, beyond AutoCode self)

If AutoCode wants to publish "look how reliable our agent is" stats:

```bash
# Generate a public-safe summary (no PII, no private content)
autocode telemetry public-report --output public-stats.json
```

Output:

```json
{
  "period": "2026-04-01 to 2026-04-30",
  "sessions": 1421,
  "success_rate": 0.85,
  "drift_incidents_per_session": 0.16,
  "ralph_recovery_rate": 0.04,
  "avg_cost_per_session_usd": 0.024,
  "evals_passing": "187 / 198 (94.4%)",
  "model_distribution": {...},
  "tool_call_distribution": {...}
}
```

Same approach Anthropic uses for "Claude on SWE-bench" public metrics. Optional, but useful for marketing and for users choosing between agents.

---

## Acceptance tests

```python
def test_telemetry_event_emitted_on_turn_completion():
    store = TelemetryStore(base_dir=tmp_path)
    store.emit(
        "turn_completed",
        session_id="s1", thread_id="t1", turn_id="tu1",
        duration_ms=1234, tools_called=5,
    )
    store.shutdown()
    
    events_file = tmp_path / f"events-{datetime.now(UTC).date()}.jsonl"
    lines = events_file.read_text().strip().splitlines()
    assert len(lines) == 1
    evt = json.loads(lines[0])
    assert evt["kind"] == "turn_completed"
    assert evt["data"]["duration_ms"] == 1234


def test_eval_case_fails_when_must_have_missing():
    case = EvalCase.from_dict({
        "id": "test1",
        "name": "test",
        "input": {"user_message": "do nothing"},
        "expected_outcomes": {
            "must_have": ["agent reads src/foo.py"],
            "must_not_have": [],
        },
        "config": {"max_turns": 1},
    })
    # Mock agent that doesn't read anything
    result = await case.run(MockHarness(does_nothing=True))
    assert result.passed is False
    assert "must_have" in result.failure_reason


def test_judge_returns_structured_scores():
    judge = LLMJudge(mock_strong_llm)
    scores = await judge.score(
        criteria={"correctness": "Is the fix correct?"},
        diff="...",
        test_output="passed",
    )
    assert "correctness" in scores
    assert 0.0 <= scores["correctness"]["score"] <= 1.0
```

---

## What this all costs and pays back

**Engineering cost:**
- Tier 8.1 telemetry: ~3 days
- Tier 8.2 eval runner: ~5 days
- Tier 8.3 discipline: ongoing, no LOC
- Tier 8.4 drift→eval: ~2 days
- Tier 8.5 public dashboards: optional, ~1 day

**Total Tier 8: ~2 weeks engineering + ongoing per-PR discipline.**

**Payback:**
- Catch regressions before merging — value increases monotonically as the eval suite grows
- Quantify "are we getting better" — required for any non-trivial product decision
- Build user trust — "94.4% of regression evals pass" is more compelling than "we tried hard"
- Compress debugging cycles — when something breaks, you have telemetry to find it instead of asking users to repro

The eval suite **becomes the product's institutional memory**. Engineers will leave; the evals stay. Each one encodes a lesson learned.

---

## Why this is last but not optional

Tier 8 is the highest-leverage *defensive* investment in the roadmap. Tiers 1–7 add capabilities. Tier 8 protects them. Without it, every later tier is a guess about whether things are getting better.

Companies that ship reliable agents in 2026 (per the harness-engineering literature) all share this trait: they have evals before they have features. Manus's six rewrites were guided by eval scores. LangChain's four architectures were validated against benchmark suites. Claude Code's Anthropic team ships against internal evals before public release.

If the team wants to ship one thing from Tiers 5–8, ship Tier 8 first. The other tiers benefit from being measurable.
