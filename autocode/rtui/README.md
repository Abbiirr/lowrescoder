# AutoCode Rust TUI

> **Status:** M1 complete — scaffold + PTY launch + minimal RPC echo

## Build

```bash
cd autocode/rtui
cargo build --release
```

Binary: `target/release/autocode-tui` (2.2 MB)

## Run

```bash
# With Python backend on PATH:
./target/release/autocode-tui

# With inline mode (default):
./target/release/autocode-tui

# With alternate screen (opt-in):
./target/release/autocode-tui --altscreen

# Version:
./target/release/autocode-tui --version
```

## Environment

- `AUTOCODE_PYTHON_CMD` — Python command to run backend (default: `autocode`)
- `AUTOCODE_SESSION_ID` — session to resume on startup
- `HOME/.autocode/tui.log` — tracing output (stdout is RPC channel)

## Architecture

- **State:** pure reducer pattern (`state/reducer.rs`)
- **PTY:** `portable-pty` with blocking I/O in `spawn_blocking` threads
- **RPC:** JSON-RPC 2.0, LF-terminated lines
- **Logging:** `tracing` → file only (stdout is RPC channel)

## Milestones

| Milestone | Status |
|-----------|--------|
| M1: Scaffold + PTY launch | ✅ DONE |
| M2: JSON-RPC codec + conformance | Pending |
| M3: Raw input loop + streaming | Pending |
| M4: Composer (line editing, history) | Pending |
| M5: Status bar + spinner | Pending |
| M6: Slash commands + palette | Pending |
| M7: Pickers | Pending |
| M8: Approval / ask-user / steer / fork | Pending |
| M9: Editor / task panel / markdown | Pending |
| M10: Linux release hardening | Pending |
| M11: Cutover (delete Go TUI) | Pending |

## Testing

```bash
# Unit tests
cargo test

# Clippy
cargo clippy

# Format check  
cargo fmt -- --check
```

## Dependencies

See `Cargo.toml` — locked baseline:
- `crossterm 0.28`
- `ratatui 0.29`
- `tokio` (full features)
- `portable-pty 0.8`
- `serde` + `serde_json`
- `anyhow`
- `tracing` + `tracing-subscriber`

## Reference

- `rust_migration_plan.md` — detailed implementation plan
- `rust_migration_todo.md` — milestone checklist
- `PLAN.md §1h` — canonical authority