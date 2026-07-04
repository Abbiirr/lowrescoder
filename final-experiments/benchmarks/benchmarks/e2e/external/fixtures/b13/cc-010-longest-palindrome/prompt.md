# Longest Palindromic Substring

## Problem

Given a string `s`, return the longest palindromic substring in `s`.

A palindrome is a string that reads the same forward and backward.

If there are multiple answers of the same length, return any one of them.

## Function Signature

```python
def longest_palindrome(s: str) -> str:
```

## Constraints

- `1 <= len(s) <= 1000`
- `s` consists of only digits and English letters.

## Examples

**Example 1:**
```
Input: s = "babad"
Output: "bab" (or "aba" — both are valid)
```

**Example 2:**
```
Input: s = "cbbd"
Output: "bb"
```

**Example 3:**
```
Input: s = "a"
Output: "a"
```

**Example 4:**
```
Input: s = "ac"
Output: "a" (or "c")
```
