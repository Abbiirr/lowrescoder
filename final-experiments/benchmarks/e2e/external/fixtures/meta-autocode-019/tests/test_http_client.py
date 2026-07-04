"""Tests for http_client — inspired by axios/axios interceptor dispatch.

axios runs request interceptors in LIFO order (last registered = first called).
This is intentional: an interceptor added later wraps an earlier one, so it
runs first on the way out. The bug is iterating in insertion order (FIFO).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_no_interceptors():
    from http_client import HttpClient
    c = HttpClient()
    assert c.request({"url": "/api"}) == {"url": "/api"}


def test_single_interceptor():
    from http_client import HttpClient
    c = HttpClient()
    c.add_interceptor(lambda cfg: {**cfg, "x": 1})
    assert c.request({})["x"] == 1


def test_empty_config_passthrough():
    from http_client import HttpClient
    c = HttpClient()
    assert c.request({}) == {}


def test_all_interceptors_run():
    from http_client import HttpClient
    # Both keys appear regardless of order — just verifies both run
    c = HttpClient()
    c.add_interceptor(lambda cfg: {**cfg, "a": True})
    c.add_interceptor(lambda cfg: {**cfg, "b": True})
    result = c.request({})
    assert result.get("a") and result.get("b")


def test_two_interceptors_lifo_order():
    from http_client import HttpClient
    # LIFO: fn2 (added second) must run first, then fn1
    # Expected steps: [2, 1]. Bug (FIFO) gives [1, 2].
    c = HttpClient()
    c.add_interceptor(lambda cfg: {**cfg, "steps": cfg.get("steps", []) + [1]})
    c.add_interceptor(lambda cfg: {**cfg, "steps": cfg.get("steps", []) + [2]})
    result = c.request({})
    assert result["steps"] == [2, 1], \
        f"expected LIFO [2, 1], got {result['steps']}"


def test_three_interceptors_lifo_order():
    from http_client import HttpClient
    # LIFO: fn3 first, fn2 second, fn1 last → [3, 2, 1]
    # Bug gives [1, 2, 3]
    c = HttpClient()
    for i in [1, 2, 3]:
        c.add_interceptor(lambda cfg, n=i: {**cfg, "steps": cfg.get("steps", []) + [n]})
    result = c.request({})
    assert result["steps"] == [3, 2, 1], \
        f"expected LIFO [3, 2, 1], got {result['steps']}"


def test_last_added_wins_on_key_conflict():
    from http_client import HttpClient
    # LIFO: fn2 runs first (sets "second"), fn1 runs last (overwrites → "first")
    # Bug (FIFO): fn1 runs first, fn2 last → "second" wins instead
    c = HttpClient()
    c.add_interceptor(lambda cfg: {**cfg, "priority": "first"})
    c.add_interceptor(lambda cfg: {**cfg, "priority": "second"})
    result = c.request({})
    assert result["priority"] == "first", \
        f"expected first-added to win (runs last in LIFO), got '{result['priority']}'"
