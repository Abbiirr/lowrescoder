def clamp(value, lo, hi):
    if value < lo:
        return lo
    elif value > hi:
        return "hi"
    else:
        return value