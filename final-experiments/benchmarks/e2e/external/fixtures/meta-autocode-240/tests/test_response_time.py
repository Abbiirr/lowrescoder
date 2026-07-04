import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from response_time import format_response_time

# PASS (ms < 1000 — no division, both bug and fix return same 'Xms')

def test_100ms():
    assert format_response_time(100) == '100ms'

def test_0ms():
    assert format_response_time(0) == '0ms'

def test_999ms():
    assert format_response_time(999) == '999ms'

def test_500ms():
    assert format_response_time(500) == '500ms'

# FAIL (ms >= 1000 — bug divides by 100, fix divides by 1000)

def test_1000ms():
    assert format_response_time(1000) == '1.00s'  # bug: '10.00s'

def test_2500ms():
    assert format_response_time(2500) == '2.50s'  # bug: '25.00s'

def test_1234ms():
    assert format_response_time(1234) == '1.23s'  # bug: '12.34s'
