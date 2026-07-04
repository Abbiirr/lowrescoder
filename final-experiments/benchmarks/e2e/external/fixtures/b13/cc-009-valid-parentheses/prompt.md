# Valid Parentheses

## Problem

Given a string `s` containing just the characters `'('`, `')'`, `'{'`, `'}'`, `'['` and `']'`, determine if the input string is valid.

An input string is valid if:

1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.
3. Every close bracket has a corresponding open bracket of the same type.

## Function Signature

```python
def is_valid(s: str) -> bool:
```

## Constraints

- `1 <= len(s) <= 10^4`
- `s` consists of parentheses only: `'()[]{}'`

## Examples

**Example 1:**
```
Input: s = "()"
Output: True
```

**Example 2:**
```
Input: s = "()[]{}"
Output: True
```

**Example 3:**
```
Input: s = "(]"
Output: False
```

**Example 4:**
```
Input: s = "([])"
Output: True
```
