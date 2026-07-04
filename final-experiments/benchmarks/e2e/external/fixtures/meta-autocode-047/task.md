# TASK-047: Fix SSL Certificate Expiry Warning Threshold (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma SSL certificate monitoring. uptime-kuma warns
when a cert has ≤30 days remaining. The bug uses ≤7 days as the threshold,
silently passing certs that should trigger a warning.

## Goal
Fix `src/cert_checker.py` so `cert_status()` returns 'expiring_soon' when
`days_until_expiry <= 30`.

## The bug
```python
# BUG: warns only within 7 days — misses 8-30 day window
if days_until_expiry <= 7:
    return 'expiring_soon'

# Fix: correct threshold
if days_until_expiry <= 30:
    return 'expiring_soon'
```

## Failing tests (3/7 fail initially)
```
test_expiring_soon_15_days ← FAILS (15 days returns 'valid')
test_expiring_soon_20_days ← FAILS (20 days returns 'valid')
test_expiring_soon_30_days ← FAILS (30 days returns 'valid')
```
