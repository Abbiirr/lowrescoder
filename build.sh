#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-run}"

case "$TARGET" in
  run)
    echo "Building Go TUI..."
    (cd cmd/hybridcoder-tui && go build -o ../../build/hybridcoder-tui .)
    echo "Build OK. Running..."
    exec ./build/hybridcoder-tui
    ;;
  tui)
    echo "Building Go TUI..."
    (cd cmd/hybridcoder-tui && go build -o ../../build/hybridcoder-tui .)
    echo "Done: build/hybridcoder-tui"
    ;;
  setup)
    echo "Installing Python dependencies..."
    uv sync --all-extras
    ;;
  test)
    echo "Running Python tests..."
    uv run pytest tests/ -v --cov=src/hybridcoder
    ;;
  test-all)
    echo "Running Go tests..."
    (cd cmd/hybridcoder-tui && go test ./... -v -count=1)
    echo "Running Python tests..."
    uv run pytest tests/ -v --cov=src/hybridcoder
    ;;
  go-test)
    echo "Running Go tests..."
    (cd cmd/hybridcoder-tui && go test ./... -v -count=1)
    ;;
  lint)
    echo "Running linters..."
    uv run ruff check src/ tests/
    ;;
  format)
    echo "Formatting code..."
    uv run ruff format src/ tests/
    ;;
  help|*)
    echo "Usage: ./build.sh [target]"
    echo ""
    echo "Targets:"
    echo "  run       Build + run Go TUI (default)"
    echo "  tui       Build Go TUI frontend only"
    echo "  setup     Install Python dependencies"
    echo "  test      Run Python unit tests"
    echo "  test-all  Run Go + Python tests"
    echo "  go-test   Run Go unit tests"
    echo "  lint      Run ruff"
    echo "  format    Run ruff format"
    ;;
esac
