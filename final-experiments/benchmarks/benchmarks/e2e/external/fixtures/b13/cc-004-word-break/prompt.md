# Word Break

## Problem

Given a string `s` and a dictionary of strings `word_dict`, return `True` if `s` can be segmented into a space-separated sequence of one or more dictionary words.

Note that the same word in the dictionary may be reused multiple times in the segmentation.

## Function Signature

```python
def word_break(s: str, word_dict: list[str]) -> bool:
```

## Constraints

- `1 <= len(s) <= 300`
- `1 <= len(word_dict) <= 1000`
- `1 <= len(word_dict[i]) <= 20`
- `s` and `word_dict[i]` consist of only lowercase English letters.
- All the strings of `word_dict` are unique.

## Examples

**Example 1:**
```
Input: s = "leetcode", word_dict = ["leet", "code"]
Output: True
Explanation: "leetcode" can be segmented as "leet code".
```

**Example 2:**
```
Input: s = "applepenapple", word_dict = ["apple", "pen"]
Output: True
Explanation: "applepenapple" can be segmented as "apple pen apple".
Note that "apple" is reused.
```

**Example 3:**
```
Input: s = "catsandog", word_dict = ["cats", "dog", "sand", "and", "cat"]
Output: False
```
