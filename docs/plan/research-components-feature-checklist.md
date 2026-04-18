# Research-Components Feature Checklist

Consolidated from three parallel source audits of `research-components/` + cross-check against `deep-research-report.md` and the existing AutoCode code. Each row is a portable pattern, its source anchor, its current AutoCode status, and a port-worth rating.

**Sources audited:**
- `research-components/pi-mono/` (pi coding agent, TypeScript monorepo)
- `research-components/claude-code/` + `research-components/claude-code-sourcemap/` + `research-components/kuberwastaken-claude-code/` (Claude Code CLI, multiple mirrors)
- `research-components/opencode/` (OpenCode, provider-agnostic TUI)
- `research-components/openai-codex/` (Codex CLI)
- `research-components/aider/` (Aider, repo-map-first editor)
- `research-components/claw-code/` (Claw Code, verification harness)
- `research-components/goose/` (Block's Goose, MCP-first)
- `research-components/open-swe/` (SWE-bench-style sandboxed)
- `research-components/gastown/`, `research-components/nodepad/`, `research-components/t3code/` (minor; mostly skipped)

**Rating:**
- **HIGH** — clear UX win, small-to-moderate effort, immediate benefit
- **MED** — meaningful improvement, larger effort or design dependency
- **LOW** — niche or covered by existing code
- **SKIP** — not applicable to AutoCode's shape

Rows marked `[DONE]` have already landed in this session's Stable TUI v1 slices.

---

## Tier 1 — HIGH port worth, bugs tied to current user screenshots

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T1-1 | **Picker filter match counter shows `[cursor/filter-count]`, not `[cursor/total]`** | pi-mono `packages/tui/src/components/select-list.ts:103-107` | `cmd/autocode-tui/view.go:247` uses `len(completions)` which is already filtered, so counter renders the filtered count today. BUG observed in user screenshot where `[1/45]` appeared — likely empty-filter edge case (composer = `/`, matches all 45). Verify this is not a user-visible surprise by never showing the counter when filter is empty and list is the full known set. | HIGH |
| T1-2 | **Composer height tracks line count exactly (min 1, max 8), no `+1` padding** | pi-mono editor `packages/tui/src/components/editor.ts`; claude-code inline mode | `composer.go` had `composerMinH=3` and `h = lines+1`. **[DONE]** this session: `composerMinH=1`, `h = lines` in `composerAutoHeight()`. Single `❯` prompt row now. | HIGH |
| T1-3 | **Inline-by-default (no alt-screen)** | claude-code CLI, pi-mono REPL | `main.go` was `--inline=false` default. **[DONE]** this session: flipped to inline default, `--altscreen` opt-in. | HIGH |
| T1-4 | **Session list shows sanitized titles only — no composer-placeholder leak** | pi-mono `session-manager.ts`; claude-code history.ts | User screenshot showed `Ask AutoCode…llo (tools)` in `/sessions` list. Backend-side bug; Go TUI reads `s.Title` directly. Hunt where Python backend derives session titles and ensure composer placeholder is never persisted as a title. | HIGH |
| T1-5 | **Completion dropdown never renders composer echo inline** | pi-mono select-list (filter text rendered separately from items) | User saw `mo` (the filter text) floating inside the dropdown as a list row. Need to confirm `view.go::renderCompletionDropdown` never includes composer text; may be a terminal repaint artifact. | HIGH |
| T1-6 | **Slash-command typeahead with aliases + auto-run for zero-arg commands** | claude-code-sourcemap `src/hooks/useSlashCommandTypeahead.ts:26-100` | `completion.go::getSlashCompletions` does prefix + fuzzy, but no alias awareness and no auto-run. `/m` is both a command and an alias; need to show the canonical resolve. | HIGH |
| T1-7 | **Settings merge: project `.claude/settings.json` then user `~/.claude/settings.json`** | claude-code hooks + `docs/reference/claude-settings.sample.json` | `hooks.py::HookRegistry.load()` already does project + user merge. **[DONE]** pre-session. | DONE |

## Tier 2 — HIGH, net-new functionality worth a dedicated slice

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T2-1 | **LSP tool surface: goToDefinition / findReferences / hover / documentSymbol / workspaceSymbol / implementations / call-hierarchy** | opencode `packages/opencode/src/tool/lsp.ts:23-97` | AutoCode has `layer2/lsp_tools.py` but only a partial Python binding. Port the 9-op surface and expose each as an agent tool. | HIGH |
| T2-2 | **Codex-style resumable thread (`startThread` / `resumeThread(id)`)** | codex-cli `sdk/typescript/src/codex.ts:25-38` | `session/store.py` persists but has no `/resume <id>` symmetric API. Add `thread.resume` RPC. | HIGH |
| T2-3 | **Sandbox modes: `read-only` / `workspace-write` / `danger-full-access`** | codex `sdk/typescript/src/exec.ts:9-40`; claw-code `permissions.py` | `agent/sandbox.py` already has `SandboxPolicy` with NONE/READ_ONLY/WRITABLE_PROJECT/FULL_ISOLATION. Surface a `/sandbox <mode>` slash command so users can switch mid-session. | HIGH |
| T2-4 | **Structured JSON output mode (`--json`, `--output-schema`)** | codex `exec.ts:73,111` | AutoCode's TUI is ANSI-only. Add a headless `autocode-tui --json` mode for programmatic clients. | HIGH |
| T2-5 | **Agent persona switch (build vs plan) with Tab-toggle** | opencode README:101-109 | `agent/mode.py` exists (RESEARCH, PLANNING, BUILD, REVIEW) — all defined, but no Tab-bound switch in TUI. | MED |
| T2-6 | **Slash-command registry with extension-registered commands** | pi-mono `core/slash-commands.ts:1-40`, `core/extensions/loader.ts:1-80` | `commands.go::knownCommands` is a static `[]string`. Refactor to a registry that hooks/extensions can append to. | MED |

## Tier 3 — Session / compaction / context intelligence

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T3-1 | **JSONL session tree with `id` + `parentId` enabling in-place forks (`/fork`, `/tree`)** | pi-mono `core/session-manager.ts:1-120` | AutoCode has SQLite+WAL, single linear timeline. Not trivial to retrofit; design doc needed. For v1, skip; post-v1 port the branching semantics. | MED |
| T3-2 | **Automatic compaction with `reserveTokens=16384`, `keepRecentTokens=20000`** | pi-mono `core/compaction/compaction.ts:110-120` | `agent/remote_compaction.py` exists but not threshold-gated. Add `contextTokens > contextWindow - reserveTokens` trigger. | MED |
| T3-3 | **Branch-summary auto-injection when resuming an alternate path** | pi-mono compaction module | Depends on T3-1. | LOW |
| T3-4 | **Repo-map token-aware ranking** | aider `aider/repomap.py:47-150` | `layer2/repomap.py` exists with token budgeting. Cross-check against aider's dependency-graph ranking and adopt if better. | MED |
| T3-5 | **Compaction provenance preservation** (user/tool/file origin labels survive summary) | deep-research-report.md §Security; codex+claude analyses | **[DONE]** Slice 5 landed additive `Provenance` field + `classify_message_provenance`. | DONE |

## Tier 4 — Safety / approval UX

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T4-1 | **Command-scoped allowlist ("always allow `git *` in this cwd")** | claude-code-sourcemap `permissions/toolUseOptions.ts:15-59` | `approval.go` has "Yes / Yes, this session / No" but no prefix-allow. Add to `.claude/settings.json` schema. | HIGH |
| T4-2 | **Command-injection detection before offering "don't ask again"** | claude-code-sourcemap permission flow | No detection today. Add a small parser that flags `$()`, backticks, `;`, `&&`, `||` chains. | MED |
| T4-3 | **`--deny-tool`, `--deny-prefix` CLI flags** | claw-code `src/main.py:45-46` + `permissions.py` | Only env-based policy today. Add flag surface for one-shot runs. | MED |
| T4-4 | **Approval dialog "Esc returns to compose with feedback prompt"** | claude-code `sourcemap/src/components/permissions/` | `approval.go` Esc cancels outright. Match claude-code: Esc → compose mode preloaded with "rejected because…" template. | MED |
| T4-5 | **PreToolUse hook blocking (exit != 0 OR `{"block":true}`)** | claude-code settings.json hooks | **[DONE]** Slice 4 — `agent/hooks.py` PreToolUse with both protocols. | DONE |

## Tier 5 — Extensibility & ecosystem

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T5-1 | **SKILL.md frontmatter discovery with progressive disclosure** | claude-code / pi-mono skills; docs/reference/skills-contract.md | **[DONE]** Slice 3 — `agent/skills.py` with project + user scope, progressive disclosure, live reload, 20 tests. | DONE |
| T5-2 | **MCP server discovery + tool namespace isolation** | goose `crates/goose/src/acp/mod.rs` | No MCP support in AutoCode today. Would need Rust or Python MCP client. Post-v1. | MED |
| T5-3 | **Extension hot-reload (TS modules intercept tool calls, register commands)** | pi-mono `core/extensions/loader.ts` | Pi's loader uses jiti + Node; not portable to Go TUI + Python backend directly. Design a simpler Python-extension contract in Python backend. | MED |
| T5-4 | **`opencode.json` config layering (project overrides global, enterprise-managed path)** | opencode provider config | `config.py` has YAML/TOML but no layering story. Minor. | LOW |
| T5-5 | **Recipe / workflow templates (goose-style)** | goose CUSTOM_DISTROS.md | Covered by AutoCode skills + Makefile pattern. | LOW |
| T5-6 | **Aider-style auto-commit after edit + per-language linter feedback loop** | aider `linter.py:21-106`, coders/base_coder auto_commit | `agent/verification_profiles.py` (Slice 6) covers the linter surface. Auto-commit is a separate small slice. | MED |

## Tier 6 — Headless / remote / verification

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T6-1 | **JSONL RPC over stdin/stdout for external UI clients** | pi-mono `modes/rpc/rpc-types.ts:1-120`, `docs/rpc.md` | Python backend already uses JSON-RPC. Formalize events for external UI clients. | MED |
| T6-2 | **`opencode serve` HTTP endpoint + `opencode attach` remote client** | opencode `packages/opencode/src/` | Out of scope per PLAN.md §1f "non-goals". | SKIP |
| T6-3 | **Verification profiles (formatter/lint/typecheck/test) + hook-gated execution** | claw-code doctor; deep-research-report Milestone F | **[DONE]** Slice 6 — `agent/verification_profiles.py` with python/go/js/rust. Hook wiring hook-ready. | DONE |
| T6-4 | **`claw doctor` diagnostics mirroring bootstrap + runtime stages** | claw-code `src/main.py:24,30` | `cli.py` has `doctor` subcommand; audit depth and mirror claw-code's checks (bootstrap-graph, tool-pool). | MED |
| T6-5 | **Transcript/export JSONL shape with replay support** | claude-code history.ts, pi-mono session-manager | `artifact_collector.py` collects transcripts. Formalize export schema for interop. | MED |

## Tier 7 — Layout polish / TUI chrome

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T7-1 | **Tool-call cards: collapsed summary + expand-on-Enter with result preview** | claude-code CLI, pi-mono | `view.go::renderToolArea` shows one-line per call today. Upgrade to card with `[↳ N lines, click to expand]`. | MED |
| T7-2 | **Grapheme-aware cursor / paste-marker atomic handling** | pi-mono `tui/src/components/editor.ts:1-100` | Bubble Tea textarea is already solid on most graphemes. Low priority. | LOW |
| T7-3 | **Status-bar live cost / token counter** | claude-code CLI | `statusbar.go` already shows cost + token accumulator from Phase 6. | DONE |
| T7-4 | **Queue indicator in status bar ("2 queued")** | pi-mono followUp queue | `statusBar.Queue` field exists. Verify rendering. | DONE |
| T7-5 | **`/permissions` in-session mode switch** | codex, claw-code | Not surfaced in Go TUI yet; back end exists via T2-3. | MED |

## Tier 8 — Benchmarks / large-repo / measurement

| # | Feature | Source anchor | AutoCode gap | Rating |
|---|---|---|---|---|
| T8-1 | **SWE-bench-style sandbox per task + auto-recreate** | open-swe README:52-62 | Harbor adapter exists for B30. Leave as-is for now. | LOW |
| T8-2 | **Large-repo comprehension agent mode** | pi-mono, aider | `/research` mode exists (Section 1 of EXECUTION_CHECKLIST). | DONE |
| T8-3 | **Operational metrics dashboard (skill trigger accuracy, hook success, retry counts, compaction failures)** | deep-research-report.md Milestone F | Only cost dashboard today. Add metrics ingestion per session. | MED |

---

## Non-goals (per deep-research-report.md §"Explicit Non-Goals")

These are **not** queued regardless of port worth:
- Remote-client architecture work (opencode serve/attach beyond headless JSONL)
- Broad subagent UX as default path
- Worktree fleets / Level-5 orchestration
- Parity-only features that don't improve stability, compatibility, or verification

---

## Next-slice suggestion (post this session)

Sort candidates by Tier 1/2 HIGH rows not already done:

1. **T1-4 session title sanitization** (bug-match to user screenshot)
2. **T1-5 composer echo isolation** (bug-match)
3. **T1-6 slash-command alias + auto-run**
4. **T2-1 LSP tool surface port** (9 ops)
5. **T2-3 `/sandbox <mode>` slash command**
6. **T4-1 command-scoped allowlist**
7. **T2-5 agent persona Tab-toggle**
8. **T3-4 repo-map ranking cross-check**

Each should become its own slice with tests + PTY evidence + VHS snapshot before merge.
