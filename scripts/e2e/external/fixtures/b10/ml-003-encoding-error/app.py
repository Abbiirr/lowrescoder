"""CSV reader with encoding support."""


def read_csv(filepath):
    """Read a CSV file and return rows as list of lists.

    Bug: opens file without specifying encoding='utf-8', which causes
    failures on systems where the default encoding is not UTF-8
    (e.g., Windows with cp1252, or POSIX with C locale).
    """
    # Bug: missing encoding='utf-8'
    with open(filepath, "r") as f:
        lines = f.read().strip().split("\n")

    rows = []
    for line in lines:
        rows.append(line.split(","))
    return rows


def get_column(filepath, col_index):
    """Extract a single column from a CSV file."""
    rows = read_csv(filepath)
    if not rows:
        return []
    return [row[col_index] for row in rows if col_index < len(row)]


def search_csv(filepath, column_index, search_term):
    """Search for rows where the given column contains the search term."""
    rows = read_csv(filepath)
    if not rows:
        return []
    header = rows[0]
    matches = []
    for row in rows[1:]:
        if column_index < len(row) and search_term in row[column_index]:
            matches.append(row)
    return matches
