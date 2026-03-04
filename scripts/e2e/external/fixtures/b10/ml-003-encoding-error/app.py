"""CSV reader with encoding support.

Bug: opens file without specifying encoding='utf-8', and also opens in
text mode which can fail on binary-like UTF-8 sequences depending on
the system's default encoding. Additionally, does not handle BOM
(byte-order mark) that some tools add to UTF-8 files.
"""


def read_csv(filepath):
    """Read a CSV file and return rows as list of lists.

    Bug: opens file without encoding='utf-8' and without
    errors='replace' or handling for BOM.
    On systems with non-UTF-8 default encoding, this will raise
    UnicodeDecodeError or produce garbled output for non-ASCII text.
    """
    # Bug: missing encoding='utf-8'
    with open(filepath, "r") as f:
        lines = f.read().strip().split("\n")

    rows = []
    for line in lines:
        rows.append(line.split(","))
    return rows


def read_csv_with_header(filepath):
    """Read CSV and return (header, rows) tuple."""
    all_rows = read_csv(filepath)
    if not all_rows:
        return [], []
    return all_rows[0], all_rows[1:]


def write_csv(filepath, rows):
    """Write rows to a CSV file.

    Bug: missing encoding='utf-8', same issue as read_csv.
    """
    # Bug: missing encoding='utf-8'
    with open(filepath, "w") as f:
        for row in rows:
            f.write(",".join(str(cell) for cell in row) + "\n")
