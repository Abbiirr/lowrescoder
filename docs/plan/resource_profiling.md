# Resource Profiling and Lightweight Performance Plan

Goal: Keep HybridCoder fast and resource-light on low-end hardware while maintaining a repeatable profiling and benchmarking cadence.

---

## 1. Lightweight Design Principles (Phase 2)

- Avoid heavy ML imports on the TUI path. Only import provider SDKs when a session starts.
- Keep default install minimal. Advanced layers (tree-sitter, embeddings, llama-cpp) remain optional extras.
- No background daemons, indexers, or file watchers in Phase 2.
- Prefer async I/O and short-lived tasks to avoid blocking the UI thread.
- Use bounded caches and explicit size limits for chat history and tool output.
- Use opt-in shell execution (`shell.enabled=false` by default).
- Prefer lightweight serialization and avoid large in-memory buffers.

---

## 2. Low-End Baseline Definition

Low-end target for Phase 2 benchmarks:
- CPU: 2-4 cores, no AVX requirement
- RAM: 8 GB
- GPU: none (integrated only)
- OS: Windows, macOS, Linux (commodity laptop)
- Screen: 1366x768 or similar (small terminal)
- LLM: OpenRouter only (remote), no local LLM

This baseline is for measuring UI responsiveness, memory footprint, and startup time. Local LLM performance is tracked separately.

---

## 3. Metrics to Capture

Core metrics:
- Startup cold and warm time (TUI ready)
- Keystroke echo latency and UI frame latency
- Idle RSS and idle CPU usage (60s window)
- Peak RSS during chat + tool execution
- Time-to-first-token (remote provider)
- Tool execution latency and output size

Stability metrics:
- 30-minute idle stability (no memory creep)
- 30-minute active typing stability
- Long session with 100+ messages (no UI lag)

---

## 4. Benchmark Suite

Existing benchmark harness:
- `scripts/bench_tui.py` for startup/ping and BENCH sentinel validation

Planned lightweight resource harness (Phase 2):
- A new `scripts/bench_resources.py` that uses psutil to record RSS, CPU%, and peak memory during:
  - TUI startup
  - Idle 60s
  - One chat round-trip
  - One tool call (read_file)

Data output:
- JSON results stored under `docs/benchmarks/tui/` and `docs/benchmarks/resources/`
- Each run tagged with OS, CPU model, RAM, and git commit

---

## 5. Profiling Tools (Recommended)

CPU sampling:
- `py-spy` for low-overhead sampling without code changes.

Line-level CPU + memory:
- `scalene` for per-line CPU and memory hotspots.

Memory allocations:
- `memray` for allocation-level leak detection (Linux/macOS).

Process telemetry:
- `psutil` for RSS/CPU% measurements in a lightweight script.

---

## 6. Profiling Cadence

Per sprint:
- Run `scripts/bench_tui.py`
- Run resource bench and record RSS/CPU/peak values
- Compare against previous sprint baselines

Monthly or pre-release:
- Run scalene on TUI startup and command routing
- Run memray for allocation profiles during a 20-minute session
- If startup or idle RSS regresses >20%, open a perf issue

---

## 7. Reference Commands

TUI bench:
```bash
uv run python scripts/bench_tui.py --cmd hybridcoder --args "chat" --json
```

CPU sampling (py-spy):
```bash
py-spy top -- python -m hybridcoder chat
py-spy record -o profile.svg -- python -m hybridcoder chat
```

Line-level profiling (scalene):
```bash
python -m scalene -m hybridcoder chat
```

Memory profiling (memray, Linux/macOS):
```bash
memray run -o memray.bin -m hybridcoder chat
memray flamegraph memray.bin
```

Process telemetry (psutil):
```python
import os, psutil
p = psutil.Process(os.getpid())
print(p.memory_info().rss / (1024 * 1024), "MB")
print(p.cpu_percent(interval=1.0), "%")
```

---

## 8. Alignment to Phase 2 Plan

- The plan’s Section 14 performance budgets are the acceptance thresholds.
- BENCH sentinels are mandatory for startup/ping verification.
- Resource benchmarking is required before Sprint 2A completion and at Sprint 2B exit.

---

## 9. Sources

- py-spy: https://github.com/benfred/py-spy
- Scalene: https://github.com/plasma-umass/scalene
- Memray: https://github.com/bloomberg/memray
- psutil: https://pypi.org/project/psutil/
