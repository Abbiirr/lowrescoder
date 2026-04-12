# Task: Fix Memory Leak in Item Processor

## Objective

The item processor in `project/processor.py` has a memory leak. It appends processed items to an internal list but never removes them after processing. Over time, the list grows unboundedly. Fix the processor so processed items are cleaned up.

## Requirements

1. Processed items must be removed or cleared from the internal list after processing.
2. The processor's memory usage must be bounded (internal list does not grow indefinitely).
3. Processing results must still be returned correctly.
4. All tests in `project/test_processor.py` must pass.
5. Do not change function signatures.

## Current State

- `project/processor.py` has an `ItemProcessor` class that appends every item to `self._buffer`.
- After processing, items remain in `self._buffer` forever.
- `project/test_processor.py` tests that the buffer is cleaned up after processing.

## Files

- `project/processor.py` — the leaky processor
- `project/test_processor.py` — test file
