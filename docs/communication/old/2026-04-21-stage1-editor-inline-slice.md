**Entry 1274 — Pre-Task Intent (Stage 1 Editor Lifecycle + Inline Preservation Slice)**

Agent: Codex | Role: Builder | Layer: 1-2 | Context: Stabilization Sprint Stage 1 | Intent: Land the next blocking Stage 1 hardening slice around editor lifecycle, alt-screen correctness, and inline terminal preservation
Replying to: Codex (Entry 1273)
Directed to: Claude, User

## Planned scope

1. Add test-first coverage for `$EDITOR` parsing, runtime-dir temp-file selection, and reducer stage transitions for Ctrl+E / editor return.
2. Replace the current direct editor spawn path with a helper that supports editor arguments, secure temp files, and conditional alt-screen restore.
3. Remove the unconditional inline `terminal.clear()` path and make editor launch/return use `Stage::EditorLaunch` correctly.

## Constraints

- I am keeping this slice focused on the editor/terminal lifecycle cluster: Inventory §24, §25, §46, §47, §48, §51, §52.
- RPC-frame hardening, resize clamp, tick broadening, mouse handling, and log rotation stay for later Stage 1 sub-slices.

## Status

RESOLVED — editor lifecycle and inline terminal preservation slice landed in `autocode/docs/qa/test-results/20260421-085810-stage1-editor-inline-verification.md`, closing Inventory §24, §25, §46, §47, §48, §51, and §52.

Tools Used: Read (`AGENT_COMMUNICATION_RULES.md`, `AGENTS_CONVERSATION.MD`, `docs/plan/stabilization-and-parity-plan.md`, `autocode/rtui/src/main.rs`, `autocode/rtui/src/state/reducer.rs`), `cargo test`, `cargo clippy -- -D warnings`, `cargo fmt --check`, `cargo build --release`, `python3 autocode/tests/pty/pty_smoke_rust_m1.py`, doc sync
