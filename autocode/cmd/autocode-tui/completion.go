package main

import (
	"io/fs"
	"path/filepath"
	"sort"
	"strings"

	"github.com/sahilm/fuzzy"
)

var completionSkipDirs = map[string]bool{
	".git":          true,
	"__pycache__":   true,
	"node_modules":  true,
	".venv":         true,
	".mypy_cache":   true,
	".pytest_cache": true,
}

// getCompletions returns completions for slash commands and @file references.
func getCompletions(partial string) []string {
	return getCompletionsInDir(partial, ".")
}

// getCompletionsInDir is testable completion logic with explicit project root.
func getCompletionsInDir(partial string, projectRoot string) []string {
	if strings.HasPrefix(partial, "/") {
		return getSlashCompletions(partial)
	}
	if strings.Contains(partial, "@") {
		return getAtFileCompletions(partial, projectRoot)
	}
	return nil
}

// getSlashCompletions returns completions for a partial slash command.
// Prefix match first, fuzzy fallback via sahilm/fuzzy.
func getSlashCompletions(partial string) []string {
	if !strings.HasPrefix(partial, "/") || strings.Contains(partial, " ") {
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

// getAtFileCompletions returns full-line suggestions for the last @token.
func getAtFileCompletions(input string, projectRoot string) []string {
	atPos := strings.LastIndex(input, "@")
	if atPos == -1 {
		return nil
	}

	query := input[atPos+1:]
	// Bare @ has no useful completion signal.
	if query == "" {
		return nil
	}
	// We only complete the active token up to cursor/end.
	if strings.ContainsAny(query, " \t\n") {
		return nil
	}

	normalizedQuery := strings.ToLower(strings.ReplaceAll(query, "\\", "/"))
	prefix := input[:atPos+1]

	root, err := filepath.Abs(projectRoot)
	if err != nil {
		root = projectRoot
	}

	type fileMatch struct {
		index int
		path  string
	}
	matches := make([]fileMatch, 0, 32)

	_ = filepath.WalkDir(root, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return nil
		}
		if d.IsDir() {
			if completionSkipDirs[d.Name()] {
				return filepath.SkipDir
			}
			return nil
		}

		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			return nil
		}
		rel = filepath.ToSlash(rel)
		relLower := strings.ToLower(rel)

		idx := strings.Index(relLower, normalizedQuery)
		if idx >= 0 {
			matches = append(matches, fileMatch{
				index: idx,
				path:  rel,
			})
		}
		return nil
	})

	if len(matches) == 0 {
		return nil
	}

	sort.Slice(matches, func(i, j int) bool {
		if matches[i].index != matches[j].index {
			return matches[i].index < matches[j].index
		}
		if len(matches[i].path) != len(matches[j].path) {
			return len(matches[i].path) < len(matches[j].path)
		}
		return matches[i].path < matches[j].path
	})

	const maxResults = 10
	if len(matches) > maxResults {
		matches = matches[:maxResults]
	}

	results := make([]string, len(matches))
	for i, m := range matches {
		// Keep the entire input prefix so accepting suggestion doesn't clobber text.
		results[i] = prefix + m.path
	}
	return results
}
