import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from interceptor_chain import apply_interceptors

# PASS with bug (single interceptor or commutative operations)

def test_no_interceptors():
    assert apply_interceptors(5, []) == 5

def test_single_interceptor():
    assert apply_interceptors(3, [lambda x: x * 2]) == 6

def test_all_same_operation():
    result = apply_interceptors(1, [lambda x: x + 1, lambda x: x + 1])
    assert result == 3

def test_returns_original_type():
    assert apply_interceptors('hello', [lambda x: x.upper()]) == 'HELLO'

# FAIL with bug (order matters)

def test_order_preserved():
    # [add 10, multiply 2] correct: (5+10)*2 = 30; bug (reversed): (5*2)+10 = 20
    add10 = lambda x: x + 10
    mul2 = lambda x: x * 2
    assert apply_interceptors(5, [add10, mul2]) == 30

def test_string_pipeline_order():
    # [a→b, b→c] correct: 'cat'→'cbt'→'cct'; bug (reversed): b→c first (no-op), then a→b: 'cbt'
    ab = lambda s: s.replace('a', 'b')
    bc = lambda s: s.replace('b', 'c')
    assert apply_interceptors('cat', [ab, bc]) == 'cct'

def test_division_order_matters():
    # [div2, sub1] correct: (10/2)-1 = 4.0; bug (reversed): (10-1)/2 = 4.5
    div2 = lambda x: x / 2
    sub1 = lambda x: x - 1
    assert apply_interceptors(10, [div2, sub1]) == 4.0
