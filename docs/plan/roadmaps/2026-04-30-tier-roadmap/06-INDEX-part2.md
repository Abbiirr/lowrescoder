# AutoCode Roadmap — Part 2

**Drafted:** 2026-04-30, after research on harness engineering (2026), ratatui rendering internals, OpenCode/Codex/Hermes TUI architectures, and post-Tier-4 reliability work.

This part picks up where `00-INDEX.md`'s Tier 4 ends. Tiers 1–4 made AutoCode *capable*. Tiers 5–8 make it *reliable* and *minimal* enough to stay maintainable.

## The shift in 2026

Three findings dominate the 2026 literature on agent harnesses:

1. **65% of enterprise AI failures trace back to harness defects, not model defects** — specifically context drift, schema misalignment, and state degradation (MemU + Atlan research, late 2025/early 2026)
2. **Context degrades 2% per step** in multi-step workflows — after 5 cycles, less than 60% of original context remains reliably accessible (MemU 2026)
3. **88% of AI agent projects never reach production** — and that number hasn't improved as models got more capable (Atlan 2026)

The conclusion: **stop adding features, start adding sensors**. Tiers 5–8 reflect this.

## Document map

| File | Topic | When to read |
|---|---|---|
| `06-INDEX-part2.md` | this file | overall sequencing |
| `07-tier5-harness-reliability.md` | drift detectors, schema validation, Plan-Execute-Verify, Ralph Loop | when first production users find weird failures |
| `08-tier6-minimal-tui.md` | a 1500-LOC Rust TUI rewrite, ratatui best practices, performance budget | when current rtui's 30k+ LOC becomes a maintenance burden |
| `09-tier7-context-engineering.md` | filesystem-as-context (Manus pattern), context entropy management, recovery loops | when long sessions start producing degraded output |
| `10-tier8-observability-evals.md` | per-tier telemetry plumbing, eval suite, regression detection | when "did this PR make things worse?" becomes a recurring question |

## Execution order

```
After Tier 1-4 ship (~3 months from now):

Month 4-5    Tier 5 (harness reliability — drift detectors)
Month 5-6    Tier 6 (minimal TUI — runs in parallel with Tier 5)
Month 6-7    Tier 7 (context engineering — Manus filesystem pattern)
Month 7-8    Tier 8 (observability + evals)
```

Tiers 5 and 6 can run in parallel — they touch different code. Tiers 7 and 8 should run after both finish.

## Why this ordering

- **Tier 5 first** because reliability problems compound. Every week without drift detectors is a week of silently-degrading agent behavior accumulating in user sessions.
- **Tier 6 in parallel** because the current rtui (4500+ LOC across `state/model.rs`, `render/view.rs`, `ui/composer.rs`) is already showing maintenance fatigue per the team's own commit messages ("Stabilizes rust tui," "Inventories bugs in new tui"). A minimal rewrite at 1500 LOC isn't speculative — it's the only path to fixing what bug-fixing alone won't catch up with.
- **Tier 7 third** because filesystem-as-context delivers the biggest reliability win after drift detection is in place. Microsoft's Azure SRE Agent moved from 100+ bespoke tools to a filesystem-based system and improved "Intent Met" from 45% to 75%.
- **Tier 8 last** because evals only catch what they were designed to catch. You write evals against known failure modes — and you don't know your failure modes until you've run in production for a while. Tier 8 codifies what Tier 5 detected.

## Success criteria

### Tier 5 — measurable
- Schema drift detector flags ≥ 90% of column renames within 1 turn
- Context staleness sensor warns when memory facts older than 7 days
- Plan-Execute-Verify (PEV) gate catches ≥ 50% of plans that would have produced failing tests
- Ralph Loop recovers ≥ 80% of sessions that hit context limits

### Tier 6 — externally observable
- Cold-start to first frame: < 80 ms (currently ~250 ms)
- Memory footprint: < 30 MB resident (currently ~85 MB)
- Lines of code: < 1500 (currently ~4500)
- Parity with current rtui on all 9 stages and 9 detail surfaces
- Render diff applied per frame: < 10 cells changed during streaming

### Tier 7 — qualitative
- Agent uses `read_file` to look up context instead of asking model to recall
- Tool result outputs > 5KB get written to `.autocode/scratch/<turn-id>/<tool>-<idx>.md` and only path is kept in context
- Model acceptance: agent-written summaries closer to user-written summaries (LLM-judge eval)

### Tier 8 — operational
- One `autocode telemetry summary` command shows: cost, cache hit ratio, drift incidents, recovery loop trigger rate, eval suite pass rate
- Pre-merge eval gate runs in < 3 min
- Each merged PR contributes one new eval case (capturing the bug it fixed)

## What this part deliberately omits

- **Multi-agent coordinator** — interesting, but only worth doing if a concrete second specialized agent is needed (e.g., a dedicated debug agent). Speculative until then.
- **MCP server hosting** — AutoCode is already a consumer of MCP via `tool_search`; becoming a host adds surface area without clear benefit
- **Web UI** — covered by Tier 2 (App Server protocol). Once the protocol is stable, a thin Vercel/Tauri client is ~3 days, not a tier
- **Voice mode** — same reasoning as Tier 4
- **Replay/debugger** — useful but expensive to build well; defer until evals (Tier 8) reveal it's needed

## Dependencies on Tier 1-4

| Part 2 tier | Needs from Part 1 |
|---|---|
| 5.1 (drift detectors) | Tier 3.1 (file-based memory; logs to grep) |
| 5.2 (PEV) | None — works standalone |
| 5.3 (Ralph Loop) | Tier 1.2 (stable/dynamic boundary so cleared context is rebuildable) |
| 6.x (minimal TUI) | Tier 2.1 (Item/Turn/Thread protocol — the new TUI consumes this directly) |
| 7.1 (filesystem context) | Tier 3.1 (memory infrastructure) |
| 7.2 (context entropy) | Tier 3.2 (Session Notes) |
| 8.x (observability) | Tier 1.3 (token tracker baseline) |

If the team wants to start a Part 2 tier before Part 1 finishes, only Tier 5.2 (PEV) is doable in isolation.

## What changed since Part 1

Part 1 was written before the 2026 literature on agent harnesses solidified. Re-reading it now, three things look different:

- **Tier 4.1 (KAIROS)** looks weaker. The proactive-mode pattern is risky and unproven outside Anthropic's controlled environment. Defer indefinitely; spend the budget on Tier 5 reliability instead.
- **Tier 2.3 (turn/steer)** looks more important. Mid-flight steering is exactly the kind of correction mechanism that prevents context drift from compounding. Promote ahead of Tier 2.2 transports if reliability becomes the priority.
- **Tier 3.3 (verify-before-use)** looks more important — it's the only mechanism in Part 1 that addresses context staleness directly. Ship before 3.2 if scoping pressure forces a choice.

## A note on the harness vs. model framing

The 2026 consensus, captured by LangChain's "Agent = Model + Harness" formula and Anthropic/OpenAI both shipping serious harness infrastructure, is that the harness is where the engineering work lives. Manus spent six months on five rewrites; LangChain spent a year on four architectures. AutoCode has done one major rewrite (Go→Rust TUI) — the team is still in the early phase of harness maturity. Expect at least one more major refactor before reaching steady state.

The single best heuristic from the literature: **whenever the agent makes a mistake, build the solution that ensures it never makes that specific mistake again.** Codify each failure as a constraint, an eval case, or a sensor. Don't rely on better prompts.
