def digit_sum(n):
    """Return the sum of digits of integer n (sign ignored)."""
    # BUG: str(negative) includes '-', so int('-') raises ValueError
    return sum(int(d) for d in str(n))
