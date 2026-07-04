"""Hidden tests for cc-007-course-schedule."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import can_finish


class TestCourseSchedule:
    """Test suite for the can_finish function."""

    def test_simple_possible(self):
        assert can_finish(2, [[1, 0]]) is True

    def test_simple_cycle(self):
        assert can_finish(2, [[1, 0], [0, 1]]) is False

    def test_no_prerequisites(self):
        assert can_finish(3, []) is True

    def test_single_course(self):
        assert can_finish(1, []) is True

    def test_chain(self):
        # 0 -> 1 -> 2 -> 3 (no cycle)
        assert can_finish(4, [[1, 0], [2, 1], [3, 2]]) is True

    def test_three_node_cycle(self):
        # 0 -> 1 -> 2 -> 0
        assert can_finish(3, [[1, 0], [2, 1], [0, 2]]) is False

    def test_disconnected_graph(self):
        # Two independent chains
        assert can_finish(4, [[1, 0], [3, 2]]) is True

    def test_multiple_prerequisites(self):
        # Course 2 requires both 0 and 1
        assert can_finish(3, [[2, 0], [2, 1]]) is True

    def test_complex_graph_no_cycle(self):
        # Diamond shape: 3 requires 1 and 2; both require 0
        assert can_finish(4, [[1, 0], [2, 0], [3, 1], [3, 2]]) is True

    def test_cycle_in_subgraph(self):
        # Course 0 is independent, but 1->2->3->1 is a cycle
        assert can_finish(4, [[2, 1], [3, 2], [1, 3]]) is False
