/*
 * events.js — AgentEvent reducer for the AutoCode WebUI.
 *
 * Classic browser script (NO ES module exports). Attaches `window.Reducer`.
 * Pure and DOM-free: `Reducer.apply(state, method, params)` returns a NEW state
 * and never mutates its input. Also loadable in Deno via indirect eval.
 *
 * Contract source of truth: docs/features/agent-events.md
 *   - duplicate event ids are silently deduplicated
 *   - `timestamp` is the authoritative sort key if delivery order is disrupted
 *   - `parentId` links a tool result to its originating tool start
 *   - malformed events are logged (console.warn) and skipped, never thrown
 *
 * `method` is the RPC notification name (on_token, on_thinking, ...). A few
 * client-synthesized methods (approval_resolve, session_list, connection) are
 * also accepted for local/optimistic updates; see the switch below. Every
 * assumption is documented in the T1 evidence file.
 */
(function (global) {
  'use strict';

  var Reducer = {};
  var warn = function (msg, extra) {
    var c = global.console;
    if (c && c.warn) { if (extra !== undefined) c.warn(msg, extra); else c.warn(msg); }
  };

  /* ---------------- initial state ---------------- */
  Reducer.createState = function () {
    return {
      connection: 'idle',
      session: { id: null, model: null, provider: null, mode: null },
      sessions: [],
      transcript: [],
      thinking: false,
      pendingApprovals: [],
      cost: { cost: 0, tokensIn: 0, tokensOut: 0 },
      tasks: [],
      errors: [],
      __seen: {}, // dedup: event id -> true
      __seq: 0    // monotonic insertion counter for stable timestamp ties
    };
  };

  /* ---------------- immutable helpers ---------------- */
  function clone(s) {
    return {
      connection: s.connection,
      session: { id: s.session.id, model: s.session.model, provider: s.session.provider, mode: s.session.mode },
      sessions: s.sessions,
      transcript: s.transcript.slice(),
      thinking: s.thinking,
      pendingApprovals: s.pendingApprovals.slice(),
      cost: { cost: s.cost.cost, tokensIn: s.cost.tokensIn, tokensOut: s.cost.tokensOut },
      tasks: s.tasks,
      errors: s.errors.slice(),
      __seen: assign({}, s.__seen),
      __seq: s.__seq
    };
  }
  function assign(t, src) { for (var k in src) if (Object.prototype.hasOwnProperty.call(src, k)) t[k] = src[k]; return t; }

  function tsOf(p) {
    if (!p || p.timestamp == null) return null;
    var t = Date.parse(p.timestamp);
    return isNaN(t) ? null : t;
  }
  function sortTranscript(s) {
    // Stable sort by (timestamp, insertion-seq). All event-derived rows carry a
    // ts, so a late event with an earlier timestamp is repositioned correctly.
    s.transcript.sort(function (a, b) {
      var ta = a.ts == null ? Infinity : a.ts;
      var tb = b.ts == null ? Infinity : b.ts;
      if (ta !== tb) return ta - tb;
      return (a.seq || 0) - (b.seq || 0);
    });
  }
  function removeThinkingRows(s) {
    s.transcript = s.transcript.filter(function (r) { return r.kind !== 'thinking'; });
  }

  /* ---------------- tool-call helpers ---------------- */
  function iconForTool(tool) {
    tool = String(tool || '').toLowerCase();
    if (/read|list|grep|search|cat|open|glob|view/.test(tool)) return 'read';
    if (/run|command|bash|shell|exec|test|vitest|pnpm|npm|cargo|make/.test(tool)) return 'term';
    if (/edit|write|patch|apply|create|modify|delete|move/.test(tool)) return 'edit';
    return 'read';
  }
  // Tool-call identity: carried by `callId`. Falls back to the event id (for a
  // start) or parentId (for a result), so the first start event's id doubles as
  // the row key — honoring "keyed by event id" while surviving status updates.
  function toolKey(p, isResult) {
    if (p.callId != null) return p.callId;
    if (isResult) return p.parentId != null ? p.parentId : p.id;
    return p.id;
  }
  function findActIndex(s, key) {
    for (var i = 0; i < s.transcript.length; i++) {
      var r = s.transcript[i];
      if (r.kind === 'act' && (r.id === key || r.callId === key)) return i;
    }
    return -1;
  }
  function applyResult(row, p) {
    var res = p.result || p;
    if (res.files != null) row.files = res.files;
    if (res.output != null) row.term = res.output;
    else if (res.term != null) row.term = res.term;
    else if (res.stdout != null) row.term = res.stdout;
    if (res.diff != null) row.diff = res.diff;
    if (p.meta != null) row.meta = p.meta;
    else if (res.meta != null) row.meta = res.meta;
    if (res.ok === false || p.status === 'failed') row.bad = true;
    row.status = p.status || 'done';
  }

  function currentAnswerIndex(s) {
    for (var i = s.transcript.length - 1; i >= 0; i--) {
      var r = s.transcript[i];
      if (r.kind === 'answer' && r.inProgress) return i;
    }
    return -1;
  }
  function splitParas(buf) {
    return buf.split(/\n\n+/).filter(function (x) { return x.length > 0; });
  }

  /* ---------------- per-method handlers ---------------- */
  function onToken(state, p) {
    var text = p.text != null ? p.text : (p.content != null ? p.content : p.delta);
    if (typeof text !== 'string') { warn('Reducer: on_token missing text', p); return state; }
    var s = clone(state);
    if (s.thinking) { s.thinking = false; removeThinkingRows(s); }
    var idx = currentAnswerIndex(s);
    var row;
    if (idx < 0) {
      row = { kind: 'answer', paras: [], meta: '', _buf: '', inProgress: true, ts: tsOf(p), seq: ++s.__seq };
      s.transcript.push(row);
    } else {
      row = assign({}, s.transcript[idx]);
      s.transcript[idx] = row;
    }
    row._buf = (row._buf || '') + text;
    row.paras = splitParas(row._buf);
    sortTranscript(s);
    return s;
  }

  function onThinking(state, p) {
    var s = clone(state);
    var off = p.status === 'done' || p.status === 'cancelled' || p.done === true;
    if (off) {
      s.thinking = false; removeThinkingRows(s);
    } else {
      s.thinking = true;
      var has = s.transcript.some(function (r) { return r.kind === 'thinking'; });
      if (!has) s.transcript.push({ kind: 'thinking', text: p.text || '', ts: tsOf(p), seq: ++s.__seq });
    }
    sortTranscript(s);
    return s;
  }

  function onToolCall(state, p) {
    var isResult = (p.type === 'ToolResultEvent') ||
      (p.type !== 'ToolStartEvent' && (p.result != null || p.parentId != null));
    var key = toolKey(p, isResult);
    if (key == null) { warn('Reducer: on_tool_call missing id/callId', p); return state; }
    var s = clone(state);
    var idx = findActIndex(s, key);
    var row;
    if (idx < 0) {
      row = {
        kind: 'act', id: key, callId: key,
        icon: iconForTool(p.tool),
        label: p.title || p.label || (p.tool || 'tool'),
        meta: p.meta || '',
        status: p.status || (isResult ? 'done' : 'pending'),
        ts: tsOf(p), seq: ++s.__seq
      };
      if (isResult) applyResult(row, p);
      s.transcript.push(row);
    } else {
      row = assign({}, s.transcript[idx]);
      if (p.title || p.label) row.label = p.title || p.label;
      if (p.tool) row.icon = iconForTool(p.tool);
      if (p.status) row.status = p.status;
      if (p.meta != null) row.meta = p.meta;
      if (isResult) applyResult(row, p);
      s.transcript[idx] = row;
    }
    sortTranscript(s);
    return s;
  }

  function doneMeta(state, p) {
    var parts = [];
    var model = state.session.model || p.model;
    if (model) parts.push(model);
    if (p.layer_used != null) parts.push('L' + p.layer_used);
    if (p.tokens_in != null || p.tokens_out != null) parts.push((p.tokens_in || 0) + ' in / ' + (p.tokens_out || 0) + ' out');
    if (p.cancelled) parts.push('cancelled');
    return parts.join(' · ');
  }
  function onDone(state, p) {
    var s = clone(state);
    s.thinking = false; removeThinkingRows(s);
    var idx = currentAnswerIndex(s);
    if (idx >= 0) {
      var r = assign({}, s.transcript[idx]);
      r.inProgress = false;
      r.meta = doneMeta(state, p);
      if (p.cancelled) r.cancelled = true;
      s.transcript[idx] = r;
    } else if (p.cancelled) {
      s.transcript.push({ kind: 'answer', paras: [], meta: doneMeta(state, p), _buf: '', inProgress: false, cancelled: true, ts: tsOf(p), seq: ++s.__seq });
    }
    sortTranscript(s);
    return s;
  }

  function onStatus(state, p) {
    var s = clone(state);
    if (p.model != null) s.session.model = p.model;
    if (p.provider != null) s.session.provider = p.provider;
    if (p.mode != null) s.session.mode = p.mode;
    if (p.session_id != null) s.session.id = p.session_id;
    else if (p.sessionId != null) s.session.id = p.sessionId;
    return s;
  }

  function onRecovery(state, p, level) {
    var s = clone(state);
    s.errors = s.errors.concat([{
      level: level,
      message: p.message != null ? p.message : (p.error != null ? p.error : ''),
      timestamp: p.timestamp != null ? p.timestamp : null,
      id: p.id != null ? p.id : null
    }]);
    return s;
  }

  function onCost(state, p) {
    var s = clone(state);
    s.cost = {
      cost: p.cost != null ? p.cost : s.cost.cost,
      tokensIn: p.tokens_in != null ? p.tokens_in : (p.tokensIn != null ? p.tokensIn : s.cost.tokensIn),
      tokensOut: p.tokens_out != null ? p.tokens_out : (p.tokensOut != null ? p.tokensOut : s.cost.tokensOut)
    };
    return s;
  }

  function onTaskState(state, p) {
    var s = clone(state);
    if (Array.isArray(p.tasks)) s.tasks = p.tasks.slice();
    else if (Array.isArray(p)) s.tasks = p.slice();
    return s;
  }

  function onChatAck(state, p) {
    var s = clone(state);
    if (p.session_id != null) s.session.id = p.session_id;
    else if (p.sessionId != null) s.session.id = p.sessionId;
    if (p.model != null) s.session.model = p.model;
    if (p.mode != null) s.session.mode = p.mode;
    // The ack echoes the acknowledged prompt so the transcript stays
    // event-sourced and replay-identical (agent-events.md persistence rule).
    var text = p.text != null ? p.text : (p.message != null ? p.message : p.prompt);
    if (typeof text === 'string' && text.length) {
      s.transcript.push({ kind: 'user', text: text, ts: tsOf(p), seq: ++s.__seq });
      sortTranscript(s);
    }
    return s;
  }

  function onApprovalRequest(state, p, kind) {
    var s = clone(state);
    var rpcId = p.rpcId != null ? p.rpcId : (p.rpc_id != null ? p.rpc_id : p.id);
    s.pendingApprovals = s.pendingApprovals.concat([{ rpcId: rpcId, kind: kind, payload: p }]);
    var row = { kind: 'approval', rpcId: rpcId, approvalKind: kind, status: 'pending', ts: tsOf(p), seq: ++s.__seq };
    if (kind === 'tool') {
      row.title = p.title || 'Approval needed';
      row.tool = p.tool || (p.args && p.args.tool) || '';
      row.command = p.command || (p.args && (p.args.command || p.args.cmd)) || '';
      row.detail = p.detail || p.reason || '';
    } else {
      row.title = p.title || 'Question';
      row.question = p.question || p.prompt || '';
      row.options = p.options || [];
      row.allowText = p.allow_text != null ? p.allow_text : (p.allowText || false);
    }
    s.transcript.push(row);
    sortTranscript(s);
    return s;
  }

  // Client-synthesized: called by the app after the user answers an approval.
  function onApprovalResolve(state, p) {
    var s = clone(state);
    var rpcId = p.rpcId;
    s.pendingApprovals = s.pendingApprovals.filter(function (a) { return a.rpcId !== rpcId; });
    for (var i = 0; i < s.transcript.length; i++) {
      var r = s.transcript[i];
      if (r.kind === 'approval' && r.rpcId === rpcId) {
        var nr = assign({}, r);
        nr.status = (p.decision === 'deny' || p.decision === 'reject') ? 'denied' : 'ok';
        if (p.answer != null) nr.answer = p.answer;
        s.transcript[i] = nr;
      }
    }
    return s;
  }

  function onSessionList(state, p) {
    var s = clone(state);
    if (Array.isArray(p.sessions)) s.sessions = p.sessions.slice();
    else if (Array.isArray(p)) s.sessions = p.slice();
    return s;
  }

  function onConnection(state, p) {
    var s = clone(state);
    s.connection = p.status || p.connection || s.connection;
    return s;
  }

  /* ---------------- dispatch ---------------- */
  function applyInner(state, method, params) {
    if (params == null || typeof params !== 'object') {
      warn('Reducer: malformed params for ' + method, params);
      return state;
    }
    // Dedup by event id (checked before apply; marked after a real change).
    if (params.id != null && state.__seen[params.id]) return state;

    var s;
    switch (method) {
      case 'on_token': s = onToken(state, params); break;
      case 'on_thinking': s = onThinking(state, params); break;
      case 'on_tool_call': s = onToolCall(state, params); break;
      case 'on_done': s = onDone(state, params); break;
      case 'on_status': s = onStatus(state, params); break;
      case 'on_error': s = onRecovery(state, params, 'error'); break;
      case 'on_warning': s = onRecovery(state, params, 'warning'); break;
      case 'on_cost_update': s = onCost(state, params); break;
      case 'on_task_state': s = onTaskState(state, params); break;
      case 'on_chat_ack': s = onChatAck(state, params); break;
      case 'on_tool_request': s = onApprovalRequest(state, params, 'tool'); break;
      case 'on_ask_user': s = onApprovalRequest(state, params, 'ask'); break;
      // client-synthesized (documented; not RPC notifications)
      case 'approval_resolve': s = onApprovalResolve(state, params); break;
      case 'session_list': s = onSessionList(state, params); break;
      case 'connection': s = onConnection(state, params); break;
      default:
        warn('Reducer: unknown method ' + method);
        return state;
    }
    // Only mark seen when the event actually changed state (s is a fresh clone).
    if (params.id != null && s !== state) s.__seen[params.id] = true;
    return s;
  }

  Reducer.apply = function (state, method, params) {
    try {
      return applyInner(state, method, params);
    } catch (e) {
      warn('Reducer: error applying ' + method, e);
      return state;
    }
  };

  // exported for white-box tests / T3 helpers
  Reducer._internals = { iconForTool: iconForTool, splitParas: splitParas };

  global.Reducer = Reducer;
})(typeof globalThis !== 'undefined' ? globalThis : this);
