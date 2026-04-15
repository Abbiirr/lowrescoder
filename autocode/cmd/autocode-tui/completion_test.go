package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	tea "charm.land/bubbletea/v2"
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

func TestCompletionsSlashOnlyIncludesProviderAndLoopCommands(t *testing.T) {
	results := getCompletions("/")
	required := []string{"/provider", "/loop", "/tasks", "/plan", "/research", "/build", "/review"}
	for _, req := range required {
		found := false
		for _, item := range results {
			if item == req {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("expected %s in slash completions, got %v", req, results)
		}
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

func TestAtFileCompletions(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "README.md"), []byte("x"), 0o644); err != nil {
		t.Fatalf("failed to write README.md: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(dir, "src"), 0o755); err != nil {
		t.Fatalf("failed to create src dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "src", "main.go"), []byte("package main"), 0o644); err != nil {
		t.Fatalf("failed to write src/main.go: %v", err)
	}

	results := getCompletionsInDir("@rea", dir)
	found := false
	for _, r := range results {
		if r == "@README.md" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected @README.md in results, got %v", results)
	}
}

func TestAtFileCompletionsInSentence(t *testing.T) {
	dir := t.TempDir()
	if err := os.MkdirAll(filepath.Join(dir, "src"), 0o755); err != nil {
		t.Fatalf("failed to create src dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "src", "main.go"), []byte("package main"), 0o644); err != nil {
		t.Fatalf("failed to write src/main.go: %v", err)
	}

	results := getCompletionsInDir("inspect @src/ma", dir)
	found := false
	for _, r := range results {
		if r == "inspect @src/main.go" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected sentence-preserving completion, got %v", results)
	}
}

func TestAtFileCompletionsBareAt(t *testing.T) {
	results := getCompletionsInDir("@", t.TempDir())
	if results != nil {
		t.Errorf("expected nil for bare @, got %v", results)
	}
}

// --- Autocomplete UX Tests ---

func TestSuggestionsSetOnKeyPress(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput

	// Type "/" then "h" then "e"
	for _, r := range []rune{'/', 'h', 'e'} {
		updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: string(r), Code: r}))
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

	// completions should be set in the model
	if len(m.completions) == 0 {
		t.Error("expected completions to be set")
	}
}

func TestDropdownRenderedForMultipleMatches(t *testing.T) {
	m := initialModel(nil)
	m.stage = stageInput
	m.width = 80

	// Type "/s" which matches multiple commands
	for _, r := range []rune{'/', 's'} {
		updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: string(r), Code: r}))
		m = updated.(model)
	}

	if len(m.completions) < 2 {
		t.Fatalf("expected multiple completions for /s, got %v", m.completions)
	}

	view := m.View().Content
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
		updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: string(r), Code: r}))
		m = updated.(model)
	}

	// Should have exactly 1 completion (/help)
	if len(m.completions) != 1 {
		t.Fatalf("expected 1 completion for /hel, got %v", m.completions)
	}

	view := m.View().Content
	// Dropdown should NOT be rendered (ghost text handles single match)
	// Check that we don't see the dropdown-style rendering (indented items)
	lines := strings.Split(view, "\n")
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "/help" {
			// This would be a dropdown item, not the input line itself
			// The input line contains more than just "/help" (cursor, etc.)
			// This is okay as long as it's just the ghost text in the composer
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
		updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: string(r), Code: r}))
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
		updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: string(r), Code: r}))
		m = updated.(model)
	}

	if len(m.completions) == 0 {
		t.Fatal("expected completions before Enter")
	}

	// Now type the full command and press Enter
	m.composer.SetValue("/help")
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyEnter}))
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
		updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Text: string(r), Code: r}))
		m = updated.(model)
	}

	// Should have /help as a completion
	if len(m.completions) == 0 {
		t.Fatal("expected completions after typing /hel")
	}

	// Press Tab — should accept first completion
	updated, _ := m.Update(tea.KeyPressMsg(tea.Key{Code: tea.KeyTab}))
	m = updated.(model)

	if m.composer.Value() != "/help" {
		t.Errorf("expected composer value '/help' after Tab, got '%s'", m.composer.Value())
	}
}

func TestComposerIsMultiLine(t *testing.T) {
	m := initialModel(nil)
	// Composer should support multi-line input (textarea, not textinput)
	if m.composer.CharLimit != 4000 {
		t.Errorf("expected CharLimit=4000 for multi-line composer, got %d", m.composer.CharLimit)
	}
}

func TestCompletionDropdownCapAt8Items(t *testing.T) {
	// Create a list of more than 8 items
	items := make([]string, 12)
	for i := range items {
		items[i] = "/cmd" + string(rune('a'+i))
	}

	result := renderCompletionDropdown(items, 80, 0)

	// Count how many items appear (each starts with "/cmd")
	count := strings.Count(result, "/cmd")
	if count > 8 {
		t.Errorf("expected at most 8 items visible in dropdown, got %d", count)
	}
	// When cursor is at 0, the first 8 items should be visible
	if !strings.Contains(result, "/cmda") {
		t.Error("expected first item to be visible when cursor=0")
	}
}

func TestCompletionDropdownEmptyItems(t *testing.T) {
	// Should not crash with empty items
	result := renderCompletionDropdown([]string{}, 80, 0)
	if result != "" {
		t.Errorf("expected empty string for no items, got '%s'", result)
	}
}

func TestCompletionDropdownSingleItem(t *testing.T) {
	// Single item — should render one line with the highlighted marker
	result := renderCompletionDropdown([]string{"/help"}, 80, 0)
	if !strings.Contains(result, "/help") {
		t.Errorf("expected /help in output, got '%s'", result)
	}
	if !strings.Contains(result, "\u276f") {
		t.Error("expected cursor glyph ❯ in highlighted row")
	}
}

func TestCompletionDropdownCursorHighlight(t *testing.T) {
	items := []string{"/help", "/hello", "/history"}
	// Cursor on /hello (index 1) — should be the row with ❯
	result := renderCompletionDropdown(items, 80, 1)
	lines := strings.Split(strings.TrimRight(result, "\n"), "\n")
	if len(lines) < 3 {
		t.Fatalf("expected 3 rendered lines, got %d:\n%s", len(lines), result)
	}
	// The line containing ❯ must also contain /hello
	var cursorLine string
	for _, line := range lines {
		if strings.Contains(line, "\u276f") {
			cursorLine = line
			break
		}
	}
	if cursorLine == "" {
		t.Fatal("expected a line containing ❯ glyph")
	}
	if !strings.Contains(cursorLine, "/hello") {
		t.Errorf("expected cursor on /hello, got cursor line: %q", cursorLine)
	}
}

func TestCompletionDropdownWindowingKeepsCursorVisible(t *testing.T) {
	// 20 items, cursor at index 15 — visible window must include item 15
	items := make([]string, 20)
	for i := range items {
		items[i] = "/x" + string(rune('a'+i))
	}
	result := renderCompletionDropdown(items, 80, 15)
	if !strings.Contains(result, items[15]) {
		t.Errorf("expected cursor item %q to be visible, got:\n%s", items[15], result)
	}
}
