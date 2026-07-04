# TASK-018: Fix Status Page Monitor Group Sort (louislam/uptime-kuma pattern)

## Source
Inspired by louislam/uptime-kuma status page display.
Monitor groups are sorted alphabetically for the public status page, but the
sort is case-sensitive — "Backend" sorts before "api" because 'B' (66) < 'a' (97).

## Goal
Fix `src/status_page.py` so `sort_monitor_groups()` sorts case-insensitively.

## The bug
```python
# BUG: case-sensitive — uppercase names always sort before lowercase
return sorted(groups, key=lambda g: g["name"])

# Fix: case-insensitive alphabetical
return sorted(groups, key=lambda g: g["name"].lower())
```

## Failing tests (3/7 fail initially)
```
test_mixed_case_basic      ← FAILS ("Backend" before "api")
test_mixed_case_boundary   ← FAILS ("Zabbix" before "monitor")
test_mixed_case_multigroup ← FAILS (all uppercase names before lowercase)
```
