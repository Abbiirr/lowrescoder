def compute_elapsed_ms(start_ts, end_ts):
    """Return elapsed time in milliseconds between two Unix timestamps."""
    # BUG: subtracts in wrong order
    elapsed_s = start_ts - end_ts
    return elapsed_s * 1000
