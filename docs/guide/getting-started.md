# Getting Started with AutoCode

## What is AutoCode?

AutoCode is an edge-native AI coding assistant that runs on your machine.
It uses deterministic tools first (tree-sitter, LSP, static analysis) and
invokes LLMs only when necessary — the opposite of how most AI coders work.

## Installation

### Prerequisites

- Python 3.11+
- Git
- Ollama (for local LLM inference)

### Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen3:8b
```

### Install AutoCode

```bash
# Clone and set up
git clone <repo-url> autocode
cd autocode
git submodule update --init --recursive
uv sync
```

### Verify Installation

```bash
# Run doctor to check everything
uv run autocode doctor

# Expected output:
# AutoCode Doctor — System Readiness Report
# =============================================
#   [PASS] python_version: Python 3.11.x
#   [PASS] git: Git available, in a git repo
#   [PASS] tree_sitter: tree-sitter + Python grammar available
#   [PASS] disk_space: Disk free: X.X GB
#   ...
# 8/8 checks passed
```

## First Chat Session

```bash
# Start an interactive session
uv run autocode chat

# Or ask a one-shot question
uv run autocode ask "What does the main function do?"
```

## Configuration

AutoCode stores its config at `~/.autocode/config.yaml`:

```yaml
llm:
  provider: ollama
  model: qwen3:8b
  api_base: http://localhost:11434

shell:
  timeout: 30
  enabled: true
```

### Using a Gateway (for benchmarks or multiple providers)

Set environment variables in `.env`:

```bash
AUTOCODE_LLM_PROVIDER=openrouter
AUTOCODE_LLM_API_BASE=http://localhost:4000/v1
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=swebench
```

## Project Structure

AutoCode is a git submodule superproject:

| Submodule | Contents |
|-----------|----------|
| `autocode/` | Python backend, Go TUI, tests |
| `benchmarks/` | Benchmark harness, fixtures |
| `docs/` | Documentation |
| `training-data/` | Training data |

## Next Steps

- Run `uv run autocode doctor` to verify your setup
- Read [Commands Reference](commands.md) for all available commands
- Check `current_directives.md` for current project status
