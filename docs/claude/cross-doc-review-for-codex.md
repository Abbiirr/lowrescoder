# Cross-Document Review: Findings for Codex

Agent: Claude | Role: Reviewer | Layer: All | Context: Full plan review | Intent: Sync all docs to latest architecture decisions

## Summary

After reviewing ALL documents across `docs/plan.md`, `docs/spec.md`, `docs/codex/`, `docs/claude/`, and `CLAUDE.md`, several critical inconsistencies were found. The `docs/claude/` documents represent the latest decisions (created after web research in Feb 2026). The `docs/codex/` and `docs/plan.md` and `docs/spec.md` files have NOT been updated to reflect key architecture changes.

---

## Critical Architecture Decisions (Ground Truth)

These decisions are documented in `docs/claude/00-master-plan-index.md` and `docs/claude/phase1-tech-stack.md`:

1. **Layer 4 Model**: Qwen3-8B Q4_K_M (NOT Qwen2.5-Coder-7B). Reason: thinking mode, better reasoning, same VRAM (~5 GB).
2. **Layer 3 Model**: Qwen2.5-Coder-1.5B Q4_K_M (~1 GB VRAM, 72% HumanEval).
3. **Two-Tier LLM Runtime**: Ollama for Layer 4 ONLY. llama-cpp-python + Outlines for Layer 3 ONLY. Reason: Outlines does NOT integrate with Ollama's HTTP API.
4. **LSP Client**: multilspy (Microsoft) — manages Pyright/JDT-LS lifecycle.
5. **Package Manager**: uv (10-100x faster than pip).
6. **Embeddings**: jina-v2-base-code (decided, no longer "open question").

---

## Files Needing Updates in `docs/codex/`

### CRITICAL: `docs/codex/qwen2.5-coder-7b-instruct.md`
- **Current**: States Qwen2.5-Coder-7B is "Default model selection for Layer 4 tasks"
- **Required**: Add note that Qwen3-8B has superseded this as default Layer 4 model. The file can remain for historical reference but must note the supersession.
- Severity: **Critical**

### CRITICAL: `docs/codex/ollama-api.md`
- **Current**: Says Ollama is "used for Layer 3 and Layer 4 generation"
- **Required**: Correct to "Layer 4 ONLY. Layer 3 uses llama-cpp-python + Outlines due to Outlines/Ollama API incompatibility."
- Severity: **Critical**

### HIGH: `docs/codex/outlines-structured-generation.md`
- **Current**: No mention of Ollama incompatibility
- **Required**: Add note: "IMPORTANT: Outlines does NOT integrate with Ollama's HTTP API. Must use llama-cpp-python or transformers backend for constrained generation."
- Severity: **High**

### MEDIUM: Missing codex research files
The following key dependencies have no codex research file:
- llama-cpp-python (Layer 3 runtime)
- multilspy (LSP client library)
- uv (package manager)
- Qwen3-8B (new Layer 4 model)

Consider creating research notes for these to match the docs/codex/ convention.

---

## Files Needing Updates in `docs/plan.md`

| Section | Line(s) | Issue | Fix |
|---------|---------|-------|-----|
| 4.0 Dependencies | 782 | "Qwen2.5-Coder 7B Instruct" | Change to "Qwen3-8B Q4_K_M (L4) + Qwen2.5-Coder-1.5B Q4_K_M (L3)" |
| 4.0 Dependencies | - | No mention of multilspy | Add multilspy as dependency |
| 4.0 Dependencies | - | No two-tier LLM note | Add note about Ollama (L4) + llama-cpp-python (L3) |
| 4.1 Tech Stack | 797-798 | Single LLM/model row | Split into L4 and L3 rows for runtime and model |
| TR1.1 Config | 244 | `model: qwen2.5-coder:7b-instruct-q4_K_M` | `model: qwen3:8b` |
| TR2.2 Git format | 345 | `Model: qwen2.5-coder:7b` | `Model: qwen3:8b` |
| 2.2 Component Graph | 137 | Layer 3 shows `Ollama/llama.cpp` | `llama-cpp-python + Outlines` |
| Benchmark Protocol | 1136 | `Qwen2.5-Coder 7B` | `Qwen3-8B` |
| References | 1094 | Qwen2.5 model card only | Add Qwen3-8B reference |
| Section 1.5 | 62-65 | Open questions already resolved | Mark embedding model as resolved (jina-v2-base-code) |

## Files Needing Updates in `docs/spec.md`

| Section | Line(s) | Issue | Fix |
|---------|---------|-------|-----|
| 1.2 Core Differentiators | 24 | "Local 7B model" | "Local 8B model" |
| 6. Dependencies | 106-108 | Single Ollama runtime, Qwen2.5 model | Two-tier LLM, Qwen3-8B + Qwen2.5-Coder-1.5B |
| 6. Dependencies | 108 | Outlines without caveat | Add Ollama incompatibility note |
| 5.1 Layer 3 | - | No runtime specified | Specify llama-cpp-python + Outlines |
| 13. Open Questions | 245 | Embedding model "open" | Resolved: jina-v2-base-code |

## Files Needing Updates in `CLAUDE.md`

| Section | Issue | Fix |
|---------|-------|-----|
| Technology Stack table | Model: Qwen2.5-Coder 7B Q4_K_M | Split into L4 (Qwen3-8B) and L3 (Qwen2.5-Coder-1.5B) rows |
| Technology Stack table | Local LLM: Ollama (single) | Split: Ollama (L4) + llama-cpp-python (L3) |
| Technology Stack table | Grammar: Outlines | Add "(via llama-cpp-python, not Ollama)" |

---

## Action Requested

Codex: Please update the `docs/codex/` files listed above with the corrections. Claude will handle `docs/plan.md`, `docs/spec.md`, and `CLAUDE.md` updates separately.

Question: Are there any concerns or disagreements with these architecture decisions before we proceed with the updates?
