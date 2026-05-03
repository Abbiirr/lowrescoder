# `requirements_and_features.md` Drift Map — Input for S-DOCSREFRESH-A

> **Purpose:** identify which sections of `docs/requirements_and_features.md` have drifted from 2026-04-25 reality, so Codex can split S-DOCSREFRESH-A into focused sub-slices instead of one large rewrite.
> **Source doc:** `docs/requirements_and_features.md` — last updated 2026-02-17 (476 lines).
> **Method:** cross-reference against `docs/features_behavior.md`, `current_directives.md`, `docs/plan/deferred/modular_migration_plan.md`, and code spot-checks performed 2026-04-25.

## Drift severity legend

- **DEAD** — section describes a system that no longer exists. Mark HISTORICAL or remove.
- **STALE** — facts in the section are partially or wholly incorrect; rewrite needed.
- **STALE-COUNTS** — structure correct, only numeric facts (test counts, tool counts) are wrong.
- **PARTIAL** — some bullets accurate, others stale; line-level edits needed.
- **CURRENT** — accurate enough; no edit needed.

## Section-by-section assessment

| Section | Title | Severity | Notes |
|---|---|---|---|
| §1 | Project Overview | CURRENT | "8GB VRAM" target still accurate. Reference to `CLAUDE.md` still valid. |
| §2.1 | CLI Commands | PARTIAL | Lists `autocode chat` as primary; today bare `autocode` is the canonical interactive launch (per memory `feedback_inline_is_shipping_frontend.md`). `autocode --mode inline\|altscreen` is preferred; `autocode chat ...` still supported. Update to lead with bare command. Add `autocode --attach HOST:PORT`, `autocode serve --transport tcp\|stdio`. Keep `--tui` (Textual fallback) and `--legacy` as documented fallbacks. |
| §2.2 | LLM Integration (Layer 4) | PARTIAL | Two providers listed (Ollama, OpenRouter) — still accurate, but should mention LiteLLM gateway `http://localhost:4000/v1` as the active L4 path. Thinking-token note ("currently parsed but not requested") will become stale once S-THINK-A lands; revisit drift after that slice. |
| §2.3 | Agent System | STALE-COUNTS | `MAX_ITERATIONS = 10` is wrong; current value is 1000 per `loop.py`. Cancellation, prompts, and project memory loading all still accurate. |
| §2.4 | Tool Registry (19 Tools) | STALE | Lists 19 tools; current registry has ~60 tools per Explore audit (`agent/tools.py` 1912 lines, ~60 built-in handlers + task tools + subagent tools). Regenerate the table from `CORE_TOOL_NAMES` (14 core) + the deferred set. Reference `tool_search` meta-tool. Update which tools require approval. |
| §2.5 | Approval System | DEAD | Multiple bullets reference `InlineApp._arrow_select`, `_approval_prompt_parallel`, `_session_approved_tools` — the InlineApp surface is GONE (Python inline REPL deleted per §1h M11). Approval semantics still apply but live in `_ServerAppContext` now. Replace InlineApp references with `BackendServer`/`_ServerAppContext` references. The 4 modes (READ_ONLY/SUGGEST/AUTO/AUTONOMOUS) and shell scoping are still accurate. |
| §2.6 | Session Management | CURRENT | SQLite WAL store, message persistence, tool call tracking, compaction, auto-titling — all still accurate. |
| §2.6b | Structured Logging & Training Data | CURRENT | All bullets still accurate. |
| §2.7 | Inline REPL (Primary UI) | **DEAD — REMOVE OR HISTORICAL** | Entire section describes the Python inline REPL with prompt_toolkit. That surface was deleted in §1h M11. Replace with a short paragraph describing the Rust TUI as the current primary frontend, with `autocode chat --tui` (Textual) and `autocode chat --legacy` (Rich REPL) as documented fallbacks. Move the inline-REPL bullet list to a "Historical: Python inline REPL (removed 2026-04-19)" subsection or delete entirely. |
| §2.8 | Textual TUI (Fullscreen Mode) | PARTIAL | Still exists but is now a fallback only. Reframe as "fallback fullscreen UI" rather than first-class. |
| §2.9 | Input Features | DEAD | Heavy Go-TUI references (`textinput.SetSuggestions`, `textinput.ShowSuggestions`, `CompletionStyle`, `renderCompletionDropdown` in `view.go`, `session_picker.go`). Go TUI is GONE. Replace with current Rust TUI input features (composer, slash autocomplete, history navigation, picker/palette, paste handling, editor round-trip). |
| §2.10 | Slash Commands (19) | STALE-COUNTS | Today the list is longer. Verified via `app/commands.py:1100+`: at least 27 `SlashCommand` registrations including `/cost` (line 1317). Regenerate the table. Add `/thinking`, `/tasks`, `/plan`, `/memory`, `/checkpoint`, `/cost`, etc. that exist today. Note `/thinking` semantics WILL CHANGE after S-THINK-A — flag for re-edit. |
| §2.11 | Configuration | CURRENT | YAML, Pydantic model, LLM/UI/Shell settings — accurate. Will need a one-line addition once S-COST adds `agent.cost_limit_usd`. |
| §2.12 | Tests | STALE-COUNTS | Says "275 Go + 1022 Python = 1297+ tests"; "1015 passed". Today: **1871 Python unit, 199 benchmark, 181 Rust = 2251 tests**. No Go tests (Go TUI deleted). Replace counts and test-file enumeration. |
| §2.13 | E2E Evaluation System | PARTIAL | Calculator benchmark engine still real. E2E-BugFix and E2E-CLI scenarios still real. Verify B7-B29 lane status references current `current_directives.md` instead of the older E2E framing. The "PR Core baseline: E2E-Calculator + E2E-BugFix + E2E-CLI" line may be stale. |
| §2.14 | Phase 3: Code Intelligence | PARTIAL | "All gates passed; 840 Python tests" is a 2026-02-13 snapshot. Layer 1 + Layer 2 capabilities are still real. Update references to "current test count" or remove the count line and link to live-state docs. |
| §3.1 | Phase 4 — Agent Orchestration & Context Intelligence | PARTIAL | Sprint 4A/4B/4C marked DONE, accurate as history. Section is fine if framed as "historical phase status." |
| §3.2 | Phase 5 — Universal Orchestrator | STALE — RECONCILE WITH MODULAR WORK | Says "PROVISIONAL_LOCKED" and references `docs/plan/phase5-agent-teams.md`. The actual modular Phase 5 (swapability proof) was closed 2026-04-23 per Entry 1402 + 1421. These are TWO DIFFERENT THINGS sharing the name "Phase 5" — confusing. Either clarify that this is "Phase 5 Universal Orchestrator (legacy plan)" vs "Modular Phase 5 (architecture proof)", OR move the legacy entry to a Historical Plans appendix. |
| §4 | Resolved UX Issues (Phase 2) | CURRENT | Historical accuracy preserved. The 8 issues are correctly framed as resolved. |
| §5 | Architecture Decision: Go Bubble Tea TUI Rewrite | **DEAD — MOVE TO HISTORICAL** | The Go Bubble Tea decision was correct in early 2026; it has been SUPERSEDED by the Rust migration (§1h M11, 2026-04-19). Move the entire section to a "Historical Architecture Decisions" appendix with a top note "Superseded by Rust TUI migration (§1h M11, 2026-04-19)." Do NOT delete — preserves design provenance. |
| §6 | Target Metrics (MVP) | PARTIAL | "Unit tests: 500+ passing — current 275 Go + 942 Python = 1217+" is wrong on counts and source mix. Update to current test totals. Other metrics (LLM call reduction, edit success rate, latency, memory) are aspirational and largely unmeasured — keep but mark as "targets, not measurements." |
| §7 | Technology Stack | STALE | Says "TUI Frontend: Go + Bubble Tea — Active." Should be "Rust + Ratatui — Active." Other entries (Python, uv, Typer, tree-sitter, LanceDB, jina-v2-base-code, LLM Gateway, model alias) still accurate. Update Go row to "DELETED" or move to historical. Add Rust + portable-pty + crossterm + ratatui rows. |

## Suggested S-DOCSREFRESH-A split (per R8 in plan §12)

- **S-DOCSREFRESH-A.1 — Section 2 catalog rewrites** (the largest lift)
  - Subsections to rewrite: §2.1, §2.4, §2.5, §2.7, §2.8, §2.9, §2.10
  - Subsections to fix counts only: §2.3, §2.12
  - Subsections to leave: §2.6, §2.6b, §2.11, §2.13 (verify), §2.14 (verify)
  - Effort: M (~3-5 days)
- **S-DOCSREFRESH-A.2 — Sections 5 + 7 historical demotion**
  - Move §5 to Historical Architecture Decisions appendix
  - Update §7 Technology Stack rows
  - Effort: S (~1 day)
- **S-DOCSREFRESH-A.3 — Section 3.2 Phase-5 disambiguation**
  - Clarify legacy "Phase 5 Universal Orchestrator" vs modular "Phase 5 swapability proof"
  - Move legacy plan to Historical Plans appendix if Phase 5 (legacy) is no longer the active intent
  - Effort: S (~1 day)
- **S-DOCSREFRESH-A.4 — Cross-reference + link audit**
  - After A.1/A.2/A.3, run a link checker over the updated doc
  - Verify references to other docs still resolve (e.g., `docs/plan/phase4-agent-orchestration.md` may have moved)
  - Effort: S (~half day)

## Validation

For each sub-slice:
- `markdown-link-check docs/requirements_and_features.md` (or equivalent — current repo doesn't have a link checker yet; could use `grep` to verify referenced files exist)
- Read the updated section in context: does a fresh reader get a current picture without confusion?
- No tests run for doc-only slices, but the slice's verification artifact should include screenshots of before/after table changes for sections 2.4 and 2.10 (the catalog tables).

## Out of scope for this drift map

- `PLAN.md` (separate slice S-DOCSREFRESH-C)
- `EXECUTION_CHECKLIST.md` (S-DOCSREFRESH-D)
- `current_directives.md` (S-DOCSREFRESH-E)
- `autocode/TESTING.md` (S-DOCSREFRESH-F)
- Archive-superseded-plans pass (S-DOCSREFRESH-G)

## Source references

- `docs/requirements_and_features.md` (the doc being assessed; 476 lines)
- `docs/features_behavior.md` (current runtime inventory)
- `current_directives.md` (active directives)
- `docs/plan/deferred/modular_migration_plan.md` and `docs/plan/deferred/modular_migration_todo.md` (architecture state)
- `autocode/src/autocode/app/commands.py` (slash command source of truth, line 1100+)
- `autocode/src/autocode/agent/tools.py` (tool registry source of truth, ~60 tools)
- `autocode/src/autocode/agent/loop.py` (MAX_ITERATIONS = 1000)
