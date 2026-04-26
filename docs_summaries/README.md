# Project Docs Summaries

This folder is a navigation layer over the project documentation. It does not replace the canonical docs; it condenses them into a smaller set of summary files with references back to the source material.

## How to use this folder

- Start with [01_control_and_governance.md](01_control_and_governance.md) if you need to understand what is authoritative right now.
- Use [02_runtime_architecture_and_backend.md](02_runtime_architecture_and_backend.md) for the current runtime shape and backend/frontend split.
- Use [03_testing_tui_and_quality.md](03_testing_tui_and_quality.md) for the TUI/testing surface and QA expectations.
- Use [04_benchmarks_and_evaluation.md](04_benchmarks_and_evaluation.md) for benchmark operations, evaluation rules, and fixture corpora.
- Use [05_plans_research_and_special_docsets.md](05_plans_research_and_special_docsets.md) for roadmap, research, and side-docset context.
- Use [06_evidence_bugs_and_archives.md](06_evidence_bugs_and_archives.md) for bug ledgers, artifact stores, and archive families.
- Use [07_doc_family_inventory.md](07_doc_family_inventory.md) for coverage counts and the family map used in this summary pass.

## Summary method

This pass covers the documentation surface by family rather than file-by-file prose rewrites.

- Canonical operating docs are summarized directly.
- Large artifact collections are summarized as collections.
- Historical archive families are summarized as historical stores, not as current source of truth.
- `docs/communication/old/` was not read directly because the repo protocol treats those archives as off-limits unless explicitly requested.

## Precedence rule when docs disagree

Use this order:

1. [current_directives.md](../current_directives.md)
2. [EXECUTION_CHECKLIST.md](../EXECUTION_CHECKLIST.md)
3. [PLAN.md](../PLAN.md)
4. the active plan/checklist file referenced by the first two docs

Everything else is context, history, research, or operator guidance unless it explicitly overrides one of those files.
