# AutoCode Commands Reference

## Core Commands

### `autocode chat`

Start an interactive coding session.

```bash
uv run autocode chat
```

### `autocode ask <question>`

Ask a one-shot question without entering interactive mode.

```bash
uv run autocode ask "What does this function do?"
uv run autocode ask "Find all usages of UserService"
```

### `autocode edit <instruction>`

Request a code edit.

```bash
uv run autocode edit "Add error handling to the login function"
```

## Diagnostic Commands

### `autocode doctor`

Run 8 system readiness checks with remediation messages.

```bash
uv run autocode doctor
```

Checks: Python version, Ollama, L4 model, LanceDB, tree-sitter, Git, VRAM, disk space.

### `autocode setup`

Run first-time bootstrap and verify all dependencies.

```bash
uv run autocode setup
```

### `autocode version`

Show the installed version.

```bash
uv run autocode version
```

## Refactoring Commands

### `autocode rename <old> <new>`

Rename a symbol across the entire project.

```bash
# Preview (dry run)
uv run autocode rename helper_func process_value

# Apply the rename
uv run autocode rename helper_func process_value --apply
```

## Team Commands

### `autocode team list`

List all defined agent teams.

```bash
uv run autocode team list
```

### `autocode team create <name>`

Create a new agent team.

```bash
uv run autocode team create bugfix
```

### `autocode team show <name>`

Show details of a team.

```bash
uv run autocode team show bugfix
```

## Configuration Commands

### `autocode config`

Show current configuration.

```bash
uv run autocode config
```

### `autocode config path`

Show the config file path.

```bash
uv run autocode config path
```

### `autocode config set <key> <value>`

Set a configuration value.

```bash
uv run autocode config set llm.model "qwen3:8b"
uv run autocode config set llm.provider "ollama"
```

## Shell Completions

Typer provides built-in shell completions:

```bash
# Install completions for your shell
uv run autocode --install-completion

# Show completion script
uv run autocode --show-completion
```

## Running Tests

```bash
# All tests
uv run pytest autocode/tests/unit/ benchmarks/tests/ -v

# Autocode tests only
uv run pytest autocode/tests/unit/ -v

# Benchmark tests only
uv run pytest benchmarks/tests/ -v
```

## Running Benchmarks

```bash
# Source environment for gateway
set -a && source .env && set +a

# List available lanes
uv run python benchmarks/benchmark_runner.py --list-lanes

# Run a specific lane
uv run python benchmarks/benchmark_runner.py --agent autocode --lane B9-PROXY --model swebench

# Prepare a human-operated TUI benchmark sweep
uv run python benchmarks/prepare_tui_benchmark_run.py --scope full --mode inline --strict

# Run all B7-B14
bash benchmarks/run_all_benchmarks.sh
```
