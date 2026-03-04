"""Tests for dtype mismatch bug in matrix operations."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import matrix_multiply, normalize_matrix, weighted_sum


def test_matrix_multiply_float_result():
    """Matrix multiplication with ints should still produce float-compatible results."""
    a = [[1, 2], [3, 4]]
    b = [[5, 6], [7, 8]]
    result = matrix_multiply(a, b)
    assert result == [[19, 22], [43, 50]]


def test_matrix_multiply_mixed_types():
    """Mixed int/float inputs should produce float results."""
    a = [[1, 2], [3, 4]]
    b = [[0.5, 0.0], [0.0, 0.5]]
    result = matrix_multiply(a, b)
    assert result[0][0] == 0.5
    assert result[0][1] == 1.0
    assert result[1][0] == 1.5
    assert result[1][1] == 2.0


def test_normalize_matrix():
    """Normalize should produce float values in [0, 1]."""
    matrix = [[2, 4], [6, 8]]
    result = normalize_matrix(matrix)
    assert result[0][0] == 0.25
    assert result[1][1] == 1.0


def test_weighted_sum_with_ints():
    """Weighted sum of integers should return accurate float result.

    values=[1, 2, 3], weights=[2, 3, 5]
    weighted = 1*2 + 2*3 + 3*5 = 2 + 6 + 15 = 23
    total_weight = 2 + 3 + 5 = 10
    result = 23 / 10 = 2.3

    Bug: with integer division (Python 2 style accumulator issue),
    this could truncate. In Python 3, `/` does float division, but
    the real bug is when `total` is built with integer ops and
    intermediate values lose precision in certain edge cases.
    """
    result = weighted_sum([1, 2, 3], [2, 3, 5])
    assert result == 2.3


def test_weighted_sum_precision():
    """Weighted sum should maintain float precision.

    values=[1, 1, 1], weights=[3, 3, 3]
    weighted = 3 + 3 + 3 = 9
    total_weight = 9
    result = 9/9 = 1.0
    """
    result = weighted_sum([1, 1, 1], [3, 3, 3])
    assert isinstance(result, float), "Result should be float, not int"


def test_weighted_sum_returns_float_type():
    """Even when result is a whole number, return type should be float."""
    result = weighted_sum([4, 4], [1, 1])
    assert isinstance(result, float), (
        "weighted_sum should return float, got %s" % type(result).__name__
    )
