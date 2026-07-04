#!/usr/bin/env bash
# Setup for tb-008-count-dataset-tokens
# Creates a text dataset and a stub tokenizer script.
# Tokenization rule: split on whitespace and punctuation.
set -euo pipefail

cat > dataset.txt << 'TEXT'
The quick brown fox jumps over the lazy dog.
Machine learning is a subset of artificial intelligence.
Python is a popular programming language for data science.
Natural language processing enables computers to understand text.
Deep learning models require large amounts of training data.
The transformer architecture revolutionized NLP in 2017.
Attention mechanisms allow models to focus on relevant parts.
Tokenization is the first step in text processing pipelines.
Word embeddings capture semantic meaning in vector space.
Transfer learning reduces the need for task-specific training data.
TEXT

# Create expected answer file (hidden from agent, used by verifier)
# Tokenization rules:
# 1. Split on whitespace
# 2. Strip punctuation (.,!?;:) from token boundaries
# 3. Lowercase everything
# 4. Count unique tokens and total tokens
python3 << 'PYCOUNT'
import re

with open("dataset.txt") as f:
    text = f.read()

# Tokenize: split on whitespace, strip punctuation, lowercase
tokens = []
for word in text.split():
    token = re.sub(r'[.,!?;:]', '', word).lower()
    if token:
        tokens.append(token)

with open(".expected_counts.txt", "w") as f:
    f.write(f"total:{len(tokens)}\n")
    f.write(f"unique:{len(set(tokens))}\n")
PYCOUNT

# Create stub script
cat > count_tokens.py << 'STUB'
#!/usr/bin/env python3
"""Count tokens in dataset.txt.

Tokenization rules:
1. Split text on whitespace
2. Strip punctuation (.,!?;:) from each token
3. Convert to lowercase
4. Ignore empty tokens

Output format (print to stdout):
  total: <total_token_count>
  unique: <unique_token_count>
"""
# TODO: Implement token counting
STUB

chmod +x count_tokens.py

echo "Setup complete. dataset.txt created with 10 lines."
