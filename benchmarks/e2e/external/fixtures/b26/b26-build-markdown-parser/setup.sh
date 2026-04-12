#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/markdown_parser.py << 'PYEOF'
"""Simple markdown-to-HTML converter."""


def convert(markdown):
    """Convert a markdown string to HTML.

    Supports: headings (h1-h6), bold, italic, links, inline code, paragraphs.

    Args:
        markdown: A markdown-formatted string.

    Returns:
        An HTML string.
    """
    # TODO: Implement markdown to HTML conversion
    pass
PYEOF

cat > project/test_parser.py << 'PYEOF'
"""Tests for the markdown-to-HTML converter."""
import unittest
from markdown_parser import convert


class TestHeadings(unittest.TestCase):

    def test_h1(self):
        self.assertEqual(convert("# Hello").strip(), "<h1>Hello</h1>")

    def test_h2(self):
        self.assertEqual(convert("## Hello").strip(), "<h2>Hello</h2>")

    def test_h3(self):
        self.assertEqual(convert("### Hello").strip(), "<h3>Hello</h3>")

    def test_h6(self):
        self.assertEqual(convert("###### Hello").strip(), "<h6>Hello</h6>")


class TestInlineFormatting(unittest.TestCase):

    def test_bold(self):
        result = convert("This is **bold** text")
        self.assertIn("<strong>bold</strong>", result)

    def test_italic(self):
        result = convert("This is *italic* text")
        self.assertIn("<em>italic</em>", result)

    def test_inline_code(self):
        result = convert("Use `print()` function")
        self.assertIn("<code>print()</code>", result)

    def test_bold_and_italic(self):
        result = convert("**bold** and *italic*")
        self.assertIn("<strong>bold</strong>", result)
        self.assertIn("<em>italic</em>", result)


class TestLinks(unittest.TestCase):

    def test_simple_link(self):
        result = convert("[Click here](https://example.com)")
        self.assertIn('<a href="https://example.com">Click here</a>', result)

    def test_link_in_text(self):
        result = convert("Visit [Google](https://google.com) for search")
        self.assertIn('<a href="https://google.com">Google</a>', result)


class TestParagraphs(unittest.TestCase):

    def test_single_paragraph(self):
        result = convert("Hello world").strip()
        self.assertEqual(result, "<p>Hello world</p>")

    def test_two_paragraphs(self):
        result = convert("First paragraph\n\nSecond paragraph")
        self.assertIn("<p>First paragraph</p>", result)
        self.assertIn("<p>Second paragraph</p>", result)

    def test_heading_not_in_paragraph(self):
        result = convert("# Heading\n\nParagraph text")
        self.assertIn("<h1>Heading</h1>", result)
        self.assertIn("<p>Paragraph text</p>", result)
        # Heading should NOT be wrapped in <p>
        self.assertNotIn("<p><h1>", result)


class TestMixed(unittest.TestCase):

    def test_heading_with_bold(self):
        result = convert("# **Bold** Heading")
        self.assertIn("<h1>", result)
        self.assertIn("<strong>Bold</strong>", result)

    def test_paragraph_with_link_and_bold(self):
        result = convert("Click **[here](https://example.com)** now")
        self.assertIn('<a href="https://example.com">here</a>', result)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. markdown_parser.py needs convert() implemented."
