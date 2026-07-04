"""Data pipeline with record processing and aggregation."""


def clean_records(records):
    """Clean a list of record dicts by removing entries with null/None values.

    Each record is a dict like {"name": "Alice", "score": 95}.
    Records with ANY None value in a field should be skipped.

    Bug: only checks if the value is falsy (which also skips 0, '', False).
    Should specifically check for None.
    """
    cleaned = []
    for record in records:
        skip = False
        for key, value in record.items():
            if not value:  # Bug: this skips 0, empty string, False too
                skip = True
                break
        if not skip:
            cleaned.append(record)
    return cleaned


def average_field(records, field):
    """Compute the average of a numeric field across records.

    Skips records where the field is None, but includes 0 values.
    """
    cleaned = clean_records(records)
    values = [r[field] for r in cleaned if field in r]
    if not values:
        return 0.0
    return sum(values) / len(values)


def count_by_field(records, field):
    """Count records grouped by a field value. Skips None values."""
    cleaned = clean_records(records)
    counts = {}
    for r in cleaned:
        if field in r and r[field] is not None:
            key = r[field]
            counts[key] = counts.get(key, 0) + 1
    return counts
