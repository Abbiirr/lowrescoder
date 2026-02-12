# Phase 3 Before/After Benchmark Protocol

This protocol defines how to measure the system **before Phase 3** and **after Phase 3** using the same command set.

## Goal

Produce comparable snapshots for:
- correctness (`pytest`)
- benchmark behavior (`tests/benchmark`)
- static quality gates (`ruff`, `mypy`)

## Commands

Run from repo root:

```bash
./scripts/run_phase3_benchmark_snapshot.sh before
./scripts/run_phase3_benchmark_snapshot.sh after
```

For individual ad-hoc runs, store artifacts with:

```bash
./scripts/store_test_results.sh <label> -- <command>
```

## Artifacts

Each run writes:
- one markdown summary report
- one raw log per step

Location:
- `docs/qa/phase3-benchmarks/`

Naming:
- `<UTC timestamp>-before.md`
- `<UTC timestamp>-after.md`
- `<UTC timestamp>-<mode>-<step>.log`

## Required Comparison Checks

1. `system_tests` must not regress (new failures are release-blocking).
2. `bench_current` must not regress on established benchmark suites.
3. `bench_phase3_gates` (once files exist) must meet Phase 3 targets:
   - router accuracy >= 90%
   - deterministic p95 latency < 50ms
   - context budget <= 5000 tokens
   - search precision@3 > 60%
4. `ruff` and `mypy` should trend toward clean; any new errors introduced by Phase 3 are blocking.

## Notes

- The script intentionally runs the same sequence in both modes to keep snapshots comparable.
- If dedicated Phase 3 benchmark files do not exist yet, `bench_phase3_gates` is marked `SKIPPED` with missing-file details in the report.
