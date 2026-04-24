# Live Runtime Bugs

Last updated: 2026-04-24

This file is the live bug ledger for user-visible runtime failures that are worth
tracking with screenshot evidence.

Screenshot folder:

- [bugs/screenshots/2026-04-23-live-runtime](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime)
- [bugs/screenshots/2026-04-23-live-runtime-post-coding](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding)
- [bugs/screenshots/2026-04-24-live-runtime-error-surfacing](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing)

Notes:

- The user-thread screenshot itself is not directly exportable from the chat into
  the repo, so the saved PNGs below are local reproductions of the same live path.
- These bugs were found even though the automated regression sweep was green. That
  means they are currently under-covered by the existing matrix.

## Regression Sweep Context

Sweep run on the same session before this bug-hunt:

- `uv run pytest autocode/tests/unit -q` -> `1862 passed`
- `uv run pytest benchmarks/tests -q` -> `199 passed`
- `cargo test --manifest-path autocode/rtui/Cargo.toml -q` -> `178 passed`
- `cargo clippy --manifest-path autocode/rtui/Cargo.toml -- -D warnings` -> passed
- `cargo build --release --manifest-path autocode/rtui/Cargo.toml` -> passed
- `python3 autocode/tests/pty/pty_smoke_rust_m1.py` -> passed
- `python3 autocode/tests/pty/pty_smoke_rust_comprehensive.py` -> passed

These runtime bugs are therefore real coverage gaps, not already-caught failures.

## 2026-04-24 Fix Verification

Follow-up after the structured warning / fail-fast fix:

- invalid alias now halts immediately with a visible recovery surface and an
  explicit alias error:
  - [bad_alias_first_turn_fixed.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/bad_alias_first_turn_fixed.png)
  - [bad_alias_first_turn_fixed.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/bad_alias_first_turn_fixed.ansi)
- dead local gateway now halts immediately with a visible connection-failure
  recovery surface:
  - [dead_gateway_first_turn_fixed.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/dead_gateway_first_turn_fixed.png)
  - [dead_gateway_first_turn_fixed.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/dead_gateway_first_turn_fixed.ansi)

Validation for the fix slice:

- `uv run pytest autocode/tests/unit/test_llm.py autocode/tests/unit/test_backend_chat.py autocode/tests/unit/test_backend_transport_conformance.py -q` -> `32 passed`
- `uv run pytest autocode/tests/unit/test_backend_server.py -q -k 'handle_chat or emit_notification'` -> `15 passed`
- `cargo test --manifest-path autocode/rtui/Cargo.toml -q` -> `181 passed`
- `cargo clippy --manifest-path autocode/rtui/Cargo.toml -- -D warnings` -> passed

Current interpretation:

- `BUG-LIVE-003` and `BUG-LIVE-004` are fixed.
- `BUG-LIVE-001` and `BUG-LIVE-002` were narrowed by the alias-default fix plus
  the new failure surfacing work; they should stay historical unless they are
  reproduced again on the current default path.

## Post-Coding Follow-Up Matrix

Follow-up run after switching the repo-level everyday gateway alias from `tools`
to `coding`:

- Healthy path now works on the real bare-`autocode` route.
- Saved healthy-path reference screens:
  - [idle_model_picker.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/idle_model_picker.png)
  - [hello_first_turn.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/hello_first_turn.png)
  - [hello_then_model.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/hello_then_model.png)
  - [new_session_then_hello.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/new_session_then_hello.png)

What this means:

- The old “plain `hello` on the default user path wedges immediately” report is
  no longer reproduced on the current repo default.
- The broader bug class is still open: when the provider path is invalid or
  unavailable, the UI still hides the underlying failure too well.

## BUG-LIVE-001 — First Turn Can Stall Indefinitely With No User-Visible Error

Status: Fixed on 2026-04-24

Severity: High

Summary:

- A fresh bare `autocode` session can accept `hello`, start a backend turn, and
  then leave the user with no assistant response and no clear surfaced provider
  failure.

User-facing impact:

- The session appears alive, but the user gets no answer for minutes.
- The failure is not explained in the terminal surface.
- The user can reasonably conclude the harness is broken.

Observed live evidence:

- User report: a bare `autocode` session sat for about 5 minutes with no visible
  response after `hello`.
- Local reproduction: a fresh TUI session accepted `hello` and then never
  rendered an assistant response.
- Saved screenshot:
  - [hello_stuck_working.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime/hello_stuck_working.png)
- Raw ANSI capture:
  - [hello_stuck_working.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime/hello_stuck_working.ansi)

Backend evidence:

- [autocode-debug.jsonl](/home/bs01763/projects/ai/lowrescoder/logs/2026/04/23/15/f3441bfc/autocode-debug.jsonl:1)
- [autocode.jsonl](/home/bs01763/projects/ai/lowrescoder/logs/2026/04/23/15/f3441bfc/autocode.jsonl:1)

Important log lines from the reproduced session:

- `backend_chat_received`
- `backend_chat_ack`
- `backend_chat_route_selected` with `selected_layer = 4`
- `llm_request` using provider `tools`
- OpenRouter retry warnings:
  - `404`
  - `429`

Config clue:

- [~/.autocode/config.yaml](/home/bs01763/.autocode/config.yaml:1) currently points the default live path at:
  - provider: `openrouter`
  - model: `tools`
  - api_base: `http://localhost:4000/v1`

Historical repro before the fix:

1. Run bare `autocode` from the repo root.
2. Submit `hello`.
3. Wait at least 10-15 seconds.
4. Observe that no assistant text appears and no explicit provider error is surfaced.

Current hypothesis:

- This is partly a provider/config problem and partly a UI/runtime-surfacing
  problem.
- The backend is retrying real provider failures, but the frontend does not turn
  that state into an honest user-visible error quickly enough.

What needs to be fixed:

- Surface provider-route failure/retry state to the user instead of silently
  spinning.
- Decide whether `tools` is a valid default interactive model on this gateway.
- Add a real regression that catches “chat accepted, no assistant output, no
  surfaced failure” on the bare user path.

Follow-up note:

- The exact default-path repro above was narrowed by switching the repo-level
  alias to `coding`.
- The same user-visible failure mode still reproduces under invalid-alias and
  dead-gateway conditions below, so this bug stays open as a runtime-surfacing
  gap rather than a pure default-alias issue.

## BUG-LIVE-002 — Slash/Picker Flow Can Hide A Still-Wedged Turn

Status: Open

Severity: Medium

Summary:

- While the first turn is already wedged, slash-command discovery can still open,
  which is good, but it also makes the screen look healthy even though the
  original turn is unresolved.

User-facing impact:

- The user can open `/model` and see a picker, yet the original `hello` still has
  no response and no explicit failure banner.
- This creates a misleading “UI is responsive, backend is fine” impression while
  the original turn is still stuck.

Saved screenshots:

- [hello_stuck_model_loading_commands.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime/hello_stuck_model_loading_commands.png)
- [hello_stuck_then_model_picker.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime/hello_stuck_then_model_picker.png)

Raw ANSI captures:

- [hello_stuck_model_loading_commands.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime/hello_stuck_model_loading_commands.ansi)
- [hello_stuck_then_model_picker.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime/hello_stuck_then_model_picker.ansi)

Related backend evidence:

- [autocode-debug.jsonl](/home/bs01763/projects/ai/lowrescoder/logs/2026/04/23/15/f3441bfc/autocode-debug.jsonl:1)

Important log lines from the reproduced session:

- `rpc_request` / `rpc_response` for `command.list`
- `rpc_request` / `rpc_response` for `model.list`
- these arrive while the original `chat` request is still retrying upstream

Repro:

1. Run bare `autocode`.
2. Submit `hello`.
3. Before any response is rendered, type `/model`.
4. Observe that slash discovery and the model picker can open on top of a still
   unresolved turn.

Current hypothesis:

- The slash/picker path is healthy enough to answer, but the UI does not make the
  unresolved original request visible enough once focus moves into palette/picker
  state.
- This is a truthful runtime bug even if the picker itself is functioning.

What needs to be fixed:

- Keep the unresolved-turn state visible while overlays are open.
- Surface the stuck/retrying request more honestly than a silent return to a
  normal-looking picker flow.
- Add a live regression that combines an in-flight turn with slash/picker
  interactions and asserts on visible pending/failure state, not just overlay
  existence.

## BUG-LIVE-003 — Invalid Model Alias Leaves The User In A Silent Working State

Status: Open

Severity: High

Summary:

- If the live session is launched against an invalid gateway alias, bare
  `autocode` accepts the turn, shows `working`, and then keeps retrying
  upstream `400` failures without surfacing an honest terminal error.

User-facing impact:

- The user sees a live spinner and no answer.
- The failure looks like a hung model rather than a concrete misconfiguration.
- The only visible clue is the wrong alias in the header, which is not enough
  as an error explanation.

Saved screenshots:

- [bad_alias_first_turn.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/bad_alias_first_turn.png)
- [bad_alias_then_model.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/bad_alias_then_model.png)

Raw captures:

- [bad_alias_first_turn.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/bad_alias_first_turn.ansi)
- [bad_alias_then_model.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/bad_alias_then_model.ansi)

Backend evidence:

- [ffac4734/autocode-debug.jsonl](/home/bs01763/projects/ai/lowrescoder/logs/2026/04/23/15/ffac4734/autocode-debug.jsonl:1)
- [9d214ace/autocode-debug.jsonl](/home/bs01763/projects/ai/lowrescoder/logs/2026/04/23/15/9d214ace/autocode-debug.jsonl:1)

Important log lines:

- `backend_chat_ack`
- `backend_chat_layer4_start`
- `llm_request` with model `this_alias_should_not_exist_404`
- repeated `OpenRouter retry ... Error code: 400`

Repro:

1. Run bare `autocode` with `OPENROUTER_MODEL=this_alias_should_not_exist_404`.
2. Submit `hello`.
3. Wait 15-30 seconds.
4. Observe that the TUI stays in `working` with no honest surfaced error.

Secondary misleading behavior:

- `/model` still opens while that invalid-alias turn is retrying:
  - [bad_alias_then_model.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/bad_alias_then_model.png)

Fix landed:

- invalid-model `400` / `404` style failures now fail fast on the interactive
  path instead of retrying like transient transport errors
- the frontend now receives a visible recovery/error state with the explicit
  alias message
- post-fix evidence:
  - [bad_alias_first_turn_fixed.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/bad_alias_first_turn_fixed.png)
  - [bad_alias_first_turn_fixed.txt](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/bad_alias_first_turn_fixed.txt)

## BUG-LIVE-004 — Dead Gateway Looks Like A Hang Instead Of A Connection Failure

Status: Fixed on 2026-04-24

Severity: High

Summary:

- If the configured gateway is unreachable, bare `autocode` accepts `hello`,
  shows `working`, and retries connection failures in the backend while the TUI
  still looks like a normal in-flight turn.

User-facing impact:

- The user gets no answer and no direct explanation that the gateway is down.
- A dead backend route is visually indistinguishable from a slow model for too
  long.

Saved screenshots:

- [dead_gateway_first_turn.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/dead_gateway_first_turn.png)
- [dead_gateway_then_model.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/dead_gateway_then_model.png)

Raw captures:

- [dead_gateway_first_turn.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/dead_gateway_first_turn.ansi)
- [dead_gateway_then_model.ansi](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/dead_gateway_then_model.ansi)

Backend evidence:

- [bbd96c12/autocode-debug.jsonl](/home/bs01763/projects/ai/lowrescoder/logs/2026/04/23/15/bbd96c12/autocode-debug.jsonl:1)
- [91ae5569/autocode-debug.jsonl](/home/bs01763/projects/ai/lowrescoder/logs/2026/04/23/15/91ae5569/autocode-debug.jsonl:1)

Important log lines:

- `backend_chat_ack`
- `backend_chat_layer4_start`
- repeated `OpenRouter retry ... Connection error.`
- `backend_chat_heartbeat` while no user-visible error is shown

Historical repro before the fix:

1. Run bare `autocode` with `AUTOCODE_LLM_API_BASE=http://127.0.0.1:9/v1`.
2. Submit `hello`.
3. Wait 15-30 seconds.
4. Observe that the TUI stays in `working` instead of surfacing a connection
   failure.

Secondary misleading behavior:

- `/model` still opens while the dead-gateway turn is retrying:
  - [dead_gateway_then_model.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-23-live-runtime-post-coding/dead_gateway_then_model.png)

Fix landed:

- loopback gateway connection failures now fail fast on the interactive path
  instead of sitting in a long silent retry loop
- the frontend now shows a visible recovery/error state with the concrete
  gateway URL
- post-fix evidence:
  - [dead_gateway_first_turn_fixed.png](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/dead_gateway_first_turn_fixed.png)
  - [dead_gateway_first_turn_fixed.txt](/home/bs01763/projects/ai/lowrescoder/bugs/screenshots/2026-04-24-live-runtime-error-surfacing/dead_gateway_first_turn_fixed.txt)
