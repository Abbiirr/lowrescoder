.PHONY: setup test lint format clean

setup:
	uv sync --all-extras

test:
	uv run pytest tests/ -v --cov=src/hybridcoder

lint:
	uv run ruff check src/ tests/
	uv run mypy src/hybridcoder/

format:
	uv run ruff format src/ tests/

clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache dist build
