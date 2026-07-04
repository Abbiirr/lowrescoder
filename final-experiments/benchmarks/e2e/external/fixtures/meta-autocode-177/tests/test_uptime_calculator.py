import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from uptime_calculator import uptime_percentage

# PASS (all uppercase — bug and fix agree)

def test_empty():
    assert uptime_percentage([]) == 0.0

def test_all_up():
    assert uptime_percentage(['UP', 'UP', 'UP']) == 100.0

def test_half_up():
    assert uptime_percentage(['UP', 'DOWN']) == 50.0

def test_all_down():
    assert uptime_percentage(['DOWN', 'DOWN']) == 0.0

# FAIL (lowercase/mixed — bug returns wrong result)

def test_lowercase_all_up():
    assert uptime_percentage(['up', 'up']) == 100.0  # bug: 0.0

def test_mixed_case_up():
    assert uptime_percentage(['UP', 'up']) == 100.0  # bug: 50.0

def test_title_case():
    assert uptime_percentage(['Up']) == 100.0  # bug: 0.0
