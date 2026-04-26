# Benchmarks And Evaluation Summary

## What this doc family covers

The benchmark docs tell you how to run the evaluation harness, what the lanes mean, how TUI benchmark operation works, and how output should be interpreted.

## Operator-facing benchmark docs

- [docs/benchmark-guide.md](../docs/benchmark-guide.md) is the main operator guide.
  - prerequisites
  - lane execution
  - resume/recovery
  - output interpretation
  - troubleshooting
- [docs/benchmark-tui-runbook.md](../docs/benchmark-tui-runbook.md) is the TUI-specific operator runbook.
  - TUI mode choice
  - operator flow
  - canonical commands
  - failure rules
- [autocode/TESTING.md](../autocode/TESTING.md) also includes benchmark execution and storage guidance.

## Evaluation policy docs

- [benchmarks/benchmarks/EVALUATION.md](../benchmarks/benchmarks/EVALUATION.md) defines the evaluation dimensions and parity validity contract.
- [benchmarks/benchmarks/README.md](../benchmarks/benchmarks/README.md) is a short entry doc into the benchmark package.

## Status docs

- [benchmarks/benchmarks/STATUS.md](../benchmarks/benchmarks/STATUS.md) contains benchmark status and historical notes.
- [current_directives.md](../current_directives.md) also reports benchmark status.

Important caution:

- `current_directives.md` currently reports the internal suite as `23/23 GREEN` and `120/120`.
- `benchmarks/benchmarks/STATUS.md` headings still show an older `102/115` style snapshot plus explicit historical notes.

So for current operator state, trust `current_directives.md` first and treat `STATUS.md` as partly historical context unless refreshed.

## TUI benchmark status

The TUI benchmark path is now a real operator path, not just a concept:

- benchmark-owned Rust TUI PTY runs exist
- resume/artifact capture is part of the harness
- canary convention is established
- TUI runbook exists for operators

The active/canonical references for that are:

- [docs/benchmark-tui-runbook.md](../docs/benchmark-tui-runbook.md)
- [docs/benchmark-guide.md](../docs/benchmark-guide.md)
- [current_directives.md](../current_directives.md)

## Benchmark fixture docs

There are many prompt/task markdown docs under:

- `benchmarks/e2e/external/fixtures/`
- `benchmarks/benchmarks/e2e/external/fixtures/`

These are workload definitions, not project-policy docs. Summarize them this way:

- B13/B14 prompts are competitive coding/problem-solving tasks
- B15-B29 tasks are engineering/refactor/security/resilience-style workload docs
- B9 Terminal-Bench tasks are shell/CLI problem statements

Use them when you need to inspect a lane’s actual prompt/task content, not for runtime policy.

## Practical takeaway

Use the benchmark docs in this order:

1. [docs/benchmark-guide.md](../docs/benchmark-guide.md)
2. [docs/benchmark-tui-runbook.md](../docs/benchmark-tui-runbook.md) if the TUI path matters
3. [benchmarks/benchmarks/EVALUATION.md](../benchmarks/benchmarks/EVALUATION.md) for scoring/parity semantics
4. fixture docs only when investigating a specific lane

## Source references

- [docs/benchmark-guide.md](../docs/benchmark-guide.md)
- [docs/benchmark-tui-runbook.md](../docs/benchmark-tui-runbook.md)
- [benchmarks/benchmarks/README.md](../benchmarks/benchmarks/README.md)
- [benchmarks/benchmarks/STATUS.md](../benchmarks/benchmarks/STATUS.md)
- [benchmarks/benchmarks/EVALUATION.md](../benchmarks/benchmarks/EVALUATION.md)
- [autocode/TESTING.md](../autocode/TESTING.md)
- [current_directives.md](../current_directives.md)
- [../benchmarks/e2e/external/fixtures/](../benchmarks/e2e/external/fixtures/)
- [../benchmarks/benchmarks/e2e/external/fixtures/](../benchmarks/benchmarks/e2e/external/fixtures/)
