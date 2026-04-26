# Documentation Family Inventory

This file records how the documentation surface was grouped for summary coverage.

## Inventory snapshot

As of this summary pass:

- `docs/`: about `916` markdown docs
- `autocode/docs/`: about `459` markdown docs

Largest `docs/` families:

- `docs/qa`: `509`
- `docs/communication`: `199`
- `docs/plan`: `69`
- `docs/research`: `30`
- `docs/codex`: `23`
- `docs/claude`: `19`
- `docs/archive`: `16`
- `docs/ailogd`: `13`
- `docs/tui-testing`: `10`
- `docs/reference`: `8`

`autocode/docs/` is almost entirely under `autocode/docs/qa`.

## Coverage strategy

Because most of the doc count is artifact/archive material, the summaries in this folder use families rather than file-by-file rewrites.

### Directly summarized as canonical prose docs

- root control docs
- architecture/runtime docs
- testing/TUI strategy docs
- benchmark operator/evaluation docs
- active plan and research docs

### Summarized as collections

- `docs/qa/`
- `autocode/docs/qa/`
- benchmark fixture prompt/task docs
- `docs/archive/`
- `bugs/screenshots/`
- `docs/codex/`
- `docs/claude/`
- `docs/ailogd/`

### Not directly re-read due protocol restriction

- `docs/communication/old/`

That family is summarized only as a historical comms archive store because repo rules require explicit permission before opening it.

## Summary file map

- [README.md](README.md): index and precedence
- [01_control_and_governance.md](01_control_and_governance.md): active authority and operating docs
- [02_runtime_architecture_and_backend.md](02_runtime_architecture_and_backend.md): runtime split and backend/frontend contract
- [03_testing_tui_and_quality.md](03_testing_tui_and_quality.md): testing and QA surface
- [04_benchmarks_and_evaluation.md](04_benchmarks_and_evaluation.md): benchmark operations and evaluation
- [05_plans_research_and_special_docsets.md](05_plans_research_and_special_docsets.md): plans, research, and special doc families
- [06_evidence_bugs_and_archives.md](06_evidence_bugs_and_archives.md): evidence stores, bug docs, and archives
