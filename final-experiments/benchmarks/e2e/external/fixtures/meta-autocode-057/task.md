# TASK-057: Fix Duplicate Output Port Detection (langflow-ai/langflow pattern)

## Source
Inspired by langflow-ai/langflow component port validation. Duplicate output
port names cause silent failures when wiring flows. The bug checks for missing
names but ignores duplicates.

## Goal
Fix `src/port_validator.py` so `validate_output_ports()` also reports an error
when two ports share the same name.

## The bug
```python
# BUG: no duplicate check
for port in ports:
    if not port.get('name'):
        errors.append('Port missing name')

# Fix: track seen names
seen = set()
for port in ports:
    if not port.get('name'):
        errors.append('Port missing name')
    elif port['name'] in seen:
        errors.append(f"Duplicate port name: {port['name']}")
    else:
        seen.add(port['name'])
```

## Failing tests (3/7 fail initially)
```
test_duplicate_port_names  ← FAILS (two 'result' ports → no error reported)
test_duplicate_among_valid ← FAILS (['a','b','a'] → no error reported)
test_all_same_name         ← FAILS (three 'x' ports → 0 errors, expected >= 2)
```
