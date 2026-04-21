# AutoCode Rust TUI

> **Status:** Rust binary is the sole interactive frontend. Stabilization Sprint Stage 0A is the active slice; the canonical RPC contract is `docs/reference/rpc-schema-v1.md`.

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

## Status

- Go TUI and Python inline fallback are deleted.
- `docs/reference/rpc-schema-v1.md` is the source of truth for backend/TUI method names.
- `autocode/tests/pty/fixtures/rpc-schema-v1/` is the schema-owned conformance corpus shared by Python and Rust tests.

## Milestones

| Milestone | Status |
|-----------|--------|
| M1-M11 migration program | ✅ DONE |
| Stabilization Stage 0A | ACTIVE |
| Stabilization Stages 1-4 | Queued behind 0A |

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
- `PLAN.md §1h` — historical migration program
- `docs/reference/rpc-schema-v1.md` — canonical Stage 0A RPC contract
