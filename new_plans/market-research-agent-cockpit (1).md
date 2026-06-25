# Coding-Agent Cockpit — Market Research

**Project:** GUI wrapper for coding agents (Codex-app-style, multi-harness like T3 Code)
**Prepared:** June 12, 2026 · v2
**Scope:** category definition, market context, deep teardowns of the two anchor products, competitive landscape, market signals, gap analysis, feature matrix, positioning, risks. All claims referenced; links in §10.

---

## 1. Executive summary

The "agent cockpit" category — GUIs that orchestrate existing coding-agent CLIs rather than building their own agent — has consolidated around a fixed core in under a year: parallel threads, a git worktree per task, a diff/review pane, and one-click commit→PR. Every credible product ships this; none of it differentiates anymore [7][13].

Three forces define the market in mid-2026:

1. **First-party squeeze.** OpenAI's Codex app (macOS/Windows) and Anthropic's April 14, 2026 redesign of Claude Code desktop (parallel sessions, drag-and-drop panes, integrated terminal/editor, cloud "Routines") now deliver most of what third-party wrappers built [1][2][20][21]. A single-provider wrapper has no future; cross-provider is the only defensible posture.
2. **Zero price tolerance.** Every surviving wrapper is free and bring-your-own-subscription. Conductor charges nothing [11]; T3 Code's pitch is literally "we don't resell tokens" [9]. The one company that tried to monetize the category directly — Bloop, behind Vibe Kanban — shut down on April 10, 2026 [13].
3. **Unclaimed flanks.** Nobody owns Linux-first (Codex app: waitlist only [1]; Conductor: Apple Silicon Mac only [11]), and nobody owns governance — audit trails, approval policies, team administration. Conductor's lack of team licensing/compliance is explicitly called a "hard stop" for team procurement [12].

**Recommendation:** build the table-stakes core (it's well-understood and ~8–10 weeks of work), differentiate on (a) Linux + self-hostable web access done securely, and (b) an auditable approval/action log aimed at regulated teams — the exact muscle BS23 already exercises in banking delivery. Treat the consumer "wrapper" market as a credibility play and dogfooding tool, not as the revenue line.

---

## 2. Category definition: the "harness approach"

These products do not call models directly. They wrap the official agent CLIs — Claude Code, Codex CLI, OpenCode, Cursor CLI — which already contain the agent loop, tools, sandboxing, and auth. T3 Code's creator frames it as a bet: a "harness" is the toolset an agent runs with, and instead of building one, T3 wraps the labs' official CLIs, wagering that labs keep investing in them [10]. The strategic thesis for the whole category was put crisply by one analyst: a GUI that treats Codex and Claude as interchangeable backends signals that "agent runtime is the commodity, the interface is what locks you in" [8].

What the wrapper actually adds:

- **Parallelism management** — N agents across M projects from one window
- **Isolation** — a git worktree (or container) per task so agents don't collide
- **Legibility** — structured rendering of plans, tool calls, and edits instead of terminal scroll
- **Review & ship** — diff viewer, staging, commit, push, PR without leaving the app
- **Persistence** — searchable thread history the terminal doesn't give you

---

## 3. Market context (why this category exists at all)

- AI code assistant market: **$4.70B (2025) → $14.62B (2033)**, 15.31% CAGR per SNS Insider [14]; a broader definition puts it at **$12.8B in 2026 → $30.1B by 2032** at ~27% CAGR [18].
- Adoption is near-saturated: **90% of developers** regularly use at least one AI tool for coding, 74% a specialized one (JetBrains, Jan 2026) [15]; **84%** use or plan to use AI (Stack Overflow 2025) [16]; an estimated **41% of global code** is now AI-generated [17].
- The agentic segment specifically: Cursor went **$100M → $1B → $2B ARR** between 2024 and March 2026, with enterprise revenue mix rising from 25% to 60% — bottom-up adoption followed by top-down procurement [17]. Claude Code adoption hit **24% in US/Canada** (18% globally) by Jan 2026 [17]; startups favor Claude Code (~75%) while large enterprises favor Copilot (~56%) for procurement reasons [18].
- The operator problem this category solves: once agents run for minutes–hours autonomously, **the bottleneck stops being the model and becomes the operator**; worktree-per-session or container-per-session is becoming standard practice [13].

Implication: the cockpit layer rides a very large wave but captures none of the model spend. Its monetizable surface is workflow, team coordination, and governance — or nothing.

---

## 4. Anchor teardown A — OpenAI Codex app

**What it is:** official desktop command center for Codex threads. macOS + Windows; **Linux is a notify-me waitlist**. Included in ChatGPT Plus/Pro/Business/Edu/Enterprise; sign-in via ChatGPT account or API key (API-key mode loses cloud threads) [1].

**Complete feature inventory** (from official docs [1][2]):

| Area | Features |
|---|---|
| Core model | Projects in a sidebar; parallel threads per project; project = sandbox scope |
| Thread modes | **Local** (work in the project dir) · **Worktree** (isolated git worktree) · **Cloud** (remote environment) |
| Git | Diff pane with **inline comments the agent addresses**; stage/revert chunks or files; commit, push, create PR in-app |
| Terminal | Per-thread integrated terminal (⌘J); **agent can read terminal output** (e.g., a running dev server); reusable "actions" buttons from local environments |
| Automations | Scheduled recurring tasks in background worktrees; **thread automations** that wake the same thread on a schedule (heartbeat loops) |
| Safety | Approval scopes ("approve once" / "for session"); sandbox controls for directories + network; optional automatic approval-review policy; native Windows sandbox (no WSL) |
| Extensibility | Skills (shared with CLI/IDE); MCP config shared across app/CLI/IDE; plugins |
| Inputs | Voice dictation (^M); drag-drop image input; agent can take screenshots to verify its work |
| Surfaces | Floating pop-out always-on-top thread window; **in-app browser** with element comments + agent browser-use; **computer use** (macOS GUI control; not in EEA/UK/CH); artifact previews (PDF/sheets/decks); task sidebar (plan, sources, summary) |
| Misc | Built-in web search (cached by default); image generation (gpt-image-2) in-thread; "Chats" (project-less threads); Memories; IDE-extension sync with auto-context; notifications; prevent-sleep |

**Design language (the reference for our v2 UI):** paper-white surfaces, hairline borders, almost no chrome; a slim plain-text sidebar (projects → threads); a wide centered conversation column where agent activity renders as **collapsed single-line rows** ("Ran command…", "Edited 3 files") that expand on demand; a quiet right-hand review pane; one dark primary button; color reserved for status dots and diff +/−. Information density comes from typography and spacing, not boxes.

**Strengths:** depth (browser, computer use, automations), zero marginal cost on a ChatGPT plan, OS-level polish. **Weaknesses:** single provider; no Linux; cloud features tied to ChatGPT account; closed source.

---

## 5. Anchor teardown B — T3 Code (pingdotgg)

**What it is:** "a minimal web GUI for coding agents — currently Codex, Claude, Cursor, and OpenCode" [3]. Run via `npx t3` or desktop builds (GitHub Releases, Homebrew cask, winget, AUR) [3][6]. MIT licensed; TypeScript ~97% [3].

**Traction:** ~12.4k stars, 2.5k forks, 106 releases in ~3 months; v0.0.25 (June 4, 2026) [3]; passed 11k stars within roughly three months of going public [6].

**Feature set:** multi-repo, multi-agent parallelism from one interface; task-oriented threads with full reasoning + tool-call visibility; git worktree per task handled automatically; one-click commit → push → PR with generated title/body/changelog; plan/code mode switching; model switching mid-thread; remote/web access mode; keybinding-driven UX [4][5][6][9].

**Positioning (their own words):** "T3 Code doesn't resell tokens. Plug in Claude Code, Codex, OpenCode, or Cursor with the credentials you already have — we orchestrate them, you keep your plan. No keys resold. No quota caps." Also explicitly markets being forkable and being "the first one to truly care about Linux users" [9].

**Reception:** performance is the most-praised trait — instant switching between projects and long threads even with multiple agents running [4]. Launch-window criticism is a checklist of what *not* to ship broken: tilde path-resolution bugs, missing file-diff views, and **no authentication on its web-server mode** [5].

**Strengths:** speed, openness, multi-harness, zero-install entry. **Weaknesses:** early/buggy ("very very early… expect bugs" — their README [3]); thin review tooling vs Codex app; no governance story.

---

## 6. Competitive landscape

| Product | Form | Agents | Isolation | Distinctive | Price/license | Platform | Status |
|---|---|---|---|---|---|---|---|
| **Codex app** (OpenAI) | Desktop | Codex only | Worktree/cloud | Automations, browser, computer use, artifacts | Free w/ ChatGPT plan | macOS, Win (Linux waitlist) | Official, active [1][2] |
| **Claude Code desktop** (Anthropic) | Desktop | Claude only | Sessions, SSH | Apr 14 2026 redesign: session sidebar, drag-drop panes, terminal+editor, **Routines** cloud automation, activity dashboard | Free w/ Pro/Max/Team/Ent | macOS, Win, Linux | Official, active [20][21][22] |
| **T3 Code** | Web + desktop | Codex, Claude, Cursor, OpenCode | Worktree | Speed, BYOK, npx entry, forkable | Free, MIT | All incl. Linux | Alpha, very active [3][9] |
| **Conductor** (Melty Labs) | Desktop | Claude Code, Codex, Cursor | Worktree (tracked files only) | Diff/PR flow, Linear intake | Free, proprietary | macOS Apple Silicon only | Active [11] |
| **Vibe Kanban** | Web, self-host | 10+ (Claude, Codex, Gemini, Copilot, Amp, Cursor, OpenCode…) | Workspace = branch + terminal + dev server | Kanban planning, preview browser w/ devtools, inline diff comments | Apache-2.0, community | Cross-platform | **Bloop shut down Apr 10 2026; community-maintained** [7][13] |
| **Crystal / Nimbalyst** | Desktop (Electron) | Claude Code (+Codex in Nimbalyst) | Worktree | Session persistence, notifications; Nimbalyst adds visual workspace (mockups, diagrams) | Free/OSS | Cross-platform | Active [7][19] |
| **Claude Squad** | Terminal (tmux) | Claude Code | tmux panes + worktrees | Keyboard-first, zero GUI | OSS | Cross-platform | Active [7] |
| **opcode** | Desktop | Claude Code | Process isolation | Usage analytics, custom background agents | OSS | Cross-platform | Active [19] |
| **Happy / Omnara** | Mobile + web | Claude Code | Remote control | Phone control of running agents, push notifications, E2E encryption | OSS/free | iOS/Android/web | Active [19][23] |
| **Sculptor** (Imbue) | Desktop | Claude | **Containers** (not worktrees) | Jump into agent environments to test; issue suggestions | Free | macOS/Linux | Active [23] |
| **Superset, Emdash, Baton, Parallel Code, Orca…** | Various | Multi-agent | Worktrees | A/B same task across models (Parallel Code); long tail | Mostly OSS | Various | Fragmented [7][13] |

---

## 7. Market signals and lessons

**S1 — Table stakes are frozen.** Independent reviews converge: every serious orchestrator solves parallelism via git worktrees [7]; the differentiation lives in review UX, planning surface, automations, and remote access [13]. Build the core fast and spend creativity elsewhere.

**S2 — Direct monetization failed.** Bloop (Vibe Kanban) — the category's most-adopted independent product — shut down April 10, 2026; the paid cloud tier was sunset and the project went community-maintained [13]. Conductor remains free with no team tier [11][12]. T3 leads with not charging [9]. Conclusion: individuals will not pay for a wrapper. Teams might pay for **administration, governance, and hosting** — which no one currently sells [12].

**S3 — The officials are absorbing the category.** Anthropic's April 2026 release note says it directly: the new app is "built for how agentic coding actually feels now: many things in flight, and you in the orchestrator seat" [20]. It shipped the session sidebar, drag-and-drop workspace, integrated terminal and file editor [20][21], plus Routines for scheduled cloud automation [22]. OpenAI's Codex app keeps adding surfaces (browser, computer use, artifacts) [2]. A wrapper must justify itself with *cross-provider* workflows and underserved platforms, not feature count.

**S4 — Security and review quality are the make-or-break details.** T3 Code's harshest launch criticism: an unsecured web-server mode and missing diff views [5]. For a tool that executes commands on a developer's machine and exposes a web UI, auth and a credible diff are launch requirements, not polish.

**S5 — Multi-tool reality.** ~70% of engineers run 2–4 AI tools simultaneously [18]; startups skew Claude Code, enterprises skew Copilot/Codex [18]. A cockpit that treats harnesses as interchangeable matches observed behavior; single-provider third-party wrappers fight their own users.

**S6 — Remote/mobile demand is proven.** Happy and Omnara exist purely to control running agents from a phone [19][23]; T3 ships a remote mode [3]. Long-running agents make "check on it from anywhere" a first-class need.

---

## 8. Gap analysis → positioning

**Gap 1 — Linux-first.** Codex app: no Linux build (waitlist) [1]. Conductor: Apple-Silicon-Mac-only [11]. T3 is praised *specifically* for caring about Linux [9] — evidence the audience is underserved. A web-served architecture (`npx`, daemon + browser) gets Linux, remote, and mobile in one move.

**Gap 2 — Governance for regulated teams.** No product in §6 publishes compliance certifications; Conductor's missing team licensing is called a procurement "hard stop" [12]. Nothing offers: immutable audit log of every agent action/approval/diff, org-level approval policies, role separation (operator vs reviewer), or on-prem deployment. For BS23 this is home turf — it is the maker-checker pattern from banking BPM applied to agents, and it is sellable to exactly the clients BS23 already serves (banks running ICCMS-style controls). It also cannot be commoditized quickly by OpenAI/Anthropic, whose cloud-account-centric models conflict with on-prem requirements.

**Gap 3 — Cross-provider A/B.** Running the same task on Claude Code and Codex in parallel worktrees and diffing the results exists only in long-tail tools (Parallel Code) [13]. Cheap to build once worktrees exist; high perceived value given S5.

**Positioning statement:** *A free, open, Linux-first cockpit for Claude Code, Codex, and OpenCode — with the only governed mode in the category: every agent action approved by policy and written to an audit log, deployable on-prem.* Free core for credibility and dogfooding; governed/team tier as the commercial product.

---

## 9. Feature matrix → our phasing

| Feature | Codex app | Claude Code desktop | T3 Code | Conductor | Vibe Kanban | **Ours** |
|---|---|---|---|---|---|---|
| Parallel threads, multi-project | ✅ | ✅ | ✅ | ✅ | ✅ | **v1** |
| Multi-harness (CC + Codex + OpenCode) | — | — | ✅ | ✅ (CC/Codex/Cursor) | ✅ 10+ | **v1** |
| Worktree per task | ✅ | partial | ✅ | ✅ | ✅ | **v1** |
| Structured stream (plan / exec / edit) | ✅ | ✅ | ✅ | ✅ | ✅ | **v1** |
| Approval prompts w/ scopes | ✅ | ✅ | partial | ✅ | ✅ | **v1** |
| Diff review + stage + commit + push + PR | ✅ | ✅ | ✅ | ✅ | ✅ | **v1** |
| Integrated terminal (agent-readable) | ✅ | ✅ | — | ✅ | ✅ | **v1** |
| Thread history / persistence | ✅ | ✅ | ✅ | ✅ | ✅ | **v1** |
| Secured remote web access | cloud only | SSH | ✅ (insecure at launch [5]) | — | self-host | **v2 (token auth from day one)** |
| Inline diff comments → agent | ✅ | — | — | — | ✅ | **v2** |
| Automations / scheduled tasks | ✅ | ✅ Routines | — | — | — | **v2** |
| Skills + shared MCP config | ✅ | ✅ | — | — | — | **v2** |
| **Audit log + approval policies + roles** | — | — | — | — | — | **v2 — differentiator** |
| Cross-provider A/B race | — | — | — | — | — | **v2 — differentiator** |
| Kanban / queue planning | — | — | — | Linear intake | ✅ | v3 |
| In-app browser preview + comments | ✅ | — | — | preview | ✅ | v3 |
| Voice, image input | ✅ | partial | — | — | — | v3 |
| Containers (vs worktrees) | — | — | — | — | — | v3 (Sculptor pattern) |
| Computer use, image generation | ✅ | — | — | — | — | **skip** (provider-specific arms race) |

---

## 10. Risks

1. **First-party absorption** (high likelihood, high impact). Mitigation: cross-provider + Linux + on-prem governance — the three things officials are structurally slow to do.
2. **Harness API churn** (medium/medium). CLIs and SDKs are pre-1.0; adapters must be thin and event-schema-normalized so breakage is contained to one adapter.
3. **No consumer revenue** (certain). Plan for it: OSS core, paid team/governed tier; do not budget consumer income.
4. **Security incident** (low likelihood, fatal impact). A cockpit executes commands and serves a web UI; T3's launch showed the scrutiny [5]. Token auth, localhost-default binding, and sandbox-respecting defaults before any public release.
5. **Crowding** (certain). 20+ tools in §6. Counter: don't launch as "another wrapper"; launch as "the governed one that runs on Linux."

---

## 11. References

1. OpenAI — Codex App overview: https://developers.openai.com/codex/app
2. OpenAI — Codex App features: https://developers.openai.com/codex/app/features
3. GitHub — pingdotgg/t3code (README, releases, languages): https://github.com/pingdotgg/t3code
4. Better Stack — "T3 Code: An Open-Source GUI for Managing AI Coding Agents": https://betterstack.com/community/guides/ai/t3-code/
5. daily.dev — "T3 Code: Another Agentic GUI that is GOOD BUT NOT USABLE": https://app.daily.dev/posts/t3-code-another-agentic-gui-that-is-good-but-not-usable--jorrdkvkz
6. Szaradowski — "T3 Code: The Bridge Between CLI and GUI in AI Coding": https://szaradowski.com/blog/t3-code-the-bridge-between-cli-and-gui-in-ai-coding
7. Augment Code — "9 Open-Source Agent Orchestrators for AI Coding (2026)": https://www.augmentcode.com/tools/open-source-agent-orchestrators
8. Clauday — "T3 Code is Theo's minimal browser GUI for Codex and Claude": https://clauday.com/article/9b2a6599-40a7-4ef3-bc22-d70a2e0ebd25
9. T3 Code official site: https://t3.codes/
10. GLN-7.5 — "T3 Code: Open Source App for Parallel AI Agents" (harness approach): https://gln75.com/en/blog/t3-code-open-source-app-parallel-ai
11. CodePick — "Conductor.build: Run a Team of Parallel AI Coding Agents on Your Mac": https://codepick.dev/en/guides/conductor-build-intro · Official: https://www.conductor.build/
12. Augment Code — "Conductor vs Intent (2026)" (team licensing/compliance gaps): https://www.augmentcode.com/tools/intent-vs-conductor-macos-agent-orchestrators
13. Nimbalyst — "Best Tools for Managing Parallel AI Coding Agents in 2026" (Bloop shutdown, landscape): https://nimbalyst.com/blog/best-agent-management-tools-2026/ · "Best Multi-Agent Coding Tools (2026)": https://nimbalyst.com/blog/best-multi-agent-coding-tools-2026/
14. SNS Insider via Yahoo Finance — "AI Code Assistant Market Set to Hit USD 14.62 Billion by 2033": https://finance.yahoo.com/news/ai-code-assistant-market-set-143000983.html
15. Digital Applied — "AI Coding Adoption 2026: 50 Statistics From 7 Surveys" (JetBrains 90%/74%): https://www.digitalapplied.com/blog/ai-coding-adoption-statistics-2026-50-data-points
16. getpanto.ai — "AI Tools Statistics 2026" (Stack Overflow 84%, Copilot 20M): https://www.getpanto.ai/blog/ai-coding-tools-adoption-statistics-by-country
17. Uvik — "AI Coding Assistant Stats 2026" (Cursor ARR, Claude Code adoption, Copilot paid subs): https://uvik.net/blog/ai-coding-assistant-statistics/
18. ideaplan.io — "AI Coding Assistant Market Share 2026" ($12.8B, multi-tool usage, segment split): https://www.ideaplan.io/blog/ai-coding-assistant-market-share-2026
19. awesome-vibe-coding directory (Crystal, opcode, Happy descriptions): https://github.com/no-fluff/awesome-vibe-coding
20. Thurrott — "Anthropic Redesigns Claude App on Desktop for Parallel Agents" (Apr 14, 2026 quote): https://www.thurrott.com/a-i/anthropic/334911/anthropic-redesigns-claude-app-on-desktop-for-parallel-agents
21. MacRumors — "Anthropic Rebuilds Claude Code Desktop App Around Parallel Sessions": https://www.macrumors.com/2026/04/15/anthropic-rebuilds-claude-code-desktop-app/
22. BuildFastWithAI — "Claude Code Desktop Redesign: Multi-Sessions + Routines (2026)": https://www.buildfastwithai.com/blogs/claude-code-desktop-redesign-2026
23. AlternativeTo — Conductor alternatives (Omnara, Sculptor): https://alternativeto.net/software/conductor
24. BloopAI/vibe-kanban README (feature set): https://github.com/BloopAI/vibe-kanban
25. rustman.org — "Parallel coding-agent orchestrators — Conductor and the 2026 ecosystem": https://rustman.org/wiki/conductor-parallel-agents/
