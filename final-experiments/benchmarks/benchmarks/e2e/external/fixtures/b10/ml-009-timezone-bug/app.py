"""Event scheduling with timezone conversions.

Bug: uses naive datetime.replace(tzinfo=...) instead of proper localize,
which does not account for UTC offset and effectively just labels the
datetime without converting it.
"""
from datetime import datetime, timezone, timedelta


# Simple timezone definitions (no pytz needed)
UTC = timezone.utc
EST = timezone(timedelta(hours=-5), name="EST")
PST = timezone(timedelta(hours=-8), name="PST")
JST = timezone(timedelta(hours=9), name="JST")
CET = timezone(timedelta(hours=1), name="CET")

TIMEZONE_MAP = {
    "UTC": UTC,
    "EST": EST,
    "PST": PST,
    "JST": JST,
    "CET": CET,
}


def convert_time(dt, target_tz_name):
    """Convert a timezone-aware datetime to another timezone.

    Bug: uses replace() instead of astimezone(), which just swaps the
    tzinfo label without actually converting the time.
    """
    target_tz = TIMEZONE_MAP.get(target_tz_name)
    if target_tz is None:
        raise ValueError(f"Unknown timezone: {target_tz_name}")

    # Bug: replace() just changes the label, doesn't convert
    return dt.replace(tzinfo=target_tz)


def schedule_event(event_time_utc, attendee_tz_name):
    """Given an event time in UTC, return the local time for an attendee.

    Returns a dict with 'utc' and 'local' datetime strings.
    """
    local_time = convert_time(event_time_utc, attendee_tz_name)
    return {
        "utc": event_time_utc.strftime("%Y-%m-%d %H:%M %Z"),
        "local": local_time.strftime("%Y-%m-%d %H:%M %Z"),
    }


def is_business_hours(dt, tz_name):
    """Check if a datetime falls within business hours (9-17) in the given tz."""
    local = convert_time(dt, tz_name)
    return 9 <= local.hour < 17
