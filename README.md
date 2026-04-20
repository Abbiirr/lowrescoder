# AutoCode

Edge-native AI coding assistant — local-first, deterministic-first.

AutoCode runs on consumer hardware (8GB VRAM, 16GB RAM) with no cloud dependency. It uses classical AI techniques (tree-sitter, LSP, static analysis) as the primary intelligence layer, invoking LLMs only when necessary.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Rust toolchain (for the TUI frontend) — `rustup install stable`
- [LLM Gateway](http://localhost:4001/docs) running at `http://localhost:4000/v1` (OpenAI-compatible, 9 free providers with auto-failover)

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-username/autocode.git
cd autocode
uv sync --all-extras

# Build the Rust TUI frontend
cd autocode/rtui && cargo build --release && cd -

# Ensure the LLM Gateway is running at http://localhost:4000/v1
# (see http://localhost:4001/docs for setup)

# Start chatting
autocode
```

Linux is the current supported platform. macOS is out of scope. Windows is post-v1 (architecture is ConPTY-capable via `portable-pty`).

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

### Rust TUI frontend

```bash
cd autocode/rtui
cargo build --release
# Binary at autocode/rtui/target/release/autocode-tui (~2.4 MB)
```

The CLI (`autocode`) auto-discovers the binary. For manual overrides:

```bash
export AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui
```

## Usage

### Interactive chat (default)

```bash
autocode
```

Bare `autocode` launches the Rust TUI. Features:

- Streaming output with a fixed composer
- Type while the assistant is generating — messages queue for the next turn
- Slash commands with autocomplete dropdown (planned — see `docs/tui-testing/`)
- Arrow-key pickers for `/model`, `/provider`, `/sessions`
- Ctrl+K command palette
- Ctrl+C multi-stage cancel / steer
- Ctrl+E to edit the composer in `$EDITOR`
- Frecency-ranked input history (Up/Down arrows in Idle)
- Bracketed paste support
- Inline mode by default; `--altscreen` opt-in via binary flag

### Explicit mode selection

```bash
autocode chat                  # Rust TUI (default)
autocode chat --tui            # Fullscreen Textual TUI (fallback)
autocode chat --legacy         # Python Rich REPL (no agent loop)
```

### Single question

```bash
autocode ask "How do I reverse a list in Python?"
autocode ask "What does this function do?" --file src/myapp/utils.py
```

### Configuration

```bash
autocode config show    # display current config
autocode config check   # validate config and show warnings
autocode config path    # show config file location
```

### Backend server (used internally by the TUI)

```bash
autocode serve           # JSON-RPC server on stdin/stdout
autocode serve --verbose # with debug logging
```

### Version

```bash
autocode --version
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
| `AUTOCODE_TUI_BIN` | Override path to the Rust TUI binary |

## Development

### Setup

```bash
make setup
# Or directly: uv sync --all-extras
```

### Run tests

```bash
# Python unit tests
uv run pytest autocode/tests/unit/ -v

# Rust TUI unit + integration tests
cd autocode/rtui && cargo test
```

### Run linting

```bash
# Python
cd autocode && uv run ruff check src/ tests/

# Rust
cd autocode/rtui && cargo clippy -- -D warnings
cd autocode/rtui && cargo fmt -- --check
```

### TUI testing

Four complementary dimensions — see [`docs/tui-testing/`](docs/tui-testing/) for the strategy and enforced checklist.

```bash
make tui-regression       # Track 1 runtime invariants
make tui-references       # Track 4 design-target ratchet
AUTOCODE_TUI_BIN=autocode/rtui/target/release/autocode-tui \
  uv run python autocode/tests/vhs/run_visual_suite.py   # VHS self-regression
python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py   # PTY smoke
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

AutoCode uses a **Rust TUI frontend** + **Python backend** split, communicating via JSON-RPC 2.0 over stdin/stdout (via PTY):

```
Rust TUI (crossterm + ratatui + tokio)  ←── JSON-RPC ──►  Python Backend (agent loop, tools, LLM)
```

The Rust frontend handles all terminal interaction (rendering, input, approvals, autocomplete). The Python backend handles intelligence: agent loop, tool execution, LLM providers, session storage, and slash commands.

### 4-Layer Intelligence Model

Each layer adds capability at increasing cost:

| Layer | What | Latency | LLM Tokens |
|-------|------|---------|------------|
| 1 - Deterministic | tree-sitter, LSP, static analysis | <50ms | 0 |
| 2 - Retrieval | Code search, embeddings, context | 100-500ms | 0 |
| 3 - Constrained | Grammar-constrained generation (1.5B model) | 500ms-2s | 500-2000 |
| 4 - Reasoning | Full LLM reasoning (8B model) | 5-30s | 2000-8000 |

The system always tries the cheapest layer first and only escalates when necessary.

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation, [docs/reference/rust-tui-architecture.md](docs/reference/rust-tui-architecture.md) for the Rust TUI internals, and [docs/reference/rust-tui-rpc-contract.md](docs/reference/rust-tui-rpc-contract.md) for the JSON-RPC protocol.

## License

MIT
