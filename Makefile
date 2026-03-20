.PHONY: setup test lint format clean tui go-test bench

setup:
	cd autocode && uv sync --all-extras

test:
	cd autocode && uv run pytest tests/ -v --cov=src/autocode

test-bench:
	cd benchmarks && uv run pytest tests/ -v

test-all:
	cd autocode && uv run pytest tests/ -v --cov=src/autocode
	cd benchmarks && uv run pytest tests/ -v

lint:
	cd autocode && uv run ruff check src/ tests/
	cd autocode && uv run mypy src/autocode/

format:
	cd autocode && uv run ruff format src/ tests/

clean:
	cd autocode && $(MAKE) clean

tui:
	cd autocode && $(MAKE) tui

go-test:
	cd autocode && $(MAKE) go-test

bench:
	cd benchmarks && bash run_all_benchmarks.sh
