# Sprint 5A-3: Provider Adapters

> Status: **NOT STARTED**
> Sprint: 5A (Identity + Eval)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: 5A-2 (ProviderRegistry)
> Owner: Claude

---

## Goal

Implement provider adapters for llama-cpp-python (L3), Ollama (L4), and OpenRouter (cloud fallback).

---

## TDD Tests (Write First)

- [ ] `test_ollama_adapter` - Ollama adapter implements LLMProvider interface
- [ ] `test_llamacpp_adapter` - llama-cpp adapter implements L3Provider interface
- [ ] `test_openrouter_adapter` - OpenRouter adapter implements LLMProvider interface
- [ ] `test_adapter_num_ctx_enforcement` - all adapters respect num_ctx policy from ProviderRegistry

## Implementation

- [ ] Implement Ollama adapter (wrap existing Ollama integration)
- [ ] Implement llama-cpp-python adapter (new, for L3 constrained generation)
- [ ] Implement OpenRouter adapter (cloud fallback, token-capped)
- [ ] All adapters implement common provider interface
- [ ] All adapters respect num_ctx from ProviderRegistry

## Acceptance Criteria

- [ ] Provider adapters for llama-cpp, Ollama, OpenRouter
- [ ] All adapters implement common interface
- [ ] Context policy enforced per adapter
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Real Ollama test (integration, self-skips if unavailable)

## Artifacts

- Test file: `tests/unit/test_adapters.py`
- Integration test: `tests/integration/test_adapter_real.py`
- QA artifact: `docs/qa/test-results/sprint-5a-3-adapters.md`
