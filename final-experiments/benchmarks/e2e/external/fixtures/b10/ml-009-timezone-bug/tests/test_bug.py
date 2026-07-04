"""Tests for timezone conversion bug."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta
from app import convert_time, schedule_event, is_business_hours, UTC, EST, PST, JST


def test_utc_to_est():
    """Converting 15:00 UTC to EST should give 10:00 EST.

    Bug: replace() just relabels to EST without adjusting hours,
    so it returns 15:00 EST instead of 10:00 EST.
    """
    utc_time = datetime(2026, 3, 4, 15, 0, tzinfo=UTC)
    est_time = convert_time(utc_time, "EST")
    assert est_time.hour == 10, (
        f"15:00 UTC should be 10:00 EST, got {est_time.hour}:00 — "
        "timezone conversion is labeling, not converting"
    )


def test_utc_to_jst():
    """Converting 15:00 UTC to JST should give 00:00 next day (JST = UTC+9)."""
    utc_time = datetime(2026, 3, 4, 15, 0, tzinfo=UTC)
    jst_time = convert_time(utc_time, "JST")
    # 15:00 + 9 = 24:00 = 00:00 next day
    assert jst_time.hour == 0, (
        f"15:00 UTC should be 00:00 JST, got {jst_time.hour}:00"
    )
    assert jst_time.day == 5, (
        f"15:00 UTC Mar 4 should be Mar 5 in JST, got day={jst_time.day}"
    )


def test_utc_to_pst():
    """Converting 20:00 UTC to PST should give 12:00 PST."""
    utc_time = datetime(2026, 3, 4, 20, 0, tzinfo=UTC)
    pst_time = convert_time(utc_time, "PST")
    assert pst_time.hour == 12, (
        f"20:00 UTC should be 12:00 PST, got {pst_time.hour}:00"
    )


def test_utc_to_utc():
    """Converting UTC to UTC should be identity."""
    utc_time = datetime(2026, 3, 4, 12, 30, tzinfo=UTC)
    result = convert_time(utc_time, "UTC")
    assert result.hour == 12
    assert result.minute == 30


def test_schedule_event_local_time():
    """Scheduled event should show correct local time."""
    event_utc = datetime(2026, 6, 15, 18, 0, tzinfo=UTC)
    result = schedule_event(event_utc, "EST")
    assert "13:00" in result["local"], (
        f"18:00 UTC event should show 13:00 EST, got {result['local']}"
    )


def test_is_business_hours_true():
    """12:00 UTC should be business hours in EST (07:00 EST)... no.
    12:00 UTC = 07:00 EST, which is before 9. Let's use 14:00 UTC = 09:00 EST.
    """
    utc_time = datetime(2026, 3, 4, 14, 0, tzinfo=UTC)
    assert is_business_hours(utc_time, "EST") is True, (
        "14:00 UTC = 09:00 EST should be business hours"
    )


def test_is_business_hours_false():
    """05:00 UTC should NOT be business hours in EST (00:00 EST)."""
    utc_time = datetime(2026, 3, 4, 5, 0, tzinfo=UTC)
    assert is_business_hours(utc_time, "EST") is False, (
        "05:00 UTC = 00:00 EST should not be business hours"
    )


def test_unknown_timezone():
    """Unknown timezone should raise ValueError."""
    utc_time = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
    try:
        convert_time(utc_time, "FAKE")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
