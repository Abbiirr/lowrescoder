.PHONY: setup test lint format clean clean-runtime tui go-test bench tui-regression tui-reference-capture

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

clean-runtime:
	rm -rf sandboxes/ logs/
	@echo "Runtime directories removed (sandboxes/, logs/)"

tui:
	cd autocode && $(MAKE) tui

go-test:
	cd autocode && $(MAKE) go-test

bench:
	cd benchmarks && bash run_all_benchmarks.sh

# -- TUI comparison (Track 1 = autocode regression; Track 2 = manual) --
#
# `tui-regression` is CI-eligible. Captures autocode against the tracked
# scenario set, writes artifacts under autocode/docs/qa/tui-comparison/
# regression/<run-id>/, and fails non-zero if any HARD invariant predicate
# fails. Soft-style predicate failures are expected on the current tree
# (Track 3 backlog) and do NOT cause this target to fail.
#
# `tui-reference-capture` is MANUAL only — never run in CI. Captures
# reference TUIs (claude, pi, codex, opencode, goose, forge) through the
# 5 portable scenarios. See PLAN.md §1g and docs/plan/tui-style-gap-backlog.md.

tui-regression:
	cd autocode && uv run python tests/tui-comparison/run.py startup
	cd autocode && uv run python tests/tui-comparison/run.py first-prompt-text
	cd autocode && uv run python tests/tui-comparison/run.py model-picker
	cd autocode && uv run python tests/tui-comparison/run.py ask-user-prompt
	cd autocode && uv run python tests/tui-comparison/run.py error-state
	cd autocode && uv run python tests/tui-comparison/run.py orphaned-startup
	cd autocode && uv run python tests/tui-comparison/run.py spinner-cadence
	cd autocode && uv run pytest tests/tui-comparison/tests/ -v

tui-reference-capture:
	@echo "Not yet implemented — Phase 3 work. See PLAN.md §1g Track 2."
	@false
