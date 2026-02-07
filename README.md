# HybridCoder

Edge-native AI coding assistant — local-first, deterministic-first.

HybridCoder runs on consumer hardware (8GB VRAM, 16GB RAM) with no cloud dependency. It uses classical AI techniques (tree-sitter, LSP, static analysis) as the primary intelligence layer, invoking LLMs only when necessary.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Ollama](https://ollama.com/) (for local LLM inference)

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-username/hybridcoder.git
cd hybridcoder
uv sync --all-extras

# Pull the default model
ollama pull qwen3:8b

# Start chatting
uv run hybridcoder chat
```

## Installation

### Basic (CLI + OpenRouter dev backend)

```bash
uv sync
```

### Full (all layers including local LLM)

```bash
uv sync --all-extras
```

### Individual layers

```bash
uv sync --extra layer1   # tree-sitter parsing
uv sync --extra layer2   # LanceDB + embeddings
uv sync --extra layer3   # llama-cpp-python + Outlines (constrained generation)
uv sync --extra layer4   # Ollama client
uv sync --extra dev      # pytest, ruff, mypy
```

## Usage

### Interactive chat

```bash
uv run hybridcoder chat
```

Starts a multi-turn REPL with streaming output. Type `exit` or press `Ctrl+C` to quit.

By default, the inline prompt stays active while the assistant is generating (type while streaming). Submitting another message while a response is streaming queues it (FIFO) and runs it after the current generation completes or is cancelled.

If your terminal has issues with the always-on prompt, use sequential mode:

```bash
uv run hybridcoder chat --sequential
```

### Single question

```bash
uv run hybridcoder ask "How do I reverse a list in Python?"
```

### Ask with file context

```bash
uv run hybridcoder ask "What does this function do?" --file src/myapp/utils.py
```

### View configuration

```bash
uv run hybridcoder config show    # display current config
uv run hybridcoder config check   # validate config and show warnings
uv run hybridcoder config path    # show config file location
```

### Version

```bash
uv run hybridcoder version
```

## Configuration

HybridCoder loads configuration with this precedence (highest wins):

1. Environment variables
2. Project config (`.hybridcoder.yaml` in project root)
3. Global config (`~/.hybridcoder/config.yaml`)
4. Built-in defaults

### Default backend: Ollama (local)

No configuration needed — just have Ollama running:

```bash
ollama serve
```

### Using OpenRouter (cloud, for development)

Copy the example env file and add your API key:

```bash
cp .env.example .env
# Edit .env with your OpenRouter key
```

Then set the provider:

```bash
# Via environment variable
HYBRIDCODER_LLM_PROVIDER=openrouter uv run hybridcoder chat

# Or in .hybridcoder.yaml
# llm:
#   provider: openrouter
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `HYBRIDCODER_LLM_PROVIDER` | `ollama` (default) or `openrouter` |
| `HYBRIDCODER_LLM_MODEL` | Model name override |
| `HYBRIDCODER_LLM_API_BASE` | API base URL override |
| `HYBRIDCODER_LLM_TEMPERATURE` | Sampling temperature (0.0-2.0) |
| `OPENROUTER_API_KEY` | OpenRouter API key (required if using OpenRouter) |
| `OPENROUTER_MODEL` | OpenRouter model override |

## Development

### Setup

```bash
make setup       # or: uv sync --all-extras
```

### Run tests

```bash
make test        # unit tests with coverage
```

### Run linting

```bash
make lint        # ruff check + mypy
```

### Format code

```bash
make format      # ruff format
```

### Integration tests

Integration tests are skipped by default. To run them:

```bash
# OpenRouter (requires OPENROUTER_API_KEY in .env)
uv run pytest -m integration tests/integration/test_openrouter.py

# Ollama (requires ollama serve running)
uv run pytest -m integration tests/integration/test_ollama.py
```

## Architecture

HybridCoder uses a 4-layer intelligence model. Each layer adds capability at increasing cost:

| Layer | What | Latency | LLM Tokens |
|-------|------|---------|------------|
| 1 - Deterministic | tree-sitter, LSP, static analysis | <50ms | 0 |
| 2 - Retrieval | Code search, embeddings, context | 100-500ms | 0 |
| 3 - Constrained | Grammar-constrained generation (1.5B model) | 500ms-2s | 500-2000 |
| 4 - Reasoning | Full LLM reasoning (8B model) | 5-30s | 2000-8000 |

The system always tries the cheapest layer first and only escalates when necessary.

## License

MIT
