package main

import "strings"

// Known slash commands (must match Python CommandRouter).
var knownCommands = []string{
	"/exit", "/quit", "/q",
	"/new",
	"/sessions", "/s",
	"/resume",
	"/help", "/h", "/?",
	"/model", "/m",
	"/mode", "/permissions",
	"/compact",
	"/init",
	"/shell",
	"/copy", "/cp",
	"/freeze", "/scroll-lock",
	"/thinking", "/think",
	"/clear", "/cls",
}

// parseCommand extracts the command name and arguments from slash command text.
func parseCommand(text string) (cmd string, args string) {
	text = strings.TrimSpace(text)
	if !strings.HasPrefix(text, "/") {
		return "", text
	}

	parts := strings.SplitN(text, " ", 2)
	cmd = strings.TrimPrefix(parts[0], "/")
	if len(parts) > 1 {
		args = parts[1]
	}
	return cmd, args
}
