import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from status_label import get_status_label

# PASS (lowercase status or truly unknown — both bug and fix agree)

def test_up_lower():
    assert get_status_label('up') == 'Online'

def test_down_lower():
    assert get_status_label('down') == 'Offline'

def test_pending_lower():
    assert get_status_label('pending') == 'Checking'

def test_unknown():
    assert get_status_label('unknown') is None

# FAIL (uppercase status — bug returns None, fix returns correct label)

def test_up_upper():
    assert get_status_label('UP') == 'Online'  # bug: None

def test_down_upper():
    assert get_status_label('DOWN') == 'Offline'  # bug: None

def test_pending_upper():
    assert get_status_label('PENDING') == 'Checking'  # bug: None
