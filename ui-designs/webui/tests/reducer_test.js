/*
 * reducer_test.js — Deno tests for events.js (the AgentEvent reducer).
 * Run:  deno test --allow-read webui/tests/reducer_test.js
 *
 * Loads the classic-script reducer via indirect eval so its IIFE attaches
 * globalThis.Reducer, then asserts the agent-events.md contract.
 */
import { assert, assertEquals } from "https://deno.land/std@0.224.0/assert/mod.ts";

const here = new URL(".", import.meta.url);
const code = await Deno.readTextFile(new URL("../events.js", here));
(0, eval)(code);
const Reducer = globalThis.Reducer;
assert(Reducer, "Reducer attached to globalThis");

let T = 0;
function ts() { T += 1000; return new Date(1700000000000 + T).toISOString(); }
function apply(state, ...evts) {
  for (const [method, params] of evts) state = Reducer.apply(state, method, params);
  return state;
}
function kinds(s) { return s.transcript.map((r) => r.kind); }
function byKind(s, k) { return s.transcript.filter((r) => r.kind === k); }

Deno.test("happy-path turn builds user + tool + answer transcript", () => {
  let s = Reducer.createState();
  s = apply(s,
    ["on_chat_ack", { id: "a1", timestamp: ts(), text: "fix the bug" }],
    ["on_thinking", { id: "t1", timestamp: ts(), status: "running" }],
    ["on_token", { id: "k1", timestamp: ts(), text: "Looking at it. " }],
    ["on_tool_call", { id: "c1", callId: "c1", timestamp: ts(), type: "ToolStartEvent", tool: "read_file", title: "Read 3 files", status: "running" }],
    ["on_tool_call", { id: "c1r", callId: "c1", timestamp: ts(), type: "ToolResultEvent", status: "done", meta: "12k tokens", result: { files: ["a.ts", "b.ts"] } }],
    ["on_token", { id: "k2", timestamp: ts(), text: "Fixed it." }],
    ["on_done", { id: "d1", timestamp: ts(), tokens_in: 100, tokens_out: 20, model: "AC-1 High" }],
  );
  assert(kinds(s).includes("user"), "has user row");
  const acts = byKind(s, "act");
  assertEquals(acts.length, 1, "one act row (start+result merged)");
  assertEquals(acts[0].status, "done");
  assertEquals(acts[0].files.length, 2);
  const ans = byKind(s, "answer");
  assertEquals(ans.length, 1, "one answer row");
  assertEquals(ans[0].inProgress, false, "answer finalized on done");
  assert(ans[0].paras.join(" ").includes("Fixed it."), "answer text accumulated");
  assert(!s.thinking, "thinking cleared after tokens/done");
});

Deno.test("duplicate event ids are deduplicated", () => {
  let s = Reducer.createState();
  const ev = ["on_token", { id: "dup", timestamp: ts(), text: "hello" }];
  s = apply(s, ev, ev, ev);
  const ans = byKind(s, "answer");
  assertEquals(ans.length, 1);
  assertEquals(ans[0].paras.join(""), "hello", "text applied exactly once");
});

Deno.test("out-of-order timestamps are resorted", () => {
  let s = Reducer.createState();
  const late = new Date(1700000000000 + 1000).toISOString();  // earlier ts
  const early = new Date(1700000000000 + 9000).toISOString();  // later ts
  s = apply(s,
    ["on_tool_call", { id: "z1", callId: "z1", timestamp: early, tool: "run_command", title: "later-by-arrival", status: "done" }],
    ["on_tool_call", { id: "z2", callId: "z2", timestamp: late, tool: "read_file", title: "earlier-by-timestamp", status: "done" }],
  );
  const labels = byKind(s, "act").map((r) => r.label);
  assertEquals(labels, ["earlier-by-timestamp", "later-by-arrival"], "sorted by timestamp");
});

Deno.test("parentId/callId links a result to its start row", () => {
  let s = Reducer.createState();
  s = apply(s,
    ["on_tool_call", { id: "s1", callId: "call-A", timestamp: ts(), type: "ToolStartEvent", tool: "run_command", title: "vitest", status: "running" }],
    ["on_tool_call", { id: "s2", parentId: "call-A", callId: "call-A", timestamp: ts(), type: "ToolResultEvent", status: "failed", meta: "2 failed", result: { ok: false, output: "boom" } }],
  );
  const acts = byKind(s, "act");
  assertEquals(acts.length, 1, "result merged into the start row, not a new row");
  assertEquals(acts[0].status, "failed");
  assertEquals(acts[0].bad, true);
  assertEquals(acts[0].term, "boom");
});

Deno.test("malformed events are skipped, never thrown", () => {
  let s = Reducer.createState();
  const before = s;
  // null params, missing text, unknown method — none should throw
  s = Reducer.apply(s, "on_token", null);
  s = Reducer.apply(s, "on_token", { id: "m1", timestamp: ts() }); // no text
  s = Reducer.apply(s, "totally_unknown", { id: "m2", timestamp: ts() });
  assertEquals(s.transcript.length, before.transcript.length, "no rows added by malformed events");
});

Deno.test("approval request queues then clears on resolve", () => {
  let s = Reducer.createState();
  s = apply(s, ["on_tool_request", { id: "r1", rpcId: 7, timestamp: ts(), command: 'pnpm test:e2e', title: "Approval needed" }]);
  assertEquals(s.pendingApprovals.length, 1);
  assertEquals(s.pendingApprovals[0].rpcId, 7);
  assertEquals(byKind(s, "approval").length, 1);
  s = Reducer.apply(s, "approval_resolve", { rpcId: 7, decision: "allow" });
  assertEquals(s.pendingApprovals.length, 0, "cleared from pending");
  assertEquals(byKind(s, "approval")[0].status, "ok", "row marked resolved");
});

Deno.test("ask_user request is queued as an ask-kind approval", () => {
  let s = Reducer.createState();
  s = apply(s, ["on_ask_user", { id: "q1", rpcId: 9, timestamp: ts(), question: "Which file?", options: ["a", "b"] }]);
  assertEquals(s.pendingApprovals[0].kind, "ask");
  assertEquals(byKind(s, "approval")[0].approvalKind, "ask");
});

Deno.test("cost + status update session model and usage", () => {
  let s = Reducer.createState();
  s = apply(s,
    ["on_status", { id: "st1", timestamp: ts(), model: "AC-1 Fast", provider: "ollama", mode: "Cloud", session_id: "s9" }],
    ["on_cost_update", { id: "co1", timestamp: ts(), cost: 0.42, tokens_in: 1200, tokens_out: 80 }],
  );
  assertEquals(s.session.model, "AC-1 Fast");
  assertEquals(s.session.id, "s9");
  assertEquals(s.cost.cost, 0.42);
  assertEquals(s.cost.tokensIn, 1200);
});
