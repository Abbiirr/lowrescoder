def calculate_avg_response_time(response_times):
    """Calculate average response time, excluding failed (0 ms) entries."""
    if not response_times:
        return 0
    # BUG: includes zero (failed) entries in average, dragging the result down
    return sum(response_times) / len(response_times)
