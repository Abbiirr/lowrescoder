# Find Median from Data Stream

## Problem

The median is the middle value in an ordered integer list. If the size of the list is even, there is no middle value, and the median is the mean of the two middle values.

Implement the `MedianFinder` class:

- `MedianFinder()` — Initializes the MedianFinder object.
- `add_num(num: int) -> None` — Adds the integer `num` from the data stream to the data structure.
- `find_median() -> float` — Returns the median of all elements so far. Answers within `10^-5` of the actual answer will be accepted.

## Class Signature

```python
class MedianFinder:
    def __init__(self):
        ...

    def add_num(self, num: int) -> None:
        ...

    def find_median(self) -> float:
        ...
```

## Constraints

- `-10^5 <= num <= 10^5`
- There will be at least one element in the data structure before calling `find_median`.
- At most `5 * 10^4` calls will be made to `add_num` and `find_median`.

## Examples

**Example 1:**
```
mf = MedianFinder()
mf.add_num(1)
mf.find_median()  # returns 1.0
mf.add_num(2)
mf.find_median()  # returns 1.5
mf.add_num(3)
mf.find_median()  # returns 2.0
```
