package main

import (
	"strings"
	"testing"
)

func TestRenderMarkdownContentPlainText(t *testing.T) {
	content := "Hello, world!"
	result := renderMarkdownContent(content, 80)

	if result == "" {
		t.Error("expected non-empty result")
	}
	// Should contain the original text (possibly with ANSI codes)
	if !strings.Contains(result, "Hello") {
		t.Errorf("expected result to contain 'Hello', got: %q", result)
	}
}

func TestRenderMarkdownContentHeading(t *testing.T) {
	content := "# My Heading\n\nSome paragraph text."
	result := renderMarkdownContent(content, 80)

	if result == "" {
		t.Error("expected non-empty result")
	}
	if !strings.Contains(result, "Heading") {
		t.Errorf("expected result to contain 'Heading', got: %q", result)
	}
}

func TestRenderMarkdownContentCodeBlock(t *testing.T) {
	content := "```python\nprint('hello')\n```"
	result := renderMarkdownContent(content, 80)

	if result == "" {
		t.Error("expected non-empty result")
	}
	if !strings.Contains(result, "print") {
		t.Errorf("expected result to contain 'print', got: %q", result)
	}
}

func TestRenderMarkdownContentNarrowWidth(t *testing.T) {
	content := "This is a long sentence that should be wrapped to fit within the specified width."
	result := renderMarkdownContent(content, 30)

	if result == "" {
		t.Error("expected non-empty result")
	}
}

func TestRenderMarkdownContentVeryNarrowWidth(t *testing.T) {
	// Width < 20 should default to 80
	content := "Some text"
	result := renderMarkdownContent(content, 5)

	if result == "" {
		t.Error("expected non-empty result")
	}
}

func TestRenderMarkdownContentEmptyString(t *testing.T) {
	result := renderMarkdownContent("", 80)
	// Empty input should not panic
	_ = result
}

func TestRenderMarkdownContentBulletList(t *testing.T) {
	content := "- Item one\n- Item two\n- Item three"
	result := renderMarkdownContent(content, 80)

	if !strings.Contains(result, "Item one") {
		t.Errorf("expected result to contain 'Item one', got: %q", result)
	}
}

func TestRenderMarkdownContentBoldItalic(t *testing.T) {
	content := "This is **bold** and *italic* text."
	result := renderMarkdownContent(content, 80)

	if !strings.Contains(result, "bold") {
		t.Errorf("expected result to contain 'bold', got: %q", result)
	}
}

func TestRenderMarkdownContentLink(t *testing.T) {
	content := "Visit [example](https://example.com) for more."
	result := renderMarkdownContent(content, 80)

	if !strings.Contains(result, "example") {
		t.Errorf("expected result to contain 'example', got: %q", result)
	}
}

func TestRenderMarkdownContentMultipleBlocks(t *testing.T) {
	content := "# Title\n\nParagraph.\n\n```\ncode\n```\n\n- list item"
	result := renderMarkdownContent(content, 80)

	if result == "" {
		t.Error("expected non-empty result")
	}
}
