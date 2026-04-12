# Sprint 5A-2: ProviderRegistry

> Status: **NOT STARTED**
> Sprint: 5A (Identity + Eval)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: 5A-1 (AgentCard/ModelSpec)
> Owner: Claude

---

## Goal

Multi-model provider management with lazy loading and max 2 models loaded constraint.

---

## TDD Tests (Write First)

- [ ] `test_provider_registry_register` - can register L3 and L4 providers
- [ ] `test_provider_registry_lazy_load` - providers load on first use, not at registration
- [ ] `test_provider_registry_max_2` - max 2 models loaded simultaneously
- [ ] `test_provider_registry_cleanup` - cleanup releases all loaded models
- [ ] `test_provider_registry_num_ctx_floor` - enforces minimum_supported_ctx=4096 (Section 15.24)

## Implementation

- [ ] Create `src/autocode/agent/provider_registry.py`
- [ ] Implement `ProviderRegistry` class with lazy loading
- [ ] Enforce max 2 models loaded constraint (L3 + L4)
- [ ] Implement `get_provider(spec: ModelSpec)` method
- [ ] Implement `cleanup()` method to release all models
- [ ] Enforce adaptive context policy: minimum_supported_ctx=4096, target_ctx=8192 (Section 15.24)
- [ ] Add telemetry warning on context downgrade

## Acceptance Criteria

- [ ] ProviderRegistry manages L3 + L4 providers with lazy loading
- [ ] Max 2 models loaded constraint enforced
- [ ] Context policy enforced (4096 min / 8192 target)
- [ ] Cleanup releases all loaded models
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Eval

- [ ] Load/unload benchmark (measure swap time)

## Artifacts

- New file: `src/autocode/agent/provider_registry.py`
- Test file: `tests/unit/test_provider_registry.py`
- QA artifact: `docs/qa/test-results/sprint-5a-2-provider-registry.md`
