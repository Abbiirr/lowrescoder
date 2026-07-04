# TASK-156: Fix Percentage Calculation Integer Division (langflow pattern)

## Source
Inspired by langflow-ai/langflow metrics computation. Integer division (`//`)
truncates fractional percentages — 1/3 reports 33% instead of 33.33%.

## Goal
Fix `src/metrics_calculator.py` so `calculate_percentage()` returns a float.

## The bug
```python
# BUG: // truncates fraction
return (part * 100) // total

# Fix: float division
return (part * 100) / total
```

## Failing tests (3/7 fail initially)
```
test_one_third   ← FAILS (33 instead of ~33.33)
test_two_thirds  ← FAILS (66 instead of ~66.67)
test_one_sixth   ← FAILS (16 instead of ~16.67)
```
