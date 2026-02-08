package main

import (
	"strings"

	"github.com/sahilm/fuzzy"
)

// getCompletions returns completions for a partial slash command.
// Prefix match first, fuzzy fallback via sahilm/fuzzy.
func getCompletions(partial string) []string {
	if !strings.HasPrefix(partial, "/") {
		return nil
	}

	// Exact prefix match first
	var prefixMatches []string
	for _, cmd := range knownCommands {
		if strings.HasPrefix(cmd, partial) {
			prefixMatches = append(prefixMatches, cmd)
		}
	}

	if len(prefixMatches) > 0 {
		return prefixMatches
	}

	// Fuzzy fallback (strip leading / for matching)
	query := strings.TrimPrefix(partial, "/")
	if query == "" {
		return knownCommands
	}

	// Build list of command names without /
	names := make([]string, len(knownCommands))
	for i, cmd := range knownCommands {
		names[i] = strings.TrimPrefix(cmd, "/")
	}

	matches := fuzzy.Find(query, names)
	var results []string
	for _, m := range matches {
		results = append(results, "/"+names[m.Index])
	}

	return results
}
