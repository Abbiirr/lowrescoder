"""Matrix operations with dtype handling."""


def matrix_multiply(a, b):
    """Multiply two 2D lists as matrices.

    Both matrices should be treated as float for consistent results.
    Returns a 2D list of floats.
    """
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])

    if cols_a != rows_b:
        raise ValueError(
            f"Incompatible shapes: ({rows_a},{cols_a}) x ({rows_b},{cols_b})"
        )

    result = []
    for i in range(rows_a):
        row = []
        for j in range(cols_b):
            total = 0  # Bug: integer zero, causes integer division truncation
            for k in range(cols_a):
                total += a[i][k] * b[k][j]
            row.append(total)
        result.append(row)

    return result


def normalize_matrix(matrix):
    """Normalize matrix values to [0, 1] range by dividing by the max value."""
    max_val = max(max(row) for row in matrix)
    if max_val == 0:
        return matrix

    result = []
    for row in matrix:
        result.append([val / max_val for val in row])
    return result


def weighted_sum(values, weights):
    """Compute weighted sum of values.

    Bug: uses integer division when values and weights are ints.
    """
    total = 0  # Bug: should be 0.0 to ensure float arithmetic
    count = 0  # Bug: should be 0.0
    for v, w in zip(values, weights):
        total += v * w
        count += w
    return total / count  # Integer division when all inputs are ints
