import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from date_range import ranges_overlap

# PASS (bug and fix agree)

def test_identical_ranges():
    assert ranges_overlap(0, 10, 0, 10) == True  # bug: 0<=0 and 10>=10 → True

def test_range1_contains_range2():
    assert ranges_overlap(0, 10, 2, 8) == True  # bug: 0<=2 and 10>=8 → True

def test_no_overlap_range1_first():
    assert ranges_overlap(0, 5, 7, 10) == False  # bug: 0<=7 and 5>=10 → False

def test_no_overlap_range2_first():
    assert ranges_overlap(6, 10, 0, 5) == False  # bug: 6<=0 → False

# FAIL (partial overlaps — bug: False, fix: True)

def test_partial_overlap_left():
    assert ranges_overlap(0, 7, 5, 10) == True  # bug: 0<=5 and 7>=10 → False

def test_partial_overlap_right():
    assert ranges_overlap(5, 10, 0, 7) == True  # bug: 5<=0 → False

def test_range2_contains_range1():
    assert ranges_overlap(2, 8, 0, 10) == True  # bug: 2<=0 → False
