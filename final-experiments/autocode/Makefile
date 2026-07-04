.PHONY: setup test lint format clean tui-build tui-test

setup:
	uv sync --all-extras

test:
	uv run pytest tests/ -v --cov=src/autocode

lint:
	uv run ruff check src/ tests/
	uv run mypy src/autocode/

format:
	uv run ruff format src/ tests/

clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache dist build

# Rust TUI targets
tui-build:
	cd rtui && cargo build --release

tui-test:
	cd rtui && cargo test
