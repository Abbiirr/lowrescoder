/*
 * e2e_live.js — end-to-end live integration gate (T3).
 * Run: deno run --allow-read --allow-net --allow-run --allow-env webui/tests/e2e_live.js
 *
 * Spawns the mock harness server, then loads the REAL client stack (rpc.js +
 * events.js + demo.js + app.js + wiring.js) in Deno under DOM stubs, connects a
 * live WebSocket, and drives one full chat turn through the UI seams:
 *   send  ->  on_token / on_tool_call  ->  on_tool_request (approve)  ->  on_done
 * asserting the rendered app state reflects each stage. This proves the WebUI works
 * against the documented harness protocol, not just in demo mode.
 */

const HERE = new URL(".", import.meta.url);
const WEBUI = new URL("../", HERE);
const PORT = 8951;

/* ---------------- DOM stubs (headless) ---------------- */
let lastHtml = "";
const appStub = {
  get innerHTML() { return lastHtml; },
  set innerHTML(v) { lastHtml = v; },
  querySelectorAll() { return []; },
};
globalThis.document = {
  getElementById(id) { return id === "app" ? appStub : null; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  activeElement: null,
};
globalThis.window = globalThis;
globalThis.addEventListener = () => {};

/* ---------------- helpers ---------------- */
function load(code) { (0, eval)(code.replace(/^\s*['"]use strict['"];/, "")); }
async function loadFile(name) { load(await Deno.readTextFile(new URL(name, WEBUI))); }
async function waitFor(pred, label, timeoutMs = 9000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (pred()) return;
    await new Promise((r) => setTimeout(r, 40));
  }
  throw new Error("timeout waiting for: " + label);
}
function activeRows() {
  const S = globalThis.Store.state;
  const id = globalThis.Live._activeId;
  const t = S.newThreads.find((x) => x.id === id);
  return (t && t.rows) || [];
}
function has(sub) { return lastHtml.includes(sub); }

let checks = 0; const fails = [];
function expect(cond, label) { checks++; if (!cond) fails.push(label); }

/* ---------------- spawn mock server ---------------- */
const child = new Deno.Command("uv", {
  args: ["run", "--no-project", "--with", "websockets>=12", "python", "mock-server.py",
         "--port", String(PORT), "--max-seconds", "90"],
  cwd: new URL(".", WEBUI).pathname.replace(/^\/([A-Za-z]:)/, "$1"),
  stdout: "piped",
  stderr: "piped",
}).spawn();

// Windows: killing `uv` does not kill its `python` child. Tree-kill by pid on cleanup;
// the mock's --max-seconds watchdog is the backstop if that ever fails.
async function killTree() {
  try {
    if (Deno.build.os === "windows") {
      await new Deno.Command("taskkill", { args: ["/F", "/T", "/PID", String(child.pid)] }).output();
    } else {
      child.kill("SIGKILL");
    }
  } catch (_) { /* ignore */ }
}

async function waitForListening() {
  const reader = child.stdout.getReader();
  const dec = new TextDecoder();
  let buf = "";
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value);
    if (buf.includes("listening on")) {
      // keep draining in the background so the pipe never blocks the server
      (async () => { try { while (true) { const r = await reader.read(); if (r.done) break; } } catch (_) {} })();
      return;
    }
  }
  throw new Error("mock server did not report listening");
}

async function main() {
  await waitForListening();

  await loadFile("rpc.js");
  await loadFile("events.js");
  await loadFile("demo.js");
  await loadFile("app.js");
  await loadFile("wiring.js");

  const { Live, Store, A } = globalThis;
  expect(!!Live && !!Store && !!A, "client stack loaded");

  // connect live
  await Live.connect(`ws://127.0.0.1:${PORT}`);
  expect(Live.enabled === true, "live enabled after connect");
  expect(Live.sessions().length === 5, "session.list populated sidebar (5)");
  expect(Live.skillsPop().length >= 5, "command.list populated skills");

  // drive a chat from the home composer
  Store.state.view = "home";
  Store.state.composerHome = "Bookings past close are billed twice — fix it";
  A.sendHome();

  // optimistic user row + switch to the new thread
  expect(Store.state.view === "thread", "switched to thread view on send");
  await waitFor(() => activeRows().some((r) => r.kind === "user"), "user row from on_chat_ack");
  await waitFor(() => activeRows().some((r) => r.kind === "act"), "tool-call act row streamed");
  await waitFor(() => activeRows().some((r) => r.kind === "answer" && (r.paras || []).join(" ").length > 0), "streamed answer tokens");

  // approval round-trip
  await waitFor(() => Live._R.pendingApprovals.length > 0, "approval requested by server");
  expect(Store.state.approval === "pending", "approval card in pending state");
  expect(has("Approval needed"), "approval card rendered");
  A.approve();
  await waitFor(() => Live._R.pendingApprovals.length === 0, "approval cleared after approve");

  // turn completes
  await waitFor(() => {
    const ans = activeRows().filter((r) => r.kind === "answer");
    return ans.length > 0 && ans[ans.length - 1].inProgress === false;
  }, "answer finalized on on_done");
  const answer = activeRows().filter((r) => r.kind === "answer").pop();
  expect((answer.paras || []).join(" ").includes("All tests green"), "post-approval answer text present");
  expect(answer.meta && answer.meta.length > 0, "answer meta set from on_done");

  // cost meter updated from on_cost_update
  expect(Live.cost().pct === 64, "cost meter updated from on_cost_update (64%)");

  // config round-trip reflected via on_status
  A.pickModel(1); // AC-1 Fast
  await waitFor(() => Store.state.model === "AC-1 Fast", "config.set model reflected via on_status");

  // report
  if (fails.length) {
    console.log(`FAILED ${fails.length}/${checks} checks:`);
    for (const f of fails) console.log("  ✗ " + f);
    throw new Error("e2e assertions failed");
  }
  console.log(`PASS — ${checks} live e2e checks OK`);
}

let code = 0;
try {
  await main();
} catch (e) {
  console.error("E2E ERROR:", e.message);
  code = 1;
} finally {
  try { globalThis.RPC && globalThis.RPC.close(); } catch (_) {}
  await killTree();
  try { await child.status; } catch (_) {}
}
Deno.exit(code);
