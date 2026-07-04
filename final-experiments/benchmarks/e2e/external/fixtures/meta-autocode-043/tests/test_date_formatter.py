import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from date_formatter import format_commit_date

def test_double_digit_month_and_day():
    assert format_commit_date(2026, 12, 31) == '2026-12-31'

def test_october():
    assert format_commit_date(2026, 10, 25) == '2026-10-25'

def test_november_tenth():
    assert format_commit_date(2026, 11, 10) == '2026-11-10'

def test_december_fifteenth():
    assert format_commit_date(2026, 12, 15) == '2026-12-15'

def test_single_digit_month():
    # BUG: f"{2026}-{3}-{5}" = '2026-3-5', should be '2026-03-05'
    assert format_commit_date(2026, 3, 5) == '2026-03-05'

def test_single_digit_month_double_digit_day():
    # BUG: f"{2026}-{3}-{15}" = '2026-3-15', should be '2026-03-15'
    assert format_commit_date(2026, 3, 15) == '2026-03-15'

def test_double_digit_month_single_digit_day():
    # BUG: f"{2026}-{12}-{5}" = '2026-12-5', should be '2026-12-05'
    assert format_commit_date(2026, 12, 5) == '2026-12-05'
