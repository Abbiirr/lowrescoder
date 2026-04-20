# AutoCode Test Suite — Master Catalog

> Last verified: 2026-02-08 — **275 Go tests, 0 failures** (`go test ./... -count=1`, 0.24s)

## How to Test

### Prerequisites

- **Go 1.21+** installed (for Go TUI tests)
- **Python 3.11+** with `uv` package manager (for Python backend tests)
- All dependencies installed: `go mod tidy` in `cmd/autocode-tui/` and `uv sync` at project root

### Running All Tests

```bash
# Quick: run everything
make test-all

# Or step by step:

# 1. Go TUI tests (fast, ~2s)
cd cmd/autocode-tui && go test ./... -v -count=1

# 2. Python backend + unit tests
uv run pytest tests/ -v --cov=src/autocode

# 3. Lint
uv run ruff check src/ tests/
```

### Running Individual Test Categories

```bash
# Go: Only view tests
cd cmd/autocode-tui && go test -run "TestView" -v

# Go: Only display pipeline tests
cd cmd/autocode-tui && go test -run "TestTokens|TestStreamBuf|TestDone" -v

# Go: Only backend IPC tests
cd cmd/autocode-tui && go test -run "TestDispatch|TestRoute|TestSend|TestMalformed" -v

# Go: Only command parsing tests
cd cmd/autocode-tui && go test -run "TestParseCommand|TestKnownCommands|TestSlashCommand" -v

# Go: Only ask-user tests
cd cmd/autocode-tui && go test -run "TestAskUser|TestEnterAskUser|TestRenderAskUser" -v

# Go: Only e2e flow tests
cd cmd/autocode-tui && go test -run "TestFull" -v

# Go: Only approval tests
cd cmd/autocode-tui && go test -run "TestApproval|TestEnterApproval" -v

# Go: Only completion/autocomplete tests
cd cmd/autocode-tui && go test -run "TestCompletions" -v

# Go: Only history tests
cd cmd/autocode-tui && go test -run "TestHistory" -v

# Go: Only markdown tests
cd cmd/autocode-tui && go test -run "TestRenderMarkdown" -v

# Python: Only backend server tests
uv run pytest tests/unit/test_backend_server.py -v

# Python: Only a specific test class
uv run pytest tests/unit/test_backend_server.py::TestCallbacks -v
```

### Running with Coverage

```bash
# Go coverage
cd cmd/autocode-tui && go test ./... -coverprofile=coverage.out && go tool cover -html=coverage.out

# Python coverage
uv run pytest tests/ -v --cov=src/autocode --cov-report=html
```

### Build & Run (Development)

```bash
# Windows
build.bat

# Linux
chmod +x build.sh && ./build.sh
```

### CI / Pre-commit Checklist

1. `cd cmd/autocode-tui && go test ./... -count=1` — all Go tests pass
2. `uv run pytest tests/ -v` — all Python tests pass
3. `uv run ruff check src/ tests/` — no lint errors
4. `go vet ./...` in `cmd/autocode-tui/` — no vet warnings

---

## Test File Index

| File | Category | Tests | Description |
|------|----------|-------|-------------|
| `cmd/autocode-tui/update_test.go` | Core | 71 | Update loop, display pipeline, parallel input, thinking, slash commands, /resume |
| `cmd/autocode-tui/protocol_test.go` | Protocol | 29 | JSON-RPC wire format marshal/unmarshal including session types |
| `cmd/autocode-tui/session_picker_test.go` | Session Picker | 24 | Session picker transitions, labels, navigation, selection, cancel |
| `cmd/autocode-tui/backend_test.go` | IPC | 22 | Backend dispatch, routing, marshal, robustness, SendRequestCmd |
| `cmd/autocode-tui/completion_test.go` | Autocomplete | 21 | Prefix, fuzzy, Tab, ghost text, dropdown, cap, columns |
| `cmd/autocode-tui/view_test.go` | Display | 18 | View() rendering for all stages, status bar |
| `cmd/autocode-tui/commands_test.go` | Commands | 18 | Slash command parsing and handling |
| `cmd/autocode-tui/askuser_test.go` | Dialog | 18 | Ask-user stage transitions, navigation, rendering |
| `cmd/autocode-tui/history_test.go` | History | 14 | Persistence, navigation, dedup |
| `cmd/autocode-tui/approval_test.go` | Dialog | 12 | Approval stage transitions, navigation, rendering |
| `cmd/autocode-tui/e2e_test.go` | E2E | 12 | Full message flows: chat, tools, approval, cancel, queue, resume, thinking tokens |
| `cmd/autocode-tui/markdown_test.go` | Rendering | 10 | Glamour markdown rendering |
| `cmd/autocode-tui/model_test.go` | Model | 6 | Initial state, defaults |
| | | **275** | **Go total** |
| `tests/unit/test_backend_server.py` | Python | 76 | Backend server, callbacks, protocol, dispatch |

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

## Category 11: Autocomplete UX Tests

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestSuggestionsSetOnKeyPress` | completion_test.go | After typing `/he`, textInput has suggestions set |
| `TestDropdownRenderedForMultipleMatches` | completion_test.go | View shows dropdown when >1 completion match |
| `TestDropdownHiddenForSingleMatch` | completion_test.go | No dropdown for exactly 1 match (ghost text only) |
| `TestDropdownHiddenForNonSlash` | completion_test.go | No dropdown for regular (non-slash) text |
| `TestDropdownClearedOnEnter` | completion_test.go | After Enter, completions list is cleared |
| `TestTabAcceptsSuggestion` | completion_test.go | Tab accepts the current ghost text suggestion |
| `TestGhostTextEnabledOnModel` | completion_test.go | ShowSuggestions is true on initial model |
| `TestSlashExitViaEnter` | update_test.go | Type `/exit`, Enter → quitting=true |
| `TestSlashThinkingViaEnter` | update_test.go | Type `/thinking`, Enter → showThinking toggled |
| `TestSlashCommandBackendDelegatedNoBackend` | update_test.go | Backend-delegated command shows error when backend nil |
| `TestSlashCommandClearsCompletions` | update_test.go | Completions cleared after slash command execution |
| `TestUpdateCompletionsForSlashInput` | update_test.go | updateCompletions() populates for `/he` |
| `TestUpdateCompletionsClearsForNonSlash` | update_test.go | updateCompletions() clears for non-slash input |
| `TestUpdateCompletionsClearsAfterSpace` | update_test.go | updateCompletions() clears when command has args |

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

### Bug 4: /resume copy-paste issue (FIXED)
- **Test**: `TestFullSessionResumeFlow`
- **Verifies**: `/resume` shows arrow-key picker when no ID given, selecting sends `session.resume`

---

## Category 12: Session Resume Picker Tests

Tests for the arrow-key session resume picker (`/resume` without args).

### Session Picker State Tests (session_picker_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestEnterSessionPickerSetsAskUserStage` | session_picker_test.go | stage=stageAskUser, askRequestID=-1 (sentinel) |
| `TestEnterSessionPickerFormatsLabels` | session_picker_test.go | Labels include ID prefix + title + model in parens |
| `TestEnterSessionPickerEmptyTitle` | session_picker_test.go | Shows "(untitled)" for empty titles |
| `TestEnterSessionPickerLongTitle` | session_picker_test.go | Truncates titles >40 chars with "..." |
| `TestEnterSessionPickerNoModel` | session_picker_test.go | Omits model parens when model is empty |
| `TestEnterSessionPickerBlursInput` | session_picker_test.go | textInput blurred in picker mode |
| `TestEnterSessionPickerStoresEntries` | session_picker_test.go | Full session entries stored (not truncated) |
| `TestEnterSessionPickerSetsQuestion` | session_picker_test.go | Question set to "Select a session to resume:" |
| `TestEnterSessionPickerCursorAtZero` | session_picker_test.go | Cursor reset to 0 on enter |
| `TestEnterSessionPickerShortID` | session_picker_test.go | IDs shorter than 8 chars don't crash |
| `TestEnterSessionPickerDisallowsText` | session_picker_test.go | askAllowText=false (no free-text in picker) |

### Session Picker Navigation Tests (session_picker_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestSessionPickerArrowNavigation` | session_picker_test.go | Up/Down with wrapping via ask-user handler |
| `TestSessionPickerEnterSelectsSession` | session_picker_test.go | Enter sends session.resume with full ID, returns to stageInput |
| `TestSessionPickerEnterFirstItem` | session_picker_test.go | First item selection sends correct ID |
| `TestSessionPickerEscapeCancels` | session_picker_test.go | Escape returns to stageInput, clears entries |
| `TestSessionPickerCtrlCCancels` | session_picker_test.go | Ctrl+C returns to stageInput, clears entries |
| `TestSessionPickerDoesNotSendResponseToBackend` | session_picker_test.go | Sentinel prevents SendResponse on cancel |
| `TestSessionPickerSelectionResetsState` | session_picker_test.go | sessionPickerEntries=nil, textInput cleared |
| `TestSessionPickerViewRendersCorrectly` | session_picker_test.go | View shows question + formatted options |

### Session Picker Edge Case Tests (session_picker_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestSessionPickerInvalidIndex` | session_picker_test.go | Invalid index → error, returns to stageInput |
| `TestSessionPickerNegativeIndex` | session_picker_test.go | Negative index → error, returns to stageInput |
| `TestSessionPickerDuplicateTitles` | session_picker_test.go | Same-title sessions distinguishable by ID prefix |
| `TestRegularAskUserNotAffectedBySentinel` | session_picker_test.go | Real ask-user works after picker used |
| `TestSessionPickerSendsFullSessionID` | session_picker_test.go | Full UUID sent, not truncated 8-char prefix |

### /resume Command Tests (update_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestSlashResumeNoArgsTriggersSessionList` | update_test.go | `/resume` sends session.list RPC |
| `TestSlashResumeWithArgsDelegatesToBackend` | update_test.go | `/resume abc` sends session.resume directly |
| `TestSlashResumeNoBackend` | update_test.go | nil backend shows error |
| `TestBackendSessionListMsgEntersSessionPicker` | update_test.go | Message triggers session picker |
| `TestBackendSessionListMsgEmptySessions` | update_test.go | Empty list → "No sessions found" error |
| `TestSlashResumeWithArgsTrimsWhitespace` | update_test.go | Whitespace trimmed from session ID arg |
| `TestSlashResumeViaEnter` | update_test.go | Full path: type /resume, press Enter |
| `TestTokenMsgEmptyText` | update_test.go | Empty text token doesn't crash |
| `TestTokenMsgEmptyTextDuringInput` | update_test.go | Empty text during input produces no output |

### SendRequestCmd Tests (backend_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestSendRequestCmdMarshal` | backend_test.go | Sends valid JSON-RPC with method and ID |
| `TestSendRequestCmdStoresPending` | backend_test.go | Stores pending channel in sync.Map |
| `TestSendRequestCmdCallbackOnResponse` | backend_test.go | Callback produces correct tea.Msg on response |
| `TestSendRequestCmdErrorResponse` | backend_test.go | RPC error → backendErrorMsg via callback |
| `TestRouteResponseDelivers` | backend_test.go | pending map + channel delivery works correctly |
| `TestSendRequestCmdWriteChFull` | backend_test.go | Returns error when write channel is full |

### Protocol Wire Format Tests (protocol_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestSessionListResultUnmarshal` | protocol_test.go | Correct deserialization of session list |
| `TestSessionListResultEmpty` | protocol_test.go | Empty session array works |
| `TestSessionInfoFieldsRoundTrip` | protocol_test.go | All SessionInfo fields round-trip |
| `TestSessionListParamsMarshal` | protocol_test.go | Empty struct serializes to {} |
| `TestSessionListResultMarshal` | protocol_test.go | SessionListResult serializes correctly |
| `TestSessionInfoEmptyFields` | protocol_test.go | Empty string fields handled |

### E2E Session Resume Tests (e2e_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestFullSessionResumeFlow` | e2e_test.go | /resume → list → navigate → pick → session.resume sent |
| `TestFullSessionResumeCancelFlow` | e2e_test.go | /resume → list → navigate → Escape → stageInput, no backend msg |
| `TestFullSessionResumeDirectIDFlow` | e2e_test.go | /resume ID → session.resume sent, no picker |

### E2E Thinking Token Tests (e2e_test.go)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestFullThinkingTokensDisplayInRealTime` | e2e_test.go | 17-chunk thinking accumulation, per-chunk visibility in View(), 5-line cap, thinking+response coexistence, cleanup on done |
| `TestThinkingTokensDisabledNotShownInView` | e2e_test.go | showThinking=false hides tokens from View(), buffer still accumulates, toggle reveals them |
| `TestThinkingTokensInterleavedWithResponseTokens` | e2e_test.go | Interleaved thinking and response tokens accumulate correctly in separate buffers |

### Gap Tests (various files)

| Test | File | What It Verifies |
|------|------|-----------------|
| `TestViewDuringStageInit` | view_test.go | View renders textInput + status bar during init |
| `TestCompletionDropdownCapAt8Items` | completion_test.go | >8 items truncated to 8 |
| `TestCompletionDropdownTwoColumns` | completion_test.go | Width>50 renders 2 columns, <=50 renders 1 |
| `TestCompletionDropdownEmptyItems` | completion_test.go | Empty items list doesn't crash |
| `TestCompletionDropdownSingleItem` | completion_test.go | Single item renders correctly |
