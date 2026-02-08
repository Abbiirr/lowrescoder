# HybridCoder Test Suite — Master Catalog

## How to Test

### Prerequisites

- **Go 1.21+** installed (for Go TUI tests)
- **Python 3.11+** with `uv` package manager (for Python backend tests)
- All dependencies installed: `go mod tidy` in `cmd/hybridcoder-tui/` and `uv sync` at project root

### Running All Tests

```bash
# Quick: run everything
make test-all

# Or step by step:

# 1. Go TUI tests (fast, ~2s)
cd cmd/hybridcoder-tui && go test ./... -v -count=1

# 2. Python backend + unit tests
uv run pytest tests/ -v --cov=src/hybridcoder

# 3. Lint
uv run ruff check src/ tests/
```

### Running Individual Test Categories

```bash
# Go: Only view tests
cd cmd/hybridcoder-tui && go test -run "TestView" -v

# Go: Only display pipeline tests
cd cmd/hybridcoder-tui && go test -run "TestTokens|TestStreamBuf|TestDone" -v

# Go: Only backend IPC tests
cd cmd/hybridcoder-tui && go test -run "TestDispatch|TestRoute|TestSend|TestMalformed" -v

# Go: Only command parsing tests
cd cmd/hybridcoder-tui && go test -run "TestParseCommand|TestKnownCommands|TestSlashCommand" -v

# Go: Only ask-user tests
cd cmd/hybridcoder-tui && go test -run "TestAskUser|TestEnterAskUser|TestRenderAskUser" -v

# Go: Only e2e flow tests
cd cmd/hybridcoder-tui && go test -run "TestFull" -v

# Go: Only approval tests
cd cmd/hybridcoder-tui && go test -run "TestApproval|TestEnterApproval" -v

# Go: Only completion/autocomplete tests
cd cmd/hybridcoder-tui && go test -run "TestCompletions" -v

# Go: Only history tests
cd cmd/hybridcoder-tui && go test -run "TestHistory" -v

# Go: Only markdown tests
cd cmd/hybridcoder-tui && go test -run "TestRenderMarkdown" -v

# Python: Only backend server tests
uv run pytest tests/unit/test_backend_server.py -v

# Python: Only a specific test class
uv run pytest tests/unit/test_backend_server.py::TestCallbacks -v
```

### Running with Coverage

```bash
# Go coverage
cd cmd/hybridcoder-tui && go test ./... -coverprofile=coverage.out && go tool cover -html=coverage.out

# Python coverage
uv run pytest tests/ -v --cov=src/hybridcoder --cov-report=html
```

### Build & Run (Development)

```bash
# Windows
build.bat

# Unix/macOS
chmod +x build.sh && ./build.sh
```

### CI / Pre-commit Checklist

1. `cd cmd/hybridcoder-tui && go test ./... -count=1` — all Go tests pass
2. `uv run pytest tests/ -v` — all Python tests pass
3. `uv run ruff check src/ tests/` — no lint errors
4. `go vet ./...` in `cmd/hybridcoder-tui/` — no vet warnings

---

## Test File Index

| File | Category | Tests | Description |
|------|----------|-------|-------------|
| `cmd/hybridcoder-tui/view_test.go` | Display | ~16 | View() rendering for all stages |
| `cmd/hybridcoder-tui/update_test.go` | Core | ~45 | Update loop, display pipeline, parallel input, thinking, history |
| `cmd/hybridcoder-tui/backend_test.go` | IPC | ~13 | Backend dispatch, routing, marshal, robustness |
| `cmd/hybridcoder-tui/commands_test.go` | Commands | ~11 | Slash command parsing and handling |
| `cmd/hybridcoder-tui/askuser_test.go` | Dialog | ~15 | Ask-user stage transitions, navigation, rendering |
| `cmd/hybridcoder-tui/approval_test.go` | Dialog | 12 | Approval stage transitions, navigation, rendering |
| `cmd/hybridcoder-tui/completion_test.go` | Autocomplete | ~10 | Prefix, fuzzy, Tab completion |
| `cmd/hybridcoder-tui/e2e_test.go` | E2E | ~6 | Full message flow simulations |
| `cmd/hybridcoder-tui/protocol_test.go` | Protocol | 25 | JSON-RPC wire format marshal/unmarshal |
| `cmd/hybridcoder-tui/model_test.go` | Model | 6 | Initial state, defaults |
| `cmd/hybridcoder-tui/history_test.go` | History | 13 | Persistence, navigation, dedup |
| `cmd/hybridcoder-tui/markdown_test.go` | Rendering | 10 | Glamour markdown rendering |
| `tests/unit/test_backend_server.py` | Python | ~74 | Backend server, callbacks, protocol, dispatch |

---

## Category 1: Display Pipeline Tests (CRITICAL)

Tests that verify the token → display → scrollback pipeline.

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestTokensAppearInStreamBuf` | update_test.go | Token → tokenBuf → tick → streamBuf pipeline |
| `TestStreamBufAppearsInView` | view_test.go | streamBuf content renders in View() during stageStreaming |
| `TestDoneCommitsContentViaTeaPrintln` | update_test.go | handleDone returns tea.Println with rendered content |
| `TestDoneWithEmptyStreamBuf` | update_test.go | handleDone with no tokens still returns separator Println |
| `TestMultipleTokensAccumulate` | update_test.go | Multiple tokenMsg accumulate correctly in tokenBuf |
| `TestTickFlushesAllTokens` | update_test.go | After tick, streamBuf = all accumulated tokens |
| `TestTokensDuringStageInputIgnored` | update_test.go | Tokens received when not streaming update tokenBuf (no crash) |
| `TestStreamBufCappedAt50Lines` | view_test.go | View truncates to last 50 lines with "[N lines above]" |

## Category 2: Parallel Input Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestTextInputStaysFocusedDuringStreaming` | update_test.go | sendChat does NOT blur textInput |
| `TestTypingDuringStreaming` | update_test.go | KeyRunes updates textInput during stageStreaming |
| `TestQueueMessageDuringStreamingPreservesInput` | update_test.go | Enter queues, clears input, stays focused |
| `TestCtrlCDuringStreamingCancels` | update_test.go | Ctrl+C clears queue during streaming |
| `TestEscapeDuringStreamingCancels` | update_test.go | Escape clears queue during streaming |
| `TestInputFocusRestoredAfterApproval` | update_test.go | textInput.Focus() after approval Enter |
| `TestInputFocusRestoredAfterApprovalDenied` | update_test.go | textInput.Focus() after approval Escape |
| `TestInputFocusRestoredAfterAskUser` | update_test.go | textInput.Focus() after ask-user Enter |

## Category 3: Thinking Token Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestThinkingTokensAccumulate` | update_test.go | Multiple backendThinkingMsg accumulate in thinkingBuf |
| `TestThinkingToggle` | update_test.go | /thinking command toggles showThinking |
| `TestThinkingResetOnDone` | update_test.go | handleDone clears thinkingBuf |
| `TestThinkingTokensAppearInViewWhenEnabled` | view_test.go | View includes thinking when showThinking=true |
| `TestThinkingTokensHiddenByDefault` | view_test.go | View excludes thinking when showThinking=false |

## Category 4: Backend IPC Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestDispatchNotificationToken` | backend_test.go | on_token notification → backendTokenMsg |
| `TestDispatchNotificationThinking` | backend_test.go | on_thinking notification → backendThinkingMsg |
| `TestDispatchNotificationToolCall` | backend_test.go | on_tool_call notification → backendToolCallMsg |
| `TestDispatchNotificationDone` | backend_test.go | on_done notification → backendDoneMsg with token counts |
| `TestDispatchNotificationError` | backend_test.go | on_error notification → backendErrorMsg |
| `TestDispatchNotificationStatus` | backend_test.go | on_status notification → backendStatusMsg |
| `TestRouteRequestApproval` | backend_test.go | on_tool_request (with ID) → backendApprovalRequestMsg |
| `TestRouteRequestAskUser` | backend_test.go | on_ask_user (with ID) → backendAskUserRequestMsg |
| `TestSendRequestMarshal` | backend_test.go | SendRequest produces valid JSON-RPC with incrementing ID |
| `TestSendResponseMarshal` | backend_test.go | SendResponse produces valid JSON-RPC response |
| `TestMalformedJSONIgnored` | backend_test.go | Invalid JSON lines don't crash |
| `TestEmptyLineIgnored` | backend_test.go | Empty lines are skipped |
| `TestWriteChFullDropsMessage` | backend_test.go | When writeCh is full, message is dropped |

## Category 5: Command Parsing Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestParseCommandSimple` | commands_test.go | `/exit` → cmd="exit", args="" |
| `TestParseCommandWithArgs` | commands_test.go | `/model qwen3:8b` → cmd="model", args="qwen3:8b" |
| `TestParseCommandWithMultipleArgs` | commands_test.go | `/resume abc123` → cmd="resume", args="abc123" |
| `TestParseCommandLeadingSlash` | commands_test.go | Leading `/` is stripped |
| `TestParseCommandNoSlash` | commands_test.go | `hello` → cmd="", args="hello" |
| `TestParseCommandEmptyAfterSlash` | commands_test.go | `/` → cmd="", args="" |
| `TestKnownCommandsList` | commands_test.go | knownCommands contains all expected commands |
| `TestSlashCommandExitQuitsApp` | commands_test.go | handleSlashCommand("/exit") sets quitting=true |
| `TestSlashCommandClearReturnsCmd` | commands_test.go | handleSlashCommand("/clear") returns ClearScreen |
| `TestSlashCommandThinkingToggles` | commands_test.go | handleSlashCommand("/thinking") toggles showThinking |
| `TestSlashCommandDelegatesToBackend` | commands_test.go | Unknown commands call backend.SendRequest |

## Category 6: Ask-User Dialog Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestEnterAskUserWithOptions` | askuser_test.go | Sets stage, blurs textInput, stores options |
| `TestEnterAskUserFreeText` | askuser_test.go | Sets stage, focuses textInput, sets placeholder |
| `TestEnterAskUserMixed` | askuser_test.go | AllowText=true with options focuses textInput |
| `TestAskUserArrowNavigation` | askuser_test.go | Up/Down arrow keys cycle through options |
| `TestAskUserArrowWrap` | askuser_test.go | Wraps top→bottom and bottom→top |
| `TestAskUserEnterSelectsOption` | askuser_test.go | Enter sends selected option |
| `TestAskUserEnterPrefersTypedText` | askuser_test.go | Typed text overrides selected option when allowText |
| `TestAskUserEscapeDefaultsFirst` | askuser_test.go | Escape selects first option as default |
| `TestAskUserEscapeEmptyOptions` | askuser_test.go | Escape with no options sends empty string |
| `TestAskUserFocusRestored` | askuser_test.go | After answer, textInput refocused |
| `TestRenderAskUserWithOptions` | askuser_test.go | Renders question + numbered options + cursor |
| `TestRenderAskUserFreeText` | askuser_test.go | Renders question + textInput |
| `TestAskUserMultiStageFlow` | askuser_test.go | ask-user → answer → back to streaming |
| `TestAskUserSelectionHighlights` | askuser_test.go | Selected option shows cursor indicator |
| `TestAskUserTypingDuringOptions` | askuser_test.go | Can type while options shown (allowText=true) |

## Category 7: Python Backend Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `test_on_chunk_emits_token_notification` | test_backend_server.py | _on_chunk("hello") → on_token |
| `test_on_thinking_emits_thinking_notification` | test_backend_server.py | _on_thinking_chunk → on_thinking |
| `test_thinking_callback_none_when_disabled` | test_backend_server.py | on_thinking=None when disabled |
| `test_thinking_callback_set_when_enabled` | test_backend_server.py | on_thinking=callback when enabled |
| `test_on_done_emits_done_notification` | test_backend_server.py | on_done sent with token counts |
| `test_approval_callback_session_approve` | test_backend_server.py | Session approve adds tool |
| `test_approval_callback_auto_approved` | test_backend_server.py | Pre-approved tool returns True |
| `test_ask_user_callback_returns_answer` | test_backend_server.py | Normal path returns answer |
| `test_config_set_valid_key` | test_backend_server.py | Valid key updates config |
| `test_emit_status_includes_all_fields` | test_backend_server.py | Status has model, provider, mode, session_id |

## Category 8: Autocomplete Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestCompletionsPrefixMatch` | completion_test.go | `/he` → includes `/help` |
| `TestCompletionsExactMatch` | completion_test.go | `/help` → exact match |
| `TestCompletionsNoPrefix` | completion_test.go | Non-slash returns nil |
| `TestCompletionsSlashOnly` | completion_test.go | `/` returns all commands |
| `TestCompletionsFuzzyFallback` | completion_test.go | `/hlp` → fuzzy match to `/help` |
| `TestCompletionsMultiplePrefixMatches` | completion_test.go | `/s` → multiple matches |
| `TestSlashCommandTabCompletion` | completion_test.go | Tab key triggers completion in update loop |

## Category 9: History & Queue Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestUpArrowNavigatesHistory` | update_test.go | Up arrow loads previous command |
| `TestDownArrowNavigatesHistoryForward` | update_test.go | Down arrow returns to next entry |
| `TestCtrlDQuitsFromInput` | update_test.go | Ctrl+D sets quitting=true |
| `TestCtrlDQuitsFromStreaming` | update_test.go | Ctrl+D handled during streaming |
| `TestQueueCountUpdatesInStatusBar` | update_test.go | Queue count reflected in status bar |

## Category 10: End-to-End Flow Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestFullChatFlow` | e2e_test.go | Input → tokens → tick → done → Println |
| `TestFullChatFlowWithToolCall` | e2e_test.go | Tool call appears during streaming |
| `TestFullApprovalFlow` | e2e_test.go | Approval prompt → approve → streaming resumes |
| `TestFullCancelFlow` | e2e_test.go | Cancel during streaming clears queue |
| `TestFullQueueFlow` | e2e_test.go | Type during streaming → queue → drain after done |
| `TestFullThinkingFlow` | e2e_test.go | Toggle thinking → thinking tokens visible in View |

---

## Known Bugs Under Test

### Bug 1: Responses Not Displayed (CRITICAL)
- **Test**: `TestDoneCommitsContentViaTeaPrintln` + `TestFullChatFlow`
- **Verifies**: handleDone with non-empty streamBuf returns non-nil tea.Cmd batch containing tea.Println

### Bug 2: Thinking Tokens Not Visible
- **Test**: `TestThinkingTokensAppearInViewWhenEnabled` + `TestFullThinkingFlow`
- **Verifies**: /thinking toggle works and thinking tokens appear in View()

### Bug 3: Parallel Input Broken (FIXED — regression test)
- **Test**: `TestTextInputStaysFocusedDuringStreaming`
- **Verifies**: sendChat() does NOT call textInput.Blur()
