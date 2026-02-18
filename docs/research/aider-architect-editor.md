# Aider Architect/Editor Pattern — Research Notes

> Researched: 2026-02-17
> Source: https://aider.chat/2024/09/26/architect.html

---

## 1. Core Pattern

Aider splits code generation into **two sequential inference steps**:

1. **Architect Phase**: A reasoning-focused model solves the coding problem (natural language output)
2. **Editor Phase**: A formatting-focused model converts the solution into properly structured file edits

Key insight: "The Architect focuses on solving the coding problem and describes the solution however comes naturally. The Editor focuses all its attention on properly formatting the edits."

## 2. Information Flow

```
User Request + Repo Context
        │
        ▼
┌──────────────┐
│  Architect   │  (reasoning model - e.g., o1-preview, DeepSeek R1)
│  "solve it"  │
└──────┬───────┘
       │ natural language solution description
       ▼
┌──────────────┐
│   Editor     │  (formatting model - e.g., Sonnet, DeepSeek)
│  "format it" │
└──────┬───────┘
       │ structured code edits (diff or whole-file)
       ▼
  Applied to files
```

## 3. Model Selection

**Architect candidates**: Strong reasoning models
- o1-preview, o1-mini, DeepSeek R1, Claude 3.7 Sonnet

**Editor candidates**: Models good at code formatting + structured output
- Claude 3.5 Sonnet, DeepSeek, o1-mini

**Key flexibility**: Architect and Editor can be different models from different providers.

## 4. Benchmark Results

| Configuration | Pass Rate | Cost |
|---|---|---|
| o1-preview + o1-mini (whole) | 85.0% | High |
| o1-preview + DeepSeek (whole) | 85.0% | Lower |
| o1-preview + Sonnet (diff) | 82.7% | Medium |
| Sonnet + Sonnet (diff) | 80.5% | Medium |
| DeepSeek R1 + Sonnet (architect) | 64% | $13.29 |

Previous best (solo models): 79.7%

## 5. Cost Optimization Insight

- Cheap models as Editor (DeepSeek at $1.27/M tokens)
- Expensive models only for Architect reasoning
- DeepSeek as Editor is "remarkably capable at turning proposed coding solutions into new, updated versions"
- Self-pairing (same model as both) still improves over solo mode

## 6. Edit Formats

- **diff format**: Faster, less data, but requires model to produce correct diffs
- **whole format**: Model rewrites entire file, slower but more reliable
- Choice significantly impacts latency

## 7. Relevance to HybridCoder

This maps PERFECTLY to our L3/L4 split:
- **Architect = L4 (Qwen3-8B)**: Complex reasoning, natural language plan
- **Editor = L3 (Qwen2.5-Coder-1.5B)**: Grammar-constrained edit application

Our advantage: L3 uses Outlines for grammar-constrained generation, guaranteeing valid output format. Aider relies on the model getting the format right.

### Implementation via SOP:
```
SOPStep 1: L4 Architect → produces EditPlan (JSON)
SOPStep 2: L3 Editor → applies edits via constrained gen
SOPStep 3: tree-sitter → validates syntax
SOPStep 4: if errors → feedback to L4 Architect (max 3 loops)
```

This is already planned in our Phase 5C LLMLOOP design.
