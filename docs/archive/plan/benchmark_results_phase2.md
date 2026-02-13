# Phase 2 Benchmark Results

**Date**: 2026-02-05
**Test suite**: 272 tests total (32 benchmarks)
**Full suite time**: 39.09s
**Benchmark time**: 18.05s
**Lint**: ruff clean, mypy clean

---

## Code Search Benchmarks (13 tests — all PASS)

### Accuracy (7 tests)
| Test | Target | Result |
|------|--------|--------|
| Find class definition (`class User`) | user.py | PASS |
| Find function definition (`def login`) | auth.py | PASS |
| Find bug comment (`BUG:`) | auth.py | PASS |
| Find TODO comment (`TODO:`) | notification.py | PASS |
| Find import usage (`from.*auth.*import`) | test_auth.py | PASS |
| Find method call (`hash_password`) | auth.py + test_auth.py | PASS |
| Find with glob filter (`**/*.py`) | Restricts correctly | PASS |

### Precision (3 tests)
| Test | Result |
|------|--------|
| `class Post` does not return `class User` | PASS |
| `def deactivate` returns exactly 1 match | PASS |
| Nonexistent pattern returns "No matches" | PASS |

### Performance (3 tests)
| Test | Files | Budget | Result |
|------|-------|--------|--------|
| Search 100 files | 100 | <5s | PASS |
| Search 250 files | 250 | <5s | PASS |
| Fallback chain (rg > grep > python) | 50 | N/A | PASS |

---

## Edit Efficiency Benchmarks (9 tests — all PASS)

### Accuracy (4 tests)
| Bug | File | Identified | Result |
|-----|------|-----------|--------|
| Off-by-one | pagination.py | `page * per_page` | PASS |
| Missing null check | user.py | `user['name']` | PASS |
| Wrong operator | calc.py | `1 + discount_pct` | PASS |
| Missing return | validator.py | No `return True` at end | PASS |

### Edit Size (3 tests)
| Fix | Lines Changed | Result |
|-----|---------------|--------|
| Off-by-one → `(page - 1) * per_page` | 1 | PASS |
| Missing return → add `return True` | +1 line | PASS |
| Wrong operator → `1 - discount_pct` | 1 | PASS |

### Diff Precision (2 tests)
| Test | Result |
|------|--------|
| Fix preserves surrounding code (sig, return) | PASS |
| write_file → read_file roundtrip preserves content | PASS |

---

## Tool Efficiency Benchmarks (10 tests — all PASS)

### Call Efficiency (3 tests)
| Scenario | LLM Calls | Result |
|----------|-----------|--------|
| Read file | 2 (tool call + response) | PASS |
| Search + read | 3 (search + read + response) | PASS |
| Runaway tool calls | Stops at MAX_ITERATIONS (5) in <30s | PASS |

### Tool Selection (4 tests)
| Test | Result |
|------|--------|
| Registry has exactly 6 tools | PASS |
| Read tools (read_file, list_files, search_text, ask_user) don't require approval | PASS |
| Write tools (write_file, run_command) require approval | PASS |
| All tool schemas follow OpenAI function-calling format | PASS |

### Approval Gating (3 tests)
| Mode | Write Behavior | Result |
|------|---------------|--------|
| read-only | Blocks all writes | PASS |
| suggest | Denied without callback | PASS |
| auto | Allows writes | PASS |

---

## Summary

| Category | Tests | Passed | Failed |
|----------|-------|--------|--------|
| Code Search | 13 | 13 | 0 |
| Edit Efficiency | 9 | 9 | 0 |
| Tool Efficiency | 10 | 10 | 0 |
| **Total Benchmarks** | **32** | **32** | **0** |
| **Full Suite** | **272** | **272** | **0** |
