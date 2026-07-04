/*
 * rpc.js — WebSocket JSON-RPC 2.0 client for the AutoCode WebUI.
 *
 * Classic browser script (NO ES module exports). Attaches `window.RPC`.
 * Dependency-free: uses only globalThis.WebSocket + timers, so it also runs
 * under Deno (native WebSocket) for the e2e gate.
 *
 * Contract (see docs/plan/webui-integration-plan.md §4 and agent-events.md):
 *   RPC.connect(url)            -> Promise (resolves on open)
 *   RPC.onStatus(fn)            -> fn('connecting'|'open'|'closed'|'reconnecting')
 *   RPC.request(method, params) -> Promise (id-correlated; rejects on JSON-RPC error/timeout)
 *   RPC.notify(method, params)  -> void (fire-and-forget)
 *   RPC.onNotification(fn)      -> fn(method, params)   [server notification: no id]
 *   RPC.onServerRequest(fn)     -> fn(method, params) => Promise<result>
 *                                  [server-initiated request: has id + method — e.g.
 *                                   on_tool_request / on_ask_user; we reply with a response]
 *   RPC.close()                 -> void (intentional close; no reconnect)
 *   RPC.isOpen()                -> boolean
 */
(function (global) {
  'use strict';

  var RPC = {};
  var ws = null;
  var url = null;
  var wantOpen = false;          // true between connect() and close()
  var nextId = 1;
  var pending = {};              // id -> { resolve, reject, timer }
  var notifHandlers = [];
  var statusHandlers = [];
  var serverReqHandler = null;
  var reconnectAttempts = 0;
  var reconnectTimer = null;
  var REQUEST_TIMEOUT_MS = 30000;
  var MAX_BACKOFF_MS = 10000;

  function emitStatus(s) {
    for (var i = 0; i < statusHandlers.length; i++) {
      try { statusHandlers[i](s); } catch (e) { /* isolate */ }
    }
  }
  function send(obj) {
    if (ws && ws.readyState === 1) { ws.send(JSON.stringify(obj)); return true; }
    return false;
  }

  RPC.onStatus = function (fn) { if (typeof fn === 'function') statusHandlers.push(fn); };
  RPC.onNotification = function (fn) { if (typeof fn === 'function') notifHandlers.push(fn); };
  RPC.onServerRequest = function (fn) { serverReqHandler = (typeof fn === 'function') ? fn : null; };
  RPC.isOpen = function () { return !!ws && ws.readyState === 1; };

  RPC.connect = function (u) {
    url = u || url;
    wantOpen = true;
    return openSocket();
  };

  function openSocket() {
    return new Promise(function (resolve, reject) {
      var settled = false;
      try {
        emitStatus(reconnectAttempts > 0 ? 'reconnecting' : 'connecting');
        ws = new global.WebSocket(url);
      } catch (e) { reject(e); return; }

      ws.onopen = function () {
        reconnectAttempts = 0;
        emitStatus('open');
        if (!settled) { settled = true; resolve(); }
      };
      ws.onmessage = function (ev) { handleMessage(ev.data); };
      ws.onerror = function () { /* onclose follows; surface there */ };
      ws.onclose = function () {
        emitStatus('closed');
        // Reject any in-flight requests so callers don't hang.
        for (var id in pending) if (pending.hasOwnProperty(id)) {
          clearTimeout(pending[id].timer);
          try { pending[id].reject(new Error('socket closed')); } catch (e) {}
        }
        pending = {};
        if (!settled) { settled = true; reject(new Error('connection failed')); }
        if (wantOpen) scheduleReconnect();
      };
    });
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectAttempts++;
    var delay = Math.min(MAX_BACKOFF_MS, 300 * Math.pow(2, reconnectAttempts - 1));
    reconnectTimer = global.setTimeout(function () {
      reconnectTimer = null;
      if (wantOpen) openSocket().catch(function () { /* onclose reschedules */ });
    }, delay);
  }

  function handleMessage(data) {
    var msg;
    try { msg = JSON.parse(data); } catch (e) { return; } // malformed frame: ignore
    if (msg == null || typeof msg !== 'object') return;

    // Batch (array) — handle each element.
    if (Object.prototype.toString.call(msg) === '[object Array]') {
      for (var i = 0; i < msg.length; i++) handleOne(msg[i]);
      return;
    }
    handleOne(msg);
  }

  function handleOne(msg) {
    if (msg == null || typeof msg !== 'object') return;
    var hasId = Object.prototype.hasOwnProperty.call(msg, 'id') && msg.id !== null && msg.id !== undefined;
    var hasMethod = typeof msg.method === 'string';

    if (hasMethod && hasId) { handleServerRequest(msg); return; }   // server-initiated request
    if (hasMethod && !hasId) { handleNotification(msg); return; }   // notification
    if (hasId) { handleResponse(msg); return; }                     // response to our request
    // else: nothing actionable
  }

  function handleNotification(msg) {
    for (var i = 0; i < notifHandlers.length; i++) {
      try { notifHandlers[i](msg.method, msg.params || {}); } catch (e) { /* isolate */ }
    }
  }

  function handleResponse(msg) {
    var p = pending[msg.id];
    if (!p) return;
    delete pending[msg.id];
    clearTimeout(p.timer);
    if (Object.prototype.hasOwnProperty.call(msg, 'error') && msg.error) {
      var err = new Error((msg.error && msg.error.message) || 'RPC error');
      err.code = msg.error && msg.error.code;
      err.data = msg.error && msg.error.data;
      p.reject(err);
    } else {
      p.resolve(msg.result);
    }
  }

  function handleServerRequest(msg) {
    if (!serverReqHandler) {
      // No handler — refuse politely so the server isn't left waiting.
      send({ jsonrpc: '2.0', id: msg.id, error: { code: -32601, message: 'no client handler' } });
      return;
    }
    var out;
    try { out = serverReqHandler(msg.method, msg.params || {}); }
    catch (e) { send({ jsonrpc: '2.0', id: msg.id, error: { code: -32000, message: String(e && e.message || e) } }); return; }
    Promise.resolve(out).then(function (result) {
      send({ jsonrpc: '2.0', id: msg.id, result: result === undefined ? null : result });
    }, function (e) {
      send({ jsonrpc: '2.0', id: msg.id, error: { code: -32000, message: String(e && e.message || e) } });
    });
  }

  RPC.request = function (method, params) {
    return new Promise(function (resolve, reject) {
      var id = nextId++;
      var timer = global.setTimeout(function () {
        if (pending[id]) { delete pending[id]; reject(new Error('request timeout: ' + method)); }
      }, REQUEST_TIMEOUT_MS);
      pending[id] = { resolve: resolve, reject: reject, timer: timer };
      var ok = send({ jsonrpc: '2.0', id: id, method: method, params: params || {} });
      if (!ok) { clearTimeout(timer); delete pending[id]; reject(new Error('socket not open')); }
    });
  };

  RPC.notify = function (method, params) {
    send({ jsonrpc: '2.0', method: method, params: params || {} });
  };

  RPC.close = function () {
    wantOpen = false;
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    if (ws) { try { ws.close(); } catch (e) {} }
  };

  // Test seam: reset module state (used by headless tests that reconnect).
  RPC._reset = function () {
    RPC.close();
    ws = null; pending = {}; notifHandlers = []; statusHandlers = [];
    serverReqHandler = null; nextId = 1; reconnectAttempts = 0;
  };

  global.RPC = RPC;
})(typeof globalThis !== 'undefined' ? globalThis : this);
