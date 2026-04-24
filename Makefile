.PHONY: setup test lint format clean clean-runtime tui go-test bench tui-regression tui-reference-capture tui-references tui-reference-gap tui-frame-sequence tui-scene-matrix

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

# -- TUI reference-driven testing (Slice 1 landed; Slice 2 in roadmap) --
#
# `tui-references` runs the design-target ratchet: structural predicates
# on the Go TUI's live pyte render, contrasted against the canonical
# scene contract extracted from `tui-references/AutoCode TUI _standalone_.html`.
#
# Expected outcome today: 4 XFAILED (strict=True). Each xfail is a
# design-to-implementation gap that will flip to a hard regression
# check the moment the matching UI feature ships — see
# `autocode/tests/tui-references/README.md`.
#
# The unit tests for the extractor + predicates do NOT require the Go
# binary and run in ~0.12s.

tui-references:
	cd autocode && uv run python tests/tui-references/extract_scenes.py
	cd autocode && uv run pytest tests/unit/test_tui_reference_extractor.py tests/unit/test_tui_reference_predicates.py -v
	cd autocode && uv run pytest tests/tui-references/ -v

# Manual screenshot-first evidence bundle:
# - fresh live PNG captures
# - side-by-side sheets against the exported reference JPG pages
# - markdown artifact under autocode/docs/qa/test-results/
tui-reference-gap:
	cd autocode && uv run python tests/tui-references/build_visual_gap_report.py

# Manual current-state sweep for all 14 reference scenes:
# - stores one current AutoCode analog per reference scene
# - includes direct, approximate, partial, and negative-evidence captures
# - writes frames under autocode/docs/qa/tui-frame-sequences/<stamp>/
# - writes markdown summary under autocode/docs/qa/test-results/
tui-scene-matrix:
	cd autocode && uv run python tests/tui-references/capture_reference_scene_matrix.py

# Manual mid-run frame capture helper. Use directly with either:
#   cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --list-presets
#   cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --name demo --preset sessions
#   cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --name demo --steps '[0.8, "/sessions\\r", 2.0]'
tui-frame-sequence:
	@echo "Use directly with explicit args. Example:"
	@echo "  cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --list-presets"
	@echo "  cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --name demo --preset sessions"
	@echo "  cd autocode && uv run python tests/tui-references/capture_frame_sequence.py --name demo --steps '[0.8, \"/sessions\\\\r\", 2.0]'"
