# Review: Later-Phase Work Since `e52e6b0`

Date: 2026-03-21

Scope:
- Compared superproject `e52e6b0f7d86a28d6c14bd0b9a1b3f1d83ae1c27` to current `HEAD` `a0bf392363cf959c65c248bcdae23172c8fcbb4c`.
- Focused on post-migration later-phase work: new Phase 5/6-era modules, eval plumbing, MCP exposure, multi-edit rollback, and the phase-transition docs.
- Review method was direct code and doc inspection in the current workspace.
- I did not rerun the full test suite for this review; this is a correctness and integration review, not a fresh verification run.

## Executive Summary

This range contains real progress:
- the submodule migration is real
- Phase 5/6-oriented modules are present
- B15-B29 expansion is materially underway

But I would not treat the later phases as ready for sign-off or clean transition yet.

There are three concrete implementation risks that can break behavior or safety:
- `multi_edit` can commit unrelated user changes into an automatic rollback point
- `MCPServer` does not actually enforce its allowlist for search-style tools
- `LLMLOOP` has multiple integration bugs that will fail once it is wired to real providers

There is also a governance/documentation problem:
- the authoritative sprint and benchmark docs still describe the pre-closeout benchmark state
- those docs do not currently support the "later phases are complete" claim

## Findings

### 1. High: `multi_edit` rollback point captures unrelated user changes

File:
- `autocode/src/autocode/agent/multi_edit.py:95-120`

What is wrong:
- `create_rollback_point()` runs `git add -A` and then `git commit`.
- That stages and commits every change in the repo, not just the files in the `MultiEditPlan`.
- In a dirty worktree, invoking multi-edit will silently pull unrelated user edits into the synthetic "rollback point" commit.

Why it matters:
- This violates the expected safety model for a local coding assistant.
- It can accidentally checkpoint unrelated work into an AutoCode-generated commit.
- A later `rollback()` uses `git reset --hard`, which can then restore or discard far more than the multi-edit operation itself.

Suggested fix:
- Never stage the full repo with `git add -A`.
- Restrict rollback capture to the exact file set in the plan.
- Prefer a non-commit rollback mechanism for dirty trees:
  - write reverse patches for touched files
  - or use `git stash push -- <paths>`-style scoped capture
  - or create an isolated index/worktree snapshot
- If a git-commit rollback path is kept, block it on a dirty tree unless the user explicitly opts in.

Testing gap:
- Existing coverage around multi-edit only proves behavior on simple temporary repos.
- I do not see a regression test for "repo already has unrelated unstaged changes" before a multi-edit run.

### 2. High: `MCPServer` allowlist is bypassed by search-style tools

File:
- `autocode/src/autocode/external/mcp_server.py:115-127`
- `autocode/src/autocode/external/mcp_server.py:168-196`

What is wrong:
- `handle_tool_call()` validates explicit path-like arguments only.
- `search_code`, `find_definition`, and `find_references` do not take a validated path and instead search `self.config.project_root` directly.
- That means `allowed_paths` is not the true enforcement boundary for those tools.

Why it matters:
- The module documents path allowlisting as a security property.
- With a narrowed `allowed_paths`, these tools can still read/search outside the intended subtree as long as it is under `project_root`.
- This is a real policy bypass, not just a documentation nit.

Suggested fix:
- Make the search root derive from validated allowed roots, not blindly from `project_root`.
- Either:
  - require a validated `directory` argument for search-like tools
  - or iterate over `allowed_paths` and constrain search to those roots
- Add explicit tests where `project_root` is broad but `allowed_paths` is intentionally narrow.

Testing gap:
- Current tests cover blocked direct file paths, but I do not see coverage for narrowed `allowed_paths` on `search_code` / `find_definition` / `find_references`.

### 3. Medium: `LLMLOOP` cannot correctly represent multi-file plans

File:
- `autocode/src/autocode/agent/llmloop.py:147-155`

What is wrong:
- The JSON parse path assigns every `Edit.file` from `data.get("file", "")`.
- Per-edit `file` values are ignored.

Why it matters:
- The data model explicitly supports `list[Edit]` and each `Edit` has its own `file`.
- As written, a multi-edit Architect response can only target one effective file.
- Any future real planner that emits edits across multiple files will be silently flattened onto the top-level `file`.

Suggested fix:
- Parse `file=e.get("file", data.get("file", ""))`.
- Add a provider-backed parse test with two edits targeting two different files.
- Decide whether `EditPlan.file` is still needed once per-edit file targets are supported.

### 4. Medium: `LLMLOOP.verify()` uses the current working directory, not `project_root`

File:
- `autocode/src/autocode/agent/llmloop.py:171-201`
- `autocode/src/autocode/agent/llmloop.py:203-225`

What is wrong:
- `apply()` resolves edits against `self._project_root` but returns the relative `edit.file` strings.
- `verify()` then does `Path(filepath)` without rejoining `self._project_root`.

Why it matters:
- If the caller sets `project_root` but runs from a different working directory, verification will often skip the edited files entirely.
- The result becomes a false-positive "verification passed" even when the edited Python file has syntax errors.

Suggested fix:
- Normalize the modified file list to absolute paths before returning from `apply()`, or
- resolve relative paths inside `verify()` against `self._project_root`.
- Add a regression test that sets `project_root` to a temp repo but calls `verify()` from another cwd.

Testing gap:
- Current `test_llmloop.py` only verifies direct file paths and simple dataclass behavior.
- I do not see a test that exercises the `project_root` path resolution path at all.

### 5. Medium: `LLMLOOP.plan()` will fail under an existing event loop and report the wrong error

File:
- `autocode/src/autocode/agent/llmloop.py:120-169`

What is wrong:
- The real-provider path calls `asyncio.run(_call_llm())`.
- If this is invoked from an already-running event loop, `asyncio.run()` raises `RuntimeError`.
- That error is swallowed by the broad `except Exception`, and the code returns an empty `EditPlan`.

Why it matters:
- Inline UI, TUI, or other async integrations are exactly where this loop is likely to be called.
- Instead of surfacing a real integration error, the user will see a misleading "Architect produced empty edit plan" failure.
- That will waste debugging time and make the feature appear flaky rather than clearly incompatible.

Suggested fix:
- Make `plan()` async and let callers await it.
- If a sync API is required, provide a loop-aware bridge instead of raw `asyncio.run()`.
- At minimum, catch event-loop misuse separately and surface a clear error instead of converting it to an empty plan.

Testing gap:
- I do not see a test for provider-backed `plan()` execution under an active event loop.

### 6. Medium: eval context strategies leak gold answers into the retrieval path

File:
- `autocode/src/autocode/eval/context_packer.py:18-47`
- `autocode/src/autocode/eval/context_packer.py:50-74`
- `autocode/src/autocode/eval/context_packer.py:104-114`

What is wrong:
- `_l1_curate()` and `_l2_curate()` iterate over `scenario.gold_files` to decide what to return.
- `_llm_curate()` returns the exact gold files and symbols directly.

Why it matters:
- This is not a valid evaluation of retrieval quality.
- Gold labels are supposed to be used only for scoring, not as the candidate pool for the strategies themselves.
- With the current setup:
  - false positives are artificially suppressed
  - the LLM baseline is an oracle, not a model
  - the resulting precision/recall/F1 numbers are not decision-grade

Suggested fix:
- Feed strategies a real candidate corpus from the repo or scenario input files.
- Use `gold_files` only in the scorer.
- If the current implementation is intentionally simulated, rename the strategies and docs to say so explicitly:
  - `simulated_l1`
  - `simulated_l2`
  - `oracle_llm_baseline`

Testing gap:
- Current eval tests validate math on provided contexts, which is fine.
- I do not see a test that guards against gold-label leakage in the strategy implementations.

### 7. Medium: the source-of-truth docs still contradict the claimed phase transition

File:
- `current_directives.md:7-20`
- `current_directives.md:60-90`
- `benchmarks/benchmarks/STATUS.md:3-19`
- `benchmarks/benchmarks/STATUS.md:107-141`
- `docs/plan/agentic-benchmarks/portfolio-b15-b29.md:30-50`
- `benchmarks/e2e/external/b19-multilingual-subset.json:9-68`

What is wrong:
- `current_directives.md` still says benchmark maxxing is in progress at `37/40` and that Phase 5A0 only starts after Sprint 6.
- `benchmarks/benchmarks/STATUS.md` is still anchored to `2026-02-19` and a much older benchmark state.
- `portfolio-b15-b29.md` still describes the old prototype batch (`17` tasks total, mostly single-task lanes).
- The live B19 manifest already contains `5` tasks, so the planning docs are behind the checked-in benchmark content.

Why it matters:
- This repo explicitly treats docs as the authoritative project state.
- If the implementation and the sprint docs disagree, the next phase cannot be considered cleanly approved.
- That creates ambiguity about what is actually complete, what is experimental, and what is still gated on benchmark closeout.

Suggested fix:
- Update the source-of-truth docs in the same change set as the claimed milestone.
- Make `current_directives.md` decisive and ensure all secondary docs conform to it.
- Do not claim the next phase is active until benchmark docs, portfolio docs, and artifact references all agree.

## Nitpicks

### A. `current_directives.md` still points at pre-split benchmark paths

File:
- `current_directives.md:27-31`

Issue:
- It points to `benchmarks/STATUS.md`, `benchmarks/EVALUATION.md`, and similar pre-split paths.
- The actual files now live under `benchmarks/benchmarks/`.

Suggestion:
- Fix these references immediately so new sessions do not start from dead paths.

### B. `benchmarks/benchmarks/STATUS.md` still describes artifact paths as "not present"

File:
- `benchmarks/benchmarks/STATUS.md:9-10`
- `benchmarks/benchmarks/STATUS.md:49-70`

Issue:
- The doc repeatedly says artifacts were generated in prior sessions and not committed.
- That is stale state for a repo that is now making much stronger completion claims.

Suggestion:
- Either commit the authoritative artifacts or stop citing missing artifacts as proof of state.

### C. `LLMLOOP` tests are still mostly structural

File:
- `autocode/tests/unit/test_llmloop.py:17-109`

Issue:
- The suite checks dataclasses, empty-plan handling, and local syntax checks.
- It does not exercise:
  - provider-backed JSON parse behavior
  - multi-file plan parsing
  - async/event-loop integration
  - `project_root` verification semantics

Suggestion:
- Add real regression tests for the failure modes above before wiring this loop into the UI.

### D. MCP tests prove the happy path but not the actual security boundary

File:
- `autocode/tests/unit/test_mcp_server.py:23-89`

Issue:
- The tests validate blocked direct file paths and audit logging.
- They do not test the critical case where `allowed_paths` is narrower than `project_root`.

Suggestion:
- Add a test that sets:
  - `project_root = tmp_path`
  - `allowed_paths = [tmp_path / "safe"]`
  - and verify `search_code` cannot read from `tmp_path / "unsafe"`.

## Recommended Next Order

1. Fix `multi_edit` rollback semantics before exposing it in normal workflows.
2. Fix MCP allowlist enforcement before treating the MCP server as safely shareable.
3. Fix `LLMLOOP` path resolution and async/provider integration before wiring it into real UIs or providers.
4. Demote the eval harness from "real benchmark" language until the gold-label leakage is removed.
5. Reconcile `current_directives.md`, benchmark status docs, and B15-B29 portfolio docs with the actual checked-in state.
6. Only after the docs and the later-phase modules agree should the repo claim a clean transition beyond benchmark closeout.
