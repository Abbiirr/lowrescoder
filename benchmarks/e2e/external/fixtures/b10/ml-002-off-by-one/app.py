"""Sliding window operations on sequences."""


def sliding_window(sequence, window_size):
    """Return all contiguous sub-sequences of the given window size.

    Example:
        sliding_window([1, 2, 3, 4, 5], 3)
        => [[1, 2, 3], [2, 3, 4], [3, 4, 5]]

    Bug: off-by-one in range upper bound causes the last window to be dropped.
    """
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    if window_size > len(sequence):
        return []

    result = []
    # Bug: should be len(sequence) - window_size + 1
    for i in range(len(sequence) - window_size):
        result.append(sequence[i:i + window_size])
    return result


def moving_average(values, window_size):
    """Compute moving average over a list of numbers.

    Returns a list of averages, one per window position.
    """
    windows = sliding_window(values, window_size)
    return [sum(w) / len(w) for w in windows]


def find_max_window(values, window_size):
    """Find the window with the maximum sum.

    Returns (start_index, window_sum).
    """
    windows = sliding_window(values, window_size)
    if not windows:
        return None

    best_idx = 0
    best_sum = sum(windows[0])
    for i, w in enumerate(windows[1:], 1):
        s = sum(w)
        if s > best_sum:
            best_sum = s
            best_idx = i

    return (best_idx, best_sum)
