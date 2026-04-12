# Phase 6 — Packaging, Distribution, and Advanced Features

> Status: **COMPLETE**
> Depends on: Phase 5 (Universal Orchestrator) — COMPLETE
> Last updated: 2026-03-31

---

## 1. Vision

Phase 6 transforms AutoCode from a developer-installed Python project into a
**single-installable, zero-setup product** that works out of the box on any
consumer machine. The standalone MVP from Phase 5 gets packaged, distributed,
and enhanced with advanced editing features.

---

## 2. Sprint Plan

### Sprint 6A: Packaging + First-Run Bootstrap

**Goal:** Single executable that handles first-run setup automatically.

| # | Task | Description | Priority |
|---|------|-------------|----------|
| 1 | PyInstaller packaging | Build single-file executable for Linux/macOS/Windows | P0 |
| 2 | First-run model bootstrap | Detect missing Ollama, prompt install, pull models | P0 |
| 3 | Platform detection | Auto-detect OS, GPU, VRAM, and configure accordingly | P0 |
| 4 | Offline mode | Full operation with local models only, no network required | P0 |
| 5 | Version management | `autocode --version`, update checks, changelog | P1 |

### Sprint 6B: Clean Install/Uninstall

**Goal:** Reversible installation that doesn't pollute the system.

| # | Task | Description | Priority |
|---|------|-------------|----------|
| 1 | `autocode install` | System-wide install with PATH registration | P0 |
| 2 | `autocode uninstall` | Complete removal of all AutoCode artifacts | P0 |
| 3 | Config migration | Upgrade configs between versions safely | P0 |
| 4 | Shell completions | Bash/Zsh/Fish/PowerShell completions | P1 |

### Sprint 6C: Advanced Edit Features

**Goal:** Multi-file editing and refactoring capabilities.

| # | Task | Description | Priority |
|---|------|-------------|----------|
| 1 | Multi-file editing | Edit multiple files in a single operation | P0 |
| 2 | Cross-file refactoring | Rename symbols across entire project | P0 |
| 3 | Edit preview + accept/reject | Show proposed changes, user confirms | P0 |
| 4 | Undo/rollback | Git-based undo for any edit operation | P1 |
| 5 | Edit conflict resolution | Handle concurrent edits gracefully | P1 |

### Sprint 6D: Team Persistence + Polish

**Goal:** Project-scoped agent teams and final polish.

| # | Task | Description | Priority |
|---|------|-------------|----------|
| 1 | Team persistence | Save/load agent teams in `.autocode/teams/` | P1 |
| 2 | `/team` command | Create, list, manage teams from CLI | P1 |
| 3 | Routing quality benchmark | Validate multi-model delegation quality | P1 |
| 4 | Performance optimization | Profile and optimize hot paths | P1 |
| 5 | Documentation polish | User guide, API docs, examples | P1 |

---

## 3. Entry Criteria (from Phase 5 Exit Gate)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Phase 5 MVP gate (M2) | Tests: 1172 passed |
| 2 | External bridges (M3) | MCP server + config merge implemented |
| 3 | Full edit command | LLMLOOP with EditPlan/Verify |
| 4 | Context quality | EvalHarness + 4 strategies implemented |
| 5 | Reliability | Benchmarks: 37/40 (92.5%) B7-B14 |
| 6 | Documentation | All docs updated for submodule structure |

---

## 4. Test Strategy

| Sprint | Est. New Tests | Cumulative |
|--------|---------------|------------|
| 6A | ~15 | ~1187 |
| 6B | ~10 | ~1197 |
| 6C | ~20 | ~1217 |
| 6D | ~10 | ~1227 |

---

## 5. Risks

| Risk | Mitigation |
|------|-----------|
| PyInstaller bloat (>100MB) | Use --onefile with UPX compression |
| Platform-specific bugs | CI matrix: Linux x64, macOS arm64, Windows x64 |
| Ollama install complexity | Detect + guide, don't auto-install system packages |
| Multi-file edit correctness | Extensive TDD, git rollback safety net |
