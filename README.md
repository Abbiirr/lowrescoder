# HybridCoder

Edge-native AI coding assistant — local-first, deterministic-first.

HybridCoder runs on consumer hardware (8GB VRAM, 16GB RAM) with no cloud dependency. It uses classical AI techniques (tree-sitter, LSP, static analysis) as the primary intelligence layer, invoking LLMs only when necessary.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Go 1.22+ (for the TUI frontend)
- [Ollama](https://ollama.com/) (for local LLM inference)

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-username/hybridcoder.git
cd hybridcoder
uv sync --all-extras

# Build the Go TUI frontend
make tui                  # Linux/macOS
build.bat tui             # Windows

# Pull the default model
ollama pull qwen3:8b

# Start Ollama
ollama serve

# Start chatting
uv run hybridcoder chat
```

## Installation

### Python backend

```bash
# Basic (CLI + OpenRouter dev backend)
uv sync

# Full (all layers including local LLM)
uv sync --all-extras

# Individual layers
uv sync --extra layer1   # tree-sitter parsing
uv sync --extra layer2   # LanceDB + embeddings
uv sync --extra layer3   # llama-cpp-python + Outlines (constrained generation)
uv sync --extra layer4   # Ollama client
uv sync --extra dev      # pytest, ruff, mypy
```

### Go TUI frontend

```bash
# Linux/macOS
make tui

# Windows
build.bat tui

# Or directly (any platform):
cd cmd/hybridcoder-tui && go build -o ../../build/hybridcoder-tui .
```

The binary is placed in `build/hybridcoder-tui` (or `build/hybridcoder-tui.exe` on Windows).

## Usage

### Interactive chat (default)

```bash
uv run hybridcoder chat
```

The default mode uses the Go Bubble Tea TUI (if built) or falls back to the Python inline REPL. Features:

- Streaming output with fixed input bar at the bottom
- Type while the assistant is generating — your message is queued
- Arrow-key tool approval selector (Yes / Yes for session / No)
- Slash command autocomplete (type `/` then Tab)
- Persistent command history (Up/Down arrows)
- Native terminal scrollback preserved after exit
- Markdown-rendered responses (on completion)

### Explicit mode selection

```bash
uv run hybridcoder chat --go-tui      # Force Go TUI
uv run hybridcoder chat --legacy       # Python Rich REPL (no agent loop)
uv run hybridcoder chat --tui          # Fullscreen Textual TUI
uv run hybridcoder chat --sequential   # Disable parallel input
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

### Backend server (used internally by Go TUI)

```bash
uv run hybridcoder serve           # JSON-RPC server on stdin/stdout
uv run hybridcoder serve --verbose # with debug logging
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
make setup       # Linux/macOS
build.bat setup  # Windows
# Or directly: uv sync --all-extras
```

### Run tests

```bash
# Python tests (569+ unit tests)
make test            # Linux/macOS
build.bat test       # Windows
# Or: uv run pytest tests/ -v --cov=src/hybridcoder

# Go tests (93 tests)
make go-test         # Linux/macOS
build.bat go-test    # Windows
# Or: cd cmd/hybridcoder-tui && go test ./... -v
```

### Run linting

```bash
make lint            # Linux/macOS
build.bat lint       # Windows
```

### Format code

```bash
make format          # Linux/macOS
build.bat format     # Windows
```

### Build Go TUI

```bash
make tui             # Linux/macOS
build.bat tui        # Windows
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

HybridCoder uses a **Go TUI frontend** + **Python backend** split, communicating via JSON-RPC 2.0 over stdin/stdout:

```
Go TUI (Bubble Tea)  ←── JSON-RPC ──►  Python Backend (agent loop, tools, LLM)
```

The Go frontend handles all terminal interaction (rendering, input, approvals, autocomplete). The Python backend handles intelligence: agent loop, tool execution, LLM providers, session storage, and slash commands.

### 4-Layer Intelligence Model

Each layer adds capability at increasing cost:

| Layer | What | Latency | LLM Tokens |
|-------|------|---------|------------|
| 1 - Deterministic | tree-sitter, LSP, static analysis | <50ms | 0 |
| 2 - Retrieval | Code search, embeddings, context | 100-500ms | 0 |
| 3 - Constrained | Grammar-constrained generation (1.5B model) | 500ms-2s | 500-2000 |
| 4 - Reasoning | Full LLM reasoning (8B model) | 5-30s | 2000-8000 |

The system always tries the cheapest layer first and only escalates when necessary.

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation including the JSON-RPC protocol, file structure, and stage machine.

## License

MIT
