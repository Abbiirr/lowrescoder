# ADR-001: Rust TUI Migration

> Status: ACCEPTED
> Date: 2026-04-19
> Related: Entry 1220 (user), Entry 1229 (Codex APPROVE)

## Summary

Migrate the Go BubbleTea TUI (`autocode/cmd/autocode-tui/`) to a Rust TUI using `crossterm` + `ratatui` + `tokio` + `portable-pty`.

## Decisions (a)-(l)

| # | Decision | Answer | Rationale |
|---|---|---|---|
| a | Strategic go/no-go | **YES — migrate Go → Rust** | Richer terminal control depth, Linux-first PTY with Windows ConPTY path, smaller maintenance surface |
| b | Crate stack | `crossterm 0.28` + `ratatui 0.29` + `tokio` + `portable-pty 0.8` + `serde_json` + `anyhow` + `tracing` | Baseline locked; M1 spikes: `tui-textarea` (REJECTED), `LinesCodec` (APPROVED) |
| c | PTY vs plain pipe | **PTY via `portable-pty`** | Uniform Linux PTY + Windows ConPTY API |
| d | Go §1f Milestone C/D/E/F timing | **FREEZE** | Go gates stopped; absorbed into Rust-M5 through M10 |
| e | Binary naming | **`autocode-tui`** | Single binary from day one; Go removed at M11 cutover |
| f | Inline vs alt-screen | **INLINE by default**; `--altscreen` opt-in | Inherited from Go TUI behavior |
| g | Platform | **Linux v1 only**; macOS NEVER; Windows post-v1 | Scope locked by user Entry 1228 |
| h | Selection mechanism | **N/A** | One binary, no selector needed |
| i | Track 4 fidelity | **Permission to improve** | Re-baseline xfails at M11 cutover |
| j | Builder agent | **Flexible** | User assigns per milestone |
| k | Python `--inline` fallback | **DELETE at M11** | No coexistence period |
| l | Research report status | **DRAFT** | `PLAN.md §1h.2` corrections are authoritative |

## References

- `rust_migration_plan.md` — detailed implementation plan
- `rust_migration_todo.md` — milestone checklist
- `PLAN.md §1h` — canonical authority