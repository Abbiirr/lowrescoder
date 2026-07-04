# meta-autocode: Beat Codex on Harness Benchmarks

## Mission
Build a coding agent harness that outperforms Codex (OpenAI) on standard harness benchmarks through superior harness architecture — not a bigger model.

## Baseline Numbers to Beat

| Harness | Model | Benchmark Score | Source |
|---|---|---|---|
| **Codex (OpenAI)** | GPT-5.5 | **61.5%** | MindStudio 2025 |
| Claude Code | Opus 4.7 | 87.2% | MindStudio 2025 |
| Cursor Agent | Opus 4.7 | 91.1% | MindStudio 2025 |
| OpenHands + Claude 3.7 | Claude 3.7 | 48.15% | GitTaskBench (arxiv 2508.18993) |
| autocode SMOKE (current) | fast/Gemini | 100% (6/6) | this session |

**Primary target: beat Codex's 61.5% on harness-bench (nyosegawa/harness-bench)**
**Stretch target: reach Cursor-level 87-91% performance**

## Why Harness Architecture Beats Model Upgrades

From research (MindStudio, GitTaskBench arxiv 2508.18993v1):
1. Same model (GPT-5.5): Codex harness = 61.5%, Cursor harness = 87.2% — the harness adds 25.7pp
2. 65% of agent failures come from environment setup issues, not model capability
3. Progressive context loading matters more than raw context window size
4. PIV (Plan-Implement-Validate) loop baked into the harness (not just prompts) improves consistency

## What meta-autocode Adds Over Baseline autocode

autocode already has:
- Rich tool set (read_file, edit_file, run_command, search_code, etc.)
- `sop_runner.py` with Scout→Architect→Engineer→Verify pipeline
- `strategy_overlays.py` with task-family detection
- Context engine, event recorder, skills system

meta-autocode adds:
1. **EnhancedPIVStrategy**: Enforces Plan→Implement→Validate at harness level, not just prompts
2. **ProgressiveContextLoader**: Relevance-scored file loading (test files first, then source, then deps)
3. **EnvironmentResilience**: Detects setup failures, retries with corrected env before giving up
4. **BenchmarkMaxxing**: Multi-attempt with variant strategies; picks best result
5. **CodexComparator**: Runs same task through Codex-compatible interface for direct comparison

## Architecture

```
meta-autocode/
  src/meta_autocode/
    piv.py              # PIV loop: Plan → Implement → Validate with harness-level gates
    context.py          # Progressive context loader with BM25 relevance scoring
    environment.py      # Environment setup detection and retry logic
    maxxing.py          # Benchmark maxxing: multi-attempt, pick best
    adapter.py          # Benchmark runner adapter (wraps AutoCodeAdapter)
    scorer.py           # Score tracking vs Codex baseline
  benchmarks/
    harness-bench/      # nyosegawa/harness-bench tasks (cloned)
    smoke_extended/     # Extended SMOKE tasks
  tests/
    test_piv.py
    test_context.py
    test_environment.py
```

## Implementation Phases

### Phase 1 — Core PIV Loop (TASK-001)
Implement `EnhancedPIVStrategy` built on top of autocode's existing `sop_runner.SOPPipeline.bugfix()`.
The key improvement: add verification-gated retry with re-planning on failure.

**Deliverables:**
- `src/meta_autocode/piv.py`
- `src/meta_autocode/__init__.py`
- `pyproject.toml`
- `tests/test_piv.py` (all pass)

**Success metric:** Solve b27-minimal-config-change in ≤8 tool calls (baseline: 10-18 calls)

### Phase 2 — Progressive Context (TASK-002)
Implement `ProgressiveContextLoader` that loads test files first, source second.
Cuts average context per call, reducing token usage and 502 timeouts.

### Phase 3 — Harness-Bench Integration (TASK-003)
Clone nyosegawa/harness-bench, create adapter, run baseline comparison.
Document Codex scores from the benchmark, run meta-autocode, measure gap.

### Phase 4 — Benchmark Maxxing (TASK-004)
Implement multi-attempt strategy:
- Attempt 1: PIV with progressive context
- Attempt 2 (if Attempt 1 fails): broader context + different approach angle
- Attempt 3: full context + step-by-step reasoning
Pick best result. This is the "benchmark maxxing" mode.

### Phase 5 — Beat Codex (TASK-005)
Run full harness-bench suite:
- meta-autocode vs Codex 61.5% baseline
- Target: ≥70% (beat Codex), stretch: ≥87% (match Claude Code)
- Document improvements in `benchmarks/results/`

## Reading List (for autocode to study)
- `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/sop_runner.py`
- `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/strategy_overlays.py`
- `/home/bs01763/projects/ai/autocode-full/autocode/src/autocode/agent/loop.py`
- `/home/bs01763/projects/ai/autocode-full/research-components/openai-codex/codex-cli/` (Codex implementation to study)
- `/home/bs01763/projects/ai/autocode-full/benchmarks/adapters/autocode_adapter.py`
