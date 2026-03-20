import pytest

from client import TransientUpstreamError, fetch_payload
from service import render_status


def test_fetch_payload_retries_once_for_transient_failure():
    state = {"calls": 0}

    def flaky_fetcher():
        state["calls"] += 1
        if state["calls"] == 1:
            raise TransientUpstreamError("temporary")
        return {"status": "ok", "count": 2}

    assert fetch_payload(flaky_fetcher) == {"status": "ok", "count": 2}
    assert state["calls"] == 2


def test_fetch_payload_stops_after_max_attempts():
    state = {"calls": 0}

    def always_fails():
        state["calls"] += 1
        raise TransientUpstreamError("still failing")

    with pytest.raises(TransientUpstreamError):
        fetch_payload(always_fails, max_attempts=2)

    assert state["calls"] == 2


def test_render_status_uses_retried_payload():
    state = {"calls": 0}

    def flaky_fetcher():
        state["calls"] += 1
        if state["calls"] == 1:
            raise TransientUpstreamError("temporary")
        return {"status": "green", "count": 5}

    assert render_status(flaky_fetcher) == "green:5"
