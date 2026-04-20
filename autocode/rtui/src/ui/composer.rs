use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

use crate::state::model::AppState;
use crate::state::reducer::{handle_slash_command, Effect};

pub struct Composer;

impl Composer {
    pub fn handle_key(mut state: AppState, key: &KeyEvent) -> (AppState, Vec<Effect>) {
        let mut effects = vec![];

        match (key.modifiers, key.code) {
            // Alt+Enter: insert newline for multi-line
            (KeyModifiers::ALT, KeyCode::Enter) => {
                let pos = state.composer_cursor;
                state.composer_text.insert(pos, '\n');
                state.composer_cursor += 1;
                effects.push(Effect::Render);
            }
            // Enter: send chat if not streaming
            (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Enter) => {
                if !state.composer_text.trim().is_empty() {
                    let trimmed = state.composer_text.trim().to_string();
                    if trimmed.starts_with('/') {
                        effects.extend(handle_slash_command(&mut state, &trimmed));
                        state.composer_text.clear();
                        state.composer_cursor = 0;
                        state.composer_lines.clear();
                        state.history_cursor = None;
                        effects.push(Effect::Render);
                    } else {
                        // Add to history with frecency
                        let now_ms = std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap_or_default()
                            .as_millis() as i64;
                        if let Some(idx) = state
                            .history
                            .iter()
                            .position(|h| h.text == state.composer_text)
                        {
                            state.history[idx].last_used_ms = now_ms;
                            state.history[idx].use_count += 1;
                        } else {
                            state.history.push(crate::state::model::HistoryEntry {
                                text: state.composer_text.clone(),
                                last_used_ms: now_ms,
                                use_count: 1,
                            });
                        }
                        state.history.sort_by(|a, b| {
                            let score_a =
                                (a.last_used_ms as f64 * 0.7) + (a.use_count as f64 * 0.3);
                            let score_b =
                                (b.last_used_ms as f64 * 0.7) + (b.use_count as f64 * 0.3);
                            score_b
                                .partial_cmp(&score_a)
                                .unwrap_or(std::cmp::Ordering::Equal)
                        });
                        // Persist history
                        let _ = crate::ui::history::persist_history(&state.history);

                        let id = state.next_request_id;
                        state.next_request_id += 1;
                        let msg = crate::rpc::protocol::RPCMessage {
                            jsonrpc: "2.0".to_string(),
                            id: Some(id),
                            method: Some("chat".to_string()),
                            params: Some(serde_json::json!({
                                "message": state.composer_text.clone(),
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
                        state.composer_text.clear();
                        state.composer_cursor = 0;
                        state.composer_lines.clear();
                        state.history_cursor = None;
                        effects.push(Effect::SendRpc(msg));
                        effects.push(Effect::Render);
                    }
                }
            }
            // Backspace
            (_, KeyCode::Backspace) => {
                if state.composer_cursor > 0 {
                    state.composer_text.remove(state.composer_cursor - 1);
                    state.composer_cursor -= 1;
                    effects.push(Effect::Render);
                }
            }
            // Delete
            (_, KeyCode::Delete) => {
                if state.composer_cursor < state.composer_text.len() {
                    state.composer_text.remove(state.composer_cursor);
                    effects.push(Effect::Render);
                }
            }
            // Left arrow
            (_, KeyCode::Left) => {
                if state.composer_cursor > 0 {
                    state.composer_cursor -= 1;
                    effects.push(Effect::Render);
                }
            }
            // Right arrow
            (_, KeyCode::Right) => {
                if state.composer_cursor < state.composer_text.len() {
                    state.composer_cursor += 1;
                    effects.push(Effect::Render);
                }
            }
            // Home
            (_, KeyCode::Home) => {
                state.composer_cursor = 0;
                effects.push(Effect::Render);
            }
            // End
            (_, KeyCode::End) => {
                state.composer_cursor = state.composer_text.len();
                effects.push(Effect::Render);
            }
            // Ctrl+U: clear line
            (KeyModifiers::CONTROL, KeyCode::Char('u')) => {
                state.composer_text.clear();
                state.composer_cursor = 0;
                effects.push(Effect::Render);
            }
            // Printable characters
            (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Char(c)) => {
                let pos = state.composer_cursor;
                state.composer_text.insert(pos, c);
                state.composer_cursor += c.len_utf8();
                effects.push(Effect::Render);
            }
            _ => {}
        }

        (state, effects)
    }
}
