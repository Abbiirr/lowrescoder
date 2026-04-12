# Repository Extraction Manifest — COMPLETED

> Extraction executed 2026-03-21 via `git filter-repo` from fresh clones.
> All 4 submodules established and functional.

## Submodules (DONE)

### 1. autocode (main product) — DONE
```
Submodule path: autocode/
Source repo:    /home/bs01763/projects/ai/lowrescoder-modules/autocode
Contents:       src/autocode/, cmd/autocode-tui/, tests/, pyproject.toml,
                Makefile, build scripts, TESTING.md, uv.lock
Tests:          915 passed, 4 skipped
```

### 2. benchmarks — DONE
```
Submodule path: benchmarks/
Source repo:    /home/bs01763/projects/ai/lowrescoder-modules/benchmarks
Contents:       adapters/, e2e/, benchmark_runner.py, docker_helpers.py,
                run_all_benchmarks.sh, tests/, pyproject.toml
Tests:          139 passed
Imports:        from benchmarks.* (renamed from scripts.*)
```

### 3. docs — DONE
```
Submodule path: docs/
Source repo:    /home/bs01763/projects/ai/lowrescoder-modules/docs
Contents:       All documentation (flattened from docs/ prefix)
                Includes ailogd/ docs (moved from root)
```

### 4. training-data — DONE
```
Submodule path: training-data/
Source repo:    /home/bs01763/projects/ai/lowrescoder-modules/training-data
Contents:       README.md (fresh init, no prior tracked content)
```

### academic-research — DEFERRED
No tracked content existed. Not extracted.

## Dependency Model (LIVE)
```
benchmarks/ depends on → autocode (via uv workspace editable dep)
training-data/         → standalone
docs/                  → standalone
```

## uv Workspace Config (LIVE)
```toml
# Root pyproject.toml
[project]
name = "autocode-workspace"
dependencies = ["autocode", "autocode-benchmarks"]

[tool.uv.workspace]
members = ["autocode", "benchmarks"]

[tool.uv.sources]
autocode = { workspace = true }
autocode-benchmarks = { workspace = true }
```

## Superproject Root (target: thin orchestration layer)
```
.gitmodules                 — submodule registry
pyproject.toml              — uv workspace config
Makefile                    — thin delegator to submodules
CLAUDE.md                   — AI assistant guidelines
AGENTS_CONVERSATION.MD      — cross-agent comms
AGENT_COMMUNICATION_RULES.md — comms protocol
AGENTS.md                   — agent registry
README.md                   — project README
current_directives.md       — active sprint directives
codex/                      — Codex CLI skill config
.env                        — environment (gitignored)
```

## Verification
- All imports resolve: `from autocode.cli import app` ✓
- Cross-module access: benchmarks can import autocode ✓
- Tests: 1054 passed, 0 failed, 4 skipped ✓
- Submodule status: 4/4 initialized ✓
