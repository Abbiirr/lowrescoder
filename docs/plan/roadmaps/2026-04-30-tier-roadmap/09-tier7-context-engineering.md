# Tier 7 — Context Engineering

**Goal:** stop putting things in context that don't need to be there. Start using the filesystem as extended memory.

**Total cost:** ~2 weeks engineering, ~600 LOC.

**The lesson from Microsoft Azure SRE Agent (2026):** they had 100+ bespoke tools and a prescriptive prompt. Replaced with a filesystem-based system where source code, runbooks, query schemas, and past investigation notes were exposed as files, and the agent used `read_file`, `grep`, `find`, and a shell. **"Intent Met" score rose from 45% to 75% on novel incidents.** Same model. Different harness.

The lesson from Manus (six months, five rewrites): the fifth and most production-hardened strategy is using the filesystem as extended context. When an observation is too large for the context window, write it to disk, keep only the path in context.

This tier operationalizes that for AutoCode.

---

## Tier 7.1 — Filesystem-as-context for tool outputs

### Files touched

- `src/autocode/agent/scratch.py` — NEW (~250 LOC)
- `src/autocode/agent/tools.py` — wrap large tool outputs (~80 LOC)
- `src/autocode/agent/context.py` — adjust truncation rules
- `tests/unit/test_scratch.py` — NEW

### What this is

When a tool call produces output larger than ~5KB (configurable), instead of truncating it (current behavior — middle-truncation losing information), write the full output to a scratch file under `.autocode/scratch/<turn-id>/<tool>-<idx>.md` and keep only the path + a short summary in agent context. The agent can `read_file` the scratch path on demand.

This is **information preservation under context pressure**. The key insight: most large tool outputs (a 50-file `list_files`, a 200-line `git_log`, a `web_fetch` of a long article) are looked at by the agent once, then forgotten. Putting them in main context wastes tokens and pushes more useful messages out via compaction. Putting them on disk keeps them accessible without paying the token cost.

### Threshold rule

```python
# Default thresholds (configurable)
SCRATCH_THRESHOLD_BYTES = 5_000        # ~1250 tokens
SCRATCH_NEVER_FOR = {"todo_read", "ask_user", "memory_index_show"}  # always inline
SCRATCH_ALWAYS_FOR = {"web_fetch", "git_log"}  # always offload
```

### Implementation

```python
# src/autocode/agent/scratch.py

from pathlib import Path
import hashlib
import json
import secrets
from datetime import datetime, UTC

class ScratchStore:
    """Per-turn scratch directory for offloaded tool outputs.

    Layout:
        .autocode/scratch/
        └── <thread-id>/
            └── <turn-id>/
                ├── manifest.json
                ├── 001-list_files.md
                ├── 002-git_log.md
                └── 003-web_fetch.md
    """

    SCRATCH_THRESHOLD_BYTES = 5_000
    HEADER_LINES_KEPT = 5      # show first N lines as preview
    SUMMARY_MAX_CHARS = 300    # plus a short generated summary

    def __init__(self, project_root: Path, thread_id: str, turn_id: str):
        self.dir = project_root / ".autocode" / "scratch" / thread_id / turn_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._counter = 0
        self._manifest_path = self.dir / "manifest.json"
        self._manifest: list[dict] = []

    def offload_if_large(
        self,
        tool_name: str,
        args: dict,
        result: str,
    ) -> str:
        """If result is large, write to disk and return a context-friendly stub.

        Returns the string that should go into the agent's context.
        """
        if (
            len(result) < self.SCRATCH_THRESHOLD_BYTES
            and tool_name not in SCRATCH_ALWAYS_FOR
        ) or tool_name in SCRATCH_NEVER_FOR:
            return result

        self._counter += 1
        filename = f"{self._counter:03d}-{tool_name}.md"
        path = self.dir / filename

        # Write full content to disk with metadata header
        body = (
            f"---\n"
            f"tool: {tool_name}\n"
            f"args: {json.dumps(args, sort_keys=True)}\n"
            f"captured_at: {datetime.now(UTC).isoformat()}\n"
            f"size_bytes: {len(result)}\n"
            f"---\n\n"
            f"{result}\n"
        )
        path.write_text(body, encoding="utf-8")

        # Build context stub
        preview_lines = result.splitlines()[:self.HEADER_LINES_KEPT]
        preview = "\n".join(preview_lines)
        if len(preview) > self.SUMMARY_MAX_CHARS:
            preview = preview[:self.SUMMARY_MAX_CHARS] + "..."

        # Compute one-line summary for the manifest
        summary = self._compute_summary(tool_name, args, result)

        self._manifest.append({
            "id": self._counter,
            "tool": tool_name,
            "filename": filename,
            "size_bytes": len(result),
            "summary": summary,
        })
        self._save_manifest()

        # The stub the agent sees in context
        return (
            f"[Tool output offloaded — {len(result):,} bytes saved to "
            f"`.autocode/scratch/{self.dir.parent.name}/{self.dir.name}/{filename}`]\n\n"
            f"Summary: {summary}\n\n"
            f"First {self.HEADER_LINES_KEPT} lines:\n"
            f"```\n{preview}\n```\n\n"
            f"Use `read_file` on the path above to see the full output."
        )

    @staticmethod
    def _compute_summary(tool_name: str, args: dict, result: str) -> str:
        """Generate a 1-line summary based on tool type."""
        if tool_name == "list_files":
            n = result.count("\n") + 1
            return f"{n} files in {args.get('directory', '.')}"
        if tool_name == "git_log":
            n = result.count("\ncommit ")
            return f"{n} commits"
        if tool_name == "web_fetch":
            return f"Fetched {args.get('url', '?')}: {len(result):,} bytes"
        if tool_name == "grep_content":
            n = result.count("\n")
            return f"{n} matches for pattern '{args.get('pattern', '?')}'"
        # Default
        first_line = result.split("\n", 1)[0]
        return first_line[:200]

    def _save_manifest(self) -> None:
        self._manifest_path.write_text(
            json.dumps(self._manifest, indent=2), encoding="utf-8"
        )

    def cleanup_after_n_turns(self, current_turn_count: int, keep_n: int = 10) -> int:
        """Delete scratch dirs from older turns. Returns count deleted."""
        if current_turn_count <= keep_n:
            return 0
        # ... iterate and delete oldest dirs
```

### Wiring into tool execution

```python
# In agent/loop.py, where tools are executed

class AgentLoop:
    def __init__(self, ...):
        self._scratch = None  # initialized per turn

    async def run(self, ...):
        for iteration in range(self.MAX_ITERATIONS):
            if self._scratch is None or self._scratch.turn_id != self.current_turn_id:
                self._scratch = ScratchStore(
                    project_root=self.project_root,
                    thread_id=self.thread_id,
                    turn_id=self.current_turn_id,
                )

            # ... existing turn body ...

            for tc in response.tool_calls:
                outcome = await self._execute_tool_call(tc)
                # NEW: offload large outputs to disk
                offloaded = self._scratch.offload_if_large(
                    tool_name=tc.name,
                    args=tc.args,
                    result=outcome.result,
                )
                # use the offloaded stub instead of the full result
                outcome.result = offloaded
```

### What this changes for the agent

The agent learns to do this pattern:

```
Agent: I'll list the source files first.
       [calls list_files]
Tool: [Tool output offloaded — 28,432 bytes saved to .autocode/scratch/.../001-list_files.md]
      Summary: 487 files in src/
      First 5 lines:
      ```
      src/auth/__init__.py
      src/auth/callback.py
      ...
      ```
      Use read_file on the path above to see the full output.

Agent: 487 files is a lot. Let me filter to just the auth module.
       [calls glob_files with pattern src/auth/*.py]
Tool: src/auth/__init__.py
      src/auth/callback.py
      src/auth/state.py
      src/auth/oauth.py

Agent: Now I'll look at callback.py.
       [calls read_file]
Tool: ... (under threshold, inlined)
```

The agent organically learns to use narrower queries because it sees the cost of broad ones (a stub instead of the full result). This is harness-driven behavior change, not prompt-driven.

### Acceptance tests

```python
def test_small_output_inlined():
    scratch = ScratchStore(tmp_path, "t1", "tu1")
    out = scratch.offload_if_large("read_file", {"path": "x.py"}, "small content")
    assert out == "small content"

def test_large_output_offloaded():
    scratch = ScratchStore(tmp_path, "t1", "tu1")
    big = "x" * 10_000
    out = scratch.offload_if_large("list_files", {"directory": "/"}, big)
    assert "[Tool output offloaded" in out
    assert "10,000 bytes" in out
    assert "First 5 lines" in out

def test_manifest_records_offload():
    scratch = ScratchStore(tmp_path, "t1", "tu1")
    scratch.offload_if_large("list_files", {}, "x" * 10_000)
    manifest = json.loads((scratch.dir / "manifest.json").read_text())
    assert len(manifest) == 1
    assert manifest[0]["tool"] == "list_files"
    assert manifest[0]["size_bytes"] == 10_000

def test_cleanup_keeps_n_recent():
    # Create 15 turns of scratch, cleanup_after_n_turns(15, keep_n=10)
    # Verify only 10 most recent remain
    ...
```

---

## Tier 7.2 — Context entropy management

### Files touched

- `src/autocode/agent/entropy.py` — NEW (~150 LOC)
- `src/autocode/agent/loop.py` — entropy check at compaction (~30 LOC)
- `src/autocode/agent/prompts.py` — anti-entropy section in system prompt

### Concept

Entropy in agent contexts: as turns accumulate, inconsistencies creep in. Variable names mentioned in conversation drift from variable names in code. Decisions made in turn 5 contradict turn 12's assumptions. Tool results from 50 turns ago describe a state that no longer exists.

The harness-engineering literature (Mitchell Hashimoto via Augment Code, Feb 2026) identifies entropy as a discrete failure mode separate from drift. Drift is data changing underneath the agent. Entropy is the agent's own context becoming internally inconsistent.

### What to do about it

Two mechanisms:

#### 1. Periodic entropy audits (every 10 turns)

Run a small subagent that scans the last N messages and flags inconsistencies:

```python
# src/autocode/agent/entropy.py

ENTROPY_AUDIT_PROMPT = """
You are an entropy auditor for an AI coding agent's conversation. Look at
the last 20 messages and identify INCONSISTENCIES.

Examples of entropy:
- Variable names that drift between mentions (state_token in turn 3, stateToken in turn 7)
- Decisions reversed without acknowledgment (turn 4: "use JWT" / turn 11: "use cookies")
- File paths that don't exist (mentioned `src/oauth.py` but it's actually `src/auth/oauth.py`)
- Tool results from older turns that describe state that's since changed
- Conflicting facts (turn 2: "test passes" / turn 9: same test failing without explanation)

Output JSON:
{
  "incidents": [
    {
      "severity": "low" | "medium" | "high",
      "kind": "naming_drift" | "decision_reversal" | "stale_reference" | "fact_conflict",
      "description": "one sentence",
      "evidence": "quote or message id"
    }
  ],
  "recommendation": "what to do" | null
}

Conversation excerpt:
{messages}
"""


class EntropyAuditor:
    AUDIT_INTERVAL_TURNS = 10
    MAX_MESSAGES_AUDITED = 20

    def __init__(self, executor):
        self.executor = executor
        self._last_audit_turn = 0

    async def maybe_audit(self, current_turn: int, messages: list) -> EntropyReport | None:
        if current_turn - self._last_audit_turn < self.AUDIT_INTERVAL_TURNS:
            return None
        recent = messages[-self.MAX_MESSAGES_AUDITED:]
        prompt = ENTROPY_AUDIT_PROMPT.format(messages=self._format(recent))
        result = await self.executor.summarize(prompt, model="cheap-fast")
        self._last_audit_turn = current_turn
        return self._parse(result)
```

When entropy is found:
- High severity: inject a system message warning + recommend rollback to last checkpoint
- Medium: inject a warning, log to telemetry
- Low: log only

#### 2. Anti-entropy system prompt section

Add to `STABLE_INSTRUCTIONS`:

```
## Internal consistency

If you find your own statements contradicting earlier statements in this
conversation, acknowledge the contradiction explicitly:
- "I earlier said X but now I'm seeing Y. Let me reconcile."
- "I'm changing my recommendation from X to Y because [evidence]."

If a file path or variable name you mentioned earlier doesn't appear when
you read the file, do NOT silently substitute. Stop and ask the user, or
verify with another tool.

If a decision was made earlier in this conversation, do not reverse it
without flagging the reversal.
```

This is small but effective. Models follow it readily once primed.

---

## Tier 7.3 — `read_file` always before relying on memory

This is a tightening of Tier 3.3 (verify-before-use). Make it concrete via a tool wrapper:

### Implementation

Wrap memory-derived facts in a markup that the agent learns to interpret:

```python
# When loading memory at session start
def render_memory_for_context(memory_index: str, topic_files: dict) -> str:
    return (
        "## Project memory (treat as HINT, not truth)\n\n"
        + memory_index
        + "\n\n"
        "**Important:** before relying on any specific fact below, "
        "verify it against current code with read_file or grep_content. "
        "Memory may be stale.\n\n"
        + "\n\n".join(f"### {slug}\n\n{content}" for slug, content in topic_files.items())
    )
```

Then add a runtime check: when the agent's response cites a fact from memory (heuristic: response mentions a file path that's in memory but no `read_file` call has occurred), inject a soft warning:

```
[Reminder: you're acting on memory of `src/auth/oauth.py` without re-reading it.
If your changes depend on its current contents, consider read_file first.]
```

This is a *prompt nudge*, not a hard block. Gentle correction, agent learns the pattern.

---

## Performance considerations

The scratch store adds disk I/O to every tool call. Profile:

- Modern SSD: write 5-50 KB takes < 1ms
- Read-back on demand: same
- Cleanup after N turns: amortized, runs in background

Net cost: negligible. Net benefit: removes the largest single source of context bloat.

---

## What this enables downstream

Tier 7 is foundational for several future improvements:

- **Better compaction**: when compacting, you no longer need to re-summarize old tool results — they're on disk and can be re-read or grep'd if relevant
- **Cross-turn debugging**: a 100-turn session that produced a weird outcome can be debugged by reading the scratch directory chronologically — every tool result is there, intact
- **Regression testing**: capture scratch dirs from production runs, replay them in CI to verify the agent makes the same decisions

---

## Acceptance tests

```python
async def test_entropy_audit_detects_naming_drift():
    auditor = EntropyAuditor(mock_executor)
    messages = [
        {"role": "user", "content": "Add state_token to the cookie"},
        {"role": "assistant", "content": "I'll add stateToken to the auth flow"},
        # 8 more turns mixing the two names...
    ]
    report = await auditor.maybe_audit(current_turn=10, messages=messages)
    assert report is not None
    assert any(inc.kind == "naming_drift" for inc in report.incidents)


async def test_scratch_directory_per_turn():
    """Each turn gets its own scratch dir."""
    scratch1 = ScratchStore(tmp_path, "t1", "turn-001")
    scratch1.offload_if_large("read_file", {"path": "x"}, "x" * 10_000)
    scratch2 = ScratchStore(tmp_path, "t1", "turn-002")
    scratch2.offload_if_large("read_file", {"path": "y"}, "y" * 10_000)

    assert (tmp_path / ".autocode/scratch/t1/turn-001/manifest.json").exists()
    assert (tmp_path / ".autocode/scratch/t1/turn-002/manifest.json").exists()


def test_scratch_cleanup_keeps_only_recent():
    project_root = tmp_path
    # Create 15 turn dirs
    for i in range(15):
        d = project_root / ".autocode/scratch/t1" / f"turn-{i:03d}"
        d.mkdir(parents=True)
        (d / "001-test.md").write_text("x")

    # Cleanup, keep 10
    deleted = ScratchStore.cleanup_old(project_root / ".autocode/scratch/t1", keep_n=10)
    assert deleted == 5
    remaining = list((project_root / ".autocode/scratch/t1").iterdir())
    assert len(remaining) == 10
```
