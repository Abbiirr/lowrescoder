import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from status_aggregator import compute_uptime_percent

# PASS with bug (symmetric or edge cases where bug and fix agree)

def test_empty_checks():
    assert compute_uptime_percent([]) == 0.0

def test_equal_split():
    # 3 up, 3 down — both bug and fix compute 3/6 = 50.0
    checks = [{'status': 'up'}] * 3 + [{'status': 'down'}] * 3
    assert compute_uptime_percent(checks) == 50.0

def test_unknown_status_only():
    # status is 'pending' — neither 'up' nor 'down' — both return 0.0
    checks = [{'status': 'pending'}, {'status': 'pending'}]
    assert compute_uptime_percent(checks) == 0.0

def test_one_up_one_down():
    checks = [{'status': 'up'}, {'status': 'down'}]
    assert compute_uptime_percent(checks) == 50.0

# FAIL with bug (asymmetric cases expose 'down' vs 'up' counting)

def test_all_up():
    checks = [{'status': 'up'}, {'status': 'up'}, {'status': 'up'}]
    assert compute_uptime_percent(checks) == 100.0  # bug: 0.0

def test_all_down():
    checks = [{'status': 'down'}, {'status': 'down'}]
    assert compute_uptime_percent(checks) == 0.0  # bug: 100.0

def test_mostly_up():
    checks = [{'status': 'up'}] * 3 + [{'status': 'down'}]
    assert compute_uptime_percent(checks) == 75.0  # bug: 25.0
