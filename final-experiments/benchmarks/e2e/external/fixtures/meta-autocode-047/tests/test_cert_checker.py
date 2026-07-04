import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from cert_checker import cert_status

def test_expired():
    assert cert_status(-5) == 'expired'

def test_valid_long_term():
    assert cert_status(365) == 'valid'

def test_expiring_soon_3_days():
    assert cert_status(3) == 'expiring_soon'

def test_expiring_soon_7_days():
    assert cert_status(7) == 'expiring_soon'

def test_expiring_soon_15_days():
    # BUG: threshold is <=7, so 15 returns 'valid' instead of 'expiring_soon'
    assert cert_status(15) == 'expiring_soon'

def test_expiring_soon_20_days():
    # BUG: 20 > 7, returns 'valid' instead of 'expiring_soon'
    assert cert_status(20) == 'expiring_soon'

def test_expiring_soon_30_days():
    # BUG: 30 > 7, returns 'valid' instead of 'expiring_soon'
    assert cert_status(30) == 'expiring_soon'
