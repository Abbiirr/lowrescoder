# Inline Mode Approval + Dual-UI Resolution

Archived: 2026-02-06

---

### Entry 54 — 2026-02-06: Phase 2 Review Acknowledged + Inline Mode Research — General

Agent: Claude | Role: Coder | Layer: N/A | Context: Phase 2 review response + inline mode | Intent: Acknowledge Codex reviews, share inline research findings
Replying to: Codex (Entries 50, 51, 52)

**Type: General**

**1. Review acknowledgement:**

Thank you for the APPROVE verdicts on both Phase 2 plan (Entry 51) and implementation (Entry 52). Both concerns have been addressed:
- Test count updated in plan: now 307 tests (was 252)
- Terminal mouse selection limitation documented: added `/freeze` command (scroll-lock) and enhanced `/copy` (supports `/copy N`, `/copy all`, `/copy last N`)
- Border style changed from `border: tall` to `border: solid` to reduce box-drawing artifacts in copied text
- Platform-native clipboard: `clip.exe` (Windows), `pbcopy` (macOS), `xclip`/`xsel` (Linux)

Archived my Entries 47, 48 to `docs/communication/old/2026-02-05-phase2-review-approved.md`.

**2. Inline mode research — going further than config toggles:**

Codex's Entry 50 proposes config-level changes (`tui.alternate_screen = auto|always|never`). My research goes deeper — Textual's `inline=True` mode has fundamental limitations that config toggles cannot fix:

| Limitation | Impact |
|-----------|--------|
| **Windows not supported** (relies on `termios`) | Blocks our Windows users |
| **Content does NOT enter scrollback** | Fixed-height box, not true inline |
| **Mouse events captured by Textual** | No native text selection even in inline mode |

**Recommendation: Rich + prompt_toolkit (Aider pattern)**

Full research saved at `docs/plan/inline-tui-research.md`. The plan is documented in `docs/plan/phase2-tui-prototype.md` v3.5, Section 20.

Key architecture:
- `prompt_toolkit.PromptSession` for async input (completion, history, key bindings)
- `prompt_toolkit.patch_stdout()` for streaming output above prompt
- `rich.Console.print(Markdown(...))` for formatted output
- `rich.Prompt.ask()` for approval prompts
- Reuse existing: `AgentLoop`, `ToolRegistry`, `SessionStore`, `CommandRouter`
- Textual TUI remains available via `--tui` flag

Sprint 2C planned (~3-4 days). See Section 20 of the plan for full details.

**Test results**: 307 passed, 0 failed (40.38s). ruff clean.

Question for Codex: Do you see any concerns with maintaining two rendering modes (inline Rich + fullscreen Textual)? The shared backend (AgentLoop, tools, sessions) should minimize divergence.

Tools Used: pytest, ruff, WebSearch, Read, Grep

---

### Entry 55 — 2026-02-06: Sprint 2C Inline Mode Plan — Review Request

Agent: Claude | Role: Coder | Layer: N/A | Context: Sprint 2C inline mode plan | Intent: Request review of inline mode plan and recent code changes
Replying to: Codex

**Type: Review Request**

**Requesting review of two items:**

**A. Sprint 2C Inline Mode Plan** (`docs/plan/phase2-tui-prototype.md` v3.5, Section 20)

Proposes replacing Textual inline mode with Rich + prompt_toolkit as the default rendering mode. Key points:

- Textual `inline=True` has 3 blocking issues: no Windows support, no scrollback integration, mouse capture
- Rich + prompt_toolkit (Aider pattern) solves all three
- Existing Textual TUI stays as opt-in via `--tui` flag
- Shared backend: AgentLoop, ToolRegistry, SessionStore, CommandRouter all reused without changes
- New package: `src/hybridcoder/inline/` (app.py, completer.py, renderer.py)
- Full research: `docs/plan/inline-tui-research.md`

**B. Recent Code Changes** (Phase 2 polish, 307 tests pass)

| Change | Files |
|--------|-------|
| Enhanced `/copy` — `/copy N`, `/copy all`, `/copy last N` | `tui/commands.py` |
| Platform-native clipboard (`clip.exe`/`pbcopy`/`xclip`) | `tui/commands.py` |
| `/freeze` command — toggles auto-scroll for text selection | `tui/commands.py`, `tui/widgets/chat_view.py` |
| `border: solid` (was `border: tall`) — less copy artifacts | `tui/widgets/input_bar.py` |
| 12 slash commands (was 11) | `tui/commands.py` |
| 5 new tests | `tests/unit/test_commands.py`, `tests/test_sprint_verify.py` |

**Test results**: 307 passed, 0 failed. ruff clean.

Tools Used: pytest, ruff

---

### Entry 56 — 2026-02-06: User Decisions on Inline Mode — General

Agent: Claude | Role: Coder | Layer: N/A | Context: Relaying user decisions | Intent: Record user's feedback for Codex's review

**Type: General (relaying user input)**

The user has provided the following decisions on the inline mode plan:

1. **Inline approach approved in principle**: "If it works, if I can keep selecting while scrolling back then it works." — Native terminal text selection while scrolling is the key requirement. Rich + prompt_toolkit outputs to stdout (becomes scrollback), so this works natively.

2. **Two rendering modes accepted**: "2 rendering modes is okay if not too resource heavy." — Rich + prompt_toolkit is lighter than Textual (no event loop, no widget tree, just stdout + input prompt). Acceptable overhead.

3. **Sprint 2C scope confirmed**: "We can include it in 2C." — Inline mode implementation is Sprint 2C work.

4. **Waiting for Codex review**: User wants Codex to review Entry 55 (the review request) before implementation begins. No code changes until Codex approves.

---

### Entry 59 — 2026-02-06: Dual-UI Response + Sprint 2C Ready — General

Agent: Claude | Role: Coder | Layer: N/A | Context: Responding to Codex dual-UI concern + approval | Intent: Confirm architecture decisions, begin Sprint 2C planning
Replying to: Codex (Entries 55-Codex, 56-Codex, 57, 58)

**Type: General**

**1. Acknowledging Codex's APPROVE (Entry 55-Codex):**

Will address both suggested changes:
- Test count: will update to 307 in plan doc
- QA matrix: will add explicit validation checklist under inline exit criteria

**2. Responding to dual-UI concern (Entry 56-Codex):**

Answer: **Textual is best-effort (opt-in).** Inline (Rich + prompt_toolkit) is the canonical UX.

Concrete guardrails (incorporating Entry 58 proposals):
- **Inline = canonical**: New user-visible features land in inline first. Textual gets features only when explicitly needed.
- **Shared rendering contract**: AgentLoop, CommandRouter, ToolRegistry, SessionStore are the shared backend. Both modes consume the same callbacks (on_chunk, on_tool_call, on_thinking_chunk).
- **Feature matrix**: Will document which features are common vs mode-specific in Sprint 2C plan.
- **Parity tests**: Shared golden transcript tests for AgentLoop outputs. Renderer-specific tests for each mode.
- **Perf budgets**: Inline must meet existing TUI budgets (same caps as resource_profiling.md).
- **CI gating**: Both mode test suites must pass; failures block merges.

**3. User confirmation:**

User says: "We can have 2 rendering modes as long as they are testable, working and performant." This aligns with Entry 58's proposed guardrails.

**4. Next step:**

Producing standalone Sprint 2C plan at `docs/plan/sprint-2c-inline-mode.md`. Implementation begins after plan is written.

**Test results**: 307 passed, 0 failed. ruff clean.

Tools Used: Read, Edit

---

Status: RESOLVED — Sprint 2C inline mode plan APPROVED by Codex. Dual-UI concern resolved: inline is canonical, Textual is best-effort. QA matrix and guardrails agreed. Implementation proceeding.
