# Sprint 5C-6: Reliability Soak Tests

> Status: **NOT STARTED**
> Sprint: 5C (Context Quality + AgentBus)
> Est. Hours: ~8h (3h tests + 5h impl + soak runs)
> Dependencies: 5B-4 (LLMLOOP Pipeline)
> Owner: Claude

---

## Goal

Reliability smoke tests (30-min) and extended soak tests (4-hour) on 8GB VRAM target hardware.

---

## TDD Tests (Write First)

- [ ] `test_smoke_memory` - Python RSS memory growth < 200 MB in 30 min
- [ ] `test_smoke_vram` - GPU VRAM delta within +/- 500 MB in 30 min
- [ ] `test_smoke_latency` - p95 <= 60s single-file / <= 300s multi-file (Section 15.22)
- [ ] `test_smoke_no_crashes` - zero segfaults/crashes in 30 min
- [ ] `test_smoke_ollama_recovery` - Ollama disconnect recovery within 60s

## Implementation

- [ ] Implement smoke test harness (30-minute fixed workload)
- [ ] Implement soak test harness (4-hour extended workload)
- [ ] Track metrics: Python RSS, GPU VRAM, SQLite sizes, open FDs, latency
- [ ] Implement Ollama disconnect/reconnect test
- [ ] Use fixed workload fixture for reproducibility (P8)

## 3 Consecutive Smoke Passes (HARD GATE)

- [ ] Smoke pass 1: all R1-R8 pass
- [ ] Smoke pass 2: all R1-R8 pass
- [ ] Smoke pass 3: all R1-R8 pass

## Extended Soak Test (Milestone Boundary)

- [ ] Memory growth < 100 MB/hour over 4h
- [ ] VRAM delta within +/- 200 MB over 4h
- [ ] No latency degradation > 20% hour 1 to 4
- [ ] Zero unrecoverable hangs
- [ ] Soak artifact stored in `docs/qa/test-results/`

## Acceptance Criteria

- [ ] 3 consecutive smoke passes achieved
- [ ] 1 stored soak artifact per milestone
- [ ] Fixed workload fixture used for all runs
- [ ] All metrics tracked and recorded
- [ ] MVP GATE: AutoCode solves real coding tasks standalone
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/benchmark/test_reliability_soak.py`
- QA artifact: `docs/qa/test-results/sprint-5c-6-reliability-soak.md`
- Soak artifact: `docs/qa/test-results/sprint-5c-soak-run-<date>.md`
