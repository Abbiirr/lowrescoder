"""Tests for incident_tracker — inspired by louislam/uptime-kuma heartbeat logic.

uptime-kuma detects service incidents from a stream of heartbeats. A common
harness-bench v2 pattern: the "still down at end of stream" case is unhandled,
silently dropping the ongoing incident.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def hb(ts, status):
    return {"ts": ts, "status": status}


def test_all_up_no_incidents():
    from incident_tracker import detect_incidents
    beats = [hb(1, "up"), hb(2, "up"), hb(3, "up")]
    assert detect_incidents(beats) == []


def test_resolved_incident():
    from incident_tracker import detect_incidents
    beats = [hb(1, "up"), hb(2, "down"), hb(3, "down"), hb(4, "up")]
    result = detect_incidents(beats)
    assert len(result) == 1
    assert result[0] == {"start": 2, "end": 4}


def test_ongoing_incident_at_end():
    from incident_tracker import detect_incidents
    # Stream ends while still down — must return open incident with end=None
    beats = [hb(1, "up"), hb(2, "down"), hb(3, "down")]
    result = detect_incidents(beats)
    assert len(result) == 1, f"expected 1 incident, got {len(result)}: {result}"
    assert result[0]["start"] == 2
    assert result[0]["end"] is None


def test_single_down_at_end():
    from incident_tracker import detect_incidents
    beats = [hb(10, "down")]
    result = detect_incidents(beats)
    assert len(result) == 1
    assert result[0] == {"start": 10, "end": None}


def test_two_incidents_second_ongoing():
    from incident_tracker import detect_incidents
    beats = [
        hb(1, "up"), hb(2, "down"), hb(3, "up"),   # first incident resolved
        hb(4, "up"), hb(5, "down"), hb(6, "down"),  # second ongoing
    ]
    result = detect_incidents(beats)
    assert len(result) == 2
    assert result[0] == {"start": 2, "end": 3}
    assert result[1] == {"start": 5, "end": None}


def test_empty_stream():
    from incident_tracker import detect_incidents
    assert detect_incidents([]) == []


def test_two_resolved_incidents():
    from incident_tracker import detect_incidents
    beats = [hb(1,"down"), hb(2,"up"), hb(3,"down"), hb(4,"up")]
    result = detect_incidents(beats)
    assert len(result) == 2
    assert result[0] == {"start": 1, "end": 2}
    assert result[1] == {"start": 3, "end": 4}
