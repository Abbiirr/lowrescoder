# Todo — AutoCode WebUI Integration

Task IDs match `../docs/plan/webui-integration-plan.md#5-task-breakdown`.
T1 / T2 / T4 were dispatched to subagents in the previous session — **verify their output
under `webui/` and `webui/test-results/` before marking done or re-doing.** T3 depends on
T1+T2 and was not started.

- [x] **T1 — Protocol core + mock harness.** `webui/rpc.js`, `webui/events.js`, `webui/mock-server.py`, `webui/tests/reducer_test.js`, `webui/tests/test_mock_protocol.py`. Reference: PLAN.md#approach. Gate: TESTING.md#task-1. — 8 reducer + 6 mock protocol tests pass.
- [x] **T2 — WebUI port of the prototype.** `webui/index.html`, `webui/styles.css`, `webui/app.js`, `webui/demo.js`, `webui/tests/ui_smoke.js`. Preserve visuals/behavior; add `?demo=1` + `LIVE SEAM` hooks. Reference: PLAN.md#approach. Gate: TESTING.md#task-2. — 57/57 demo smoke checks pass.
- [x] **T4 — Backend WS drop-in.** `webui/backend/ws_host.py`, `webui/backend/test_ws_host.py`, `webui/backend/README.md`. Loopback-only, single-active-client + queue, serialized writes, static file serving. Reference: PLAN.md#approach. Gate: TESTING.md#task-4. — 11/11 ws_host tests pass.
- [x] **T3 — Live wiring.** Add `webui/wiring.js` (`window.Live`) + connect `app.js` seams to `RPC`+`Reducer` per plan §4 (sessions, chat streaming, tool cards, approvals, thinking, cost, settings, skills, cancel). Live-vs-demo switch + recovery banner on `on_error`. Depends on T1+T2. Reference: PLAN.md#approach. Gate: TESTING.md#task-3. — 10/10 live e2e checks pass.
- [x] **T5 — Full verification + handoff.** All tests green (deno reducer + ui_smoke, pytest mock protocol + ws_host); end-to-end mock-server↔client turn; prototype + design sources untouched; evidence files under `webui/test-results/`. Reference: PLAN.md#goal. Gate: TESTING.md#task-5. — 92 checks green; evidence at `webui/test-results/20260703-155051-verification.md`.
