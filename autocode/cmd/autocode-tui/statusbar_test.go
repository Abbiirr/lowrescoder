package main

import (
	"strings"
	"testing"
)

func TestStatusBarBasic(t *testing.T) {
	s := statusBarModel{
		Model:    "qwen3:8b",
		Provider: "openrouter",
		Mode:     "suggest",
	}
	view := s.View()
	if !strings.Contains(view, "qwen3:8b") {
		t.Errorf("expected model name in view, got: %s", view)
	}
	if !strings.Contains(view, "openrouter") {
		t.Errorf("expected provider in view, got: %s", view)
	}
	if !strings.Contains(view, "suggest") {
		t.Errorf("expected mode in view, got: %s", view)
	}
}

func TestStatusBarTokens(t *testing.T) {
	s := statusBarModel{
		Model:  "qwen3:8b",
		Mode:   "suggest",
		Tokens: 1500,
	}
	view := s.View()
	if !strings.Contains(view, "1.5k") {
		t.Errorf("expected 1.5k tokens in view, got: %s", view)
	}
}

func TestStatusBarTokensSmall(t *testing.T) {
	s := statusBarModel{
		Model:  "qwen3:8b",
		Mode:   "suggest",
		Tokens: 42,
	}
	view := s.View()
	if !strings.Contains(view, "42 tokens") {
		t.Errorf("expected '42 tokens' in view, got: %s", view)
	}
}

func TestStatusBarDotSeparator(t *testing.T) {
	s := statusBarModel{
		Model:  "qwen3:8b",
		Mode:   "suggest",
		Tokens: 100,
	}
	view := s.View()
	if !strings.Contains(view, " · ") {
		t.Errorf("expected ' · ' separator in view, got: %s", view)
	}
	if strings.Contains(view, " | ") {
		t.Errorf("expected no pipe separator in view, got: %s", view)
	}
}

func TestStatusBarCost(t *testing.T) {
	s := statusBarModel{
		Model: "qwen3:8b",
		Mode:  "auto",
		Cost:  "$0.02",
	}
	view := s.View()
	if !strings.Contains(view, "$0.02") {
		t.Errorf("expected cost in view, got: %s", view)
	}
}

func TestStatusBarQueue(t *testing.T) {
	s := statusBarModel{
		Model: "qwen3:8b",
		Mode:  "suggest",
		Queue: 3,
	}
	view := s.View()
	if !strings.Contains(view, "queue: 3") {
		t.Errorf("expected queue indicator in view, got: %s", view)
	}
}

func TestStatusBarTruncation(t *testing.T) {
	s := statusBarModel{
		Model: "very-long-model-name-that-should-be-truncated-when-the-terminal-is-narrow",
		Mode:  "suggest",
		Width: 20,
	}
	view := s.View()
	if len(view) > 30 {
		t.Errorf("expected truncated status bar for narrow width, got %d chars: %s", len(view), view)
	}
}

func TestStatusBarAllFields(t *testing.T) {
	s := statusBarModel{
		Model:  "qwen3:8b",
		Mode:   "auto",
		Tokens: 5000,
		Cost:   "$0.12",
		Width:  80,
	}
	view := s.View()
	if !strings.Contains(view, "qwen3:8b") {
		t.Errorf("expected model name in view, got: %s", view)
	}
	if !strings.Contains(view, "5.0k") {
		t.Errorf("expected token count in view, got: %s", view)
	}
	if !strings.Contains(view, "$0.12") {
		t.Errorf("expected cost in view, got: %s", view)
	}
}
