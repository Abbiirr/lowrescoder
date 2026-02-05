# TUI Quality Checklist & Performance Budget

Goal: The HybridCoder TUI should feel faster and more polished than Claude Code’s TUI.

---

**Performance Budgets (p95 unless noted)**
- Startup ready (cold): <300 ms to UI ready
- Startup ready (warm): <150 ms
- Keystroke echo: <16 ms
- UI frame update: <16 ms
- Non-LLM command latency: <150 ms
- Local LLM first token: <2 s
- Remote LLM first token (opt-in): <3 s
- Streaming stability: no pauses >250 ms

---

**Polish Checklist**
- Consistent layout: header, main pane, status bar
- Clear model/backend indicator and online/offline state
- Stable keybinds with in-app help
- Predictable undo/redo and safe cancel
- Clean error surfaces with recovery steps
- No blocking operations on the UI thread

---

**Reliability Checklist**
- LSP or embeddings unavailable should not block the UI
- Background tasks have visible progress and can be cancelled
- All file I/O and network calls are async or off-thread
- Hard timeouts for tools and LLM calls

---

**Benchmark Instrumentation Contract**
When `HYBRIDCODER_BENCH=1` is set, the TUI should emit sentinel lines:
- `BENCH:READY` when the UI is ready for input
- `BENCH:PONG` after receiving `:bench-ping`
- `BENCH:EXIT` after receiving `:quit` or `:exit`

The benchmark harness depends on these strings and will report unsupported if they are missing.

---

**How to Run Benchmarks**
1. Run the benchmark script:

```bash
uv run python scripts/bench_tui.py --cmd hybridcoder --args "chat"
```

2. Compare results to the budgets above.

---

**Acceptance Criteria (Phase 1)**
- Meets startup and non-LLM latency budgets on a baseline dev machine
- No visible jank during typing or scrolling
- TUI benchmarks produce a stable JSON report
