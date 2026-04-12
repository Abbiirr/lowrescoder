# Daemon Design (`daemon.py`)

The daemon is the central orchestrator — it runs all parsers, proxies, and the unified merger as asyncio tasks.

---

## Startup Sequence

1. Ensure `~/logs/` directory structure with `chmod 700`
2. Load `config.yaml` — source paths, proxy ports, domain filters, all resolved executable paths
3. Open state DB (`state.db`) — checkpoint store with per-source strategies
4. Validate dependencies:
   - Check resolved `mitmdump` path exists
   - Check ports 11435 (Ollama proxy) and 8080 (mitmproxy) are free
   - Check mitmproxy CA cert exists at `~/.mitmproxy/mitmproxy-ca-cert.pem`
5. Compile `NitriteExtractor.java` if `.class` not present (one-time, using resolved `javac` + classpath)

---

## Runtime Workers (asyncio)

All workers run as concurrent asyncio tasks within the daemon's event loop.

### Worker 1: Incremental File Tailers

One tailer per JSONL source type. Each tailer:
1. Opens files from the known file list
2. Seeks to last checkpoint (inode + byte offset)
3. Reads new lines
4. Passes to the appropriate parser
5. Writes normalized events to per-source sink

**Sources:**
- Claude Code: `~/.claude/projects/**/*.jsonl`
- Codex: `~/.codex/sessions/**/*.jsonl`
- Codex TUI log: `~/.codex/log/codex-tui.log`
- Copilot VS Code: `~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl`

### File Tailing with asyncinotify

```python
from asyncinotify import Inotify, Mask
from pathlib import Path

async def tail_jsonl(filepath: Path, checkpoint: int = 0):
    """Tail a JSONL file from a byte offset, yielding new lines."""
    f = open(filepath, 'r')
    f.seek(checkpoint)

    with Inotify() as inotify:
        inotify.add_watch(filepath.parent, Mask.MODIFY | Mask.CREATE)

        # Read any existing content first
        while True:
            line = f.readline()
            if not line:
                break
            line = line.strip()
            if line:
                yield line, f.tell()

        # Then watch for new content
        async for event in inotify:
            if event.path and event.path.name == filepath.name:
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        yield line, f.tell()
```

**Key details:**
- Watch the **parent directory** (not the file itself) — handles file rotation/recreation
- `Mask.CREATE` detects new files (for the file discovery scanner)
- `readline()` may return partial lines if the write hasn't flushed — skip empty results
- For local files, synchronous `readline()` doesn't actually block (kernel-buffered)

**Recommended library:** `asyncinotify` (zero-dependency, ctypes-based, supports both sync and async iteration)

### Worker 2: Periodic File Discovery Scanner (every 30s)

Scans for new session files across all JSONL sources:

```python
async def discover_new_files(known_files: set[Path], source_globs: dict):
    """Find new session files not yet being tailed."""
    while True:
        for source, glob_pattern in source_globs.items():
            for path in Path.home().glob(glob_pattern):
                if path not in known_files:
                    known_files.add(path)
                    # Register with appropriate tailer
                    await register_new_file(source, path)
        await asyncio.sleep(30)
```

**Source globs:**
- Claude Code: `.claude/projects/**/*.jsonl`
- Codex: `.codex/sessions/**/*.jsonl`
- Copilot VS Code: `.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl`

### Worker 3: Database Pollers

**OpenCode** — poll every 5s:

```python
import sqlite3

async def poll_opencode(db_path: Path, checkpoint: dict):
    """Poll OpenCode SQLite DB for new messages/parts."""
    while True:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute("PRAGMA journal_mode=WAL")

        try:
            # Query new messages
            cursor = conn.execute(
                "SELECT * FROM message WHERE time_created > ? ORDER BY time_created",
                (checkpoint.get("message_time", 0),)
            )
            for row in cursor:
                # Parse and normalize
                msg = parse_message_row(row)

                # Query related parts
                parts_cursor = conn.execute(
                    "SELECT * FROM part WHERE message_id = ? ORDER BY id",
                    (msg["id"],)
                )
                for part_row in parts_cursor:
                    part = parse_part_row(part_row)
                    yield normalize_part(part, msg)

                checkpoint["message_time"] = msg["time_created"]
        except sqlite3.OperationalError:
            # SQLITE_BUSY — retry next cycle
            pass
        finally:
            conn.close()

        await asyncio.sleep(5)
```

**Copilot JetBrains** — poll every 60s:

```python
import shutil
import subprocess
import tempfile

async def poll_jetbrains(db_paths: list[Path], classpath: str, checkpoint: dict):
    """Poll JetBrains Nitrite DBs via Java subprocess."""
    while True:
        for db_path in db_paths:
            if not db_path.exists():
                continue

            # Copy to avoid lock conflicts
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                shutil.copy2(db_path, tmp.name)
                tmp_path = tmp.name

            try:
                result = subprocess.run(
                    ["java", "-cp", classpath, "NitriteExtractor", tmp_path],
                    capture_output=True, text=True, timeout=30,
                )
                for line in result.stdout.strip().split("\n"):
                    if line:
                        doc = json.loads(line)
                        yield normalize_jetbrains_doc(doc)
            finally:
                os.unlink(tmp_path)

        await asyncio.sleep(60)
```

### Worker 4: Ollama Reverse Proxy

See [06-phase3-ollama-proxy.md](06-phase3-ollama-proxy.md). Runs as an inline asyncio HTTP server on `localhost:11435`.

### Worker 5: mitmproxy Subprocess

See [07-phase4-mitmproxy.md](07-phase4-mitmproxy.md). Managed as an `asyncio.create_subprocess_exec()` child process.

### Worker 6: Unified Merger

Tails all per-source JSONL sinks and writes to `~/logs/unified.jsonl`:

```python
async def unified_merger(source_sinks: list[Path]):
    """Merge all per-source sinks into unified.jsonl."""
    unified_path = Path.home() / "logs" / "unified.jsonl"

    async for source_path, line in tail_multiple_files(source_sinks):
        try:
            event = json.loads(line)
            validate_schema(event)  # Check against ailogd.v1
            with open(unified_path, "a") as f:
                f.write(line + "\n")
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Skipping invalid event from {source_path}: {e}")
```

---

## Checkpoint Strategy

### Per-Source Strategies

| Source | Checkpoint Key | Dedup Key |
|--------|---------------|-----------|
| JSONL files (Claude, Codex, Copilot VS Code) | `inode + byte_offset` per file | `source_file + byte_offset + content_hash` |
| OpenCode SQLite | `max(time_created)` per table | `message.id` / `part.id` (row PK) |
| Copilot JetBrains Nitrite | `max(modifiedAt)` per collection | `NtTurn.id` / `NtAgentTurn.id` |
| Ollama proxy | N/A (real-time) | Request hash (method + path + body_hash) |
| mitmproxy | N/A (real-time) | Request hash |

### Persistence

All checkpoints persisted to `state.db` (SQLite) every 5 seconds and on `SIGTERM`:

```python
# state.py
class CheckpointStore:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                source TEXT,
                source_file TEXT,
                checkpoint_key TEXT,
                checkpoint_value TEXT,
                updated_at TEXT,
                PRIMARY KEY (source, source_file, checkpoint_key)
            )
        """)

    def save(self, source: str, source_file: str, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?, ?)",
            (source, source_file, key, value, datetime.utcnow().isoformat()),
        )

    def load(self, source: str, source_file: str, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT checkpoint_value FROM checkpoints WHERE source=? AND source_file=? AND checkpoint_key=?",
            (source, source_file, key),
        ).fetchone()
        return row[0] if row else None
```

---

## Retention & Archival

**Policy:** Keep forever, with compression.

- **Active logs:** `~/logs/<source>/*.jsonl` — written to actively
- **Segment rotation:** When any active log exceeds 100MB, rotate to `<name>.<ISO-timestamp>.jsonl.gz`
- **Compression worker:** Background asyncio task, runs every 60s, gzips rotated segments
- **No deletion:** All segments retained indefinitely
- **Disk monitoring:** `analyze.py --disk-usage` reports per-source sizes and growth rate

```python
async def rotation_worker(log_dir: Path, max_size_mb: int = 100):
    """Rotate and compress log files exceeding max size."""
    while True:
        for jsonl_file in log_dir.rglob("*.jsonl"):
            if jsonl_file.name.startswith("."):
                continue
            size_mb = jsonl_file.stat().st_size / (1024 * 1024)
            if size_mb >= max_size_mb:
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
                rotated = jsonl_file.with_suffix(f".{ts}.jsonl")
                jsonl_file.rename(rotated)
                # Touch new empty file
                jsonl_file.touch()
                # Compress in background
                await asyncio.to_thread(gzip_file, rotated)
        await asyncio.sleep(60)
```

---

## Signal Handling

```python
import signal

async def main():
    loop = asyncio.get_event_loop()

    # Graceful shutdown on SIGTERM/SIGINT
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    # Start all workers...

async def shutdown():
    """Graceful shutdown: persist checkpoints, close connections."""
    logger.info("Shutting down...")
    checkpoint_store.flush()
    await mitmproxy_proc.terminate()
    await client.aclose()
    # Cancel all worker tasks
    for task in worker_tasks:
        task.cancel()
```

---

## config.yaml Structure

```yaml
# Default config — resolved paths filled by install.sh
sources:
  claude_code:
    glob: "~/.claude/projects/**/*.jsonl"
    poll_interval: null  # inotify-based
  codex:
    glob: "~/.codex/sessions/**/*.jsonl"
    poll_interval: null
  opencode:
    db_path: "~/.local/share/opencode/opencode.db"
    poll_interval: 5
  copilot_vscode:
    glob: "~/.config/Code/User/workspaceStorage/*/chatSessions/*.jsonl"
    poll_interval: null
  copilot_jetbrains:
    db_paths:
      - "~/.config/github-copilot/db/chat-agent-sessions/*/copilot-agent-sessions-nitrite.db"
      - "~/.config/github-copilot/db/chat-sessions/*/copilot-chat-nitrite.db"
      - "~/.config/github-copilot/db/chat-edit-sessions/*/copilot-edit-sessions-nitrite.db"
    poll_interval: 60

capture:
  ollama_proxy:
    listen_port: 11435
    upstream: "http://localhost:4000"
  mitmproxy:
    listen_port: 8080
    target_domains:
      - "api.anthropic.com"
      - "api.openai.com"
      - "api.openrouter.ai"

log_sink: "~/logs/"
state_db: "~/logs/.state.db"
rotation_max_mb: 100

resolved_paths:
  python: null       # filled by install.sh
  mitmdump: null
  java: null
  claude_real: null
  codex_real: null
  jetbrains_lib: null
  mitm_addon: null
```
