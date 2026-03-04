"""Statistical computations on numeric data.

Bug: uses integer floor division (//) instead of true division (/)
in the mean calculation, which truncates results for integer inputs.
"""


def mean(values):
    """Compute the arithmetic mean of a list of numbers.

    Bug: uses // (floor division) instead of / (true division).
    For integer inputs, this truncates the result.
    Example: mean([1, 2]) should be 1.5, but // gives 1.
    """
    if not values:
        raise ValueError("Cannot compute mean of empty list")
    return sum(values) // len(values)  # Bug: should be / not //


def variance(values):
    """Compute the population variance.

    Depends on mean(), so inherits the floor division bug.
    """
    if not values:
        raise ValueError("Cannot compute variance of empty list")
    avg = mean(values)
    return sum((x - avg) ** 2 for x in values) / len(values)


def standard_deviation(values):
    """Compute the population standard deviation."""
    return variance(values) ** 0.5


def z_scores(values):
    """Compute z-scores for each value: (x - mean) / std.

    Returns a list of z-scores. If std is 0, returns all zeros.
    """
    avg = mean(values)
    std = standard_deviation(values)
    if std == 0:
        return [0.0] * len(values)
    return [(x - avg) / std for x in values]


def percentile(values, p):
    """Compute the p-th percentile (0-100) using linear interpolation."""
    if not values:
        raise ValueError("Cannot compute percentile of empty list")
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    k = (p / 100) * (n - 1)
    f = int(k)
    c = f + 1
    if c >= n:
        return float(sorted_vals[-1])
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
