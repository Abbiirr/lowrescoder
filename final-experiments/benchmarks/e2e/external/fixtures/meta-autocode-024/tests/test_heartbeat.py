"""Tests for heartbeat — inspired by louislam/uptime-kuma HTTP monitor status.

Uptime-kuma treats any 2xx HTTP response as "up" for an HTTP monitor. The bug
checks only `response_code == 200`, so 201, 204, and other 2xx codes are
wrongly reported as "down".
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_200_is_up():
    from heartbeat import compute_status
    assert compute_status(200) is True


def test_404_is_down():
    from heartbeat import compute_status
    assert compute_status(404) is False


def test_500_is_down():
    from heartbeat import compute_status
    assert compute_status(500) is False


def test_custom_codes_match():
    from heartbeat import compute_status
    assert compute_status(301, expected_codes=[301, 302]) is True


def test_201_created_is_up():
    from heartbeat import compute_status
    # Bug: 201 == 200 is False → reports down; expected: up (2xx)
    result = compute_status(201)
    assert result is True, f"201 Created should be up, got {result}"


def test_204_no_content_is_up():
    from heartbeat import compute_status
    # Bug: 204 == 200 is False → reports down; expected: up (2xx)
    result = compute_status(204)
    assert result is True, f"204 No Content should be up, got {result}"


def test_299_edge_of_2xx_is_up():
    from heartbeat import compute_status
    # Bug: 299 == 200 is False → reports down; expected: up (2xx range)
    result = compute_status(299)
    assert result is True, f"299 should be up (within 2xx range), got {result}"
