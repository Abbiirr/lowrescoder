/*
 * ui_smoke.js — demo-mode smoke test for the WebUI port.
 * Run: deno run --allow-read webui/tests/ui_smoke.js
 *
 * Loads demo.js + app.js (NOT wiring.js) under DOM stubs so window.Live is absent
 * and every LIVE SEAM falls back to window.DEMO. Drives all five views and every
 * interaction, mirroring the standalone prototype's verification (47 checks), then
 * adds structural checks for the multi-file layout + live seams.
 */
const WEBUI = new URL("../", import.meta.url);

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

async function load(name) {
  const code = await Deno.readTextFile(new URL(name, WEBUI));
  (0, eval)(code.replace(/^\s*['"]use strict['"];/, ""));
}
await load("demo.js");
await load("app.js");

const A = globalThis.A;
if (!A) throw new Error("A not found — app.js did not load");

let checks = 0; const fails = [];
function expect(cond, label) { checks++; if (!cond) fails.push(label); }
function has(s) { return lastHtml.includes(s); }

/* ---- home ---- */
expect(has("What are we coding next?"), "home heading");
expect(has("Fix booking double-charge on overlap"), "thread list");
expect(has("ACTIVE NOW"), "home active section");

/* ---- popovers ---- */
A.togglePopSkills({ stopPropagation() {} });
expect(has("/fix-ci"), "skills popover open");
A.closePops();
expect(!has("Manage skills"), "popovers closed");
A.togglePopModel({ stopPropagation() {} });
expect(has("Deep reasoning for gnarly work"), "model popover");
A.pickModel(1);
expect(has("AC-1 Fast"), "model picked");
A.pickReasoning("Low");

/* ---- thread + chat rows ---- */
A.openThread("t1");
expect(has("Approval needed"), "approval card");
expect(has("Trace the charge path in bookingStore"), "plan steps");
A.toggleAct("a2");
expect(has("2 failed | 6 passed"), "act term expanded");
A.toggleAct("a3");
expect(has("chargeable = Math.min(session.endsAt, closeTime)"), "act diff expanded");
A.approve();
expect(has("Approved"), "approval approved");
A.toggleApprovalOut();
expect(has("4 passed (4)"), "e2e output shown");

/* ---- editor + IntelliSense ---- */
A.selEditor();
expect(has("EXPLORER"), "editor file rail");
expect(has("venueCloseFor"), "code rendered");
expect(has("Tab ↹"), "ghost pending");
A.acceptGhost();
expect(!has("Tab ↹"), "ghost accepted");
A.startCompletion();
expect(has("↑↓ navigate"), "completion popup");
A.complPick({ stopPropagation() {} }, 0);
expect(has("0 errors"), "quick fix applied");
A.chipTry(2);
expect(has("Peek definition ⌥F12"), "hover card");
A.chipTry(3);
expect(has("Param 1 of 2"), "signature card");
A.chipTry(4);
expect(has("src/lib/sessions.ts · 82:17"), "peek window");
A.chipTry(5);
expect(!has(">at:<"), "inlay hints hidden");
A.resetDemo();
expect(has("1 error"), "demo reset");

/* ---- review rail ---- */
A.toggleReview();
expect(has("2 of 3 staged"), "review rail open + staged count");
A.stageAll();
expect(has("3 of 3 staged"), "stage all");
A.selDiff("f3");
expect(has("charges once when session spans close"), "diff switch");
A.createPR();
expect(has("Opening PR…"), "pr creating");

/* ---- other threads ---- */
A.openThread("t5");
expect(has("Triggered by automation"), "trigger row");
A.openThread("t3");
expect(has("Working — porting slices to Zustand…"), "thinking row");

/* ---- views ---- */
A.setView("automations");
expect(has("Flaky test hunter"), "automations view");
A.autoToggle("a2");
A.setView("skills");
expect(has("/scaffold"), "skills view");
A.setView("settings");
expect(has("MCP SERVERS"), "settings view");
expect(has("Auth expired"), "stripe error state");
A.mcpReconnect();
A.pickPerm("full");
A.togglePerm("permNet");
A.setTheme("light");
expect(has("--t1:#181d2a"), "light palette applied");
A.setDir("mono");
expect(has("--desk:#e9e9e9"), "mono light palette");
A.setDir("warm");
A.setTheme("dark");
expect(has("--acc:#e79a3c"), "warm dark palette");
A.setDir("glass");

/* ---- search ---- */
A.onSearch({ target: { value: "zustand" } });
expect(has("Migrate booking store to Zustand") && !has("Weekly dependency audit"), "search filters");
A.onSearch({ target: { value: "" } });

/* ---- async send flows (demo fallback) ---- */
A.setView("home");
A.onComposerHome({ target: { value: "Add rate-limit middleware to the API" } });
A.sendHome();
expect(has("Add rate-limit middleware to the API"), "new thread user row");
await new Promise((r) => setTimeout(r, 1700));
expect(has("Locate relevant code"), "plan appended after delay");
expect(has("Thread started in a worktree"), "toast shown");
A.onComposerThread({ target: { value: "Also add tests please" } });
A.sendThread();
await new Promise((r) => setTimeout(r, 1500));
expect(has("Noted — folding that into the current plan."), "reply answer appended");

/* ---- balanced markup ---- */
for (const tag of ["div", "span", "button", "svg", "pre"]) {
  const open = (lastHtml.match(new RegExp("<" + tag + "(\\s|>)", "g")) || []).length;
  const close = (lastHtml.match(new RegExp("</" + tag + ">", "g")) || []).length;
  expect(open === close, `balanced <${tag}>: ${open} open vs ${close} close`);
}

/* ---- structural checks (multi-file layout + seams) ---- */
const indexHtml = await Deno.readTextFile(new URL("index.html", WEBUI));
for (const f of ["styles.css", "rpc.js", "events.js", "demo.js", "app.js", "wiring.js"]) {
  expect(indexHtml.includes(f), `index.html references ${f}`);
}
expect(indexHtml.includes("demo") && indexHtml.includes("live"), "index.html has demo/live switch");
const appSrc = await Deno.readTextFile(new URL("app.js", WEBUI));
const seamCount = (appSrc.match(/LIVE SEAM/g) || []).length;
expect(seamCount >= 8, `app.js has LIVE SEAM markers (found ${seamCount})`);
expect(appSrc.includes("window.Store"), "app.js exposes window.Store");
expect(appSrc.includes("function live()"), "app.js has live() switch");

/* ---- report ---- */
if (fails.length) {
  console.log(`FAILED ${fails.length}/${checks} checks:`);
  for (const f of fails) console.log("  ✗ " + f);
  Deno.exit(1);
} else {
  console.log(`PASS — ${checks} checks OK`);
}
