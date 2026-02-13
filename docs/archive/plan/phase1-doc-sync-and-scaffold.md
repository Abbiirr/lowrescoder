# Phase 1 Plan: Doc Sync & Project Scaffold

> **Status:** COMPLETE — Steps 1-4 done.
> **Date:** 2026-02-05 (updated)

---

## Overview

Synchronize all project documentation to `docs/claude/` ground truth and scaffold the project skeleton before Sprint 1 implementation begins.

---

## Step 1: Finish Codex Research Notes

**Owner:** Codex
**Status:** COMPLETE

### Update 3 outdated files

| File | Issue | Required Fix |
|------|-------|--------------|
| `docs/codex/qwen2.5-coder-7b-instruct.md` | Wrong model — says Qwen2.5-Coder-7B is default L4 | Add note that Qwen3-8B has superseded this as default Layer 4 model. |
| `docs/codex/ollama-api.md` | Says "Layer 3 and Layer 4" | Correct to "Layer 4 ONLY. Layer 3 uses llama-cpp-python + Outlines." |
| `docs/codex/outlines-structured-generation.md` | Missing Ollama incompatibility | Add: "IMPORTANT: Outlines does NOT integrate with Ollama HTTP API. Must use llama-cpp-python backend." |

### Create 4 missing files

| File | Content |
|------|---------|
| `docs/codex/qwen3-8b.md` | L4 model. Qwen3-8B Q4_K_M, ~5 GB VRAM, thinking mode. Ollama runtime. |
| `docs/codex/llama-cpp-python.md` | L3 runtime. Required for Outlines grammar-constrained decoding. Replaces Ollama for Layer 3. |
| `docs/codex/multilspy.md` | Microsoft LSP client library. Manages Pyright/JDT-LS lifecycle. MIT license. |
| `docs/codex/uv-package-manager.md` | Package manager by Astral (ruff creators). 10-100x faster than pip. Replaces pip/poetry. |

### Constraint
- Codex already applied "small fixes" to the 3 files. Must verify they match the **full** corrections specified above (not just partial fixes).

### Evidence
- `docs/claude/phase1-tech-stack.md` Section 2.7-2.8
- `docs/claude/01-local-llm-inference-research.md`
- `docs/claude/cross-doc-review-for-codex.md`

---

## Step 2: Sync Core Docs to Ground Truth

**Owner:** Codex
**Status:** COMPLETE
**Constraint:** Source of truth is `docs/claude/` files ONLY. Do not introduce information that isn't in those docs.

### `CLAUDE.md` — Tech Stack Table (lines 94-105)

Current table is ~38% incomplete. Required changes:

| Row | Current | Updated |
|-----|---------|---------|
| Model (L4) | Qwen2.5-Coder 7B Q4_K_M | **Qwen3-8B Q4_K_M** |
| Model (L3) | *(missing)* | **Qwen2.5-Coder-1.5B Q4_K_M** |
| Local LLM (L4) | Ollama | Ollama **(Layer 4 only)** |
| Local LLM (L3) | *(missing)* | **llama-cpp-python + Outlines (Layer 3 only)** |
| Grammar | Outlines / Pydantic integration | Outlines / Pydantic integration — **requires llama-cpp-python, NOT Ollama** |
| LSP Client | *(missing)* | **multilspy** |
| Package Manager | *(missing)* | **uv** |

### `docs/plan.md` — 6 Outdated References

| Location | Current | Fix |
|----------|---------|-----|
| Section 4.0 (line 782) | `Qwen2.5-Coder 7B Instruct` | `Qwen3-8B Q4_K_M` |
| Section 4.1 (line 797-798) | Single LLM/model row | Split into L4 (Ollama/Qwen3-8B) and L3 (llama-cpp-python/Qwen2.5-Coder-1.5B) |
| Section 2.2 (line 137) | `Ollama/llama.cpp` for Layer 3 | `llama-cpp-python + Outlines` |
| Config (line 244) | `qwen2.5-coder:7b-instruct-q4_K_M` | `qwen3:8b` |
| Git commit format (line 345) | `Model: qwen2.5-coder:7b` | `Model: qwen3:8b` |
| Benchmark protocol (line 1136) | `Qwen2.5-Coder 7B` | `Qwen3-8B` |

Also:
- Add multilspy to Section 4.0 dependencies
- Resolve Section 1.5 (line 62): Embedding model "Open" → Resolved: jina-v2-base-code

### `docs/spec.md` — 3 Outdated References

| Location | Current | Fix |
|----------|---------|-----|
| Line 107 | `Qwen2.5-Coder 7B Instruct` | Two models: Qwen3-8B (L4) + Qwen2.5-Coder-1.5B (L3) |
| Line 106 | Only `Ollama` | Add `llama-cpp-python + Outlines (L3)` |
| Line 108 | Outlines without caveat | Add Ollama incompatibility note |

Also:
- Line 24: "Local 7B model" → "Local 8B model"
- Section 13: Embedding model "Open" → Resolved: jina-v2-base-code

---

## Step 3: Scaffold Project Skeleton

**Owner:** ~~Codex~~ Claude (user override)
**Status:** COMPLETE

Sprint 0 was executed by Claude per user direction. Completed items:

| File | Status | Notes |
|------|--------|-------|
| `pyproject.toml` | DONE | uv, hatch build, all layer deps as optional extras |
| `src/hybridcoder/__init__.py` | DONE | `__version__ = "0.1.0"` |
| `src/hybridcoder/__main__.py` | DONE | Entry point |
| `src/hybridcoder/cli.py` | DONE | Stub |
| `src/hybridcoder/config.py` | DONE | Stub |
| `tests/conftest.py` | DONE | Basic fixtures |
| `tests/unit/` | DONE | Directory created |
| `tests/integration/` | DONE | Directory created |
| `Makefile` | DONE | setup, test, lint, format, clean |
| `.gitignore` | DONE | Full Python patterns |
| `.env.example` | DONE | OpenRouter template |

**Not created** (user decision):
- `.pre-commit-config.yaml` — CI/CD skipped, everything local
- GitHub Actions — skipped

**Verification:** `uv sync --all-extras` (85 packages), `ruff check` (pass), `mypy` (pass), `pytest` (runs, 0 collected).

---

## Step 4: Report Completion

**Owner:** Codex
**Status:** COMPLETE — Report posted to `AGENTS_CONVERSATION.MD`.

1. Post completion summary to `AGENTS_CONVERSATION.MD`
2. Include full list of files changed/created
3. Note any deviations from this plan
4. Claude will review

---

## Sprint 1 Plan (Agreed)

Sprint 1 has been agreed upon in Entries 11-13 of `AGENTS_CONVERSATION.MD`. See `docs/plan/` for the Sprint 1 detailed plan (to be written when Sprint 1 kicks off).

**Key Sprint 1 agreements:**
- `llm.provider` default = `"ollama"` (local-first). OpenRouter via explicit env var only.
- Integration tests use `@pytest.mark.integration` + env/server guards, skipped by default.
- `python-dotenv` loads `.env` before Pydantic config validation.

**Task split:**
| Agent | Role | Sprint 1 Work |
|-------|------|---------------|
| Claude | Coder | S1.1 Config, S1.2 CLI, S1.3 LLM providers, S1.4 File tools, S1.5 Core types, all tests |
| Codex | Reviewer/Architect | Doc sync (Steps 1-2 above), code reviews, codex note updates |

---

## Risk Items (For Reference)

| # | Risk | Severity | When |
|---|------|----------|------|
| 1 | VRAM budget headroom (0.2-0.7 GB on 8 GB cards) | HIGH | S1: test script |
| 2 | multilspy stability (limited adoption) | HIGH | S0/S3: spike |
| 3 | Outlines + llama-cpp-python version compat | HIGH | S1: integration test |
| 4 | Qwen3-8B Ollama availability | MEDIUM | S1: verify |
| 5 | Timeline slip (14 weeks → likely 17-18) | MEDIUM | Ongoing: milestones |

---

## Approval Record

| Agent | Entry | Verdict |
|-------|-------|---------|
| Codex | Entry 7 | Proposed plan |
| Claude | Entry 8 | Approved with modifications |
| Codex | Entry 9 | Accepted all modifications |
| Claude | Entry 10 | Confirmed version string, unblocked |
| Claude | Entry 11 | Sprint 0 complete, Sprint 1 proposed |
| Codex | Entry 12 | Sprint 1 approved with modifications |
| Claude | Entry 13 | Accepted all S1 modifications, assigned tasks |
