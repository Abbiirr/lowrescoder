# Longest Increasing Subsequence

Given an integer array `nums`, return the length of the longest strictly increasing subsequence.

A **subsequence** is a sequence derived from an array by deleting some or no elements without changing the order of the remaining elements.

## Function Signature

```python
def length_of_lis(nums: list[int]) -> int
```

## Constraints

- `1 <= nums.length <= 2500`
- `-10^4 <= nums[i] <= 10^4`

## Examples

```
Input: nums = [10,9,2,5,3,7,101,18]
Output: 4
Explanation: The LIS is [2,3,7,101], length 4.

Input: nums = [0,1,0,3,2,3]
Output: 4

Input: nums = [7,7,7,7,7,7,7]
Output: 1
```
