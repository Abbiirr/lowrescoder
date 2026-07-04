use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

use crate::state::model::AppState;
use crate::state::reducer::{handle_slash_command, Effect};

const FOLLOWUP_QUEUE_LIMIT: usize = 32;

pub struct Composer;

impl Composer {
    pub fn handle_key(mut state: AppState, key: &KeyEvent) -> (AppState, Vec<Effect>) {
        let mut effects = vec![];

        match (key.modifiers, key.code) {
            // Alt+Enter: insert newline for multi-line
            (KeyModifiers::ALT, KeyCode::Enter) => {
                state.composer_text.insert('\n');
                effects.push(Effect::Render);
            }
            // Enter: send chat if not streaming
            (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Enter) => {
                if !state.composer_text.as_str().trim().is_empty() {
                    let trimmed = state.composer_text.as_str().trim().to_string();
                    if trimmed.starts_with('/') {
                        effects.extend(handle_slash_command(&mut state, &trimmed));
                        state.composer_text.clear();
                        state.composer_lines.clear();
                        state.history_cursor = None;
                        effects.push(Effect::Render);
                    } else {
                        let normalized_text = crate::ui::history::canonicalize_history_text(
                            state.composer_text.as_str(),
                        );

                        if normalized_text.is_empty() {
                            state.composer_text.clear();
                            effects.push(Effect::Render);
                            return (state, effects);
                        }

                        // Add to history with frecency
                        let now_ms = std::time::SystemTime::now()
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap_or_default()
                            .as_millis() as i64;
                        if let Some(idx) = state.history.iter().position(|h| {
                            crate::ui::history::canonicalize_history_text(&h.text)
                                == normalized_text
                        }) {
                            state.history[idx].last_used_ms = now_ms;
                            state.history[idx].use_count += 1;
                            state.history[idx].text = normalized_text.clone();
                        } else {
                            state.history.push(crate::state::model::HistoryEntry {
                                text: normalized_text.clone(),
                                last_used_ms: now_ms,
                                use_count: 1,
                            });
                        }
                        crate::ui::history::sort_history_by_frecency(&mut state.history);
                        // Persist history
                        let _ = crate::ui::history::persist_history(&state.history);

                        let user_text = state.composer_text.as_str().to_string();
                        if state.stage == crate::state::model::Stage::Streaming {
                            state.followup_queue.push_back(user_text);
                            if state.followup_queue.len() > FOLLOWUP_QUEUE_LIMIT {
                                let overflow = state.followup_queue.len() - FOLLOWUP_QUEUE_LIMIT;
                                state.followup_queue.drain(..overflow);
                            }
                            state.composer_text.clear();
                            state.composer_lines.clear();
                            state.history_cursor = None;
                            effects.push(Effect::Render);
                            return (state, effects);
                        }

                        let id = state.next_request_id;
                        state.next_request_id += 1;
                        let msg = crate::rpc::protocol::RPCMessage {
                            jsonrpc: "2.0".to_string(),
                            id: Some(id),
                            method: Some("chat".to_string()),
                            params: Some(serde_json::json!({
                                "message": user_text,
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
                        state.stage = crate::state::model::Stage::Streaming;
                        state.scrollback.push_back(format!("> {}", user_text));
                        state.composer_text.clear();
                        state.composer_lines.clear();
                        state.history_cursor = None;
                        effects.push(Effect::SendRpc(msg));
                        effects.push(Effect::Render);
                    }
                }
            }
            // Backspace
            (_, KeyCode::Backspace) => {
                let before = state.composer_text.cursor();
                state.composer_text.delete_left();
                if state.composer_text.cursor() != before {
                    effects.push(Effect::Render);
                }
            }
            // Delete
            (_, KeyCode::Delete) => {
                let before = state.composer_text.as_str().len();
                state.composer_text.delete_right();
                if state.composer_text.as_str().len() != before {
                    effects.push(Effect::Render);
                }
            }
            // Left arrow
            (_, KeyCode::Left) => {
                let before = state.composer_text.cursor();
                if key.modifiers.contains(KeyModifiers::CONTROL) {
                    state.composer_text.move_word_left();
                } else {
                    state.composer_text.move_left();
                }
                if state.composer_text.cursor() != before {
                    effects.push(Effect::Render);
                }
            }
            // Right arrow
            (_, KeyCode::Right) => {
                let before = state.composer_text.cursor();
                if key.modifiers.contains(KeyModifiers::CONTROL) {
                    state.composer_text.move_word_right();
                } else {
                    state.composer_text.move_right();
                }
                if state.composer_text.cursor() != before {
                    effects.push(Effect::Render);
                }
            }
            // Home
            (_, KeyCode::Home) => {
                state.composer_text.home();
                effects.push(Effect::Render);
            }
            // End
            (_, KeyCode::End) => {
                state.composer_text.end();
                effects.push(Effect::Render);
            }
            // Ctrl+U: clear line
            (KeyModifiers::CONTROL, KeyCode::Char('u')) => {
                state.composer_text.clear();
                effects.push(Effect::Render);
            }
            // Printable characters
            (KeyModifiers::NONE | KeyModifiers::SHIFT, KeyCode::Char(c)) => {
                state.composer_text.insert(c);
                effects.push(Effect::Render);
            }
            _ => {}
        }

        (state, effects)
    }
}
