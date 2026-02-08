package main

import (
	"testing"
)

func TestCompletionsPrefixMatch(t *testing.T) {
	results := getCompletions("/he")
	if len(results) == 0 {
		t.Fatal("expected at least one completion for /he")
	}
	found := false
	for _, r := range results {
		if r == "/help" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected /help in results, got %v", results)
	}
}

func TestCompletionsExactMatch(t *testing.T) {
	results := getCompletions("/help")
	if len(results) == 0 {
		t.Fatal("expected at least one completion for /help")
	}
	if results[0] != "/help" {
		t.Errorf("expected first result to be /help, got %s", results[0])
	}
}

func TestCompletionsNoPrefix(t *testing.T) {
	results := getCompletions("hello")
	if results != nil {
		t.Errorf("expected nil for non-slash input, got %v", results)
	}
}

func TestCompletionsSlashOnly(t *testing.T) {
	results := getCompletions("/")
	if len(results) == 0 {
		t.Error("expected all commands for /")
	}
	if len(results) != len(knownCommands) {
		t.Errorf("expected %d commands, got %d", len(knownCommands), len(results))
	}
}

func TestCompletionsFuzzyFallback(t *testing.T) {
	// "hlp" doesn't prefix-match anything, but fuzzy matches "help"
	results := getCompletions("/hlp")
	found := false
	for _, r := range results {
		if r == "/help" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected fuzzy match to find /help for /hlp, got %v", results)
	}
}

func TestCompletionsMultiplePrefixMatches(t *testing.T) {
	// /s should match /sessions and /s (alias) and /shell and /scroll-lock
	results := getCompletions("/s")
	if len(results) < 2 {
		t.Errorf("expected multiple matches for /s, got %v", results)
	}
}

func TestCompletionsModel(t *testing.T) {
	results := getCompletions("/mo")
	found := false
	for _, r := range results {
		if r == "/model" || r == "/mode" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected /model or /mode for /mo, got %v", results)
	}
}

func TestCompletionsClear(t *testing.T) {
	results := getCompletions("/cl")
	found := false
	for _, r := range results {
		if r == "/clear" || r == "/cls" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected /clear or /cls for /cl, got %v", results)
	}
}

func TestCompletionsExit(t *testing.T) {
	results := getCompletions("/ex")
	found := false
	for _, r := range results {
		if r == "/exit" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected /exit for /ex, got %v", results)
	}
}

func TestCompletionsNoMatch(t *testing.T) {
	results := getCompletions("/zzzzzzzz")
	// Fuzzy might still match something, but it should be empty or very few
	// The important thing is no panic
	_ = results
}
