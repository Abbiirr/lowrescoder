import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from monitor_updater import update_monitor_status

# --- PASS with bug (monitor was previously down — both update last_check) ---

def test_down_monitor_gets_check_time():
    monitor = {'is_up': False, 'last_check': 0}
    update_monitor_status(monitor, True, 1000)
    assert monitor['last_check'] == 1000

def test_is_up_field_always_updated():
    monitor = {'is_up': True, 'last_check': 0}
    update_monitor_status(monitor, False, 500)
    assert monitor['is_up'] is False

def test_down_to_up_updates_check_time():
    monitor = {'is_up': False, 'last_check': 100}
    update_monitor_status(monitor, True, 200)
    assert monitor['last_check'] == 200

def test_returns_monitor_object():
    monitor = {'is_up': False, 'last_check': 0}
    assert update_monitor_status(monitor, True, 1) is monitor

# --- FAIL with bug (monitor was up — bug skips last_check update, fix updates) ---

def test_up_monitor_last_check_updated():
    monitor = {'is_up': True, 'last_check': 0}
    update_monitor_status(monitor, True, 123)
    assert monitor['last_check'] == 123

def test_up_to_down_updates_last_check():
    monitor = {'is_up': True, 'last_check': 50}
    update_monitor_status(monitor, False, 100)
    assert monitor['last_check'] == 100

def test_repeated_up_checks_update_time():
    monitor = {'is_up': True, 'last_check': 10}
    update_monitor_status(monitor, True, 20)
    update_monitor_status(monitor, True, 30)
    assert monitor['last_check'] == 30
