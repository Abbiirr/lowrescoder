package main

import (
	"bufio"
	"os"
	"path/filepath"
	"strings"
)

// History manages command history with persistence.
type History struct {
	entries []string
	cursor  int
	path    string
	maxSize int
}

var globalHistory *History

func init() {
	home, err := os.UserHomeDir()
	if err != nil {
		home = "."
	}
	dir := filepath.Join(home, ".hybridcoder")
	_ = os.MkdirAll(dir, 0o755)
	globalHistory = &History{
		path:    filepath.Join(dir, "go_history"),
		maxSize: 1000,
	}
	globalHistory.load()
}

// load reads history from file.
func (h *History) load() {
	f, err := os.Open(h.path)
	if err != nil {
		return
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" {
			h.entries = append(h.entries, line)
		}
	}

	// Enforce max size
	if len(h.entries) > h.maxSize {
		h.entries = h.entries[len(h.entries)-h.maxSize:]
	}
	h.cursor = len(h.entries)
}

// save writes history to file.
func (h *History) save() {
	f, err := os.Create(h.path)
	if err != nil {
		return
	}
	defer f.Close()

	writer := bufio.NewWriter(f)
	for _, entry := range h.entries {
		writer.WriteString(entry + "\n")
	}
	writer.Flush()
}

// Add appends a new entry and saves.
func (h *History) Add(text string) {
	text = strings.TrimSpace(text)
	if text == "" {
		return
	}

	// Deduplicate last entry
	if len(h.entries) > 0 && h.entries[len(h.entries)-1] == text {
		h.cursor = len(h.entries)
		return
	}

	h.entries = append(h.entries, text)

	// Enforce max size
	if len(h.entries) > h.maxSize {
		h.entries = h.entries[len(h.entries)-h.maxSize:]
	}

	h.cursor = len(h.entries)
	h.save()
}

// Previous returns the previous history entry (moves cursor up).
func (h *History) Previous() string {
	if len(h.entries) == 0 {
		return ""
	}
	if h.cursor > 0 {
		h.cursor--
	}
	return h.entries[h.cursor]
}

// Next returns the next history entry (moves cursor down).
func (h *History) Next() string {
	if len(h.entries) == 0 {
		return ""
	}
	if h.cursor < len(h.entries)-1 {
		h.cursor++
		return h.entries[h.cursor]
	}
	h.cursor = len(h.entries)
	return ""
}

// historyAdd adds to global history.
func historyAdd(text string) {
	if globalHistory != nil {
		globalHistory.Add(text)
	}
}

// historyPrevious navigates global history up.
func historyPrevious() string {
	if globalHistory != nil {
		return globalHistory.Previous()
	}
	return ""
}

// historyNext navigates global history down.
func historyNext() string {
	if globalHistory != nil {
		return globalHistory.Next()
	}
	return ""
}
