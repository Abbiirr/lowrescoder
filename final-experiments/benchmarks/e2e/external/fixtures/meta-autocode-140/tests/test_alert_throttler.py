import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from alert_throttler import should_send_alert

# PASS with bug (elapsed in seconds >> cooldown in minutes — bug agrees)

def test_no_time_passed():
    # elapsed=0, cooldown=5min → 0 >= 5 False (both agree)
    assert should_send_alert(1000, 1000, 5) is False

def test_much_time_passed():
    # elapsed=3600s, cooldown=5min → bug: 3600>=5 True; fix: 3600>=300 True
    assert should_send_alert(0, 3600, 5) is True

def test_zero_cooldown():
    # cooldown=0 → elapsed >= 0 always True (both agree)
    assert should_send_alert(100, 101, 0) is True

def test_elapsed_equals_cooldown_minutes_in_seconds():
    # elapsed=5s, cooldown=5min → bug: 5>=5 True; fix: 5>=300 False
    # This FAILS with bug — actually let's use a case that PASSES with bug
    # elapsed=301s, cooldown=5min → bug: 301>=5 True; fix: 301>=300 True
    assert should_send_alert(0, 301, 5) is True

# FAIL with bug (seconds vs minutes mismatch causes early sending)

def test_four_minutes_not_ready():
    # 240s elapsed, cooldown=5min (300s needed); bug: 240>=5 True (wrong!)
    assert should_send_alert(0, 240, 5) is False

def test_one_minute_too_early():
    # 60s elapsed, cooldown=2min; bug: 60>=2 True; fix: 60>=120 False
    assert should_send_alert(1000, 1060, 2) is False

def test_half_cooldown_elapsed():
    # 150s elapsed, cooldown=5min; bug: 150>=5 True; fix: 150>=300 False
    assert should_send_alert(0, 150, 5) is False
