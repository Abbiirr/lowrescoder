# Repository Extraction Manifest

## Target Repos

### 1. autocode (main product)
```
src/autocode/           → autocode/src/autocode/
cmd/autocode-tui/       → autocode/cmd/autocode-tui/
pyproject.toml          → autocode/pyproject.toml
Makefile                → autocode/Makefile
go.mod                  → autocode/go.mod
go.sum                  → autocode/go.sum
uv.lock                 → autocode/uv.lock
README.md               → autocode/README.md
CLAUDE.md               → autocode/CLAUDE.md
TESTING.md              → autocode/TESTING.md
.env.example            → autocode/.env.example
build.bat               → autocode/build.bat
build.sh                → autocode/build.sh
tests/unit/             → autocode/tests/unit/ (product tests)
tests/integration/      → autocode/tests/integration/
tests/test_sprint_verify.py → autocode/tests/
```

### 2. benchmarks
```
benchmarks/             → benchmarks/ (already structured)
scripts/e2e/            → benchmarks/e2e/ (already copied)
scripts/adapters/       → benchmarks/adapters/ (already copied)
tests/benchmark/        → benchmarks/tests/
sandboxes/              → benchmarks/sandboxes/ (gitignored)
```

### 3. docs
```
docs/                   → docs/ (as-is)
AGENT_COMMUNICATION_RULES.md → docs/
AGENTS.md               → docs/
```

### 4. tests (cross-repo integration tests only)
```
tests/                  → split: unit→autocode, benchmark→benchmarks
```

### 5. training-data
```
training_data/          → training-data/ (as-is)
```

### 6. academic-research
```
academic_research/      → deferred (no tracked content)
```

## Dependency Model
```
benchmarks/ depends on → autocode (editable path dep)
tests/ depends on      → autocode + benchmarks
training-data/         → standalone
docs/                  → standalone
```

## uv Workspace Config (superproject)
```toml
[tool.uv.workspace]
members = ["autocode", "benchmarks"]

[tool.uv.sources]
autocode = { path = "autocode", editable = true }
```
