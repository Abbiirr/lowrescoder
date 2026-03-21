# AutoCode

Edge-native AI coding assistant — local-first, deterministic-first.

AutoCode runs on consumer hardware (8GB VRAM, 16GB RAM) with no cloud dependency. It uses classical AI techniques (tree-sitter, LSP, static analysis) as the primary intelligence layer, invoking LLMs only when necessary.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Go 1.22+ (for the TUI frontend)
- [LLM Gateway](http://localhost:4001/docs) running at `http://localhost:4000/v1` (OpenAI-compatible, 9 free providers with auto-failover)

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-username/autocode.git
cd autocode
uv sync --all-extras

# Build the Go TUI frontend
make tui                  # Linux/macOS
build.bat tui             # Windows

# Ensure the LLM Gateway is running at http://localhost:4000/v1
# (see http://localhost:4001/docs for setup)

# Start chatting
uv run autocode chat
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
uv sync --extra layer4   # LLM Gateway client (OpenAI-compatible)
uv sync --extra dev      # pytest, ruff, mypy
```

### Go TUI frontend

```bash
# Linux/macOS
make tui

# Windows
build.bat tui

# Or directly (any platform):
cd cmd/autocode-tui && go build -o ../../build/autocode-tui .
```

The binary is placed in `build/autocode-tui` (or `build/autocode-tui.exe` on Windows).

## Usage

### Interactive chat (default)

```bash
uv run autocode chat
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
uv run autocode chat --go-tui      # Force Go TUI
uv run autocode chat --legacy       # Python Rich REPL (no agent loop)
uv run autocode chat --tui          # Fullscreen Textual TUI
uv run autocode chat --sequential   # Disable parallel input
```

### Single question

```bash
uv run autocode ask "How do I reverse a list in Python?"
```

### Ask with file context

```bash
uv run autocode ask "What does this function do?" --file src/myapp/utils.py
```

### View configuration

```bash
uv run autocode config show    # display current config
uv run autocode config check   # validate config and show warnings
uv run autocode config path    # show config file location
```

### Backend server (used internally by Go TUI)

```bash
uv run autocode serve           # JSON-RPC server on stdin/stdout
uv run autocode serve --verbose # with debug logging
```

### Version

```bash
uv run autocode version
```

## Configuration

AutoCode loads configuration with this precedence (highest wins):

1. Environment variables
2. Project config (`.autocode.yaml` in project root)
3. Global config (`~/.autocode/config.yaml`)
4. Built-in defaults

### Default backend: LLM Gateway

No configuration needed — just have the LLM Gateway running at `http://localhost:4000/v1`:

```bash
# Verify the gateway is up
curl http://localhost:4000/health/readiness

# See available model aliases
curl http://localhost:4000/v1/models
```

The gateway aggregates 9 free providers (OpenRouter, Google AI Studio, Cerebras, Groq, Mistral, GitHub Models, NVIDIA NIM, Cloudflare, Cohere) with automatic failover and latency-based routing. See [gateway docs](http://localhost:4001/docs) for details.

### Model aliases

Set `AUTOCODE_LLM_MODEL` to one of these aliases:

| Alias | Best for |
|-------|----------|
| `coding` | Code generation, review, agentic coding (default for AutoCode) |
| `default` | General purpose, tries all providers |
| `fast` | Lowest latency (Cerebras, Groq) |
| `thinking` | Deep reasoning (DeepSeek R1, Gemini 2.5 Pro) |
| `vision` | Image/multimodal understanding |
| `tools` | Function/tool calling |
| `big` | Largest models (120B-405B) |
| `local` | Ollama only, never leaves machine |

### Environment variables

| Variable | Description |
|----------|-------------|
| `AUTOCODE_LLM_PROVIDER` | `ollama` (default, works with gateway's OpenAI-compatible API) |
| `AUTOCODE_LLM_MODEL` | Model alias: `coding`, `default`, `fast`, `thinking`, etc. |
| `AUTOCODE_LLM_API_BASE` | Gateway URL (default: `http://localhost:4000`) |
| `AUTOCODE_LLM_TEMPERATURE` | Sampling temperature (0.0-2.0) |
| `OLLAMA_HOST` | Legacy: gateway URL (default: `http://localhost:4000`) |

## Development

### Setup

```bash
make setup       # Linux/macOS
build.bat setup  # Windows
# Or directly: uv sync --all-extras
```

### Run tests

```bash
# All tests (1054 unit tests across autocode + benchmarks)
uv run pytest autocode/tests/unit/ benchmarks/tests/ -v

# Autocode tests only
uv run pytest autocode/tests/unit/ -v --cov=src/autocode

# Go tests (93 tests)
cd autocode && make go-test
# Or: cd autocode/cmd/autocode-tui && go test ./... -v
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

# LLM Gateway (requires gateway running at localhost:4000)
uv run pytest -m integration tests/integration/test_ollama.py
```

## Architecture

AutoCode uses a **Go TUI frontend** + **Python backend** split, communicating via JSON-RPC 2.0 over stdin/stdout:

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
