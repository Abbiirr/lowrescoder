# Task: Build a Simple Markdown-to-HTML Converter

## Objective

Build a simple markdown-to-HTML converter that handles the most common markdown elements. Implement the `convert(markdown)` function in `project/markdown_parser.py`.

## Requirements

1. Convert the following markdown elements to HTML:
   - `# Heading` to `<h1>`, `## Heading` to `<h2>`, up to `###### Heading` to `<h6>`
   - `**bold**` to `<strong>bold</strong>`
   - `*italic*` to `<em>italic</em>`
   - `[text](url)` to `<a href="url">text</a>`
   - `` `code` `` to `<code>code</code>`
   - Blank lines separate paragraphs wrapped in `<p>` tags
2. All tests in `project/test_parser.py` must pass.

## Files

- `project/markdown_parser.py` — implement the converter here
- `project/test_parser.py` — test file with expected HTML output
