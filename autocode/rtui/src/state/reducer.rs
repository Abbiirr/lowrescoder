use std::time::Duration;

use portable_pty::ExitStatus;

use crate::rpc::protocol::RPCMessage;
use crate::rpc::schema;
use crate::state::model::{AskUserSource, DetailSurface, InboundId, PaletteMode, Stage};
use crate::ui::textbuf::TextBuf;

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub enum Event {
    Key(crossterm::event::KeyEvent),
    Mouse(crossterm::event::MouseEvent),
    Resize(u16, u16),
    Tick,

    RpcNotification(RPCMessage),
    RpcResponse(RPCMessage),
    RpcInboundRequest(RPCMessage),

    RpcFrameTooLarge(usize),
    BackendReadyTimeout,
    BackendExit(ExitStatus),
    BackendError(String),
    BackendWarning(String),
    BackendWriteFailed(String),
    EditorDone(String),
    EditorFailed(String),
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
            crossterm::event::Event::Mouse(m) => Some(Event::Mouse(m)),
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

const DEFAULT_STALE_REQUEST_TIMEOUT_SECS: u64 = 30;
const CTRL_C_HARD_QUIT_WINDOW: Duration = Duration::from_secs(2);
const FOLLOWUP_QUEUE_LIMIT: usize = 32;
const ACTIVE_TOOLS_LIMIT: usize = 16;
const RECOVERY_ACTION_COUNT: usize = 6;

pub(crate) fn stale_request_timeout() -> Duration {
    std::env::var("AUTOCODE_STALE_REQUEST_TIMEOUT_SECS")
        .ok()
        .and_then(|raw| raw.parse::<u64>().ok())
        .filter(|value| *value > 0)
        .map(Duration::from_secs)
        .unwrap_or(Duration::from_secs(DEFAULT_STALE_REQUEST_TIMEOUT_SECS))
}

pub fn reduce(
    state: crate::state::model::AppState,
    event: Event,
) -> (crate::state::model::AppState, Vec<Effect>) {
    match event {
        Event::Key(key) => handle_key(state, key),
        Event::Mouse(mouse) => handle_mouse(state, mouse),
        Event::Resize(w, h) => {
            let mut s = state;
            s.terminal_size = (w, h);
            (
                s,
                vec![Effect::ResizePty(w.max(40), h.max(6)), Effect::Render],
            )
        }
        Event::Tick => handle_tick(state),
        Event::RpcNotification(msg) => handle_notification(state, msg),
        Event::RpcResponse(msg) => handle_response(state, msg),
        Event::RpcInboundRequest(msg) => handle_inbound_request(state, msg),
        Event::RpcFrameTooLarge(max_bytes) => {
            let mut s = state;
            s.stage = crate::state::model::Stage::Shutdown;
            s.error_banner = Some(format!(
                "backend RPC frame exceeded {} bytes; restart required",
                max_bytes
            ));
            (s, vec![Effect::Render])
        }
        Event::BackendReadyTimeout => {
            let mut s = state;
            s.error_banner = Some("Backend not responding".into());
            s.recovery_action_idx = 0;
            (s, vec![Effect::Render])
        }
        Event::BackendExit(status) => {
            let mut s = state;
            s.stage = crate::state::model::Stage::Shutdown;
            if status.success() {
                (s, vec![Effect::Quit])
            } else {
                s.error_banner = Some(format!("backend crashed (code {})", status.exit_code()));
                s.recovery_action_idx = 0;
                (s, vec![Effect::Render])
            }
        }
        Event::BackendError(err) => {
            let mut s = state;
            s.error_banner = Some(err);
            s.recovery_action_idx = 0;
            (s, vec![Effect::Render])
        }
        Event::BackendWarning(message) => {
            let mut s = state;
            s.scrollback.push_back(format!("⚠ [backend] {}", message));
            (s, vec![Effect::Render])
        }
        Event::BackendWriteFailed(err) => {
            let mut s = state;
            s.stage = Stage::Shutdown;
            s.error_banner = Some(err);
            s.recovery_action_idx = 0;
            (s, vec![Effect::Render])
        }
        Event::EditorDone(text) => {
            let mut s = state;
            s.composer_text.set_text(text);
            s.stage = Stage::Idle;
            s.error_banner = None;
            (s, vec![Effect::Render])
        }
        Event::EditorFailed(err) => {
            let mut s = state;
            s.stage = Stage::Idle;
            s.error_banner = Some(err);
            (s, vec![Effect::Render])
        }
        Event::Paste(text) => {
            let mut s = state;
            for c in text.chars() {
                s.composer_text.insert(c);
            }
            (s, vec![Effect::Render])
        }
    }
}

fn clear_transcript(state: &mut crate::state::model::AppState) {
    state.scrollback.clear();
    state.stream_buf.clear();
    state.stream_lines.clear();
    state.error_banner = None;
    state.current_tool = None;
    state.active_tools.clear();
    state.followup_queue.clear();
    state.detail_surface = None;
    state.recovery_action_idx = 0;
}

fn sync_composer_lines(state: &mut crate::state::model::AppState) {
    state.composer_lines = state
        .composer_text
        .as_str()
        .lines()
        .map(String::from)
        .collect();
}

fn set_composer_text(state: &mut crate::state::model::AppState, text: impl Into<String>) {
    state.composer_text.set_text(text.into());
    sync_composer_lines(state);
}

fn clear_composer(state: &mut crate::state::model::AppState) {
    state.composer_text.clear();
    state.composer_lines.clear();
}

fn reset_for_session_switch(
    state: &mut crate::state::model::AppState,
    session_id: String,
    notice: String,
) {
    clear_transcript(state);
    state.stage = Stage::Idle;
    state.pending_requests.clear();
    state.stale_request_ids.clear();
    state.picker = None;
    state.palette = None;
    state.approval = None;
    state.ask_user = None;
    state.modal_queue.clear();
    state.session_list = None;
    state.tasks.clear();
    state.subagents.clear();
    state.status.session_id = Some(session_id);
    state.status.tokens_in = 0;
    state.status.tokens_out = 0;
    state.status.cost = None;
    state.status.bg_tasks = 0;
    state.scroll_offset = 0;
    state.history_cursor = None;
    clear_composer(state);
    state.scrollback.push_back(format!("[System] {}", notice));
}

fn flush_stream_lines(state: &mut crate::state::model::AppState) {
    if !state.stream_lines.is_empty() {
        for line in state.stream_lines.drain(..) {
            state.scrollback.push_back(line);
        }
        if state.scrollback.len() > 10_000 {
            let excess = state.scrollback.len() - 10_000;
            state.scrollback.drain(..excess);
        }
        state.stream_buf.clear();
    }
}

fn oldest_pending_request_id_by_method(
    state: &crate::state::model::AppState,
    method: &str,
) -> Option<i64> {
    state
        .pending_requests
        .iter()
        .filter(|(_, pending)| pending.method == method)
        .min_by_key(|(_, pending)| pending.sent_at)
        .map(|(&id, _)| id)
}

fn touch_oldest_pending_request_by_method(
    state: &mut crate::state::model::AppState,
    method: &str,
) -> bool {
    if let Some(id) = oldest_pending_request_id_by_method(state, method) {
        if let Some(pending) = state.pending_requests.get_mut(&id) {
            pending.sent_at = std::time::Instant::now();
            return true;
        }
    }
    false
}

fn remove_oldest_pending_request_by_method(
    state: &mut crate::state::model::AppState,
    method: &str,
) -> Option<i64> {
    let id = oldest_pending_request_id_by_method(state, method)?;
    state.pending_requests.remove(&id)?;
    Some(id)
}

fn activate_next_modal(state: &mut crate::state::model::AppState) {
    match state.modal_queue.pop_front() {
        Some(crate::state::model::ModalRequest::Approval(approval)) => {
            state.approval = Some(approval);
            state.ask_user = None;
            state.stage = Stage::Approval;
        }
        Some(crate::state::model::ModalRequest::AskUser(ask_user)) => {
            state.ask_user = Some(ask_user);
            state.approval = None;
            state.stage = Stage::AskUser;
        }
        None => {
            state.approval = None;
            state.ask_user = None;
            state.stage = Stage::Idle;
        }
    }
}

fn queue_or_activate_modal(
    state: &mut crate::state::model::AppState,
    modal: crate::state::model::ModalRequest,
) {
    if state.approval.is_none() && state.ask_user.is_none() {
        match modal {
            crate::state::model::ModalRequest::Approval(approval) => {
                state.approval = Some(approval);
                state.ask_user = None;
                state.stage = Stage::Approval;
            }
            crate::state::model::ModalRequest::AskUser(ask_user) => {
                state.ask_user = Some(ask_user);
                state.approval = None;
                state.stage = Stage::AskUser;
            }
        }
    } else {
        state.modal_queue.push_back(modal);
    }
}

fn record_ctrl_c(state: &mut crate::state::model::AppState, now: std::time::Instant) -> bool {
    let within_window = state
        .last_ctrl_c_at
        .is_some_and(|last| now.duration_since(last) <= CTRL_C_HARD_QUIT_WINDOW);

    state.ctrl_c_count = if within_window {
        state.ctrl_c_count.saturating_add(1)
    } else {
        1
    };
    state.last_ctrl_c_at = Some(now);

    state.ctrl_c_count >= 3
}

fn handle_key(
    mut state: crate::state::model::AppState,
    key: crossterm::event::KeyEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::{KeyCode, KeyModifiers};

    if state.stage == Stage::EditorLaunch {
        return (state, vec![]);
    }

    match (key.modifiers, key.code) {
        (KeyModifiers::CONTROL, KeyCode::Char('c')) => {
            if record_ctrl_c(&mut state, std::time::Instant::now()) {
                state.stage = Stage::Shutdown;
                return (state, vec![Effect::Quit]);
            }

            match &state.stage {
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
                        source: AskUserSource::Steer,
                        question: "Steer message: ".to_string(),
                        options: vec![],
                        allow_text: true,
                        selected: 0,
                        free_text: TextBuf::default(),
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
            }
        }
        (KeyModifiers::CONTROL, KeyCode::Char('k')) => {
            state.palette = Some(crate::state::model::PaletteState {
                mode: PaletteMode::CommandPalette,
                filter: TextBuf::default(),
                cursor: 0,
                entries: vec![],
            });
            state.stage = crate::state::model::Stage::Palette;
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("command.list".to_string()),
                params: Some(serde_json::json!({})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "command.list".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            (state, vec![Effect::SendRpc(msg), Effect::Render])
        }
        (KeyModifiers::CONTROL, KeyCode::Char('t')) => {
            state.task_panel_open = !state.task_panel_open;
            (state, vec![Effect::Render])
        }
        (KeyModifiers::CONTROL, KeyCode::Char('q')) => {
            state.followup_panel_open = !state.followup_panel_open;
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Char('/'))
            if matches!(
                state.stage,
                Stage::Idle | Stage::Streaming | Stage::ToolCall
            ) && state.composer_text.is_empty() =>
        {
            state.palette = Some(crate::state::model::PaletteState {
                mode: PaletteMode::SlashAutocomplete,
                filter: TextBuf::default(),
                cursor: 0,
                entries: vec![],
            });
            set_composer_text(&mut state, "/");
            state.stage = Stage::Palette;
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("command.list".to_string()),
                params: Some(serde_json::json!({})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "command.list".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            (state, vec![Effect::SendRpc(msg), Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Esc) if state.detail_surface.is_some() => {
            state.detail_surface = None;
            (state, vec![Effect::Render])
        }
        (KeyModifiers::CONTROL, KeyCode::Char('l')) => {
            clear_transcript(&mut state);
            (state, vec![Effect::Render])
        }
        (KeyModifiers::CONTROL, KeyCode::Char('e')) => {
            if let Ok(editor) = std::env::var("EDITOR") {
                state.composer_lines = state
                    .composer_text
                    .as_str()
                    .lines()
                    .map(String::from)
                    .collect();
                state.stage = Stage::EditorLaunch;
                state.error_banner = Some(format!("Launching {}...", editor));
                (state, vec![Effect::SpawnEditor(editor), Effect::Render])
            } else {
                state.error_banner = Some("$EDITOR not set".to_string());
                (state, vec![Effect::Render])
            }
        }
        _ if state.error_banner.is_some() || state.stage == Stage::Shutdown => {
            handle_recovery_key(state, &key)
        }
        // Up/Down: history browse in Idle
        (KeyModifiers::NONE, KeyCode::Up) if state.stage == crate::state::model::Stage::Idle => {
            if !state.history.is_empty() {
                let idx = state
                    .history_cursor
                    .map_or(0, |c| (c + 1).min(state.history.len().saturating_sub(1)));
                if idx < state.history.len() {
                    state
                        .composer_text
                        .set_text(state.history[idx].text.clone());
                    state.history_cursor = Some(idx);
                }
            }
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Down) if state.stage == crate::state::model::Stage::Idle => {
            if let Some(idx) = state.history_cursor {
                if idx > 0 {
                    state
                        .composer_text
                        .set_text(state.history[idx - 1].text.clone());
                    state.history_cursor = Some(idx - 1);
                } else {
                    state.composer_text.clear();
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

fn handle_recovery_key(
    mut state: crate::state::model::AppState,
    key: &crossterm::event::KeyEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::{KeyCode, KeyModifiers};

    match (key.modifiers, key.code) {
        (KeyModifiers::NONE, KeyCode::Esc) => (state, vec![Effect::Render]),
        (KeyModifiers::NONE, KeyCode::Left) => {
            if !state.recovery_action_idx.is_multiple_of(3) {
                state.recovery_action_idx -= 1;
            }
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Right) => {
            if state.recovery_action_idx % 3 < 2
                && state.recovery_action_idx + 1 < RECOVERY_ACTION_COUNT
            {
                state.recovery_action_idx += 1;
            }
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Up) => {
            if state.recovery_action_idx >= 3 {
                state.recovery_action_idx -= 3;
            }
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Down) => {
            if state.recovery_action_idx + 3 < RECOVERY_ACTION_COUNT {
                state.recovery_action_idx += 3;
            }
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Tab) => {
            state.recovery_action_idx = (state.recovery_action_idx + 1) % RECOVERY_ACTION_COUNT;
            (state, vec![Effect::Render])
        }
        (KeyModifiers::SHIFT, KeyCode::BackTab) => {
            state.recovery_action_idx =
                (state.recovery_action_idx + RECOVERY_ACTION_COUNT - 1) % RECOVERY_ACTION_COUNT;
            (state, vec![Effect::Render])
        }
        (KeyModifiers::NONE, KeyCode::Enter) => {
            let idx = state.recovery_action_idx;
            run_recovery_action(state, idx)
        }
        (KeyModifiers::NONE, KeyCode::Char('e')) => run_recovery_action(state, 1),
        (KeyModifiers::NONE, KeyCode::Char('r')) => run_recovery_action(state, 2),
        (KeyModifiers::NONE, KeyCode::Char('w')) => run_recovery_action(state, 3),
        (KeyModifiers::NONE, KeyCode::Char('c')) => run_recovery_action(state, 4),
        (KeyModifiers::NONE, KeyCode::Char('p')) => run_recovery_action(state, 5),
        _ => crate::ui::composer::Composer::handle_key(state, key),
    }
}

fn run_recovery_action(
    mut state: crate::state::model::AppState,
    idx: usize,
) -> (crate::state::model::AppState, Vec<Effect>) {
    state.recovery_action_idx = idx.min(RECOVERY_ACTION_COUNT.saturating_sub(1));

    match state.recovery_action_idx {
        0 => retry_from_recovery(state),
        1 => {
            state.detail_surface = Some(DetailSurface::CommandCenter);
            (state, vec![Effect::Render])
        }
        2 | 3 => {
            state.detail_surface = Some(DetailSurface::Restore);
            (state, vec![Effect::Render])
        }
        4 => {
            let effects = handle_slash_command(&mut state, "/compact");
            (state, effects)
        }
        5 => {
            let effects = handle_slash_command(&mut state, "/plan");
            (state, effects)
        }
        _ => (state, vec![Effect::Render]),
    }
}

fn retry_from_recovery(
    mut state: crate::state::model::AppState,
) -> (crate::state::model::AppState, Vec<Effect>) {
    if state.composer_text.as_str().trim().is_empty() {
        if let Some(last_input) = last_retryable_input(&state) {
            state.composer_text.set_text(last_input);
        } else {
            return (state, vec![Effect::Render]);
        }
    }

    state.stage = Stage::Idle;
    state.error_banner = None;
    crate::ui::composer::Composer::handle_key(
        state,
        &crossterm::event::KeyEvent::new(
            crossterm::event::KeyCode::Enter,
            crossterm::event::KeyModifiers::NONE,
        ),
    )
}

fn last_retryable_input(state: &crate::state::model::AppState) -> Option<String> {
    state.scrollback.iter().rev().find_map(|line| {
        if let Some(rest) = line.strip_prefix("> ") {
            Some(rest.to_string())
        } else if line.starts_with('/') {
            Some(line.clone())
        } else {
            None
        }
    })
}

fn handle_mouse(
    mut state: crate::state::model::AppState,
    mouse: crossterm::event::MouseEvent,
) -> (crate::state::model::AppState, Vec<Effect>) {
    use crossterm::event::MouseEventKind;

    match mouse.kind {
        MouseEventKind::ScrollUp => {
            state.scroll_offset = state.scroll_offset.saturating_add(1);
            (state, vec![Effect::Render])
        }
        MouseEventKind::ScrollDown => {
            state.scroll_offset = state.scroll_offset.saturating_sub(1);
            (state, vec![Effect::Render])
        }
        _ => (state, vec![]),
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
            let clear_draft = state.palette.as_ref().is_some_and(|palette| {
                palette.mode == PaletteMode::SlashAutocomplete && palette.filter.is_empty()
            });
            state.stage = crate::state::model::Stage::Idle;
            state.palette = None;
            if clear_draft {
                clear_composer(&mut state);
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Enter) | (KeyModifiers::NONE, KeyCode::Tab) => {
            let mut command_to_dispatch: Option<String> = None;
            let mut completed_draft: Option<String> = None;
            let mut clear_draft_after_dispatch = false;

            if let Some(palette) = &state.palette {
                let visible = visible_palette_indices(palette);
                if let Some(selected_idx) = visible.get(palette.cursor).copied() {
                    let entry = &palette.entries[selected_idx];
                    match palette.mode {
                        PaletteMode::CommandPalette => {
                            command_to_dispatch = Some(entry.name.clone());
                        }
                        PaletteMode::SlashAutocomplete => {
                            let filter = palette.filter.as_str().trim().to_lowercase();
                            let exact_match = filter
                                == entry.name.trim_start_matches('/').to_lowercase()
                                || filter == entry.name.to_lowercase();
                            if matches!(key.code, KeyCode::Enter) && exact_match {
                                command_to_dispatch = Some(entry.name.clone());
                                clear_draft_after_dispatch = true;
                            } else {
                                completed_draft = Some(entry.name.clone());
                            }
                        }
                    }
                } else if palette.mode == PaletteMode::SlashAutocomplete
                    && matches!(key.code, KeyCode::Enter)
                {
                    let filter = palette.filter.as_str().trim();
                    if !filter.is_empty() {
                        command_to_dispatch = Some(format!("/{}", filter));
                        clear_draft_after_dispatch = true;
                    }
                }
            }

            state
                .pending_requests
                .retain(|_, pending| pending.method != "command.list");
            state.stage = crate::state::model::Stage::Idle;
            state.palette = None;

            if let Some(draft) = completed_draft {
                set_composer_text(&mut state, draft);
            }

            if let Some(cmd) = command_to_dispatch {
                effects.extend(handle_slash_command(&mut state, &cmd));
                if clear_draft_after_dispatch {
                    clear_composer(&mut state);
                    state.history_cursor = None;
                }
            }

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
                let max = visible_palette_indices(palette).len().saturating_sub(1);
                if palette.cursor < max {
                    palette.cursor += 1;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Char(c)) if !c.is_control() => {
            let mut slash_filter: Option<String> = None;
            if let Some(palette) = &mut state.palette {
                palette.filter.insert(c);
                palette.cursor = 0;
                if palette.mode == PaletteMode::SlashAutocomplete {
                    slash_filter = Some(palette.filter.as_str().to_string());
                }
            }
            if let Some(filter) = slash_filter {
                set_composer_text(&mut state, format!("/{}", filter));
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Backspace) => {
            let mut slash_filter: Option<String> = None;
            let mut close_empty_slash = false;
            if let Some(palette) = &mut state.palette {
                if palette.filter.is_empty() && palette.mode == PaletteMode::SlashAutocomplete {
                    state.palette = None;
                    state.stage = Stage::Idle;
                    close_empty_slash = true;
                } else {
                    palette.filter.delete_left();
                    palette.cursor = 0;
                    if palette.mode == PaletteMode::SlashAutocomplete {
                        slash_filter = Some(palette.filter.as_str().to_string());
                    }
                }
            }
            if close_empty_slash {
                clear_composer(&mut state);
            } else if let Some(filter) = slash_filter {
                set_composer_text(&mut state, format!("/{}", filter));
            }
            effects.push(Effect::Render);
        }
        _ => {}
    }
    (state, effects)
}

fn dispatch_backend_slash_command(
    state: &mut crate::state::model::AppState,
    cmd: &str,
    pending_method: Option<String>,
) -> Vec<Effect> {
    state.scrollback.push_back(cmd.into());
    let id = state.next_request_id;
    state.next_request_id += 1;
    let msg = crate::rpc::protocol::RPCMessage {
        jsonrpc: "2.0".to_string(),
        id: Some(id),
        method: Some("command".to_string()),
        params: Some(serde_json::json!({"cmd": cmd})),
        result: None,
        error: None,
    };
    state.pending_requests.insert(
        id,
        crate::state::model::PendingRequest {
            method: pending_method.unwrap_or_else(|| format!("command:{cmd}")),
            sent_at: std::time::Instant::now(),
        },
    );
    vec![Effect::SendRpc(msg)]
}

pub(crate) fn handle_slash_command(
    state: &mut crate::state::model::AppState,
    cmd: &str,
) -> Vec<Effect> {
    let mut effects = vec![];
    let command = cmd.split_whitespace().next().unwrap_or(cmd);
    let args = cmd.strip_prefix(command).map(str::trim).unwrap_or_default();

    match command {
        "/new" => {
            let title = if args.is_empty() {
                None
            } else {
                Some(args.to_string())
            };
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("session.new".to_string()),
                params: Some(serde_json::json!({
                    "title": title,
                })),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "session.new".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
            effects.push(Effect::Render);
        }
        "/clear" => {
            clear_transcript(state);
            state.scrollback.push_back("/clear".into());
            effects.push(Effect::Render);
        }
        "/exit" => {
            state.scrollback.push_back("/exit".into());
            effects.push(Effect::Quit);
        }
        "/plan" => {
            state.scrollback.push_back("/plan".into());
            state.detail_surface = Some(DetailSurface::Plan);
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("plan.set".to_string()),
                params: Some(serde_json::json!({
                    "mode": if state.plan_mode { "normal" } else { "planning" }
                })),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "plan.set".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
            effects.push(Effect::Render);
        }
        "/multi" => {
            state.scrollback.push_back("/multi".into());
            state.detail_surface = Some(DetailSurface::Multi);
            effects.push(Effect::Render);
        }
        "/review" => {
            state.scrollback.push_back("/review".into());
            state.detail_surface = Some(DetailSurface::Review);
            effects.push(Effect::Render);
        }
        "/cc" => {
            state.scrollback.push_back("/cc".into());
            state.detail_surface = Some(DetailSurface::CommandCenter);
            effects.push(Effect::Render);
        }
        "/restore" => {
            state.scrollback.push_back("/restore".into());
            state.detail_surface = Some(DetailSurface::Restore);
            effects.push(Effect::Render);
        }
        "/diff" => {
            state.scrollback.push_back("/diff".into());
            state.detail_surface = Some(DetailSurface::Diff);
            effects.push(Effect::Render);
        }
        "/grep" | "/search" => {
            state.scrollback.push_back(cmd.into());
            state.detail_surface = Some(DetailSurface::Grep);
            effects.push(Effect::Render);
        }
        "/escalation" => {
            state.scrollback.push_back("/escalation".into());
            state.detail_surface = Some(DetailSurface::Escalation);
            effects.push(Effect::Render);
        }
        "/fork" => {
            state.scrollback.push_back("/fork".into());
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
            effects.extend(dispatch_backend_slash_command(
                state,
                "/compact",
                Some("command:/compact".to_string()),
            ));
        }
        "/sessions" | "/resume" => {
            state.scrollback.push_back(cmd.into());
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
            state.scrollback.push_back("/model".into());
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("model.list".to_string()),
                params: Some(serde_json::json!({})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "model.list".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
        }
        "/provider" => {
            state.scrollback.push_back("/provider".into());
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("provider.list".to_string()),
                params: Some(serde_json::json!({})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "provider.list".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
        }
        "/help" => {
            state.scrollback.push_back("/help".into());
            state.stage = crate::state::model::Stage::Palette;
            state.palette = Some(crate::state::model::PaletteState {
                mode: PaletteMode::CommandPalette,
                filter: TextBuf::default(),
                cursor: 0,
                entries: vec![],
            });
            let id = state.next_request_id;
            state.next_request_id += 1;
            let msg = crate::rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(id),
                method: Some("command.list".to_string()),
                params: Some(serde_json::json!({})),
                result: None,
                error: None,
            };
            state.pending_requests.insert(
                id,
                crate::state::model::PendingRequest {
                    method: "command.list".to_string(),
                    sent_at: std::time::Instant::now(),
                },
            );
            effects.push(Effect::SendRpc(msg));
            effects.push(Effect::Render);
        }
        _ => {
            effects.extend(dispatch_backend_slash_command(state, cmd, None));
        }
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
    let stale_request_timeout = stale_request_timeout();
    let stale_ids: Vec<i64> = state
        .pending_requests
        .iter()
        .filter(|(_, req)| now.duration_since(req.sent_at) > stale_request_timeout)
        .map(|(&id, _)| id)
        .collect();

    if state.followup_queue.len() > FOLLOWUP_QUEUE_LIMIT {
        let overflow = state.followup_queue.len() - FOLLOWUP_QUEUE_LIMIT;
        state.followup_queue.drain(..overflow);
    }

    let mut effects = vec![];
    for id in stale_ids {
        if let Some(req) = state.pending_requests.remove(&id) {
            tracing::warn!(
                "stale RPC request: id={} method={} (>{:?} old)",
                id,
                req.method,
                stale_request_timeout
            );
        }
        state.stale_request_ids.push(id);
    }

    if !state.stale_request_ids.is_empty() {
        let count = state.stale_request_ids.len();
        state.error_banner = Some(if count == 1 {
            "1 request timed out".to_string()
        } else {
            format!("{} requests timed out", count)
        });
        effects.push(Effect::Render);
    }

    if state.stage == crate::state::model::Stage::Streaming
        || state.error_banner.is_some()
        || state.current_tool.is_some()
        || !state.active_tools.is_empty()
        || !state.stream_lines.is_empty()
        || !state.followup_queue.is_empty()
        || state.task_panel_open
        || state.followup_panel_open
    {
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
        Some("on_warning") => {
            if let Some(params) = &msg.params {
                if let Ok(warn) =
                    serde_json::from_value::<crate::rpc::protocol::WarningParams>(params.clone())
                {
                    state.scrollback.push_back(warn.message);
                }
            }
            (state, vec![Effect::Render])
        }
        Some("on_chat_ack") => {
            if let Some(params) = &msg.params {
                let _ =
                    serde_json::from_value::<crate::rpc::protocol::ChatAckParams>(params.clone());
            }
            touch_oldest_pending_request_by_method(&mut state, "chat");
            (state, vec![])
        }
        Some("on_token") => {
            if let Some(params) = &msg.params {
                if let Ok(token) =
                    serde_json::from_value::<crate::rpc::protocol::TokenParams>(params.clone())
                {
                    touch_oldest_pending_request_by_method(&mut state, "chat");
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
                    touch_oldest_pending_request_by_method(&mut state, "chat");
                    state.stream_buf.push_str(&thinking.text);
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
        Some("on_done") => {
            if let Some(params) = &msg.params {
                if let Ok(done) =
                    serde_json::from_value::<crate::rpc::protocol::DoneParams>(params.clone())
                {
                    state.status.tokens_in = done.tokens_in;
                    state.status.tokens_out = done.tokens_out;
                }
            }
            remove_oldest_pending_request_by_method(&mut state, "chat");
            flush_stream_lines(&mut state);
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
                    touch_oldest_pending_request_by_method(&mut state, "chat");
                    let tool_info = crate::state::model::ToolCallInfo {
                        name: tool.name,
                        status: tool.status,
                        args: tool.args,
                        result: tool.result,
                    };
                    if let Some(existing) = state.active_tools.iter_mut().find(|existing| {
                        existing.name == tool_info.name && existing.args == tool_info.args
                    }) {
                        *existing = tool_info.clone();
                    } else {
                        state.active_tools.push(tool_info.clone());
                        if state.active_tools.len() > ACTIVE_TOOLS_LIMIT {
                            let overflow = state.active_tools.len() - ACTIVE_TOOLS_LIMIT;
                            state.active_tools.drain(..overflow);
                        }
                    }
                    state.current_tool = Some(tool_info);
                }
            }
            (state, vec![Effect::Render])
        }
        Some(method) if schema::is_task_state_method(method) => {
            if let Some(params) = &msg.params {
                if let Ok(task_state) =
                    serde_json::from_value::<crate::rpc::protocol::TaskStateParams>(params.clone())
                {
                    touch_oldest_pending_request_by_method(&mut state, "chat");
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
                    touch_oldest_pending_request_by_method(&mut state, "chat");
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
            "command.list" => {
                if let Some(result) = &msg.result {
                    if let Some(error) = result.get("error").and_then(|value| value.as_str()) {
                        state.error_banner = Some(error.to_string());
                    } else if let Ok(command_result) = serde_json::from_value::<
                        crate::rpc::protocol::CommandListResult,
                    >(result.clone())
                    {
                        let filter = state
                            .palette
                            .as_ref()
                            .map(|palette| palette.filter.clone())
                            .unwrap_or_default();
                        let mode = state
                            .palette
                            .as_ref()
                            .map(|palette| palette.mode.clone())
                            .unwrap_or(PaletteMode::CommandPalette);
                        state.stage = Stage::Palette;
                        state.palette = Some(crate::state::model::PaletteState {
                            mode,
                            filter,
                            cursor: 0,
                            entries: command_result
                                .commands
                                .into_iter()
                                .map(|entry| crate::state::model::PaletteEntry {
                                    name: format!("/{}", entry.name),
                                    description: entry.description,
                                })
                                .collect(),
                        });
                    }
                }
            }
            "session.fork" => {
                if let Some(result) = &msg.result {
                    if let Ok(fork_result) = serde_json::from_value::<
                        crate::rpc::protocol::ForkSessionResult,
                    >(result.clone())
                    {
                        let short_id = fork_result
                            .new_session_id
                            .chars()
                            .take(8)
                            .collect::<String>();
                        state.status.session_id = Some(fork_result.new_session_id);
                        state.scrollback.push_back(format!("Forked → {}", short_id));
                    }
                }
            }
            "session.new" => {
                if let Some(result) = &msg.result {
                    if let Some(error) = result.get("error").and_then(|value| value.as_str()) {
                        state.error_banner = Some(error.to_string());
                    } else if let Ok(change_result) = serde_json::from_value::<
                        crate::rpc::protocol::SessionChangeResult,
                    >(result.clone())
                    {
                        let title = change_result
                            .title
                            .unwrap_or_else(|| "New session".to_string());
                        reset_for_session_switch(
                            &mut state,
                            change_result.session_id,
                            format!("Started new session: {}", title),
                        );
                    }
                }
            }
            "session.list" => {
                if let Some(result) = &msg.result {
                    if let Ok(list_result) = serde_json::from_value::<
                        crate::rpc::protocol::SessionListResult,
                    >(result.clone())
                    {
                        let entries = list_result
                            .sessions
                            .iter()
                            .map(|session| {
                                format!(
                                    "{} [{}] · {} / {}",
                                    session.title, session.id, session.provider, session.model
                                )
                            })
                            .collect();
                        state.session_list = Some(list_result.sessions);
                        state.picker = Some(crate::state::model::PickerState {
                            kind: crate::state::model::PickerKind::Session,
                            entries,
                            filter: TextBuf::default(),
                            cursor: 0,
                        });
                        state.stage = Stage::Picker(crate::state::model::PickerKind::Session);
                    }
                }
            }
            "session.resume" => {
                if let Some(result) = &msg.result {
                    if let Some(error) = result.get("error").and_then(|value| value.as_str()) {
                        state.error_banner = Some(error.to_string());
                    } else if let Ok(change_result) = serde_json::from_value::<
                        crate::rpc::protocol::SessionChangeResult,
                    >(result.clone())
                    {
                        let title = change_result.title.unwrap_or_else(|| "session".to_string());
                        reset_for_session_switch(
                            &mut state,
                            change_result.session_id,
                            format!("Resumed session: {}", title),
                        );
                    }
                }
            }
            "model.list" => {
                if let Some(result) = &msg.result {
                    if let Some(error) = result.get("error").and_then(|value| value.as_str()) {
                        state.error_banner = Some(error.to_string());
                    } else if let Ok(list_result) = serde_json::from_value::<
                        crate::rpc::protocol::ModelListResult,
                    >(result.clone())
                    {
                        state.picker = Some(crate::state::model::PickerState {
                            kind: crate::state::model::PickerKind::Model,
                            entries: list_result.models,
                            filter: TextBuf::default(),
                            cursor: 0,
                        });
                        state.stage = Stage::Picker(crate::state::model::PickerKind::Model);
                    }
                }
            }
            "provider.list" => {
                if let Some(result) = &msg.result {
                    if let Some(error) = result.get("error").and_then(|value| value.as_str()) {
                        state.error_banner = Some(error.to_string());
                    } else if let Ok(list_result) = serde_json::from_value::<
                        crate::rpc::protocol::ProviderListResult,
                    >(result.clone())
                    {
                        state.picker = Some(crate::state::model::PickerState {
                            kind: crate::state::model::PickerKind::Provider,
                            entries: list_result.providers,
                            filter: TextBuf::default(),
                            cursor: 0,
                        });
                        state.stage = Stage::Picker(crate::state::model::PickerKind::Provider);
                    }
                }
            }
            "plan.set" => {
                if let Some(result) = &msg.result {
                    if let Some(error) = result.get("error").and_then(|value| value.as_str()) {
                        state.error_banner = Some(error.to_string());
                    } else if let Ok(plan_result) = serde_json::from_value::<
                        crate::rpc::protocol::PlanSetResult,
                    >(result.clone())
                    {
                        state.plan_mode = plan_result.mode == "planning";
                        state.scrollback.push_back(format!(
                            "Plan mode → {}",
                            if state.plan_mode {
                                "planning"
                            } else {
                                "normal"
                            }
                        ));
                    }
                }
            }
            "command:/compact" => {
                if let Some(result) = &msg.result {
                    if let Some(error) = result.get("error").and_then(|value| value.as_str()) {
                        state.error_banner = Some(error.to_string());
                    } else if let Ok(compact_result) = serde_json::from_value::<
                        crate::rpc::protocol::CompactCommandResult,
                    >(result.clone())
                    {
                        if compact_result.messages_compacted > 0 {
                            state.scrollback.push_back(format!(
                                "Compacted {} turns → {} tokens",
                                compact_result.messages_compacted, compact_result.summary_tokens
                            ));
                        }
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
        Some(method) if schema::is_tool_request_method(method) => {
            if let Some(params) = &msg.params {
                if let Ok(approval) = serde_json::from_value::<
                    crate::rpc::protocol::ApprovalRequestParams,
                >(params.clone())
                {
                    touch_oldest_pending_request_by_method(&mut state, "chat");
                    flush_stream_lines(&mut state);
                    queue_or_activate_modal(
                        &mut state,
                        crate::state::model::ModalRequest::Approval(
                            crate::state::model::ApprovalRequest {
                                rpc_id: InboundId::new(msg.id.unwrap_or(0)),
                                tool: approval.tool,
                                args: approval.args,
                            },
                        ),
                    );
                }
            }
            (state, vec![Effect::Render])
        }
        Some(method) if schema::is_ask_user_method(method) => {
            if let Some(params) = &msg.params {
                if let Ok(ask) = serde_json::from_value::<crate::rpc::protocol::AskUserRequestParams>(
                    params.clone(),
                ) {
                    touch_oldest_pending_request_by_method(&mut state, "chat");
                    flush_stream_lines(&mut state);
                    queue_or_activate_modal(
                        &mut state,
                        crate::state::model::ModalRequest::AskUser(
                            crate::state::model::AskUserRequest {
                                source: AskUserSource::Inbound(InboundId::new(msg.id.unwrap_or(0))),
                                question: ask.question,
                                options: ask.options,
                                allow_text: ask.allow_text,
                                selected: 0,
                                free_text: TextBuf::default(),
                            },
                        ),
                    );
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
                let visible = visible_picker_indices(picker);
                if let Some(selected_idx) = visible.get(picker.cursor).copied() {
                    let selected = &picker.entries[selected_idx];
                    match picker.kind {
                        crate::state::model::PickerKind::Model => {
                            let id = state.next_request_id;
                            state.next_request_id += 1;
                            let msg = crate::rpc::protocol::RPCMessage {
                                jsonrpc: "2.0".to_string(),
                                id: Some(id),
                                method: Some("config.set".to_string()),
                                params: Some(
                                    serde_json::json!({"key": "llm.model", "value": selected}),
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
                                    serde_json::json!({"key": "llm.provider", "value": selected}),
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
                                if let Some(session) = sessions.get(selected_idx) {
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
                let visible = visible_picker_indices(picker).len();
                if visible > 0 && picker.cursor < visible.saturating_sub(1) {
                    picker.cursor += 1;
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Backspace) => {
            if let Some(picker) = &mut state.picker {
                picker.filter.delete_left();
                picker.cursor = 0;
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Char(c))
            if c.is_ascii_alphanumeric() || c.is_ascii_punctuation() || c == ' ' =>
        {
            if let Some(picker) = &mut state.picker {
                picker.filter.insert(c);
                picker.cursor = 0;
            }
            effects.push(Effect::Render);
        }
        _ => {}
    }
    (state, effects)
}

fn visible_palette_indices(palette: &crate::state::model::PaletteState) -> Vec<usize> {
    let filter = palette.filter.as_str().to_lowercase();
    palette
        .entries
        .iter()
        .enumerate()
        .filter(|(_, entry)| {
            filter.is_empty()
                || entry.name.to_lowercase().contains(&filter)
                || entry.description.to_lowercase().contains(&filter)
        })
        .map(|(idx, _)| idx)
        .collect()
}

fn visible_picker_indices(picker: &crate::state::model::PickerState) -> Vec<usize> {
    let filter = picker.filter.as_str().to_lowercase();
    picker
        .entries
        .iter()
        .enumerate()
        .filter(|(_, entry)| filter.is_empty() || entry.to_lowercase().contains(&filter))
        .map(|(idx, _)| idx)
        .collect()
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
                id: Some(approval.rpc_id.get()),
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
        activate_next_modal(&mut state);
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
                match ask.source {
                    AskUserSource::Steer => {
                        let id = state.next_request_id;
                        state.next_request_id += 1;
                        let msg = crate::rpc::protocol::RPCMessage {
                            jsonrpc: "2.0".to_string(),
                            id: Some(id),
                            method: Some("steer".to_string()),
                            params: Some(serde_json::json!({"message": ask.free_text.as_str()})),
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
                    }
                    AskUserSource::Inbound(rpc_id) => {
                        let answer = if !ask.options.is_empty() {
                            ask.options.get(ask.selected).cloned().unwrap_or_default()
                        } else {
                            ask.free_text.as_str().to_string()
                        };
                        let msg = crate::rpc::protocol::RPCMessage {
                            jsonrpc: "2.0".to_string(),
                            id: Some(rpc_id.get()),
                            method: None,
                            params: None,
                            result: Some(
                                serde_json::to_value(crate::rpc::protocol::AskUserResult {
                                    answer,
                                })
                                .unwrap_or_default(),
                            ),
                            error: None,
                        };
                        effects.push(Effect::SendRpc(msg));
                        state.ask_user = None;
                        activate_next_modal(&mut state);
                    }
                }
            }
            if state.stage == Stage::Streaming {
                state.ask_user = None;
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Esc) => {
            state.ask_user = None;
            activate_next_modal(&mut state);
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
        (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Char(c)) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.allow_text {
                    ask.free_text.insert(c);
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Backspace) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.allow_text {
                    ask.free_text.delete_left();
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Left) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.allow_text {
                    ask.free_text.move_left();
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Right) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.allow_text {
                    ask.free_text.move_right();
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::Home) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.allow_text {
                    ask.free_text.home();
                }
            }
            effects.push(Effect::Render);
        }
        (KeyModifiers::NONE, KeyCode::End) => {
            if let Some(ask) = &mut state.ask_user {
                if ask.allow_text {
                    ask.free_text.end();
                }
            }
            effects.push(Effect::Render);
        }
        _ => {}
    }
    (state, effects)
}
