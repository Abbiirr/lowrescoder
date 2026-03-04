"""Tests for floor division bug in statistical computations."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import mean, variance, standard_deviation, z_scores, percentile


def test_mean_even_division():
    """Mean of [2, 4] = 3.0 -- works even with floor division."""
    assert mean([2, 4]) == 3.0


def test_mean_fractional_result():
    """Mean of [1, 2] should be 1.5, not 1.

    This is the core bug: // truncates 3 // 2 = 1, but / gives 3 / 2 = 1.5.
    """
    result = mean([1, 2])
    assert result == 1.5, (
        f"mean([1, 2]) should be 1.5, got {result} — "
        "using floor division (//) instead of true division (/)"
    )


def test_mean_of_single_value():
    """Mean of a single value should be that value as float."""
    result = mean([7])
    assert result == 7


def test_mean_with_odd_sum():
    """Mean of [1, 2, 4] = 7/3 = 2.333..."""
    result = mean([1, 2, 4])
    assert abs(result - 7 / 3) < 1e-9, (
        f"mean([1, 2, 4]) should be ~2.333, got {result}"
    )


def test_variance_depends_on_mean():
    """Variance computation depends on correct mean.

    If mean is truncated, variance will be wrong too.
    """
    # values = [1, 2, 3], mean should be 2.0
    # variance = ((1-2)^2 + (2-2)^2 + (3-2)^2) / 3 = (1+0+1)/3 = 0.666...
    result = variance([1, 2, 3])
    assert abs(result - 2 / 3) < 1e-9, (
        f"variance([1, 2, 3]) should be ~0.667, got {result}"
    )


def test_standard_deviation():
    """Standard deviation of [1, 2, 3]."""
    result = standard_deviation([1, 2, 3])
    expected = (2 / 3) ** 0.5  # ~0.8165
    assert abs(result - expected) < 1e-9


def test_z_scores():
    """Z-scores should be symmetric for symmetric data."""
    scores = z_scores([1, 2, 3])
    # Mean = 2, std = sqrt(2/3)
    # z(1) = -sqrt(3/2), z(2) = 0, z(3) = sqrt(3/2)
    assert abs(scores[1]) < 1e-9, "Middle value z-score should be ~0"
    assert abs(scores[0] + scores[2]) < 1e-9, "Z-scores should be symmetric"


def test_mean_empty_raises():
    """Mean of empty list should raise ValueError."""
    try:
        mean([])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_percentile_median():
    """50th percentile should match the median."""
    result = percentile([1, 2, 3, 4, 5], 50)
    assert result == 3.0
