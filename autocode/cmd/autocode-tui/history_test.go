package main

import (
	"os"
	"path/filepath"
	"testing"
)

func newTestHistory(t *testing.T) *History {
	t.Helper()
	dir := t.TempDir()
	return &History{
		path:    filepath.Join(dir, "test_history"),
		maxSize: 5,
	}
}

func TestHistoryAdd(t *testing.T) {
	h := newTestHistory(t)
	h.Add("hello")
	h.Add("world")

	if len(h.entries) != 2 {
		t.Errorf("expected 2 entries, got %d", len(h.entries))
	}
	if h.entries[0] != "hello" {
		t.Errorf("expected first entry='hello', got '%s'", h.entries[0])
	}
	if h.entries[1] != "world" {
		t.Errorf("expected second entry='world', got '%s'", h.entries[1])
	}
}

func TestHistoryAddEmpty(t *testing.T) {
	h := newTestHistory(t)
	h.Add("")
	h.Add("   ")

	if len(h.entries) != 0 {
		t.Errorf("expected 0 entries for empty input, got %d", len(h.entries))
	}
}

func TestHistoryAddDeduplicate(t *testing.T) {
	h := newTestHistory(t)
	h.Add("hello")
	h.Add("hello")

	if len(h.entries) != 1 {
		t.Errorf("expected 1 entry after dedup, got %d", len(h.entries))
	}
}

func TestHistoryAddNonConsecutiveDuplicates(t *testing.T) {
	h := newTestHistory(t)
	h.Add("hello")
	h.Add("world")
	h.Add("hello")

	if len(h.entries) != 3 {
		t.Errorf("expected 3 entries (non-consecutive dupes allowed), got %d", len(h.entries))
	}
}

func TestHistoryMaxSize(t *testing.T) {
	h := newTestHistory(t)
	h.maxSize = 3

	h.Add("a")
	h.Add("b")
	h.Add("c")
	h.Add("d")

	if len(h.entries) != 3 {
		t.Errorf("expected 3 entries (max size), got %d", len(h.entries))
	}
	if h.entries[0] != "b" {
		t.Errorf("expected oldest remaining='b', got '%s'", h.entries[0])
	}
}

func TestHistoryPrevious(t *testing.T) {
	h := newTestHistory(t)
	h.Add("first")
	h.Add("second")
	h.Add("third")

	// Cursor starts at end (len(entries))
	prev := h.Previous()
	if prev != "third" {
		t.Errorf("expected 'third', got '%s'", prev)
	}

	prev = h.Previous()
	if prev != "second" {
		t.Errorf("expected 'second', got '%s'", prev)
	}

	prev = h.Previous()
	if prev != "first" {
		t.Errorf("expected 'first', got '%s'", prev)
	}

	// Already at beginning, should stay at first
	prev = h.Previous()
	if prev != "first" {
		t.Errorf("expected 'first' (at beginning), got '%s'", prev)
	}
}

func TestHistoryNext(t *testing.T) {
	h := newTestHistory(t)
	h.Add("first")
	h.Add("second")

	// Go back
	h.Previous()
	h.Previous()

	// Go forward
	next := h.Next()
	if next != "second" {
		t.Errorf("expected 'second', got '%s'", next)
	}

	// Past end should return empty
	next = h.Next()
	if next != "" {
		t.Errorf("expected empty string at end, got '%s'", next)
	}
}

func TestHistoryPreviousEmpty(t *testing.T) {
	h := newTestHistory(t)
	prev := h.Previous()
	if prev != "" {
		t.Errorf("expected empty string for empty history, got '%s'", prev)
	}
}

func TestHistoryNextEmpty(t *testing.T) {
	h := newTestHistory(t)
	next := h.Next()
	if next != "" {
		t.Errorf("expected empty string for empty history, got '%s'", next)
	}
}

func TestHistoryPersistence(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "test_history")

	// Write history
	h1 := &History{path: path, maxSize: 100}
	h1.Add("persistent1")
	h1.Add("persistent2")

	// Load into new History
	h2 := &History{path: path, maxSize: 100}
	h2.load()

	if len(h2.entries) != 2 {
		t.Errorf("expected 2 entries after load, got %d", len(h2.entries))
	}
	if h2.entries[0] != "persistent1" {
		t.Errorf("expected 'persistent1', got '%s'", h2.entries[0])
	}
	if h2.entries[1] != "persistent2" {
		t.Errorf("expected 'persistent2', got '%s'", h2.entries[1])
	}
}

func TestHistoryLoadNonExistentFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "nonexistent")

	h := &History{path: path, maxSize: 100}
	h.load()

	if len(h.entries) != 0 {
		t.Errorf("expected 0 entries for nonexistent file, got %d", len(h.entries))
	}
}

func TestHistorySaveCreatesFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "new_history")

	h := &History{path: path, maxSize: 100}
	h.Add("test")

	// Verify file exists
	if _, err := os.Stat(path); os.IsNotExist(err) {
		t.Error("expected history file to be created")
	}
}

func TestHistoryCursorResetOnAdd(t *testing.T) {
	h := newTestHistory(t)
	h.Add("first")
	h.Add("second")

	// Navigate back
	h.Previous()

	// Add new entry should reset cursor
	h.Add("third")

	if h.cursor != len(h.entries) {
		t.Errorf("expected cursor=%d after Add, got %d", len(h.entries), h.cursor)
	}
}

func TestHistoryLoadMaxSize(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "big_history")

	// Write more entries than maxSize
	h1 := &History{path: path, maxSize: 100}
	for i := 0; i < 10; i++ {
		h1.entries = append(h1.entries, "entry")
	}
	h1.save()

	// Load with small maxSize
	h2 := &History{path: path, maxSize: 3}
	h2.load()

	if len(h2.entries) != 3 {
		t.Errorf("expected 3 entries (maxSize), got %d", len(h2.entries))
	}
}
