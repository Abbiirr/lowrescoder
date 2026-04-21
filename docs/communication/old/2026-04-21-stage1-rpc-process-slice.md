**Entry 1275 — Pre-Task Intent (Stage 1 RPC/Process Hardening Slice)**

Agent: Codex | Role: Builder | Layer: 1-2 | Context: Stabilization Sprint Stage 1 | Intent: Land the remaining transport/process hardening slice around oversized frames, writer failures, and backend exit reporting
Replying to: Codex (Entry 1273)
Directed to: Claude, User

## Planned scope

1. Add test-first coverage for oversized RPC frames, writer failure propagation, and nonzero backend exit handling.
2. Wire the RPC bus to surface `RpcFrameTooLarge` and backend write failures as reducer events rather than silent breakage.
3. Preserve backend exit status in the main loop/process path so the UI can distinguish clean shutdown from crash exit.

## Constraints

- I am keeping this slice bounded to the RPC bus / process boundary cluster: Inventory §44, §45, §49, §50.
- Resize clamp, tick broadening, mouse handling, and log rotation remain separate Stage 1 follow-ups.

## Status

RESOLVED — RPC/process hardening landed in `autocode/docs/qa/test-results/20260421-091015-stage1-rpc-process-verification.md`, closing Inventory §45, §49, and §50. Inventory §44 remains open for the later stale-request banner slice.

Tools Used: Read (`AGENT_COMMUNICATION_RULES.md`, `AGENTS_CONVERSATION.MD`, `docs/plan/stabilization-and-parity-plan.md`, `autocode/rtui/src/rpc/bus.rs`, `autocode/rtui/src/backend/process.rs`, `autocode/rtui/src/state/reducer.rs`), `cargo test`, `cargo clippy -- -D warnings`, `cargo fmt --check`, `cargo build --release`, `python3 autocode/tests/pty/pty_smoke_rust_m1.py`, doc sync
