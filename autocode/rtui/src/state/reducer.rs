use std::time::Duration;

use crate::rpc::protocol::RPCMessage;
use crate::state::model::Stage;

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub enum Event {
    Key(crossterm::event::KeyEvent),
    Resize(u16, u16),
    Tick,

    RpcNotification(RPCMessage),
    RpcResponse(RPCMessage),
    RpcInboundRequest(RPCMessage),

    BackendExit(i32),
    BackendError(String),
    EditorDone(String),
    Paste(String),
}

impl Event {
    pub fn from_rpc(msg: RPCMessage) -> Self {
        let has_id = msg.id.is_some();
        let has_method = msg.method.as_ref().is_some_and(|m| !m.is_empty());

        match (has_id, has_method) {
            (false, true) => Event::RpcNotification(msg),
            (true, false) => Event::RpcResponse(msg),
            (true, true) => Event::RpcInboundRequest(msg),
            (false, false) => Event::RpcNotification(msg),
        }
    }

    pub fn from_crossterm(evt: crossterm::event::Event) -> Option<Self> {
        match evt {
            crossterm::event::Event::Key(k) => Some(Event::Key(k)),
            crossterm::event::Event::Resize(w, h) => Some(Event::Resize(w, h)),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum Effect {
    SendRpc(RPCMessage),
    Render,
    Quit,
    ResizePty(u16, u16),
    SpawnEditor(String),
}

const STALE_REQUEST_TIMEOUT: Duration = Duration::from_secs(30);

pub fn reduce(
    state: crate::state::model::AppState,
    event: Event,
) -> (crate::state::model::AppState, Vec<Effect>) {
    match event {
        Event::Key(key) => handle_key(state, key),
        Event::Resize(w, h) => {
            let mut s = state;
            s.terminal_size = (w, h);
            (s, vec![Effect::ResizePty(w, h), Effect::Render])
        }
        Event::Tick => handle_tick(state),
        Event::RpcNotification(msg) => handle_notification(state, msg),
        Event::RpcResponse(msg) => handle_response(state, msg),
        Event::RpcInboundRequest(msg) => handle_inbound_request(state, msg),
        Event::BackendExit(_) => {
            let mut s = state;
            s.stage = crate::state::model::Stage::Shutdown;
            (s, vec![Effect::Quit])
        }
        Event::BackendError(err) => {
            let mut s = state;
            s.error_banner = Some(err);
            (s, vec![Effect::Render])
        }
        Event::EditorDone(text) => {
            let mut s = state;
            s.composer_text = text;
            s.composer_cursor = s.composer_text.len();
            s.error_banner = None;
            (s, vec![Effect::Render])
        }
        Event::Paste(text) => {
            let mut s = state;
            let pos = s.composer_cursor;
            s.composer_text.insert_str(pos, &text);
            s.composer_cursor += text.len();
            (s, vec![Effect::Render])
        }
    }
}

fn handle_key(
    mut state: crate::state::model::AppState,
    key: crossterm::event::KeyEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::{KeyCode, KeyModifiers};

    match (key.modifiers, key.code) {
        (KeyModifiers::CONTROL, KeyCode::Char('c')) => match &state.stage {
            Stage::Idle => {
                let id = state.next_request_id;
                state.next_request_id += 1;
                let msg = crate::rpc::protocol::RPCMessage {
                    jsonrpc: "2.0".to_string(),
                    id: Some(id),
                    method: Some("cancel".to_string()),
                    params: Some(serde_json::json!({})),
                    result: None,
                    error: None,
                };
                state.pending_requests.insert(
                    id,
                    crate::state::model::PendingRequest {
                        method: "cancel".to_string(),
                        sent_at: std::time::Instant::now(),
                    },
                );
                (state, vec![Effect::SendRpc(msg), Effect::Render])
            }
            Stage::Streaming => {
                state.stage = Stage::AskUser;
                state.ask_user = Some(crate::state::model::AskUserRequest {
                    rpc_id: 0,
                    question: "Steer message: ".to_string(),
                    options: vec![],
                    allow_text: true,
                    selected: 0,
                    free_text: String::new(),
                });
                (state, vec![Effect::Render])
            }
            Stage::AskUser => {
                state.ask_user = None;
                state.stage = Stage::Streaming;
                (state, vec![Effect::Render])
            }
            _ => {
                state.stage = Stage::Shutdown;
                (state, vec![Effect::Quit])
            }
        },
        (KeyModifiers::CONTROL, KeyCode::Char('k')) => {
            state.palette = Some(crate::state::model::PaletteState {
                filter: String::new(),
                cursor: 0,
                entries: vec![
                    crate::state::model::PaletteEntry {
                        name: "/clear".into(),
                        description: "Clear scrollback".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/exit".into(),
                        description: "Exit TUI".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/fork".into(),
                        description: "Fork session".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/compact".into(),
                        description: "Compact context".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/plan".into(),
                        description: "Toggle plan mode".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/sessions".into(),
                        description: "List sessions".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/model".into(),
                        description: "Change model".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/provider".into(),
                        description: "Change provider".into(),
                    },
                    crate::state::model::PaletteEntry {
                        name: "/help".into(),
                        description: "Show help".into(),
                    },
                ],
            });
            state.stage = crate::state::model::Stage::Palette;
            (state, vec![Effect::Render])
        }
        (KeyModifiers::CONTROL, KeyCode::Char('l')) => {
            state.scrollback.clear();
            state.stream_buf.clear();
            state.stream_lines.clear();
            (state, vec![Effect::Render])
        }
        (KeyModifiers::CONTROL, KeyCode::Char('e')) => {
            if let Ok(editor) = std::env::var("EDITOR") {
                state.composer_lines = state.composer_text.lines().map(String::from).collect();
                state.error_banner = Some(format!("Launching {}...", editor));
                (state, vec![Effect::SpawnEditor(editor), Effect::Render])
            } else {
                state.error_banner = Some("$EDITOR not set".to_string());
                (state, vec![Effect::Render])
            }
        }
        // Up/Down: history browse in Idle
        (KeyModifiers::NONE, KeyCode::Up) if state.stage == crate::state::model::Stage::Idle => {
            if !state.history.is_empty() {
                let idx = state.history_cursor.map_or(0, |c| c.saturating_sub(1));
                if idx < state.history.len() {
                    state.composer_text = state.history[idx].text.clone();
                    state.composer_cursor = state.composer_text.len();
                    state.history_cursor = Some(idx);
                }
            }
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Down) if state.stage == crate::state::model::Stage::Idle => {
            if let Some(idx) = state.history_cursor {
                if idx + 1 < state.history.len() {
                    state.composer_text = state.history[idx + 1].text.clone();
                    state.composer_cursor = state.composer_text.len();
                    state.history_cursor = Some(idx + 1);
                } else {
                    state.composer_text.clear();
                    state.composer_cursor = 0;
                    state.history_cursor = None;
                }
            }
            (state, vec![Effect::Render])
        }
        // Palette key handling
        _ if state.stage == crate::state::model::Stage::Palette => handle_palette_key(state, &key),
        // Picker key handling
        _ if matches!(state.stage, crate::state::model::Stage::Picker(_)) => {
            handle_picker_key(state, &key)
        }
        // Approval key handling
        _ if state.stage == crate::state::model::Stage::Approval => {
            handle_approval_key(state, &key)
        }
        // AskUser key handling
        _ if state.stage == crate::state::model::Stage::AskUser => handle_ask_user_key(state, &key),
        // Composer key handling
        _ => crate::ui::composer::Composer::handle_key(state, &key),
    }
}

fn handle_palette_key(
    mut state: crate::state::model::AppState,
    key: &crossterm::event::KeyEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::{KeyCode, KeyModifiers};

    let mut effects = vec![];
    match (key.modifiers, key.code) {
        (KeyModifiers::NONE, KeyCode::Esc) => {
            state.stage = crate::state::model::Stage::Idle;
            state.palette = None;
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Enter) => {
            if let Some(palette) = &state.palette {
                if let Some(entry) = palette.entries.get(palette.cursor) {
                    let cmd = entry.name.clone();
                    effects.extend(handle_slash_command(&mut state, &cmd));
                }
            }
            state.stage = crate::state::model::Stage::Idle;
            state.palette = None;
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Up) => {
            if let Some(palette) = &mut state.palette {
                if palette.cursor > 0 {
                    palette.cursor -= 1;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Down) => {
            if let Some(palette) = &mut state.palette {
                let max = palette.entries.len().saturating_sub(1);
                if palette.cursor < max {
                    palette.cursor += 1;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Char(c)) => {
            if let Some(palette) = &mut state.palette {
                palette.filter.push(c);
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Backspace) => {
            if let Some(palette) = &mut state.palette {
                palette.filter.pop();
            }
            effects.push(Effect::Render);
        }
        _ => {}
    }
    (state, effects)
}

pub(crate) fn handle_slash_command(
    state: &mut crate::state::model::AppState,
    cmd: &str,
) -> Vec<Effect> {
    let mut effects = vec![];
    match cmd {
        "/clear" => {
            state.scrollback.clear();
            state.stream_buf.clear();
            state.stream_lines.clear();
            effects.push(Effect::Render);
        }
        "/exit" => {
            effects.push(Effect::Quit);
        }
        "/plan" => {
            state.plan_mode = !state.plan_mode;
            effects.push(Effect::Render);
        }
        "/fork" => {
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("session.fork".to_string()),
                params: Some(serde_json::json!({})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "session.fork".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
        }
        "/compact" => {
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("command".to_string()),
                params: Some(serde_json::json!({"cmd": "/compact"})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "command".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
        }
        "/sessions" | "/resume" => {
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("session.list".to_string()),
                params: Some(serde_json::json!({})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "session.list".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
        }
        "/model" => {
            state.picker = Some(crate::state::model::PickerState {
                kind: crate::state::model::PickerKind::Model,
                entries: vec!["tools".into(), "coding".into(), "fast".into()],
                filter: String::new(),
                cursor: 0,
            });
            state.stage =
                crate::state::model::Stage::Picker(crate::state::model::PickerKind::Model);
            effects.push(Effect::Render);
        }
        "/provider" => {
            state.picker = Some(crate::state::model::PickerState {
                kind: crate::state::model::PickerKind::Provider,
                entries: vec!["openrouter".into(), "anthropic".into(), "openai".into()],
                filter: String::new(),
                cursor: 0,
            });
            state.stage =
                crate::state::model::Stage::Picker(crate::state::model::PickerKind::Provider);
            effects.push(Effect::Render);
        }
        "/help" => {
            state.scrollback.push_back("Available commands: /clear /exit /fork /compact /plan /sessions /resume /model /provider /help".into());
            effects.push(Effect::Render);
        }
        _ => {}
    }
    effects
}

fn handle_tick(
    mut state: crate::state::model::AppState,
) -> (crate::state::model::AppState, Vec<Effect>) {
    // Spinner rotation
    if state.stage == crate::state::model::Stage::Streaming {
        state.spinner_frame = (state.spinner_frame + 1) % 4;
        if state.spinner_frame == 0 {
            state.spinner_verb_idx = (state.spinner_verb_idx + 1) % 194;
        }
    }

    // Stale request detection
    let now = std::time::Instant::now();
    let stale_ids: Vec<i64> = state
        .pending_requests
        .iter()
        .filter(|(_, req)| now.duration_since(req.sent_at) > STALE_REQUEST_TIMEOUT)
        .map(|(&id, _)| id)
        .collect();

    let mut effects = vec![];
    for id in stale_ids {
        if let Some(req) = state.pending_requests.remove(&id) {
            tracing::warn!(
                "stale RPC request: id={} method={} (>{:?} old)",
                id,
                req.method,
                STALE_REQUEST_TIMEOUT
            );
        }
        if state.error_banner.is_none() {
            state.error_banner = Some(format!("Request {} timed out", id));
            effects.push(Effect::Render);
        }
    }

    if state.stage == crate::state::model::Stage::Streaming {
        effects.push(Effect::Render);
    }

    (state, effects)
}

fn handle_notification(
    mut state: crate::state::model::AppState,
    msg: RPCMessage,
) -> (crate::state::model::AppState, Vec<Effect>) {
    match msg.method.as_deref() {
        Some("on_status") => {
            if let Some(params) = &msg.params {
                if let Ok(status) =
                    serde_json::from_value::<crate::rpc::protocol::StatusParams>(params.clone())
                {
                    state.status.model = status.model;
                    state.status.provider = status.provider;
                    state.status.mode = status.mode;
                    state.status.session_id = status.session_id;
                }
            }
            (state, vec![Effect::Render])
        }
        Some("on_error") => {
            if let Some(params) = &msg.params {
                if let Ok(err) =
                    serde_json::from_value::<crate::rpc::protocol::ErrorParams>(params.clone())
                {
                    state.error_banner = Some(err.message);
                }
            }
            (state, vec![Effect::Render])
        }
        Some("on_token") => {
            if let Some(params) = &msg.params {
                if let Ok(token) =
                    serde_json::from_value::<crate::rpc::protocol::TokenParams>(params.clone())
                {
                    state.stream_buf.push_str(&token.text);
                    state.stream_lines = state.stream_buf.split('\n').map(String::from).collect();
                    if state.stage == crate::state::model::Stage::Idle {
                        state.stage = crate::state::model::Stage::Streaming;
                    }
                    if state.stream_lines.len() > 20 {
                        let overflow = state.stream_lines.len() - 20;
                        for line in state.stream_lines.drain(..overflow) {
                            state.scrollback.push_back(line);
                        }
                        if state.scrollback.len() > 10_000 {
                            let excess = state.scrollback.len() - 10_000;
                            state.scrollback.drain(..excess);
                        }
                        state.stream_buf = state.stream_lines.join("\n");
                    }
                }
            }
            (state, vec![Effect::Render])
        }
        Some("on_thinking") => {
            if let Some(params) = &msg.params {
                if let Ok(thinking) =
                    serde_json::from_value::<crate::rpc::protocol::ThinkingParams>(params.clone())
                {
                    state.stream_buf.push_str(&thinking.text);
                    state.stream_lines = state.stream_buf.split('\n').map(String::from).collect();
                    if state.stage == crate::state::model::Stage::Idle {
                        state.stage = crate::state::model::Stage::Streaming;
                    }
                }
            }
            (state, vec![Effect::Render])
        }
        Some("on_done") => {
            if let Some(params) = &msg.params {
                if let Ok(done) =
                    serde_json::from_value::<crate::rpc::protocol::DoneParams>(params.clone())
                {
                    state.status.tokens_in = done.tokens_in;
                    state.status.tokens_out = done.tokens_out;
                }
            }
            if !state.stream_lines.is_empty() {
                for line in state.stream_lines.drain(..) {
                    state.scrollback.push_back(line);
                }
                if state.scrollback.len() > 10_000 {
                    let excess = state.scrollback.len() - 10_000;
                    state.scrollback.drain(..excess);
                }
            }
            state.stream_buf.clear();
            state.stream_lines.clear();
            state.stage = crate::state::model::Stage::Idle;

            let mut effects = vec![Effect::Render];
            if !state.followup_queue.is_empty() {
                if let Some(next_msg) = state.followup_queue.pop_front() {
                    let id = state.next_request_id;
                    state.next_request_id += 1;
                    let msg = RPCMessage {
                        jsonrpc: "2.0".to_string(),
                        id: Some(id),
                        method: Some("chat".to_string()),
                        params: Some(serde_json::json!({
                            "message": next_msg,
                        })),
                        result: None,
                        error: None,
                    };
                    state.pending_requests.insert(
                        id,
                        crate::state::model::PendingRequest {
                            method: "chat".to_string(),
                            sent_at: std::time::Instant::now(),
                        },
                    );
                    effects.push(Effect::SendRpc(msg));
                }
            }

            (state, effects)
        }
        Some("on_tool_call") => {
            if let Some(params) = &msg.params {
                if let Ok(tool) =
                    serde_json::from_value::<crate::rpc::protocol::ToolCallParams>(params.clone())
                {
                    state.current_tool = Some(crate::state::model::ToolCallInfo {
                        name: tool.name,
                        status: tool.status,
                        args: tool.args,
                        result: tool.result,
                    });
                }
            }
            (state, vec![Effect::Render])
        }
        Some("on_tasks") => {
            if let Some(params) = &msg.params {
                if let Ok(task_state) =
                    serde_json::from_value::<crate::rpc::protocol::TaskStateParams>(params.clone())
                {
                    state.tasks = task_state.tasks;
                    state.subagents = task_state.subagents;
                    state.status.bg_tasks = state.subagents.len() as u32;
                }
            }
            (state, vec![Effect::Render])
        }
        Some("on_cost_update") => {
            if let Some(params) = &msg.params {
                if let Ok(cost) =
                    serde_json::from_value::<crate::rpc::protocol::CostUpdateParams>(params.clone())
                {
                    state.status.cost = Some(cost.cost);
                    state.status.tokens_in = cost.tokens_in;
                    state.status.tokens_out = cost.tokens_out;
                }
            }
            (state, vec![Effect::Render])
        }
        _ => (state, vec![]),
    }
}

fn handle_response(
    mut state: crate::state::model::AppState,
    msg: RPCMessage,
) -> (crate::state::model::AppState, Vec<Effect>) {
    let id = msg.id.unwrap_or(-1);
    if let Some(pending) = state.pending_requests.remove(&id) {
        match pending.method.as_str() {
            "session.fork" => {
                if let Some(result) = &msg.result {
                    if let Ok(fork_result) = serde_json::from_value::<
                        crate::rpc::protocol::ForkSessionResult,
                    >(result.clone())
                    {
                        let short_id = fork_result.new_session_id
                            [..fork_result.new_session_id.len().min(8)]
                            .to_string();
                        state.status.session_id = Some(fork_result.new_session_id);
                        state.scrollback.push_back(format!("Forked → {}", short_id));
                    }
                }
            }
            "session.list" => {
                if let Some(result) = &msg.result {
                    if let Ok(list_result) = serde_json::from_value::<
                        crate::rpc::protocol::SessionListResult,
                    >(result.clone())
                    {
                        state.session_list = Some(list_result.sessions);
                    }
                }
            }
            _ => {}
        }
    }
    (state, vec![Effect::Render])
}

fn handle_inbound_request(
    mut state: crate::state::model::AppState,
    msg: RPCMessage,
) -> (crate::state::model::AppState, Vec<Effect>) {
    match msg.method.as_deref() {
        Some("approval") => {
            if let Some(params) = &msg.params {
                if let Ok(approval) = serde_json::from_value::<
                    crate::rpc::protocol::ApprovalRequestParams,
                >(params.clone())
                {
                    state.approval = Some(crate::state::model::ApprovalRequest {
                        rpc_id: msg.id.unwrap_or(0),
                        tool: approval.tool,
                        args: approval.args,
                    });
                    state.stage = crate::state::model::Stage::Approval;
                }
            }
            (state, vec![Effect::Render])
        }
        Some("ask_user") => {
            if let Some(params) = &msg.params {
                if let Ok(ask) = serde_json::from_value::<crate::rpc::protocol::AskUserRequestParams>(
                    params.clone(),
                ) {
                    state.ask_user = Some(crate::state::model::AskUserRequest {
                        rpc_id: msg.id.unwrap_or(0),
                        question: ask.question,
                        options: ask.options,
                        allow_text: ask.allow_text,
                        selected: 0,
                        free_text: String::new(),
                    });
                    state.stage = crate::state::model::Stage::AskUser;
                }
            }
            (state, vec![Effect::Render])
        }
        _ => (state, vec![]),
    }
}

fn handle_picker_key(
    mut state: crate::state::model::AppState,
    key: &crossterm::event::KeyEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::{KeyCode, KeyModifiers};

    let mut effects = vec![];
    match (key.modifiers, key.code) {
        (KeyModifiers::NONE, KeyCode::Esc) => {
            if let Some(picker) = &mut state.picker {
                if !picker.filter.is_empty() {
                    picker.filter.clear();
                    picker.cursor = 0;
                } else {
                    state.picker = None;
                    state.stage = Stage::Idle;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Enter) => {
            if let Some(picker) = &state.picker {
                let visible: Vec<&String> = picker
                    .entries
                    .iter()
                    .filter(|e| e.to_lowercase().contains(&picker.filter.to_lowercase()))
                    .collect();
                if let Some(selected) = visible.get(picker.cursor) {
                    match picker.kind {
                        crate::state::model::PickerKind::Model => {
                            let id = state.next_request_id;
                            state.next_request_id += 1;
                            let msg = crate::rpc::protocol::RPCMessage {
                                jsonrpc: "2.0".to_string(),
                                id: Some(id),
                                method: Some("config.set".to_string()),
                                params: Some(
                                    serde_json::json!({"key": "model", "value": selected}),
                                ),
                                result: None,
                                error: None,
                            };
                            state.pending_requests.insert(
                                id,
                                crate::state::model::PendingRequest {
                                    method: "config.set".to_string(),
                                    sent_at: std::time::Instant::now(),
                                },
                            );
                            effects.push(Effect::SendRpc(msg));
                        }
                        crate::state::model::PickerKind::Provider => {
                            let id = state.next_request_id;
                            state.next_request_id += 1;
                            let msg = crate::rpc::protocol::RPCMessage {
                                jsonrpc: "2.0".to_string(),
                                id: Some(id),
                                method: Some("config.set".to_string()),
                                params: Some(
                                    serde_json::json!({"key": "provider", "value": selected}),
                                ),
                                result: None,
                                error: None,
                            };
                            state.pending_requests.insert(
                                id,
                                crate::state::model::PendingRequest {
                                    method: "config.set".to_string(),
                                    sent_at: std::time::Instant::now(),
                                },
                            );
                            effects.push(Effect::SendRpc(msg));
                        }
                        crate::state::model::PickerKind::Session => {
                            if let Some(sessions) = &state.session_list {
                                if let Some(session) = sessions.get(picker.cursor) {
                                    let id = state.next_request_id;
                                    state.next_request_id += 1;
                                    let msg = crate::rpc::protocol::RPCMessage {
                                        jsonrpc: "2.0".to_string(),
                                        id: Some(id),
                                        method: Some("session.resume".to_string()),
                                        params: Some(serde_json::json!({"session_id": session.id})),
                                        result: None,
                                        error: None,
                                    };
                                    state.pending_requests.insert(
                                        id,
                                        crate::state::model::PendingRequest {
                                            method: "session.resume".to_string(),
                                            sent_at: std::time::Instant::now(),
                                        },
                                    );
                                    effects.push(Effect::SendRpc(msg));
                                }
                            }
                        }
                    }
                }
            }
            state.picker = None;
            state.stage = Stage::Idle;
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Up) | (KeyModifiers::NONE, KeyCode::Char('k')) => {
            if let Some(picker) = &mut state.picker {
                if picker.cursor > 0 {
                    picker.cursor -= 1;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Down) | (KeyModifiers::NONE, KeyCode::Char('j')) => {
            if let Some(picker) = &mut state.picker {
                let visible = picker
                    .entries
                    .iter()
                    .filter(|e| e.to_lowercase().contains(&picker.filter.to_lowercase()))
                    .count();
                if visible > 0 && picker.cursor < visible.saturating_sub(1) {
                    picker.cursor += 1;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Backspace) => {
            if let Some(picker) = &mut state.picker {
                picker.filter.pop();
                picker.cursor = 0;
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Char(c))
            if c.is_ascii_alphanumeric() || c.is_ascii_punctuation() || c == ' ' =>
        {
            if let Some(picker) = &mut state.picker {
                picker.filter.push(c);
                picker.cursor = 0;
            }
            effects.push(Effect::Render);
        }
        _ => {}
    }
    (state, effects)
}

fn handle_approval_key(
    mut state: crate::state::model::AppState,
    key: &crossterm::event::KeyEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::{KeyCode, KeyModifiers};

    let mut effects = vec![];
    let approved = match (key.modifiers, key.code) {
        (_, KeyCode::Char('y'))
        | (_, KeyCode::Char('Y'))
        | (KeyModifiers::NONE, KeyCode::Enter) => Some(true),
        (_, KeyCode::Char('a')) | (_, KeyCode::Char('A')) => Some(true),
        (_, KeyCode::Char('n')) | (_, KeyCode::Char('N')) | (_, KeyCode::Esc) => Some(false),
        _ => None,
    };

    if let Some(approved) = approved {
        if let Some(approval) = &state.approval {
            let session_approve = matches!(
                (key.modifiers, key.code),
                (_, KeyCode::Char('a')) | (_, KeyCode::Char('A'))
            );
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(approval.rpc_id),
                method: None,
                params: None,
                result: Some(
                    serde_json::to_value(crate::rpc::protocol::ApprovalResult {
                        approved,
                        session_approve: if session_approve { Some(true) } else { None },
                    })
                    .unwrap_or_default(),
                ),
                error: None,
            };
            effects.push(Effect::SendRpc(msg));
        }
        state.approval = None;
        state.stage = Stage::Idle;
        effects.push(Effect::Render);
    }

    (state, effects)
}

fn handle_ask_user_key(
    mut state: crate::state::model::AppState,
    key: &crossterm::event::KeyEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::{KeyCode, KeyModifiers};

    let mut effects = vec![];
    match (key.modifiers, key.code) {
        (KeyModifiers::NONE, KeyCode::Enter) => {
            if let Some(ask) = &state.ask_user {
                // Steer mode: rpc_id=0 means this is a steer prompt, not a backend ask_user
                if ask.rpc_id == 0 {
                    let id = state.next_request_id;
                    state.next_request_id += 1;
                    let msg = crate::rpc::protocol::RPCMessage {
                        jsonrpc: "2.0".to_string(),
                        id: Some(id),
                        method: Some("steer".to_string()),
                        params: Some(serde_json::json!({"message": ask.free_text})),
                        result: None,
                        error: None,
                    };
                    state.pending_requests.insert(
                        id,
                        crate::state::model::PendingRequest {
                            method: "steer".to_string(),
                            sent_at: std::time::Instant::now(),
                        },
                    );
                    effects.push(Effect::SendRpc(msg));
                    state.stage = Stage::Streaming;
                } else {
                    let answer = if !ask.options.is_empty() {
                        ask.options.get(ask.selected).cloned().unwrap_or_default()
                    } else {
                        ask.free_text.clone()
                    };
                    let msg = crate::rpc::protocol::RPCMessage {
                        jsonrpc: "2.0".to_string(),
                        id: Some(ask.rpc_id),
                        method: None,
                        params: None,
                        result: Some(
                            serde_json::to_value(crate::rpc::protocol::AskUserResult { answer })
                                .unwrap_or_default(),
                        ),
                        error: None,
                    };
                    effects.push(Effect::SendRpc(msg));
                    state.stage = Stage::Idle;
                }
            }
            state.ask_user = None;
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Esc) => {
            state.ask_user = None;
            state.stage = Stage::Idle;
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Up) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.selected > 0 {
                    ask.selected -= 1;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Down) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.selected + 1 < ask.options.len() {
                    ask.selected += 1;
                }
            }
            effects.push(Effect::Render);
        }
        _ => {}
    }
    (state, effects)
}
