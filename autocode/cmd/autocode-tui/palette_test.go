package main

import "testing"

func containsCommand(commands []string, want string) bool {
	for _, cmd := range commands {
		if cmd == want {
			return true
		}
	}
	return false
}

func TestFilterPaletteCommandsIncludesRecentSessionCommands(t *testing.T) {
	matches := filterPaletteCommands("")

	for _, want := range []string{"/undo", "/diff", "/cost", "/export"} {
		if !containsCommand(matches, want) {
			t.Fatalf("expected palette entries to include %s", want)
		}
	}
}
