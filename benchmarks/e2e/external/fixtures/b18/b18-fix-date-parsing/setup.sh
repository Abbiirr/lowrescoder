#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/dateparser.py << 'PYEOF'
"""Date parser module — parses ISO 8601 date strings."""
from datetime import datetime, timezone, timedelta


def parse_date(date_string):
    """Parse an ISO 8601 date string into a datetime object.

    Supports:
    - Date only: 2024-01-15
    - Date and time: 2024-01-15T10:30:00
    - UTC indicator: 2024-01-15T10:30:00Z
    - Timezone offset: 2024-01-15T10:30:00+05:30 (BUG: crashes here)

    Args:
        date_string: An ISO 8601 formatted date string.

    Returns:
        A datetime object.

    Raises:
        ValueError: If the date string cannot be parsed.
    """
    date_string = date_string.strip()

    # Handle UTC 'Z' suffix
    if date_string.endswith('Z'):
        date_string = date_string[:-1]
        dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)

    # BUG: Does not handle +HH:MM or -HH:MM offsets — just tries to parse
    # directly, which fails because strptime with %Y-%m-%dT%H:%M:%S
    # doesn't consume the offset.
    if 'T' in date_string:
        dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        return dt
    else:
        dt = datetime.strptime(date_string, "%Y-%m-%d")
        return dt


def format_date(dt, include_tz=True):
    """Format a datetime object to ISO 8601 string.

    Args:
        dt: A datetime object.
        include_tz: If True, include timezone info in output.

    Returns:
        An ISO 8601 formatted string.
    """
    if include_tz and dt.tzinfo is not None:
        return dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    return dt.strftime("%Y-%m-%dT%H:%M:%S")
PYEOF

cat > project/test_dateparser.py << 'PYEOF'
"""Tests for the date parser module."""
import unittest
from datetime import datetime, timezone, timedelta
from dateparser import parse_date, format_date


class TestParseDateNaive(unittest.TestCase):
    """Tests for naive date parsing — should already work."""

    def test_date_only(self):
        dt = parse_date("2024-01-15")
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)

    def test_date_and_time(self):
        dt = parse_date("2024-01-15T10:30:00")
        self.assertEqual(dt.hour, 10)
        self.assertEqual(dt.minute, 30)

    def test_utc_z(self):
        dt = parse_date("2024-01-15T10:30:00Z")
        self.assertEqual(dt.tzinfo, timezone.utc)


class TestParseDateTimezone(unittest.TestCase):
    """Tests for timezone offset parsing — these currently crash."""

    def test_positive_offset(self):
        dt = parse_date("2024-01-15T10:30:00+05:30")
        self.assertEqual(dt.hour, 10)
        self.assertEqual(dt.minute, 30)
        expected_tz = timezone(timedelta(hours=5, minutes=30))
        self.assertEqual(dt.utcoffset(), expected_tz.utcoffset(None))

    def test_negative_offset(self):
        dt = parse_date("2024-01-15T10:30:00-08:00")
        expected_tz = timezone(timedelta(hours=-8))
        self.assertEqual(dt.utcoffset(), expected_tz.utcoffset(None))

    def test_zero_offset(self):
        dt = parse_date("2024-01-15T10:30:00+00:00")
        self.assertEqual(dt.utcoffset(), timedelta(0))

    def test_negative_offset_half_hour(self):
        dt = parse_date("2024-01-15T10:30:00-05:30")
        expected_tz = timezone(timedelta(hours=-5, minutes=-30))
        self.assertEqual(dt.utcoffset(), expected_tz.utcoffset(None))

    def test_positive_offset_whole_hour(self):
        dt = parse_date("2024-01-15T10:30:00+09:00")
        expected_tz = timezone(timedelta(hours=9))
        self.assertEqual(dt.utcoffset(), expected_tz.utcoffset(None))


class TestFormatDate(unittest.TestCase):
    """Tests for date formatting."""

    def test_format_naive(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        self.assertEqual(format_date(dt, include_tz=False), "2024-01-15T10:30:00")

    def test_format_with_tz(self):
        tz = timezone(timedelta(hours=5, minutes=30))
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=tz)
        result = format_date(dt, include_tz=True)
        self.assertIn("+0530", result)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. dateparser.py crashes on timezone offsets like +05:30."
