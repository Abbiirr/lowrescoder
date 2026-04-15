package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
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
	dir := filepath.Join(home, ".autocode")
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

// historyEntry is a frecency-ranked prompt history entry.
type historyEntry struct {
	Text  string
	Count int   // number of times used
	Last  int64 // unix timestamp of last use
}

// frecencyScore computes the frecency ranking score.
func frecencyScore(entry historyEntry) int {
	return entry.Count*10 + int((entry.Last % 100000))
}

// sortByFrecency sorts promptHistory entries by frecency score (highest first).
func sortByFrecency(entries []historyEntry) []historyEntry {
	sorted := make([]historyEntry, len(entries))
	copy(sorted, entries)
	for i := 0; i < len(sorted)-1; i++ {
		for j := i + 1; j < len(sorted); j++ {
			if frecencyScore(sorted[j]) > frecencyScore(sorted[i]) {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}
	return sorted
}

// historyAddFrecency adds or updates a frecency history entry.
func historyAddFrecency(entries []historyEntry, text string) []historyEntry {
	now := time.Now().Unix()
	for i := range entries {
		if entries[i].Text == text {
			entries[i].Count++
			entries[i].Last = now
			return entries
		}
	}
	entries = append(entries, historyEntry{Text: text, Count: 1, Last: now})
	return entries
}

// loadFrecencyHistory reads frecency-ranked history from JSONL file.
func loadFrecencyHistory(path string) []historyEntry {
	f, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer f.Close()

	var entries []historyEntry
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var entry historyEntry
		if err := parseHistoryEntry(line, &entry); err == nil {
			entries = append(entries, entry)
		}
	}
	return entries
}

// saveFrecencyHistory writes frecency history to JSONL file.
func saveFrecencyHistory(path string, entries []historyEntry) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	writer := bufio.NewWriter(f)
	for _, entry := range entries {
		writer.WriteString(formatHistoryEntry(entry) + "\n")
	}
	return writer.Flush()
}

func parseHistoryEntry(line string, entry *historyEntry) error {
	parts := strings.SplitN(line, "|", 3)
	if len(parts) != 3 {
		return fmt.Errorf("invalid history entry format")
	}
	count, err := strconv.Atoi(parts[0])
	if err != nil {
		return err
	}
	last, err := strconv.ParseInt(parts[1], 10, 64)
	if err != nil {
		return err
	}
	entry.Count = count
	entry.Last = last
	entry.Text = parts[2]
	return nil
}

func formatHistoryEntry(entry historyEntry) string {
	return fmt.Sprintf("%d|%d|%s", entry.Count, entry.Last, entry.Text)
}
