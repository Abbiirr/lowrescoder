# Tests

Test suite for AutoCode.

## Contents
- `unit/` — Unit tests (~1200+ tests)
- `integration/` — LLM provider integration tests
- `benchmark/` — Scoring rubrics and benchmark tests
- `test_sprint_verify.py` — Sprint exit criteria

## Running
```bash
uv run pytest tests/ -v          # All tests
uv run pytest tests/unit/ -v     # Unit only
make test                        # Via Makefile
```
