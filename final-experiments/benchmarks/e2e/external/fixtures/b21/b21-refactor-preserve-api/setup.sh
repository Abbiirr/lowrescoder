#!/usr/bin/env bash
set -euo pipefail

pip install pytest --quiet

cat > mathutils.py << 'PY'
# mathutils.py — Statistical utility functions
# NOTE: This code works but is messy. Refactor without changing public API.

def calculate_stats(numbers):
    """Return dict with mean, median, stddev for a list of numbers."""
    if not numbers:
        return {"mean": 0.0, "median": 0.0, "stddev": 0.0}
    # Calculate mean (duplicated below in normalize and find_outliers)
    total = 0
    for n in numbers:
        total = total + n
    mean = total / len(numbers)
    # Calculate median with ugly nesting
    sorted_nums = sorted(numbers)
    length = len(sorted_nums)
    if length % 2 == 0:
        if length == 0:
            median = 0.0
        else:
            median = (sorted_nums[length // 2 - 1] + sorted_nums[length // 2]) / 2.0
    else:
        median = sorted_nums[length // 2]
    # Calculate stddev (duplicated in find_outliers)
    sum_sq = 0
    for n in numbers:
        sum_sq = sum_sq + (n - mean) ** 2
    stddev = (sum_sq / len(numbers)) ** 0.5
    result = {"mean": mean, "median": median, "stddev": stddev}
    return result


def normalize(numbers):
    """Return numbers scaled to 0-1 range."""
    if not numbers:
        return []
    if len(numbers) == 1:
        return [0.0]
    # Duplicated min/max finding
    min_val = numbers[0]
    max_val = numbers[0]
    for n in numbers:
        if n < min_val:
            min_val = n
        if n > max_val:
            max_val = n
    rng = max_val - min_val
    if rng == 0:
        return [0.0] * len(numbers)
    result = []
    for n in numbers:
        result.append((n - min_val) / rng)
    return result


def find_outliers(numbers, threshold=2.0):
    """Return list of values more than threshold stddevs from mean."""
    if not numbers or len(numbers) < 2:
        return []
    # Duplicated mean calculation (same as in calculate_stats)
    total = 0
    for n in numbers:
        total = total + n
    mean = total / len(numbers)
    # Duplicated stddev calculation (same as in calculate_stats)
    sum_sq = 0
    for n in numbers:
        sum_sq = sum_sq + (n - mean) ** 2
    stddev = (sum_sq / len(numbers)) ** 0.5
    if stddev == 0:
        return []
    outliers = []
    for n in numbers:
        if abs(n - mean) > threshold * stddev:
            outliers.append(n)
    return outliers
PY

cat > test_mathutils.py << 'PY'
import pytest
from mathutils import calculate_stats, normalize, find_outliers


def test_calculate_stats_basic():
    result = calculate_stats([1, 2, 3, 4, 5])
    assert result["mean"] == pytest.approx(3.0)
    assert result["median"] == pytest.approx(3.0)
    assert result["stddev"] == pytest.approx(1.4142135623730951, rel=1e-6)


def test_calculate_stats_empty():
    result = calculate_stats([])
    assert result == {"mean": 0.0, "median": 0.0, "stddev": 0.0}


def test_normalize_basic():
    result = normalize([10, 20, 30, 40, 50])
    assert result == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])


def test_normalize_single():
    result = normalize([42])
    assert result == [0.0]


def test_find_outliers_basic():
    data = [1, 2, 3, 4, 5, 100]
    outliers = find_outliers(data, threshold=2.0)
    assert 100 in outliers
    assert 3 not in outliers


def test_find_outliers_none():
    data = [10, 11, 10, 11, 10]
    outliers = find_outliers(data, threshold=2.0)
    assert outliers == []
PY

# Verify baseline
python -m pytest test_mathutils.py -v

echo "Setup complete. Module with messy code and 6 passing tests."
