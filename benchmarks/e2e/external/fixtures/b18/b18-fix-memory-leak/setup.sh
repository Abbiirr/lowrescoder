#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/processor.py << 'PYEOF'
"""Item processor module — processes items in batches."""


class ItemProcessor:
    """Processes items and returns results.

    WARNING: This processor has a memory leak. Processed items accumulate
    in self._buffer and are never removed.
    """

    def __init__(self, batch_size=100):
        self._buffer = []
        self._batch_size = batch_size
        self._total_processed = 0

    def add_item(self, item):
        """Add an item to the processing buffer.

        Args:
            item: The item to add for processing.
        """
        self._buffer.append(item)

    def add_items(self, items):
        """Add multiple items to the processing buffer.

        Args:
            items: Iterable of items to add.
        """
        for item in items:
            self.add_item(item)

    def process(self):
        """Process all items in the buffer and return results.

        Returns:
            list: Processed results (each item transformed to uppercase if string,
                  doubled if number).
        """
        results = []
        for item in self._buffer:
            if isinstance(item, str):
                results.append(item.upper())
            elif isinstance(item, (int, float)):
                results.append(item * 2)
            else:
                results.append(item)
        self._total_processed += len(self._buffer)
        # BUG: Never clears self._buffer after processing.
        # Items accumulate forever, causing a memory leak.
        return results

    @property
    def buffer_size(self):
        """Return the current number of items in the buffer."""
        return len(self._buffer)

    @property
    def total_processed(self):
        """Return the total number of items processed since creation."""
        return self._total_processed
PYEOF

cat > project/test_processor.py << 'PYEOF'
"""Tests for the item processor module."""
import unittest
from processor import ItemProcessor


class TestProcessorBasic(unittest.TestCase):

    def test_process_strings(self):
        p = ItemProcessor()
        p.add_items(["hello", "world"])
        results = p.process()
        self.assertEqual(results, ["HELLO", "WORLD"])

    def test_process_numbers(self):
        p = ItemProcessor()
        p.add_items([1, 2, 3])
        results = p.process()
        self.assertEqual(results, [2, 4, 6])

    def test_process_mixed(self):
        p = ItemProcessor()
        p.add_items(["hi", 5, "bye", 10])
        results = p.process()
        self.assertEqual(results, ["HI", 10, "BYE", 20])

    def test_total_processed(self):
        p = ItemProcessor()
        p.add_items([1, 2, 3])
        p.process()
        self.assertEqual(p.total_processed, 3)


class TestProcessorMemoryLeak(unittest.TestCase):
    """Tests that verify the memory leak is fixed."""

    def test_buffer_cleared_after_process(self):
        """After calling process(), the buffer should be empty."""
        p = ItemProcessor()
        p.add_items(["a", "b", "c"])
        self.assertEqual(p.buffer_size, 3)
        p.process()
        self.assertEqual(p.buffer_size, 0,
                         "Buffer should be empty after process()")

    def test_repeated_processing_bounded(self):
        """Processing multiple batches should not accumulate items."""
        p = ItemProcessor()
        for batch in range(10):
            p.add_items(list(range(100)))
            p.process()
        # Buffer should only have the items from the last unprocessed batch (0)
        self.assertEqual(p.buffer_size, 0,
                         "Buffer should be empty — items accumulating!")

    def test_second_process_only_new_items(self):
        """Second process() call should only process newly added items."""
        p = ItemProcessor()
        p.add_items([1, 2])
        first = p.process()
        self.assertEqual(first, [2, 4])

        p.add_items([3, 4])
        second = p.process()
        # Should only process [3, 4], NOT [1, 2, 3, 4]
        self.assertEqual(second, [6, 8],
                         "Second process() should only return new items")

    def test_total_processed_across_batches(self):
        """Total processed should accumulate correctly across batches."""
        p = ItemProcessor()
        p.add_items([1, 2, 3])
        p.process()
        p.add_items([4, 5])
        p.process()
        self.assertEqual(p.total_processed, 5)

    def test_large_volume_bounded(self):
        """Processing 10000 items in batches should keep buffer small."""
        p = ItemProcessor()
        for i in range(100):
            p.add_items(list(range(100)))
            p.process()
        self.assertEqual(p.buffer_size, 0)
        self.assertEqual(p.total_processed, 10000)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. processor.py never clears buffer after processing."
