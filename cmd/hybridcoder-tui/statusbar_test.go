package main

import (
	"strings"
	"testing"
)

func TestStatusBarLayerEmpty(t *testing.T) {
	s := statusBarModel{
		Model:    "qwen3:8b",
		Provider: "ollama",
		Mode:     "suggest",
	}
	view := s.View()
	if strings.Contains(view, "[L") {
		t.Errorf("expected no layer indicator when Layer is empty, got: %s", view)
	}
}

func TestStatusBarLayerL1(t *testing.T) {
	s := statusBarModel{
		Model:    "qwen3:8b",
		Provider: "ollama",
		Mode:     "suggest",
		Layer:    "[L1]",
	}
	view := s.View()
	if !strings.Contains(view, "[L1]") {
		t.Errorf("expected [L1] in status bar, got: %s", view)
	}
}

func TestStatusBarLayerL4(t *testing.T) {
	s := statusBarModel{
		Model:    "qwen3:8b",
		Provider: "ollama",
		Mode:     "suggest",
		Layer:    "[L4]",
	}
	view := s.View()
	if !strings.Contains(view, "[L4]") {
		t.Errorf("expected [L4] in status bar, got: %s", view)
	}
}

func TestStatusBarLayerL2(t *testing.T) {
	s := statusBarModel{
		Model:    "qwen3:8b",
		Provider: "ollama",
		Mode:     "suggest",
		Layer:    "[L2]",
	}
	view := s.View()
	if !strings.Contains(view, "[L2]") {
		t.Errorf("expected [L2] in status bar, got: %s", view)
	}
}

func TestStatusBarAllFields(t *testing.T) {
	s := statusBarModel{
		Model:    "qwen3:8b",
		Provider: "ollama",
		Mode:     "suggest",
		Layer:    "[L1]",
		Tokens:   1500,
		Edits:    3,
	}
	view := s.View()
	if !strings.Contains(view, "qwen3:8b") {
		t.Errorf("expected model name in view, got: %s", view)
	}
	if !strings.Contains(view, "[L1]") {
		t.Errorf("expected [L1] in view, got: %s", view)
	}
	if !strings.Contains(view, "1.5k") {
		t.Errorf("expected token count in view, got: %s", view)
	}
}
