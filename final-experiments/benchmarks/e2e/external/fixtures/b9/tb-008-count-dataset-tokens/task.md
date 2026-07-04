# Task: Count Dataset Tokens

## Objective

Write a Python script that tokenizes a text file and counts total and unique tokens.

## Requirements

1. Edit `count_tokens.py` to process `dataset.txt`.
2. Tokenization rules:
   - Split text on whitespace
   - Strip punctuation characters `.,!?;:` from each token
   - Convert to lowercase
   - Ignore empty tokens after stripping
3. Output exactly two lines to stdout:
   ```
   total: <total_token_count>
   unique: <unique_token_count>
   ```
4. Run with `python count_tokens.py`.

## Example

For input `"Hello, World! Hello."`, the tokens are `["hello", "world", "hello"]`:
- total: 3
- unique: 2

## Files

- `dataset.txt` — the text file to process (10 lines)
- `count_tokens.py` — the script you must edit
