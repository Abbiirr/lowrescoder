/*
 * wiring.js — window.Live: the live-mode adapter (T3).
 *
 * Classic browser script. Bridges window.RPC (rpc.js) + window.Reducer (events.js)
 * into the LIVE SEAMs that app.js exposes. When Live.enabled is true, app.js routes
 * sessions / chat / approvals / config / cost / skills through here instead of the
 * demo behaviors; when false (or absent), app.js falls back to window.DEMO.
 *
 * Bridge model:
 *   - One Reducer state `R` per active session. Backend notifications are applied to
 *     R, then syncActive() projects R.transcript into the app's own state containers
 *     (Store.state.newThreads[activeId].rows) and re-renders. The app's row vocabulary
 *     already matches the reducer's, so projection is a pass-through.
 *   - Server-initiated requests (on_tool_request / on_ask_user) arrive via
 *     RPC.onServerRequest; we hold the reply until the user answers, and mirror the
 *     pending approval into the reducer + the app's approval card.
 */
(function (global) {
  'use strict';

  var Reducer = global.Reducer;
  var RPC = global.RPC;

  var Live = {
    enabled: false,
    _R: null,
    _threads: [],           // sessions from session.list (card shape)
    _skills: [],            // commands from command.list
    _activeId: null,
    _activeTitle: '',
    _costPct: 62,
    _approvalResolve: null, // resolver for the in-flight server request
    _approvalRpcKey: null   // synthetic key for reducer bookkeeping
  };

  function Store() { return global.Store; }
  function DEMO() { return global.DEMO || {}; }

  function resetReducer() { Live._R = Reducer.createState(); }

  function mapSession(t) {
    return {
      id: t.id, title: t.title || 'Thread', meta: t.meta || '',
      group: t.group || 'active', running: !!t.running, done: !!t.done,
      badge: t.badge || null, badgeKind: t.badgeKind || null
    };
  }

  /* Project the reducer transcript into the app's state for the active thread and
     re-render. Chat rows share a vocabulary, so rows pass straight through. */
  function syncActive() {
    var S = Store().state;
    var id = Live._activeId;
    if (id == null) { Store().render(); return; }
    var rows = Live._R.transcript.slice();

    var found = false;
    S.newThreads = S.newThreads.map(function (t) {
      if (t.id === id) { found = true; return Object.assign({}, t, { rows: rows, running: Live._R.thinking }); }
      return t;
    });
    if (!found) {
      S.newThreads = [{ id: id, title: Live._activeTitle || 'Thread', meta: '', rows: rows, group: 'active', running: Live._R.thinking }].concat(S.newThreads);
    }
    // The reducer owns the thinking row; suppress the app's own so it isn't doubled.
    S.thinking[id] = false;
    // The reducer owns the transcript; drop any optimistic echo in extras.
    S.extras[id] = [];
    // Approval card visual reflects the reducer's pending state.
    if (Live._R.pendingApprovals.length > 0) S.approval = 'pending';

    Store().render();
    pinChatBottom();
  }

  function pinChatBottom() {
    if (!global.document || !global.document.querySelector) return;
    var el = global.document.querySelector('[data-scroll="chat"]');
    if (el) el.scrollTop = el.scrollHeight;
  }

  function liteToast(msg) {
    var S = Store().state;
    var id = 'live-' + Date.now() + '-' + Math.random();
    S.toasts = S.toasts.concat([{ id: id, msg: msg }]);
    Store().render();
    global.setTimeout(function () {
      S.toasts = S.toasts.filter(function (t) { return t.id !== id; });
      Store().render();
    }, 3000);
  }

  /* ---------------- notification + server-request handlers ---------------- */
  function onNotify(method, params) {
    // Capture a couple of fields the reducer doesn't model.
    if (method === 'on_cost_update' && params && params.pct != null) Live._costPct = params.pct;
    if ((method === 'on_status' || method === 'on_chat_ack') && params) {
      var S = Store().state;
      if (params.model) S.model = params.model;
      if (params.mode) S.mode = params.mode;
    }
    Live._R = Reducer.apply(Live._R, method, params);
    if (method === 'on_error' || method === 'on_warning') {
      var msg = (params && (params.message || params.error)) || 'backend issue';
      liteToast((method === 'on_error' ? 'Error: ' : 'Warning: ') + msg);
    }
    syncActive();
  }

  function onServerRequest(method, params) {
    // Hold the reply until the user answers; mirror into reducer + approval card.
    return new global.Promise(function (resolve) {
      Live._approvalResolve = resolve;
      Live._approvalRpcKey = 'srv-' + Date.now();
      Live._R = Reducer.apply(Live._R, method, Object.assign({ rpcId: Live._approvalRpcKey }, params));
      Store().state.approval = 'pending';
      Store().state.showApprovalOut = false;
      syncActive();
    });
  }

  function settleApproval(decision, uiState) {
    if (Live._approvalResolve) { Live._approvalResolve({ decision: decision }); Live._approvalResolve = null; }
    if (Live._approvalRpcKey != null) {
      Live._R = Reducer.apply(Live._R, 'approval_resolve', { rpcId: Live._approvalRpcKey, decision: decision });
      Live._approvalRpcKey = null;
    }
    Store().state.approval = uiState;
    syncActive();
  }

  /* ---------------- public API consumed by app.js seams ---------------- */
  Live.sessions = function () {
    var S = Store().state;
    // Locally created threads (from the composer) merged with server sessions.
    var local = S.newThreads.map(function (t) {
      return { id: t.id, title: t.title, meta: t.meta, group: t.group || 'active',
               running: !!S.thinking[t.id] || !!t.running, done: !!t.done, badge: t.badge, badgeKind: t.badgeKind };
    });
    var seen = {}; local.forEach(function (t) { seen[t.id] = 1; });
    var remote = Live._threads.filter(function (t) { return !seen[t.id]; });
    return local.concat(remote);
  };
  Live.cost = function () { return { pct: Live._costPct != null ? Live._costPct : 62 }; };
  Live.skillsPop = function () {
    if (Live._skills.length) return Live._skills.map(function (s) { return { cmd: s.cmd, desc: s.desc }; });
    return DEMO().SKILLS_POP || [];
  };
  Live.skillCards = function () {
    if (Live._skills.length) return Live._skills.map(function (s) { return { cmd: s.cmd, desc: s.desc, meta: 'live' }; });
    return DEMO().SKILL_CARDS || [];
  };

  Live.sendHome = function (id, text) {
    Live._activeId = id;
    Live._activeTitle = text.length > 44 ? text.slice(0, 44) + '…' : text;
    resetReducer();
    Store().state.extras[id] = [];
    RPC.request('chat', { text: text, session_id: id, model: Store().state.model, mode: Store().state.mode })
      .catch(function (e) { liteToast('chat failed: ' + e.message); });
  };
  Live.sendThread = function (tid, text) {
    Live._activeId = tid;
    Store().state.extras[tid] = [];
    RPC.request('chat', { text: text, session_id: tid, model: Store().state.model, mode: Store().state.mode })
      .catch(function (e) { liteToast('chat failed: ' + e.message); });
  };
  Live.openThread = function (id) {
    Live._activeId = id;
    resetReducer();
    Store().state.extras[id] = [];
    RPC.request('session.resume', { session_id: id }).then(function (r) {
      var tr = r && r.transcript;
      if (Array.isArray(tr)) tr.forEach(function (ev) { Live._R = Reducer.apply(Live._R, ev.method || ev.type, ev.params || ev); });
      syncActive();
    }).catch(function () { /* leave empty on failure */ });
  };
  Live.newThread = function () { /* session.new is issued lazily on first send; nothing to do here */ };
  Live.onSearch = function (_q) { /* client-side filter handled by allThreads() */ };

  Live.setMode = function (label) { RPC.request('config.set', { mode: label }).catch(function () {}); };
  Live.setModel = function (label) { RPC.request('config.set', { model: label }).catch(function () {}); };
  Live.setReasoning = function (r) { RPC.request('config.set', { reasoning: r }).catch(function () {}); };

  Live.approve = function () { settleApproval('allow', 'ok'); };
  Live.deny = function () { settleApproval('deny', 'no'); };
  Live.cancel = function () { RPC.request('cancel', {}).catch(function () {}); };

  /* ---------------- lifecycle ---------------- */
  Live.connect = function (url) {
    resetReducer();
    RPC.onNotification(onNotify);
    RPC.onServerRequest(onServerRequest);
    RPC.onStatus(function (s) {
      if (s === 'closed' || s === 'reconnecting') { /* keep last-known UI; banner optional */ }
    });
    return RPC.connect(url).then(function () {
      Live.enabled = true;
      return global.Promise.all([
        RPC.request('session.list').then(function (r) { Live._threads = (r && r.sessions ? r.sessions : []).map(mapSession); }).catch(function () {}),
        RPC.request('command.list').then(function (r) { Live._skills = (r && r.commands) ? r.commands : []; }).catch(function () {}),
        RPC.request('config.get').then(function (r) {
          if (r) { var S = Store().state; if (r.model) S.model = r.model; if (r.mode) S.mode = r.mode; }
        }).catch(function () {})
      ]).then(function () { if (Store()) Store().render(); return true; });
    });
  };

  global.Live = Live;
})(typeof globalThis !== 'undefined' ? globalThis : this);
