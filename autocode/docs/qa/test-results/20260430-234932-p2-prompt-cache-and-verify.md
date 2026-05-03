# P2 Prompt Cache And Verify-Before-Use Verification

Date: 2026-04-30 23:49:32 Asia/Dhaka
Agent: Codex
Slice: P2 — Tier 1 prompt cache + verify-before-use

## Scope

Implemented and validated:

- Stable/dynamic prompt split with `CACHE_BOUNDARY_MARKER`.
- Verify-before-use memory discipline in stable instructions.
- Deterministic tool-definition serialization for stable prompt prefix.
- OpenRouter explicit-cache gating for `anthropic/*` and `google/gemini-*`.
- OpenRouter→Anthropic `anthropic-beta: prompt-caching-2024-07-31` header.
- Cache breakpoint injection on stable system block only.
- 4-cache-control hard-limit enforcement.
- Provider cache-control rejection fallback to non-cached retry.
- Ollama cache-control no-op normalization.
- Cache/reasoning usage extraction, token tracker aggregation, billable input multiplier, SQLite persistence, session resume hydration.
- `/cost --detail` cache writes/reasoning/effective multiplier output.
- Backend cost update cached-token projection and Rust TUI `⚡N% cached` status indicator.
- P1 AI verification cache-hit-ratio predicate and scenario.

## Validation

- Focused P2 slice:
  `uv run pytest autocode/tests/unit/test_prompt_cache_boundary.py autocode/tests/unit/test_token_tracker_cache.py autocode/tests/unit/test_llm.py::TestProviderUsageCapture autocode/tests/unit/test_agent_loop.py::TestPromptSplitting autocode/tests/unit/test_commands.py::TestHandleCost autocode/tests/unit/test_backend_server.py::TestCostUpdateProducer benchmarks/tests/test_ai_verification_substrate.py -q`
  Result: `67 passed in 1.80s`

- Provider/cost regression slice:
  `uv run pytest autocode/tests/unit/test_llm.py autocode/tests/unit/test_token_counting.py autocode/tests/unit/test_cost_dashboard.py autocode/tests/unit/test_layer45_router.py autocode/tests/unit/test_commands.py::TestHandleCost autocode/tests/integration/test_prompt_cache.py -q`
  Result: `83 passed, 1 skipped in 1.13s`

- Touched Python/benchmark slice:
  `uv run pytest autocode/tests/unit/test_prompt_cache_boundary.py autocode/tests/unit/test_token_tracker_cache.py autocode/tests/unit/test_llm.py autocode/tests/unit/test_token_counting.py autocode/tests/unit/test_cost_dashboard.py autocode/tests/unit/test_layer45_router.py autocode/tests/unit/test_agent_loop.py::TestPromptSplitting autocode/tests/unit/test_agent_loop.py::TestAgentLoop::test_telemetry_emits_turn_and_llm_events autocode/tests/unit/test_commands.py::TestHandleCost autocode/tests/unit/test_backend_server.py::TestCostUpdateProducer benchmarks/tests/test_ai_verification_substrate.py autocode/tests/integration/test_prompt_cache.py -q`
  Result: `139 passed, 1 skipped in 2.24s`

- Full Python unit suite:
  `timeout 360 uv run pytest autocode/tests/unit/ -q`
  Result: `2192 passed, 12 skipped in 101.50s`

- Benchmark substrate:
  `uv run pytest benchmarks/tests/test_ai_verification_substrate.py -q`
  Result: `22 passed in 0.25s`

- Rust TUI:
  `cd autocode/rtui && cargo fmt -- --check && cargo test`
  Result: `210 passed` in main TUI unit binary plus `2 passed` in Rust integration-style test binaries.

- Ruff:
  `uv run ruff check ...`
  Result: `All checks passed!`

- Whitespace:
  `git diff --check`
  Result: clean.

## Notes

- Live prompt-cache provider verification exists as `autocode/tests/integration/test_prompt_cache.py` and is skipped by default unless `AUTOCODE_RUN_LIVE_PROMPT_CACHE=1` and `OPENROUTER_API_KEY` are set. This avoids accidental token spend in default CI/local sweeps.
- The full unit suite exposed and fixed an unrelated-looking but real P1a regression: backend telemetry emission was resetting the attached transport to default stdout. Regression coverage was added in `test_backend_transport_conformance.py`.
