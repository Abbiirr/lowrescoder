# TASK-098: Fix File Size Formatter Binary Units (sharkdp/bat pattern)

## Source
Inspired by sharkdp/bat file size display. Binary file sizes use 1024 as the
divisor (KiB/MiB/GiB), not 1000 (KB/MB/GB decimal).

## Goal
Fix `src/file_sizer.py` so `format_file_size()` uses 1024 as the boundary
and divisor.

## The bug
```python
# BUG: 1000 (decimal)
if size_bytes < 1000:
    return f"{size_bytes} B"
elif size_bytes < 1000 ** 2:
    return f"{size_bytes / 1000:.1f} KB"

# Fix: 1024 (binary)
if size_bytes < 1024:
    return f"{size_bytes} B"
elif size_bytes < 1024 ** 2:
    return f"{size_bytes / 1024:.1f} KB"
```

## Failing tests (3/7 fail initially)
```
test_1000_bytes_is_b  ← FAILS ('1.0 KB' != '1000 B')
test_1023_bytes_is_b  ← FAILS ('1.0 KB' != '1023 B')
test_one_mb_boundary  ← FAILS ('512.0 KB' != '500.0 KB')
```
