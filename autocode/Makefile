.PHONY: setup test lint format clean tui tui-spike go-test

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

# Go TUI targets
tui:
	cd cmd/autocode-tui && go build -o ../../build/autocode-tui$(if $(filter Windows_NT,$(OS)),.exe,) .

tui-spike:
	cd cmd/hybridcoder-tui-spike && go build -o ../../build/hybridcoder-tui-spike$(if $(filter Windows_NT,$(OS)),.exe,) .

go-test:
	cd cmd/autocode-tui && go test ./... -v
