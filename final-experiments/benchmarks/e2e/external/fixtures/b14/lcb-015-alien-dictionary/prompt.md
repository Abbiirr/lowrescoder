# Alien Dictionary

There is a new alien language that uses the English alphabet. However, the order of the letters is unknown to you.

You are given a list of strings `words` from the alien language's dictionary, where the strings in `words` are **sorted lexicographically** by the rules of this new language.

Derive the order of letters in this language and return it as a string of unique letters. If there are multiple valid orderings, return any of them. If there is no valid ordering (i.e., the input is invalid), return an empty string `""`.

## Function Signature

```python
def alien_order(words: list[str]) -> str
```

## Constraints

- `1 <= words.length <= 100`
- `1 <= words[i].length <= 100`
- `words[i]` consists of only lowercase English letters

## Rules

- A letter `a` comes before letter `b` if `a` appears before `b` in the alien alphabet.
- If a shorter word is a prefix of a longer word, the shorter word must come first. If this rule is violated, return `""`.

## Examples

```
Input: words = ["wrt","wrf","er","ett","rftt"]
Output: "wertf"

Input: words = ["z","x"]
Output: "zx"

Input: words = ["z","x","z"]
Output: ""
Explanation: The order is invalid, so return "".

Input: words = ["abc","ab"]
Output: ""
Explanation: "abc" should come after "ab" since "ab" is a prefix, so this is invalid.
```
