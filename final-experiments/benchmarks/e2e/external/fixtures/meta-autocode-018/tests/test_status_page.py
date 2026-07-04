"""Tests for status_page — inspired by louislam/uptime-kuma status page grouping.

uptime-kuma shows monitor groups sorted alphabetically on the public status page.
With case-sensitive sort, any group whose name starts with an uppercase letter
sorts before groups starting with lowercase — "Backend" before "api" — which
looks wrong to users expecting standard alphabetical order.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _groups(*names):
    return [{"name": n, "id": i} for i, n in enumerate(names)]


def test_empty():
    from status_page import sort_monitor_groups
    assert sort_monitor_groups([]) == []


def test_single():
    from status_page import sort_monitor_groups
    g = _groups("api")
    assert sort_monitor_groups(g) == g


def test_all_lowercase_already_sorted():
    from status_page import sort_monitor_groups
    groups = _groups("api", "backend", "frontend")
    result = [g["name"] for g in sort_monitor_groups(groups)]
    assert result == ["api", "backend", "frontend"]


def test_all_uppercase():
    from status_page import sort_monitor_groups
    groups = _groups("API", "BACKEND", "FRONTEND")
    result = [g["name"] for g in sort_monitor_groups(groups)]
    assert result == ["API", "BACKEND", "FRONTEND"]


def test_mixed_case_basic():
    from status_page import sort_monitor_groups
    # Case-insensitive: api < Backend < Frontend
    # Bug (case-sensitive): Backend < Frontend < api  ('B'=66 < 'F'=70 < 'a'=97)
    groups = _groups("Frontend", "api", "Backend")
    result = [g["name"] for g in sort_monitor_groups(groups)]
    assert result == ["api", "Backend", "Frontend"], \
        f"expected case-insensitive order, got {result}"


def test_mixed_case_boundary():
    from status_page import sort_monitor_groups
    # Case-insensitive: API < monitor < Zabbix  (a < m < z)
    # Bug: API < Zabbix < monitor  ('Z'=90 < 'm'=109)
    groups = _groups("monitor", "API", "Zabbix")
    result = [g["name"] for g in sort_monitor_groups(groups)]
    assert result == ["API", "monitor", "Zabbix"], \
        f"expected ['API', 'monitor', 'Zabbix'], got {result}"


def test_mixed_case_multigroup():
    from status_page import sort_monitor_groups
    # Real-world scenario: mixed team-named groups
    # Case-insensitive alphabetical: ["api-gateway", "Backend Jobs", "frontend", "Web Servers"]
    # Bug produces: ["Backend Jobs", "Web Servers", "api-gateway", "frontend"]
    groups = _groups("frontend", "Backend Jobs", "api-gateway", "Web Servers")
    result = [g["name"] for g in sort_monitor_groups(groups)]
    assert result == ["api-gateway", "Backend Jobs", "frontend", "Web Servers"], \
        f"got {result}"
