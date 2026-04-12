# Phase 5: Documentation & Quality Plan

> HybridCoder — Edge-Native AI Coding Assistant
> Version: 2.0 | Date: 2026-02-05

---

## 1. Documentation Inventory

| Document | Audience | Location | Phase |
|----------|----------|----------|-------|
| README.md | Users + Contributors | `/README.md` | S0 (stub), S6 (final) |
| Installation Guide | Users | `docs/installation.md` | S6 |
| Usage Guide | Users | `docs/usage.md` | S6 |
| Configuration Reference | Users | `docs/configuration.md` | S1 (draft), S6 (final) |
| Architecture Guide | Contributors | `docs/architecture.md` | S6 |
| API Reference | Contributors | Auto-generated (pdoc/mkdocs) | S6 |
| Layer Design Docs | Contributors | `docs/layers.md` | S3-S5 |
| Benchmark Report | Everyone | `docs/benchmarks.md` | S6 |
| Contributing Guide | Contributors | `CONTRIBUTING.md` | S0 |
| Changelog | Everyone | `CHANGELOG.md` | Every sprint |

---

## 2. README.md Structure

```markdown
# HybridCoder

Edge-native AI coding assistant that runs on consumer hardware.

## Why HybridCoder?

- 60-80% fewer LLM tokens than cloud-based alternatives
- Fully local — no API keys, no cloud, no data leaves your machine
- <50ms for deterministic queries (find refs, go-to-def, type info)
- Runs on 8GB VRAM (NVIDIA RTX 3060 or equivalent)

## Quick Start

[Installation, first chat, first edit]

## Features

[Feature table with layer indicators]

## Architecture

[4-layer diagram, link to docs/architecture.md]

## Benchmarks

[Key numbers, link to docs/benchmarks.md]

## Contributing

[Link to CONTRIBUTING.md]
```

---

## 3. Installation Guide (`docs/installation.md`)

### Sections
1. **Prerequisites** — Python 3.11+, Ollama, GPU (optional)
2. **Install via pip** — `pip install hybridcoder`
3. **Install from source** — `git clone`, `uv sync`
4. **Install Ollama** — OS-specific instructions
5. **Download models** — `ollama pull qwen3:8b`
6. **Verify installation** — `hybridcoder config --check`
7. **Troubleshooting** — Common issues (Ollama not running, GPU not detected, etc.)

### Platform-Specific Notes
- **Windows**: Note about long paths, WSL2 option
- **macOS**: Apple Silicon vs Intel, Ollama Metal backend
- **Linux**: CUDA driver requirements, apt/yum packages

---

## 4. Usage Guide (`docs/usage.md`)

### Sections
1. **Chat Mode** — `hybridcoder chat` (basic conversation)
2. **Ask Mode** — `hybridcoder ask "question"` (one-shot)
3. **Edit Mode** — `hybridcoder edit file.py "add docstrings"`
4. **Undo** — Rolling back AI edits
5. **Configuration** — `hybridcoder config show/set/check`
6. **Project Rules** — How to set up `.rules/`, `AGENTS.md`, `.cursorrules`
7. **Advanced** — Verbose mode, debug logging, model selection

---

## 5. Configuration Reference (`docs/configuration.md`)

- Complete YAML schema with every key documented
- Default values and valid ranges
- Examples for common setups:
  - Minimal (CPU-only, basic chat)
  - Standard (8GB GPU, full features)
  - Advanced (12GB+ GPU, custom models)

---

## 6. Architecture Decision Records (ADRs)

Located in `docs/adr/` (created as decisions are made):

| ADR # | Decision | Status |
|-------|----------|--------|
| ADR-001 | Two-tier LLM architecture (Ollama + llama-cpp-python) | Accepted |
| ADR-002 | Qwen3-8B as default Layer 4 model | Accepted |
| ADR-003 | LanceDB for embedded vector storage | Accepted |
| ADR-004 | multilspy for LSP client | Accepted |
| ADR-005 | Router uses regex classification (no LLM) | Accepted |
| ADR-006 | jina-v2-base-code for MVP embeddings | Accepted |

### ADR Template
```markdown
# ADR-XXX: [Title]

## Status: [Proposed | Accepted | Deprecated | Superseded]

## Context
[What problem are we solving?]

## Decision
[What did we decide?]

## Consequences
[Positive and negative effects]

## Alternatives Considered
[What else was evaluated and why it was rejected]
```

---

## 7. Code Quality Standards

### 7.1 Style
- **Formatter**: ruff format (Black-compatible)
- **Linter**: ruff check (replaces flake8, isort, etc.)
- **Type checker**: mypy (strict mode for public APIs)
- **Line length**: 100 chars
- **Docstrings**: Google style, required for public APIs only
- **Imports**: sorted by ruff (isort-compatible)

### 7.2 Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### 7.3 CI Pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --all-extras
      - run: uv run ruff check src/ tests/
      - run: uv run ruff format --check src/ tests/
      - run: uv run mypy src/hybridcoder/

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: ${{ matrix.python }}
      - run: uv sync --extras dev --extras layer1
      - run: uv run pytest tests/unit/ -v --cov=src/hybridcoder
      - run: uv run pytest tests/unit/ --cov-report=xml
      - uses: codecov/codecov-action@v4
```

### 7.4 Code Coverage Targets
| Module | Target |
|--------|--------|
| `core/` | >90% |
| `edit/` | >85% |
| `layer1/` | >80% |
| `layer2/` | >75% |
| `layer3/` | >60% (LLM-dependent) |
| `layer4/` | >50% (LLM-dependent) |
| `git/` | >85% |
| `shell/` | >90% |
| `utils/` | >90% |
| **Overall** | **>75%** |

---

## 8. Release Process

### 8.1 Versioning
- Semantic versioning: MAJOR.MINOR.PATCH
- MVP = 0.1.0
- Breaking changes = bump MINOR (until 1.0)

### 8.2 Release Checklist
1. All tests pass (unit + integration)
2. All 12 MVP acceptance criteria pass
3. Benchmarks documented
4. CHANGELOG updated
5. Version bumped in `pyproject.toml`
6. README and docs reviewed
7. Create git tag
8. Build and publish to PyPI

### 8.3 PyPI Publishing
```bash
# Build
uv build

# Publish (test)
uv publish --repository testpypi

# Publish (production)
uv publish
```

---

## 9. Example Projects

Located in `examples/`:

| Example | Purpose |
|---------|---------|
| `examples/hello-chat/` | Basic chat interaction walkthrough |
| `examples/edit-python/` | Python file editing with undo |
| `examples/search-project/` | Code search across a real project |
| `examples/agentic-task/` | Multi-step refactoring task |
| `examples/rules-setup/` | Project rules configuration |
