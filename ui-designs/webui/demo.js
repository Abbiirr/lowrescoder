'use strict';
/* AutoCode WebUI — demo data + simulated async behaviors (classic script).
   Everything here is the hardcoded content of the original AutoCode.html prototype:
   the seed threads, chat transcripts, editor/IntelliSense fixtures, review diffs,
   automations, skills, settings cards, and the file tree. It also owns the four
   simulated async behaviors that the prototype faked with setTimeout — send()'s two
   deferred bodies, createPR, mcpReconnect, and the toast lifetime.

   Loaded before app.js. The sim* functions reference app.js globals (state, set,
   render, toast, scrollChatBottom) which resolve lazily at call time — they are only
   ever invoked after a user interaction, long after app.js has loaded. When a live
   backend is wired (T3), these demo behaviors are the fallback for when live() is null. */

window.DEMO = {

  /* ---------- seed threads (sidebar + home cards) ---------- */
  THREADS: [
    { id:'t1', title:'Fix booking double-charge on overlap', meta:'worktree · AC-1 High · running 4m', group:'active', running:true, badge:'Needs approval', badgeKind:'warn' },
    { id:'t3', title:'Migrate booking store to Zustand', meta:'cloud · AC-1 Fast · running 12m', group:'active', running:true },
    { id:'t2', title:'Pricing calculator: member discounts', meta:'worktree · merged 1h ago', group:'recent', done:true, badge:'PR #128', badgeKind:'ok' },
    { id:'t4', title:'Dark mode for kiosk check-in', meta:'local · yesterday', group:'recent', done:true },
    { id:'t5', title:'Weekly dependency audit', meta:'automation · Mon 09:00', group:'recent', done:true, badge:'Auto', badgeKind:'dim' }
  ],

  /* ---------- chat transcripts per thread ---------- */
  BASE_ROWS: {
    t1: [
      { kind:'user', text:'Bookings that run past closing are getting charged twice — a 9–11pm session at Station 4 billed $48 instead of $24. Find it and fix it.' },
      { kind:'plan', title:'Plan', steps:[
        { t:'Reproduce with a failing test', s:'done' },
        { t:'Trace the charge path in bookingStore', s:'done' },
        { t:'Fix overlap handling in pricing.ts', s:'now' },
        { t:'Run the full suite + e2e', s:'todo' },
        { t:'Open a PR with a changelog note', s:'todo' } ] },
      { kind:'act', id:'a1', icon:'read', label:'Read 3 files', meta:'12.4k tokens', files:['src/stores/bookingStore.ts — 212 lines','src/lib/pricing.ts — 84 lines','src/lib/sessions.ts — 141 lines'] },
      { kind:'act', id:'a2', icon:'term', label:'pnpm vitest run pricing', meta:'2 failed', bad:true, term:'✗ charges once when session spans close\n    expected 2400 to equal 1200\n✗ applies member discount after clamp\n    expected 1080 to equal 540\n\nTests  2 failed | 6 passed (8)\nDuration  1.42s' },
      { kind:'act', id:'a3', icon:'edit', label:'Edited src/lib/pricing.ts', meta:'+18 −6', diff:[
        { t:'c', s:'export function calcTotal(session: Session, rate: Rate) {' },
        { t:'d', s:'  const hours = Math.ceil((session.endsAt - session.startsAt) / MS_PER_HOUR);' },
        { t:'a', s:'  const closeTime = venueCloseFor(session.startsAt);' },
        { t:'a', s:'  const chargeable = Math.min(session.endsAt, closeTime) - session.startsAt;' },
        { t:'a', s:'  const hours = Math.ceil(chargeable / MS_PER_HOUR);' },
        { t:'c', s:'  let total = hours * rate.hourly;' } ] },
      { kind:'approval' },
      { kind:'answer', paras:[
        'Found it. splitAtClose() breaks a spanning booking into two sessions, but both kept the full duration — so calcTotal billed the whole 9–11pm block twice.',
        'calcTotal now clamps chargeable time at venue close and credits the overlap once. Both failing tests pass, plus a new regression spec for sessions ending exactly at close.' ],
        meta:'AC-1 High · 4m 12s · +68 −8 across 3 files', actions:[{ label:'Open pricing.ts', act:'editor' }, { label:'Review changes', act:'review' }] }
    ],
    t2: [
      { kind:'user', text:'Add member-tier discounts to the pricing calculator — Silver 10%, Gold 20%, applied after tax.' },
      { kind:'plan', title:'Plan', steps:[{ t:'Add MemberTier type + rate table', s:'done' },{ t:'Implement applyDiscount()', s:'done' },{ t:'Wire into calcTotal + UI', s:'done' },{ t:'Cover with unit tests', s:'done' }] },
      { kind:'act', id:'b1', icon:'edit', label:'Created src/lib/discounts.ts', meta:'+64 −0', diff:[{ t:'a', s:'export function applyDiscount(amount: number, tier: MemberTier): number {' },{ t:'a', s:'  const pct = tier === "gold" ? 0.2 : tier === "silver" ? 0.1 : 0;' },{ t:'a', s:'  return Math.round(amount * (1 - pct) * 100) / 100;' },{ t:'a', s:'}' }] },
      { kind:'act', id:'b2', icon:'term', label:'pnpm vitest run', meta:'8 passed', term:'Tests  8 passed (8)\nDuration  1.05s' },
      { kind:'answer', paras:['Shipped. Discounts apply after tax per PRICING.md, rounded to the cent. PR #128 is merged into main.'], meta:'AC-1 High · 6m 40s · +112 −9', actions:[{ label:'View PR #128', act:'toast' }] }
    ],
    t3: [
      { kind:'user', text:'Migrate bookingStore from Redux to Zustand. Keep the selector API stable so components don’t churn.' },
      { kind:'plan', title:'Plan', steps:[{ t:'Inventory store slices + selectors', s:'done' },{ t:'Port slices to Zustand', s:'now' },{ t:'Codemod component imports', s:'todo' },{ t:'Delete Redux plumbing', s:'todo' }] },
      { kind:'act', id:'c1', icon:'read', label:'Read 14 files', meta:'48k tokens', files:['src/stores/** — 9 files','src/components/booking/** — 5 files'] },
      { kind:'thinking' }
    ],
    t4: [
      { kind:'user', text:'The kiosk check-in screen needs a dark mode that follows the venue’s hours — dark after 6pm.' },
      { kind:'answer', paras:['Done — kiosk theme now derives from venueCloseFor() with a manual override in settings. Merged yesterday.'], meta:'AC-1 Fast · 3m 02s · +54 −11', actions:[] }
    ],
    t5: [
      { kind:'trigger', text:'Triggered by automation · Weekly dependency audit' },
      { kind:'act', id:'d1', icon:'term', label:'pnpm audit --prod', meta:'2 advisories', term:'2 moderate advisories\n  vite 5.2.1 → 5.2.11 (patched)\n  zod 3.22.0 → 3.23.4 (patched)' },
      { kind:'answer', paras:['Patched both advisories, lockfile updated, full suite green. No API changes required.'], meta:'AC-mini · 1m 18s · +6 −6', actions:[] }
    ]
  },

  /* ---------- editor: completion list ---------- */
  COMPL: [
    { n:'endsAt', t:'Date', d:'When the session ends. Always set by the scheduler; clamp against venue close before billing.' },
    { n:'startsAt', t:'Date', d:'When the session starts.' },
    { n:'memberId', t:'string | null', d:'Loyalty member id, if the booking is attached to an account.' },
    { n:'memberTier', t:'MemberTier', d:"'none' | 'silver' | 'gold' — drives applyDiscount." },
    { n:'spansClose', t:'boolean', d:'True when the session crosses venue closing time.' },
    { n:'rate', t:'Rate', d:'Hourly rate card resolved at booking time.' }
  ],

  /* ---------- skills (composer popover) ---------- */
  SKILLS_POP: [
    { cmd:'/review', desc:'Audit the current diff for risky changes and missing tests' },
    { cmd:'/test', desc:'Write or update tests for the selected code path' },
    { cmd:'/fix-ci', desc:'Pull the latest CI failure and fix it' },
    { cmd:'/explain', desc:'Explain the selected code with references' },
    { cmd:'/commit', desc:'Stage, write a conventional commit, and push' }
  ],

  /* ---------- harness modes / models ---------- */
  MODES: [
    { label:'Local', desc:'Edit files in place' },
    { label:'Worktree', desc:'Isolated branch copy — safe to run wild' },
    { label:'Cloud', desc:'Runs on AutoCode servers, PR when done' }
  ],
  MODELS: [
    { label:'AC-1 High', desc:'Deep reasoning for gnarly work' },
    { label:'AC-1 Fast', desc:'Everyday edits and reviews' },
    { label:'AC-mini', desc:'Cheap bulk tasks' }
  ],
  QUICK_CHIPS: ['Fix the failing pricing tests', '/review my staged diff', 'Scaffold a booking widget'],

  /* ---------- review rail ---------- */
  REVIEW_FILES: [
    { id:'f1', name:'src/lib/pricing.ts', add:18, del:6 },
    { id:'f2', name:'src/stores/bookingStore.ts', add:9, del:2 },
    { id:'f3', name:'tests/pricing.spec.ts', add:41, del:0 }
  ],
  DIFFS: {
    f1: [
      { t:'c', s:'export function calcTotal(session: Session, rate: Rate) {' },
      { t:'d', s:'  const hours = Math.ceil((session.endsAt - session.startsAt) / MS_PER_HOUR);' },
      { t:'a', s:'  const closeTime = venueCloseFor(session.startsAt);' },
      { t:'a', s:'  const chargeable = Math.min(session.endsAt, closeTime) - session.startsAt;' },
      { t:'a', s:'  const hours = Math.ceil(chargeable / MS_PER_HOUR);' },
      { t:'c', s:'  let total = hours * rate.hourly;' },
      { t:'a', s:'  if (session.spansClose) total -= overlapCredit(session, rate);' },
      { t:'c', s:'  return applyDiscount(total, session.memberTier);' }
    ],
    f2: [
      { t:'c', s:'function settle(booking: Booking) {' },
      { t:'d', s:'  const parts = splitAtClose(booking);' },
      { t:'a', s:'  const parts = splitAtClose(booking, { clampDurations: true });' },
      { t:'c', s:'  return parts.map(chargeFor);' }
    ],
    f3: [
      { t:'a', s:'it("charges once when session spans close", () => {' },
      { t:'a', s:'  const s = mkSession("21:00", "23:00", { close: "22:00" });' },
      { t:'a', s:'  expect(calcTotal(s, RATE)).toBe(1200);' },
      { t:'a', s:'});' }
    ]
  },

  /* ---------- automations ---------- */
  AUTOMATIONS: [
    { id:'a1', name:'Weekly dependency audit', desc:'Audits prod deps, patches minors, opens a PR if tests pass.', sched:'Mon 09:00', last:'Ran 2d ago · patched 2', view:'t5' },
    { id:'a2', name:'Flaky test hunter', desc:'Re-runs the suite 5× nightly and quarantines flakes.', sched:'Nightly 02:00', last:'Ran 6h ago · 2 quarantined', view:null },
    { id:'a3', name:'Changelog draft', desc:'Drafts release notes when a version tag is pushed.', sched:'On release tag', last:'Never ran', view:null }
  ],

  /* ---------- skills page cards ---------- */
  SKILL_CARDS: [
    { cmd:'/review', desc:'Audit the current diff for risky changes, missing tests, and perf traps.', meta:'Used 24× · edited 3d ago' },
    { cmd:'/test', desc:'Write or update tests for the selected code path.', meta:'Used 18× · edited 1w ago' },
    { cmd:'/fix-ci', desc:'Pull the latest CI failure, reproduce locally, and fix it.', meta:'Used 11× · edited 2w ago' },
    { cmd:'/explain', desc:'Explain the selected code with references to callers.', meta:'Used 9× · edited 1mo ago' },
    { cmd:'/commit', desc:'Stage, write a conventional commit, and push.', meta:'Used 31× · edited 3w ago' },
    { cmd:'/scaffold', desc:'Generate a component with stories and tests.', meta:'Used 6× · edited 2mo ago' }
  ],

  /* ---------- settings: permissions ---------- */
  PERM_CARDS: [
    { id:'readonly', name:'Read-only', desc:'Agent proposes changes; you apply them.' },
    { id:'balanced', name:'Balanced', desc:'Writes in the workspace. Asks before commands and network.', rec:true },
    { id:'full', name:'Full access', desc:'Runs commands and network without asking.' }
  ],
  PERM_TOGGLES: [
    { id:'permNet', label:'Network access in sandbox', desc:'Let commands reach the internet without asking' },
    { id:'permTests', label:'Auto-run unit tests after edits', desc:'vitest related --run on every file change' }
  ],

  /* ---------- editor: file tree ---------- */
  FILE_TREE: [
    { n:'src', dir:true, ind:0 },
    { n:'components', dir:true, ind:1 },
    { n:'lib', dir:true, ind:1 },
    { n:'constants.ts', ind:2 },
    { n:'discounts.ts', ind:2, badge:'A' },
    { n:'pricing.ts', ind:2, active:true, badge:'M' },
    { n:'sessions.ts', ind:2 },
    { n:'stores', dir:true, ind:1 },
    { n:'bookingStore.ts', ind:2, badge:'M' },
    { n:'tests', dir:true, ind:0 },
    { n:'pricing.spec.ts', ind:1, badge:'A' }
  ],

  /* ---------- simulated async behaviors ---------- */
  /* Toast lifetime — the setTimeout body of the prototype's toast(). */
  TOAST_MS: 2600,
  dismissToastLater: function(id){
    setTimeout(function(){ state.toasts = state.toasts.filter(function(t){ return t.id !== id; }); render(); }, 2600);
  },

  /* send('home') deferred body — appends a canned plan after the "thinking" beat. */
  simSendHome: function(id){
    setTimeout(function(){
      state.newThreads = state.newThreads.map(function(t){
        return t.id===id ? Object.assign({}, t, { rows: t.rows.concat([{ kind:'plan', title:'Plan', steps:[{t:'Understand the request',s:'done'},{t:'Locate relevant code',s:'now'},{t:'Implement and verify',s:'todo'}] }]) }) : t;
      });
      state.thinking[id] = false;
      render(); scrollChatBottom();
      toast('Thread started in a worktree');
    }, 1500);
  },

  /* send('thread') deferred body — appends a canned reply. */
  simSendThread: function(tid){
    setTimeout(function(){
      state.extras[tid] = (state.extras[tid]||[]).concat([{ kind:'answer', paras:['Noted — folding that into the current plan.'], meta:state.model+' · 2s', actions:[] }]);
      state.thinking[tid] = false;
      render(); scrollChatBottom();
    }, 1300);
  },

  /* createPR deferred body — flips the review rail to the "PR open" state. */
  simCreatePR: function(){
    setTimeout(function(){ set({prState:'open'}); toast('PR #131 opened — checks running'); }, 1000);
  },

  /* mcpReconnect deferred body — resolves the stripe MCP server back to "ok". */
  simMcpReconnect: function(){
    setTimeout(function(){ set({mcpStripe:'ok'}); toast('stripe-fixtures connected'); }, 1100);
  }
};
