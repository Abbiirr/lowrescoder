# Migration Review Brief

Date: 2026-03-20
Status: Review prep

## Purpose

This brief prepares a review of the in-progress migration work.

The goal of the review is not to approve a full split yet. The goal is to judge
whether the current worktree is moving toward the agreed extraction model or
whether it is creating temporary in-monorepo structures that should be stopped
before more migration work continues.

## Current Factual State

1. The repo has **not** been converted to submodules yet.
   - No `.gitmodules`
   - `git submodule status` is empty

2. A pre-split state snapshot exists in `docs/qa/pre-split-snapshot.md`.

3. A partial benchmark-internal package structure now exists under
   `benchmarks/`.

4. The worktree still contains the original monorepo owners:
   - `src/`
   - `cmd/`
   - `scripts/`
   - `tests/`
   - `docs/`
   - `benchmarks/`
   - `training_data/`

5. Migration-related work is mixed with unrelated benchmark/harness fixes in the
   same worktree.

## What Changed That Needs Review

### 1. New benchmark-owned tree exists, but ownership is duplicated

New files now exist under:

- `benchmarks/adapters/`
- `benchmarks/e2e/`
- `benchmarks/benchmark_runner.py`
- `benchmarks/docker_helpers.py`
- `benchmarks/run_all_benchmarks.sh`

Equivalent benchmark code still exists under:

- `scripts/adapters/`
- `scripts/e2e/`
- `scripts/benchmark_runner.py`
- `scripts/run_all_benchmarks.sh`

This is the main migration review question:

- Is `benchmarks/` now the intended owner and `scripts/` only temporary
  compatibility?
- Or is this duplicate tree premature and should it be rolled back until real
  extraction starts?

### 2. Per-directory comms files were introduced

New files include:

- `benchmarks/AGENTS_CONVERSATION.MD`
- `docs/AGENTS_CONVERSATION.MD`
- `tests/AGENTS_CONVERSATION.MD`

Under the current repo rules, this is a direct policy conflict because the repo
still requires one active `AGENTS_CONVERSATION.MD`.

Review question:

- Should these be removed now rather than carried further into the migration?

### 3. The extraction model needs review before more work continues

There is now an extraction manifest in `docs/plan/extraction-manifest.md`.

It is useful as a draft, but it still contains a path model that should be
reviewed critically:

- `src/autocode/ → autocode/src/autocode/`
- `cmd/autocode-tui/ → autocode/cmd/autocode-tui/`

This can be read two different ways:

- correct extraction into a child repo that preserves internal layout
- incorrect in-monorepo move plan that would force large path churn

The reviewer should make that distinction explicit before any further migration
work.

### 4. `autocode` accessibility for benchmark/test modules needs a chosen model

A new requirement was stated:

- the latest `autocode` source/release must stay accessible to other modules,
  especially `benchmarks` and tests

The review should decide whether the project will use:

- editable local path dependencies
- a `uv` workspace member model
- or another explicit sibling-repo dependency model

The review should reject any approach that requires mass in-place import/path
rewrites just to make cross-module access work.

## Files A Reviewer Should Inspect First

### Migration state and plan

- `docs/qa/pre-split-snapshot.md`
- `docs/plan/extraction-manifest.md`
- `AGENTS_CONVERSATION.MD` (migration thread around Entries 770-776)

### Benchmark ownership duplication

- `benchmarks/README.md`
- `benchmarks/benchmark_runner.py`
- `benchmarks/adapters/autocode_adapter.py`
- `benchmarks/e2e/run_scenario.py`
- `scripts/benchmark_runner.py`
- `scripts/adapters/autocode_adapter.py`
- `scripts/e2e/run_scenario.py`

### Packaging / dependency model

- `pyproject.toml`
- `Makefile`
- `cmd/autocode-tui/detect.go`

### New rule conflicts

- `benchmarks/AGENTS_CONVERSATION.MD`
- `docs/AGENTS_CONVERSATION.MD`
- `tests/AGENTS_CONVERSATION.MD`

## Recommended Review Questions

1. Is the migration still following the agreed extraction-first model, or has it
   drifted into in-monorepo path churn?
2. Should `benchmarks/` be declared the future owner now, with thin wrappers in
   `scripts/`, or should the duplicate benchmark tree be paused until extraction?
3. Should the per-directory comms files be removed immediately as rule-violating
   noise?
4. What is the chosen dependency model for making `autocode` available to
   `benchmarks` and cross-repo tests?
5. Which tests belong with `autocode`, which belong with `benchmarks`, and which
   are true cross-repo contract tests?
6. Which root files are real cleanup candidates after benchmarking completes, and
   which should remain until the extraction actually happens?

## Reviewer Output Wanted

The review should end with a short decision on:

1. `benchmarks/` ownership: `accept now` or `pause`
2. duplicate comms files: `remove now` or `keep temporarily`
3. extraction model: `extract child repos with preserved internal layout` or
   `other`
4. cross-module access model: `editable path/workspace deps` or `other`
5. whether migration work should continue now or wait until benchmark work is
   fully stabilized

## Non-Goals For This Review

- not a full code review of benchmark bug fixes
- not a final submodule implementation review
- not a cleanup pass on all stored logs or artifacts
- not a decision on recreating untracked `academic_research/` content unless a
  concrete source is produced
