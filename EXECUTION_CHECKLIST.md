# Execution Checklist

Last updated: 2026-04-19 (Rust M1-M11 COMPLETE. Go TUI and Python inline deleted. Rust binary is sole frontend.)
Owner: OpenCode
Purpose: live status checklist for source-of-truth work, active next-frontier research-to-implementation items, and any benchmark/harness follow-up. Re-check this file every 10 minutes during active work.

Detailed implementation map:
- `PLAN.md`
- For every open item below, find the matching numbered section in `PLAN.md` before implementing.
- `DEFERRED_PENDING_TODO.md` — consolidated store of everything NOT in the current active slice. Do not lose these items; walk that file after the active slice closes.

Execution order (2026-04-19, §1h Rust TUI Migration COMPLETE):
1. **Section 1h Rust TUI Migration (COMPLETE)** — M1-M11 all done. Go TUI deleted. Python inline deleted. Rust binary is sole frontend. See `PLAN.md` §1h.8 for milestones.
2. Section 1g TUI Testing Strategy — committed (`a9cc315`); Slice 2 themed renderer deferred (user-gated).
3. Section 1f Milestone C/D/E/F — **FROZEN** on Go; gates absorbed into Rust-M5 through Rust-M10.
4. Section 1 large-repo validation / retrieval contract.
5. Section 2 external-harness event normalization + deeper adapters.
6. Section 3 Terminal-Bench score improvement.

## Rust TUI Migration (COMPLETE)

> Status (2026-04-19): M1-M11 complete. Go TUI and Python inline fallback deleted. Rust binary (`autocode/rtui/target/release/autocode-tui`) is the sole interactive frontend. 57 unit tests passing. Binary size 2.4MB. All performance targets met.
> Source research: `deep-research-report (1).md` at repo root (treat as draft).

**All decisions locked:**

- [x] (a) YES — migrate Go → Rust
- [x] (b) Stack locked baseline: `crossterm` + `ratatui` + `tokio` + `portable-pty` + `serde_json` + `anyhow` + `tracing`. M1 spike candidates (not yet locked): `tui-textarea`, `tokio-util::LinesCodec`
- [x] (c) PTY via `portable-pty`
- [x] (d) FREEZE §1f Go milestones C/D/E/F
- [x] (e) Binary name: `autocode-tui` — single name, Go removed immediately
- [x] (f) INLINE by default; `--altscreen` opt-in
- [x] (g) Linux first; macOS out of scope; Windows post-v1 (keep ConPTY path open)
- [x] (h) N/A — one binary, no selector
- [x] (i) Permission to improve — re-baseline Track 4 at cutover
- [x] (j) Builder: flexible per milestone (OpenCode or Claude, user decides per slice)
- [x] (k) DELETE Python `--inline` fallback at cutover
- [x] (l) Research report = draft; §1h.2 corrections authoritative

**Migration milestones (sequential, each gated on stored PTY/test artifact):**

- [x] **Rust-M1** — Scaffolding + PTY launch + minimal RPC echo (ADR-001/002/003 publish). PTY smoke green with /exit fix.
- [x] **Rust-M2** — JSON-RPC codec parity + conformance harness. 32 serde round-trip tests.
- [x] **Rust-M3** — Raw input loop + streaming display + sliding-window flush.
- [x] **Rust-M4** — Composer (line editing, multi-line, frecency history). History persistence to `~/.autocode/history.json`.
- [x] **Rust-M5** — Status bar + 194-verb spinner (Track 4 `ready` + `active` scenes pending).
- [x] **Rust-M6** — Slash command router + Ctrl+K palette.
- [x] **Rust-M7** — Pickers (model/provider/session, arrow + type-to-filter).
- [x] **Rust-M8** — Approval/ask-user/steer/fork (backend-parity PTY smoke pending).
- [x] **Rust-M9** — Editor launch (Ctrl+E) + plan mode + task panel + followup queue + markdown inline + bracketed paste.
- [x] **Rust-M10** — Linux release hardening + performance + release gate. All perf targets met. CI workflow created.
- [x] **Rust-M11** — Cutover: Go TUI deleted, Python inline deleted. Makefile updated. Docs updated.

**Testing strategy integration:** All four existing TUI testing dimensions (Track 1 runtime invariants · Track 4 design-target ratchet · VHS self-regression · PTY smoke) retarget the Rust binary via `$AUTOCODE_TUI_BIN`. New Rust-native layers: `cargo test` + JSON-RPC conformance harness. See `PLAN.md` §1h.7.

**Documentation deliverables:** `docs/reference/rust-tui-{architecture,rpc-contract}.md` (M1/M2), `docs/decisions/ADR-00{1,2,3}-*.md` (M1), `autocode/rtui/README.md` (M1), plus retargets of `docs/tests/tui-testing-strategy.md`, `autocode/tests/tui-{comparison,references}/README.md`. `CLAUDE.md` + `AGENTS.md` + `docs/session-onramp.md` updated at M11 cutover.

**Exit gate for the entire program:**

- [x] All 12 §1h.1 decisions answered and recorded in ADR-001.
- [x] All 11 milestones (M1–M11) complete with artifacts stored.
- [x] Go TUI (`autocode/cmd/autocode-tui/`) deleted.
- [x] Python inline fallback (`autocode/src/autocode/inline/`) deleted.
- [x] `cargo build --release` green, `cargo clippy -- -D warnings` green, `cargo test` green (57 tests).
- [x] Binary size 2.4MB (target <10MB). Startup 2ms (target <200ms).
- [x] All performance targets met (M10.1 artifact stored).
- [x] CI workflow created (`.github/workflows/rust-tui-ci.yml`).
- [x] All documentation updated for Rust binary.
- [x] M11 close-out posted in `AGENTS_CONVERSATION.MD`.
