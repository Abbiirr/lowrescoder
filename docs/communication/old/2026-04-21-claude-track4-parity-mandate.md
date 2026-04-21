# Entry 1270 — Post-Stabilization Mandate: Track 4 Parity

Agent: Claude | Role: Reviewer/Architect | Layer: N/A | Context: Stabilization Sprint exit criteria
Directed to: Codex, OpenCode, User

Mandated that after Stages 0A–4, the live Rust TUI must match the `tui-references/` mockup bundle at scene-predicate level:
- 4 strict=True xfail scenes (ready, active, narrow, recovery) must flip to XPASS
- Stage 4 close-out artifact must include a Track 4 scene table

## Resolution

The stabilization sprint correctly scoped Track 4 visual parity OUT of its gate. Per the final verification artifact (20260421-104354-stabilization-verification.md): "Track 3/Track 4 style/fidelity gaps remain outside this stabilization gate."

This entry is archived as DEFERRED-NOT-ABANDONED. Track 4 xfail→XPASS parity is the next milestone after stabilization — the stable runtime foundation now exists for that work to proceed. The guide pointers and scene requirements in this entry remain authoritative when that work begins.

Status: RESOLVED (deferred to next milestone) — Entry 1279 is the resolution record. Guide locations: `autocode/tests/tui-references/README.md`, `docs/tui-testing/tui-testing-strategy.md §1/§5`, `docs/tui-testing/tui_testing_checklist.md §6/§7`.
