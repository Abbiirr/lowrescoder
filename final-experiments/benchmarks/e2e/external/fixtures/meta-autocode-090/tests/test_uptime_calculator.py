import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from uptime_calculator import calculate_uptime_percentage

# PASS with bug (all-up or all-down edge cases)

def test_empty_checks_returns_zero():
    assert calculate_uptime_percentage([]) == 0.0

def test_all_up_is_100():
    checks = [{'status': 'up'}] * 5
    assert calculate_uptime_percentage(checks) == 100.0

def test_returns_float():
    assert isinstance(calculate_uptime_percentage([{'status': 'up'}]), float)

def test_single_check_up():
    assert calculate_uptime_percentage([{'status': 'up'}]) == 100.0

# FAIL with bug (mixed checks always return 100%)

def test_half_up_half_down():
    checks = [{'status': 'up'}, {'status': 'down'}, {'status': 'up'}, {'status': 'down'}]
    assert calculate_uptime_percentage(checks) == 50.0  # bug: 100.0

def test_one_up_three_down():
    checks = [{'status': 'up'}, {'status': 'down'}, {'status': 'down'}, {'status': 'down'}]
    assert calculate_uptime_percentage(checks) == 25.0  # bug: 100.0

def test_all_down_is_zero():
    checks = [{'status': 'down'}] * 4
    assert calculate_uptime_percentage(checks) == 0.0  # bug: 100.0
