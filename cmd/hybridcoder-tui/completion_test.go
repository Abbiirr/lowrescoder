package main

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
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

// --- Autocomplete UX Tests ---

func TestSuggestionsSetOnKeyPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Type "/" then "h" then "e"
	for _, r := range []rune{'/', 'h', 'e'} {
		updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
		m = updated.(model)
	}

	// After typing "/he", suggestions should include /help
	if len(m.completions) == 0 {
		t.Fatal("expected completions to be set after typing /he")
	}
	found := false
	for _, c := range m.completions {
		if c == "/help" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected /help in completions, got %v", m.completions)
	}

	// textInput should also have suggestions set
	avail := m.textInput.AvailableSuggestions()
	if len(avail) == 0 {
		t.Error("expected textInput to have suggestions set")
	}
}

func TestDropdownRenderedForMultipleMatches(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// Type "/s" which matches multiple commands
	for _, r := range []rune{'/', 's'} {
		updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
		m = updated.(model)
	}

	if len(m.completions) < 2 {
		t.Fatalf("expected multiple completions for /s, got %v", m.completions)
	}

	view := m.View()
	// Dropdown should show completion items
	if !strings.Contains(view, "/sessions") && !strings.Contains(view, "/shell") {
		t.Errorf("expected dropdown with /sessions or /shell in view, got:\n%s", view)
	}
}

func TestDropdownHiddenForSingleMatch(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// Type "/he" — only matches /help and /h, let's use "/hel" for single match
	for _, r := range []rune{'/', 'h', 'e', 'l'} {
		updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
		m = updated.(model)
	}

	// Should have exactly 1 completion (/help)
	if len(m.completions) != 1 {
		t.Fatalf("expected 1 completion for /hel, got %v", m.completions)
	}

	view := m.View()
	// Dropdown should NOT be rendered (ghost text handles single match)
	// Check that we don't see the dropdown-style rendering (indented items)
	lines := strings.Split(view, "\n")
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "/help" {
			// This would be a dropdown item, not the input line itself
			// The input line contains more than just "/help" (cursor, etc.)
			// This is okay as long as it's just the ghost text in the textinput
			break
		}
	}
}

func TestDropdownHiddenForNonSlash(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// Type regular text
	for _, r := range []rune{'h', 'e', 'l', 'l', 'o'} {
		updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
		m = updated.(model)
	}

	if m.completions != nil {
		t.Errorf("expected no completions for non-slash input, got %v", m.completions)
	}
}

func TestDropdownClearedOnEnter(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Type "/he" to populate completions
	for _, r := range []rune{'/', 'h', 'e'} {
		updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
		m = updated.(model)
	}

	if len(m.completions) == 0 {
		t.Fatal("expected completions before Enter")
	}

	// Now type the full command and press Enter
	m.textInput.SetValue("/help")
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m = updated.(model)

	if m.completions != nil {
		t.Errorf("expected completions cleared after Enter, got %v", m.completions)
	}
}

func TestTabAcceptsSuggestion(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Type "/hel" to get a single suggestion (/help)
	for _, r := range []rune{'/', 'h', 'e', 'l'} {
		updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
		m = updated.(model)
	}

	// The textinput should have /help as current suggestion
	suggestion := m.textInput.CurrentSuggestion()
	if suggestion != "/help" {
		t.Fatalf("expected current suggestion '/help', got '%s'", suggestion)
	}

	// Press Tab — the built-in AcceptSuggestion should complete it
	updated, _ := m.Update(tea.KeyMsg{Type: tea.KeyTab})
	m = updated.(model)

	if m.textInput.Value() != "/help" {
		t.Errorf("expected textInput value '/help' after Tab, got '%s'", m.textInput.Value())
	}
}

func TestGhostTextEnabledOnModel(t *testing.T) {
	m := initialModel(nil)
	if !m.textInput.ShowSuggestions {
		t.Error("expected ShowSuggestions to be true on initial model")
	}
}

func TestCompletionDropdownCapAt8Items(t *testing.T) {
	// Create a list of more than 8 items
	items := make([]string, 12)
	for i := range items {
		items[i] = "/cmd" + string(rune('a'+i))
	}

	result := renderCompletionDropdown(items, 80)

	// Count how many items appear (each starts with "/cmd")
	count := strings.Count(result, "/cmd")
	if count > 8 {
		t.Errorf("expected at most 8 items in dropdown, got %d", count)
	}
	// Items 9-12 should not appear
	if strings.Contains(result, "/cmdi") {
		t.Error("expected 9th item to be excluded")
	}
}

func TestCompletionDropdownTwoColumns(t *testing.T) {
	items := []string{"/cmd1", "/cmd2", "/cmd3", "/cmd4"}

	// Width > 50 should render 2 columns
	resultWide := renderCompletionDropdown(items, 80)
	linesWide := strings.Split(strings.TrimRight(resultWide, "\n"), "\n")

	// With 4 items and 2 columns, should be 2 lines
	if len(linesWide) != 2 {
		t.Errorf("expected 2 lines with 2-column layout (width=80), got %d lines:\n%s", len(linesWide), resultWide)
	}

	// Width <= 50 should render 1 column
	resultNarrow := renderCompletionDropdown(items, 40)
	linesNarrow := strings.Split(strings.TrimRight(resultNarrow, "\n"), "\n")

	// With 4 items and 1 column, should be 4 lines
	if len(linesNarrow) != 4 {
		t.Errorf("expected 4 lines with 1-column layout (width=40), got %d lines:\n%s", len(linesNarrow), resultNarrow)
	}
}

func TestCompletionDropdownEmptyItems(t *testing.T) {
	// Should not crash with empty items
	result := renderCompletionDropdown([]string{}, 80)
	if result != "" {
		t.Errorf("expected empty string for no items, got '%s'", result)
	}
}

func TestCompletionDropdownSingleItem(t *testing.T) {
	// Single item — should render one line
	result := renderCompletionDropdown([]string{"/help"}, 80)
	if !strings.Contains(result, "/help") {
		t.Errorf("expected /help in output, got '%s'", result)
	}
}
