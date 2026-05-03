# Tier 4 — Future Tracks (Behind Feature Flags)

These are higher-risk, more speculative additions. Each is gated behind an environment variable / config flag; default off. Promote to default-on only after 4+ weeks of clean telemetry.

---

## Tier 4.1 — KAIROS proactive mode

**Goal:** match Anthropic's unreleased KAIROS daemon behavior — agent receives `<tick>` messages between user turns and decides whether to act or sleep.

**Total cost:** ~1 week, ~400 LOC. Behind `AUTOCODE_FEATURE_KAIROS=true`.

**Why behind a flag:** proactive autonomy has a high blast radius. Wrong action while user is away can rack up cost or break things. Stay opt-in until trust is earned.

### Files touched

- `src/autocode/agent/proactive.py` — NEW (~400 LOC)
- `src/autocode/agent/loop.py` — tick injection point (~30 LOC)
- `src/autocode/agent/tools.py` — add SleepTool (~80 LOC)
- `src/autocode/agent/prompts.py` — proactive mode system prompt section
- `src/autocode/cli.py` — `autocode daemon` subcommand

### The tick loop (verified architecture from research)

```python
# src/autocode/agent/proactive.py

import asyncio
from dataclasses import dataclass
from datetime import datetime, UTC

@dataclass
class TickConfig:
    enabled: bool = False
    base_interval_sec: float = 30.0     # interval when sleeping
    blocking_budget_sec: float = 15.0   # max time any single action can block
    cache_ttl_sec: int = 300            # 5 min — dictates max sensible sleep
    terminal_focus_aware: bool = True


class ProactiveLoop:
    """Implements Claude Code's KAIROS pattern.

    When the message queue is empty and proactive mode is enabled,
    inject a <tick> message. The model decides on each tick:
    - Act (call tools to do useful work)
    - Sleep via SleepTool (yield until next tick)
    - Send user a brief notification

    Critical anti-pattern to prevent: emitting "still waiting" status
    text on a tick. Per Claude Code design, model MUST call SleepTool
    when there's nothing to do.
    """

    def __init__(
        self,
        agent_loop,
        config: TickConfig,
    ):
        self.agent_loop = agent_loop
        self.config = config
        self._task: asyncio.Task | None = None
        self._sleep_until: datetime | None = None
        self._terminal_focused: bool = True

    async def start(self) -> None:
        if not self.config.enabled:
            return
        self._task = asyncio.create_task(self._tick_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def _tick_loop(self) -> None:
        while True:
            try:
                # If model called SleepTool, honor it
                if self._sleep_until and datetime.now(UTC) < self._sleep_until:
                    sleep_remaining = (self._sleep_until - datetime.now(UTC)).total_seconds()
                    await asyncio.sleep(min(sleep_remaining, self.config.base_interval_sec))
                    continue

                # If user is mid-typing in terminal, hold off
                if self.config.terminal_focus_aware and self._terminal_focused:
                    if self.agent_loop.has_pending_user_input():
                        await asyncio.sleep(self.config.base_interval_sec)
                        continue

                # Inject <tick>
                await self._inject_tick()
                await asyncio.sleep(self.config.base_interval_sec)
            except asyncio.CancelledError:
                break

    async def _inject_tick(self) -> None:
        """Inject a <tick> message into the agent's queue."""
        local_time = datetime.now().astimezone()
        tick_msg = (
            f"<tick>{local_time.isoformat()}</tick>\n\n"
            f"You're awake. Look at conversation history for any open work — "
            f"running CI checks, unresolved questions, or stalled tasks. "
            f"If there's nothing useful to do, call SleepTool."
        )
        await self.agent_loop.enqueue_user_message(
            tick_msg,
            metadata={"kind": "tick", "time": local_time.isoformat()},
        )

    def request_sleep(self, duration_sec: float) -> None:
        """Called by SleepTool to defer next tick."""
        from datetime import timedelta
        # Cap at 10x cache TTL — beyond that, cache will be cold anyway
        max_sleep = self.config.cache_ttl_sec * 10
        duration_sec = min(duration_sec, max_sleep)
        self._sleep_until = datetime.now(UTC) + timedelta(seconds=duration_sec)

    def set_terminal_focused(self, focused: bool) -> None:
        self._terminal_focused = focused
```

### SleepTool

```python
def _make_sleep_tool(proactive_loop: ProactiveLoop) -> ToolDefinition:
    return ToolDefinition(
        name="sleep",
        description=(
            "Wait for a specified duration. The user can interrupt the sleep "
            "at any time. Use this when the user tells you to sleep or rest, "
            "when you have nothing to do, or when you're waiting for something. "
            "You may receive <tick> prompts — these are periodic check-ins. "
            "Look for useful work to do before sleeping. "
            "Each wake-up costs an API call, but the prompt cache expires after "
            "5 minutes of inactivity — balance accordingly. "
            "Prefer this over `run_command(\"sleep ...\")` — it doesn't hold a shell process."
        ),
        parameters={
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "How long to sleep, in seconds.",
                },
                "reason": {
                    "type": "string",
                    "description": "Brief explanation (for logs).",
                },
            },
            "required": ["seconds"],
        },
        handler=lambda **kw: (
            proactive_loop.request_sleep(kw["seconds"]),
            f"Sleeping for {kw['seconds']}s. Reason: {kw.get('reason', 'no reason given')}.",
        )[1],
        requires_approval=False,
        safe=True,
    )
```

### System prompt section (when KAIROS active)

Drop-in from `Leonxlnx/claude-code-system-prompts/blob/main/prompts/18_proactive_mode.md`:

```python
PROACTIVE_MODE_PROMPT = """
# Autonomous work

You are running autonomously. You will receive `<tick>` prompts that keep
you alive between turns — just treat them as "you're awake, what now?"

The time in each `<tick>` is the user's current local time. Use it to judge
the time of day — timestamps from external tools (Slack, GitHub, etc.) may
be in a different timezone.

Multiple ticks may be batched into a single message. This is normal — just
process the latest one. Never echo or repeat tick content in your response.

## Pacing

Use the Sleep tool to control how long you wait between actions. Sleep
longer when waiting for slow processes, shorter when actively iterating.
Each wake-up costs an API call, but the prompt cache expires after 5
minutes of inactivity — balance accordingly.

**If you have nothing useful to do on a tick, you MUST call Sleep.** Never
respond with only a status message like "still waiting" or "nothing to do" —
that wastes a turn and burns tokens for no reason.

## What to do on subsequent wake-ups

Look for useful work. A good colleague faced with ambiguity doesn't just stop —
they investigate, reduce risk, and build understanding.
"""
```

### 15-second blocking budget

Every action initiated proactively must finish or yield within 15 seconds.

```python
# In agent/loop.py

async def _execute_tool_call_with_budget(self, tc, *, blocking_budget_sec: float):
    try:
        return await asyncio.wait_for(
            self._execute_tool_call(tc),
            timeout=blocking_budget_sec,
        )
    except asyncio.TimeoutError:
        return ToolOutcome(
            status="deferred",
            result=(
                f"Action exceeded {blocking_budget_sec}s blocking budget. "
                "Deferred — try again on next tick or break into smaller steps."
            ),
        )
```

This budget only applies when tick is the trigger — manual user requests get unlimited time.

### CLI

```bash
# Start daemon mode
autocode daemon --watch /path/to/repo

# Daemon connects to existing backend via Unix socket (Tier 2.2)
# Sends ticks to it in proactive mode
# Logs to ~/.autocode/daemon.log
# Sends desktop notifications via libnotify / osx-notifier
```

### Telemetry to track during opt-in period

- Tick invocations per hour
- SleepTool call ratio (target: > 70% of ticks should result in sleep)
- Anti-narration violations (model emits text without acting AND without sleeping) — alert if > 5%
- Cost per active hour
- User-perceived value: optional `/kairos pulse` shows "what KAIROS did while you were away"

---

## Tier 4.2 — Ephemeral fork side conversations

**Goal:** "second opinion" pattern — fork a conversation into an in-memory thread with a different model, without polluting main session history.

**Total cost:** ~50 LOC if Tier 2.1 is done; not possible before that.

### Behavior

User in main session presses `Ctrl+Shift+T`:
- Composer opens with current conversation context preloaded
- User types a question
- It's sent against a different model (config: `ephemeral_fork_model`)
- Response shown in side pane
- On close, nothing is persisted

### Implementation

```python
# Tier 2.1 already implements thread/fork with ephemeral=true
# This adds the UX for it.

# In rtui/src/state/reducer.rs:
match key {
    Key::CtrlShiftT if matches!(stage, Stage::Idle | Stage::Streaming) => {
        Effect::OpenEphemeralFork {
            parent_thread_id: state.current_thread_id,
            model_override: state.config.ephemeral_fork_model.clone(),
        }
    }
    ...
}

// Effect handler calls thread/fork with ephemeral=true
// Then turn/start on the new thread with user input
// Renders responses in a side pane (new DetailSurface variant)
```

---

## Tier 4.3 — Sticky environments per turn

**Goal:** match Codex #18897 — each thread has a persistent execution environment (cwd, env vars, persistent shell).

**Total cost:** ~200 LOC, depends on Tier 2.1.

### What it does

Today, each `run_command` tool call spawns a fresh subprocess. Sticky envs let the agent maintain a long-running shell across tool calls:

```
Turn 1, run_command:  cd /tmp && python -m http.server 8000 &
                       PID 12345 saved as part of thread environment

Turn 5, run_command:  curl localhost:8000/index.html
                       The HTTP server from turn 1 is still running.

Turn 10, run_command: exit
                       Cleanup: kill PID 12345.
```

### Implementation

Bind to existing `agent/sandbox.py` and `agent/worktree.py` infrastructure.

```python
# src/autocode/agent/sticky_env.py

class StickyEnvironment:
    """Long-lived execution context for a thread.

    Owns a persistent shell process and an env-var dict.
    Tool calls executed within this env share state.
    """

    def __init__(self, thread_id: str, cwd: Path):
        self.thread_id = thread_id
        self.cwd = cwd
        self.env_vars: dict[str, str] = {}
        self._shell_proc: asyncio.subprocess.Process | None = None
        self._background_pids: set[int] = set()

    async def start(self) -> None:
        """Spawn a persistent bash subprocess."""
        self._shell_proc = await asyncio.create_subprocess_exec(
            "/bin/bash", "--noprofile", "--norc",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
        )

    async def exec(self, cmd: str, *, timeout: float = 30.0) -> tuple[int, str, str]:
        """Send a command to the persistent shell.

        Uses a unique sentinel to detect command completion.
        """
        import secrets
        sentinel = f"__AUTOCODE_DONE_{secrets.token_hex(8)}__"

        full_cmd = f"{cmd}\necho {sentinel}$?\n"
        self._shell_proc.stdin.write(full_cmd.encode())
        await self._shell_proc.stdin.drain()

        # Read until sentinel
        out_chunks = []
        rc = -1
        async for line in self._read_until(sentinel, timeout):
            if line.startswith(sentinel):
                rc = int(line[len(sentinel):])
                break
            out_chunks.append(line)
        return rc, "".join(out_chunks), ""

    async def stop(self) -> None:
        """Kill background processes and the shell itself."""
        for pid in self._background_pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if self._shell_proc:
            self._shell_proc.terminate()
            await self._shell_proc.wait()
```

### Thread protocol additions

```
thread/start  params: { ..., experimental_environments: [...] }
              [] → no sticky env (current behavior)
              [{cwd: "/path"}] → one sticky env, defaults from thread cwd

thread/environment/list   → list active environments for a thread
thread/environment/reset  → kill and recreate
```

---

## Tier 4.4 — Headless `--json` mode for automation

**Goal:** match `codex exec --json` for CI/automation use cases. Already on the active backend tranche plan as C6 G5.

**Total cost:** ~150 LOC.

### CLI surface

```bash
# Single-shot, prints structured output
autocode exec "fix the auth bug" --json --output-schema=schema.json

# Output (one JSON object per line, newline-delimited):
{"type":"thread_started","thread_id":"01HXY..."}
{"type":"turn_started","turn_id":"01HXZ..."}
{"type":"item_started","item":{"id":"...","kind":"agent_message","status":"streaming"}}
{"type":"item_delta","item_id":"...","delta":"Looking at the auth module..."}
{"type":"item_completed","item_id":"...","status":"completed"}
{"type":"item_started","item":{"id":"...","kind":"tool_execution","tool_name":"read_file"}}
{"type":"item_completed","item_id":"...","status":"completed","result":"..."}
...
{"type":"turn_completed","turn_id":"...","status":"completed","reasoning_tokens":1247}
```

### Schema generation (matches Codex)

```bash
autocode generate-schema --out ./schemas
# Writes:
#   schemas/items.schema.json
#   schemas/turns.schema.json
#   schemas/threads.schema.json
#   schemas/methods.schema.json
```

This makes it possible to write strongly-typed clients in any language.

### Reasoning token reporting (Codex #19308)

```json
{
  "type": "turn_completed",
  "turn_id": "...",
  "status": "completed",
  "usage": {
    "prompt_tokens": 23410,
    "completion_tokens": 1832,
    "cached_input_tokens": 18204,
    "cache_creation_tokens": 412,
    "reasoning_tokens": 1247
  }
}
```

### Use cases this unlocks

- CI hook: comment on PR with `autocode exec --json "review this diff"` output
- Slack bot: pipe user messages through autocode, post structured response
- Voice frontend: hook autocode to a TTS pipeline, stream text-to-speak from `item/agentMessage/delta`
- Web client: SSE bridge from `--json` output to browser

---

## What's deliberately out of scope for Tier 4

- **Voice mode** — requires Realtime API budget, not a clean fit for free-tier focus
- **Multi-agent Coordinator** — adds complexity disproportionate to value at current scale
- **Buddy/Tamagotchi** — pure entertainment
- **Anti-distillation** — irrelevant for non-distilled product
- **Cron tools, GitHub webhook subscriptions** — depend on hosted infrastructure that AutoCode doesn't have
- **Anthropic-style "Auto Memory" with LLM-decided saving** — defer until MEMORY.md baseline (Tier 3.1) proves stable
