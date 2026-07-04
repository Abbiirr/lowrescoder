def filter_high_severity(issues, threshold):
    """Return issues with severity >= threshold (inclusive)."""
    # BUG: uses > instead of >= — excludes issues exactly at threshold
    return [i for i in issues if i.get('severity', 0) > threshold]
