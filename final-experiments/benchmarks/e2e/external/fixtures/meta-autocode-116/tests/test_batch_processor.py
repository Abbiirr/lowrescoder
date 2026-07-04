import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from batch_processor import process_in_batches

identity = lambda batch: batch

# PASS with bug

def test_empty_input():
    assert process_in_batches([], 3, identity) == []

def test_single_batch_size_one():
    # batch_size=1: slice items[0:0] = [] each iteration... hmm
    # Actually batch_size=1: items[0:0] = [], items[1:1] = [] — always empty!
    # This test won't pass. Let me use size=2 for a 1-item list:
    # items=[1], batch_size=2: slice [0:1] = [1]. Returns [1]. Both bug and fix return [1].
    assert process_in_batches([1], 2, identity) == [1]

def test_result_is_list():
    assert isinstance(process_in_batches([1, 2], 2, identity), list)

def test_exactly_one_batch_size_larger():
    # 2 items, batch_size=5: bug slice [0:4] = [0,1] (both items). fix: [0:5]=[0,1]. Same!
    assert process_in_batches([10, 20], 5, identity) == [10, 20]

# FAIL with bug (last item of each batch dropped)

def test_full_batch_all_items():
    items = [1, 2, 3]
    result = process_in_batches(items, 3, identity)
    assert result == [1, 2, 3]  # bug: [1, 2] (last item dropped)

def test_multiple_batches_complete():
    items = list(range(6))
    result = process_in_batches(items, 3, identity)
    assert len(result) == 6  # bug: 4 (drops last of each batch)

def test_no_item_dropped():
    items = [1, 2, 3, 4]
    result = process_in_batches(items, 4, identity)
    assert 4 in result  # bug: [1, 2, 3] — 4 dropped
