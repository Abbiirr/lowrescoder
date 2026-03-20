"""Tests for off-by-one bug in sliding window."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import sliding_window, moving_average, find_max_window


def test_sliding_window_basic():
    """Basic sliding window should return all windows."""
    result = sliding_window([1, 2, 3, 4, 5], 3)
    assert result == [[1, 2, 3], [2, 3, 4], [3, 4, 5]]


def test_sliding_window_count():
    """Number of windows should be len(seq) - window_size + 1."""
    result = sliding_window([1, 2, 3, 4, 5], 3)
    assert len(result) == 3, f"Expected 3 windows, got {len(result)}"


def test_sliding_window_size_equals_sequence():
    """Window size == sequence length should return one window."""
    result = sliding_window([1, 2, 3], 3)
    assert result == [[1, 2, 3]]


def test_sliding_window_size_one():
    """Window size 1 should return each element as its own window."""
    result = sliding_window([10, 20, 30], 1)
    assert result == [[10], [20], [30]]


def test_sliding_window_too_large():
    """Window larger than sequence returns empty list."""
    result = sliding_window([1, 2], 5)
    assert result == []


def test_moving_average():
    """Moving average should include the last window."""
    result = moving_average([1, 2, 3, 4, 5], 3)
    # Windows: [1,2,3]=2.0, [2,3,4]=3.0, [3,4,5]=4.0
    assert len(result) == 3
    assert result[-1] == 4.0


def test_find_max_window_at_end():
    """Max window at the end of sequence should be found."""
    result = find_max_window([1, 1, 1, 1, 10], 2)
    # Windows: [1,1]=2, [1,1]=2, [1,1]=2, [1,10]=11
    assert result is not None
    assert result == (3, 11)


def test_sliding_window_negative_size():
    """Negative window size should raise ValueError."""
    try:
        sliding_window([1, 2, 3], -1)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
