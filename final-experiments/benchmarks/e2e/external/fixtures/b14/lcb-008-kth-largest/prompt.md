# Kth Largest Element in an Array

Given an integer array `nums` and an integer `k`, return the `k`th largest element in the array.

Note that it is the `k`th largest element in sorted order, not the `k`th distinct element.

You must solve it without sorting the entire array (though any correct solution will be accepted by the tests).

## Function Signature

```python
def find_kth_largest(nums: list[int], k: int) -> int
```

## Constraints

- `1 <= k <= nums.length <= 10^5`
- `-10^4 <= nums[i] <= 10^4`

## Examples

```
Input: nums = [3,2,1,5,6,4], k = 2
Output: 5

Input: nums = [3,2,3,1,2,4,5,5,6], k = 4
Output: 4
```
