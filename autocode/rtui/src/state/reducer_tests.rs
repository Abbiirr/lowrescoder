#[cfg(test)]
mod tests {
    use std::time::Duration;

    use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
    use crossterm::event::{MouseButton, MouseEvent, MouseEventKind};
    use portable_pty::ExitStatus;

    use crate::rpc::protocol::RPCMessage;
    use crate::state::model::{
        AppState, AskUserRequest, AskUserSource, DetailSurface, InboundId, PaletteMode, Stage,
    };
    use crate::state::reducer::{reduce, stale_request_timeout, Effect, Event};
    use crate::ui::textbuf::TextBuf;

    fn new_state() -> AppState {
        AppState::new((80, 24), false)
    }

    #[test]
    fn stale_request_timeout_respects_env_override() {
        let old = std::env::var_os("AUTOCODE_STALE_REQUEST_TIMEOUT_SECS");
        std::env::set_var("AUTOCODE_STALE_REQUEST_TIMEOUT_SECS", "120");

        let timeout = stale_request_timeout();

        if let Some(value) = old {
            std::env::set_var("AUTOCODE_STALE_REQUEST_TIMEOUT_SECS", value);
        } else {
            std::env::remove_var("AUTOCODE_STALE_REQUEST_TIMEOUT_SECS");
        }

        assert_eq!(timeout, Duration::from_secs(120));
    }

    fn on_status_msg() -> RPCMessage {
        RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_status".to_string()),
            params: Some(serde_json::json!({
                "model": "tools",
                "provider": "openrouter",
                "mode": "suggest"
            })),
            result: None,
            error: None,
        }
    }

    fn on_token_msg(text: &str) -> RPCMessage {
        RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_token".to_string()),
            params: Some(serde_json::json!({"text": text})),
            result: None,
            error: None,
        }
    }

    fn on_chat_ack_msg() -> RPCMessage {
        RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_chat_ack".to_string()),
            params: Some(serde_json::json!({"request_id": 1})),
            result: None,
            error: None,
        }
    }

    fn on_done_msg() -> RPCMessage {
        RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_done".to_string()),
            params: Some(serde_json::json!({
                "tokens_in": 10,
                "tokens_out": 5,
                "cancelled": false,
                "layer_used": 4
            })),
            result: None,
            error: None,
        }
    }

    fn has_effect(effects: &[Effect], target: &Effect) -> bool {
        effects
            .iter()
            .any(|e| std::mem::discriminant(e) == std::mem::discriminant(target))
    }

    fn find_sent_rpc<'a>(effects: &'a [Effect], method: &str) -> Option<&'a RPCMessage> {
        effects.iter().find_map(|effect| match effect {
            Effect::SendRpc(msg) if msg.method.as_deref() == Some(method) => Some(msg),
            _ => None,
        })
    }

    #[test]
    fn on_status_updates_status_info() {
        let state = new_state();
        let (state, effects) = reduce(state, Event::RpcNotification(on_status_msg()));
        assert_eq!(state.status.model, "tools");
        assert_eq!(state.status.provider, "openrouter");
        assert_eq!(state.status.mode, "suggest");
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn on_token_transitions_to_streaming() {
        let state = new_state();
        assert_eq!(state.stage, Stage::Idle);
        let (state, _) = reduce(state, Event::RpcNotification(on_token_msg("hello")));
        assert_eq!(state.stage, Stage::Streaming);
        assert_eq!(state.stream_buf, "hello");
    }

    #[test]
    fn on_token_appends_stream_buf() {
        let state = new_state();
        let (state, _) = reduce(state, Event::RpcNotification(on_token_msg("hello")));
        let (state, _) = reduce(state, Event::RpcNotification(on_token_msg(" world")));
        assert_eq!(state.stream_buf, "hello world");
        assert_eq!(state.stream_lines, vec!["hello world"]);
    }

    #[test]
    fn on_token_splits_on_newline() {
        let state = new_state();
        let (state, _) = reduce(state, Event::RpcNotification(on_token_msg("line1\nline2")));
        assert_eq!(state.stream_lines, vec!["line1", "line2"]);
    }

    #[test]
    fn on_done_flushes_to_scrollback() {
        let state = new_state();
        let (state, _) = reduce(state, Event::RpcNotification(on_token_msg("response")));
        let (state, _) = reduce(state, Event::RpcNotification(on_done_msg()));
        assert_eq!(state.stage, Stage::Idle);
        assert!(state.scrollback.contains(&"response".to_string()));
        assert!(state.stream_buf.is_empty());
        assert!(state.stream_lines.is_empty());
    }

    #[test]
    fn on_done_updates_token_counts() {
        let state = new_state();
        let (state, _) = reduce(state, Event::RpcNotification(on_done_msg()));
        assert_eq!(state.status.tokens_in, 10);
        assert_eq!(state.status.tokens_out, 5);
    }

    #[test]
    fn on_done_clears_pending_chat_request_but_keeps_other_pending_requests() {
        let mut state = new_state();
        state.pending_requests.insert(
            1,
            crate::state::model::PendingRequest {
                method: "chat".into(),
                sent_at: std::time::Instant::now(),
            },
        );
        state.pending_requests.insert(
            2,
            crate::state::model::PendingRequest {
                method: "command.list".into(),
                sent_at: std::time::Instant::now(),
            },
        );

        let (state, _) = reduce(state, Event::RpcNotification(on_done_msg()));

        assert!(!state.pending_requests.contains_key(&1));
        assert!(state.pending_requests.contains_key(&2));
    }

    #[test]
    fn on_token_keeps_active_chat_request_from_timing_out() {
        let mut state = new_state();
        state.pending_requests.insert(
            1,
            crate::state::model::PendingRequest {
                method: "chat".into(),
                sent_at: std::time::Instant::now() - std::time::Duration::from_secs(31),
            },
        );

        let (state, _) = reduce(state, Event::RpcNotification(on_token_msg("still working")));
        let (state, _) = reduce(state, Event::Tick);

        assert!(state.pending_requests.contains_key(&1));
        assert!(state.error_banner.is_none());
    }

    #[test]
    fn on_chat_ack_keeps_active_chat_request_from_timing_out_without_render() {
        let mut state = new_state();
        state.pending_requests.insert(
            1,
            crate::state::model::PendingRequest {
                method: "chat".into(),
                sent_at: std::time::Instant::now() - std::time::Duration::from_secs(31),
            },
        );

        let (state, effects) = reduce(state, Event::RpcNotification(on_chat_ack_msg()));
        let (state, _) = reduce(state, Event::Tick);

        assert!(state.pending_requests.contains_key(&1));
        assert!(state.error_banner.is_none());
        assert!(effects.is_empty());
        assert_eq!(state.stage, Stage::Idle);
    }

    #[test]
    fn chat_submission_echoes_user_message_immediately() {
        let mut state = new_state();
        state.composer_text.set_text("hello world");

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        assert!(state.scrollback.iter().any(|line| line == "> hello world"));
        assert!(find_sent_rpc(&effects, "chat").is_some());
        assert_eq!(state.stage, Stage::Streaming);
    }

    #[test]
    fn enter_during_streaming_queues_followup_instead_of_sending() {
        let mut state = new_state();
        state.stage = Stage::Streaming;
        state.composer_text.set_text("follow-up");

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        assert_eq!(state.followup_queue.len(), 1);
        assert_eq!(
            state.followup_queue.front().map(|s| s.as_str()),
            Some("follow-up")
        );
        assert!(find_sent_rpc(&effects, "chat").is_none());
    }

    #[test]
    fn backend_exit_quits() {
        let state = new_state();
        let (_, effects) = reduce(state, Event::BackendExit(ExitStatus::with_exit_code(0)));
        assert!(has_effect(&effects, &Effect::Quit));
    }

    #[test]
    fn backend_crash_sets_banner_without_quitting() {
        let state = new_state();
        let (state, effects) = reduce(state, Event::BackendExit(ExitStatus::with_exit_code(17)));
        assert_eq!(state.stage, Stage::Shutdown);
        assert_eq!(state.error_banner, Some("backend crashed (code 17)".into()));
        assert!(has_effect(&effects, &Effect::Render));
        assert!(!has_effect(&effects, &Effect::Quit));
    }

    #[test]
    fn oversized_rpc_frame_sets_shutdown_banner() {
        let state = new_state();
        let (state, effects) = reduce(state, Event::RpcFrameTooLarge(1024));
        assert_eq!(state.stage, Stage::Shutdown);
        assert_eq!(
            state.error_banner,
            Some("backend RPC frame exceeded 1024 bytes; restart required".into())
        );
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn backend_write_failed_sets_shutdown_banner() {
        let state = new_state();
        let (state, effects) = reduce(
            state,
            Event::BackendWriteFailed("backend RPC write failed: broken pipe".into()),
        );
        assert_eq!(state.stage, Stage::Shutdown);
        assert_eq!(
            state.error_banner,
            Some("backend RPC write failed: broken pipe".into())
        );
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn backend_warning_surfaces_in_scrollback() {
        let state = new_state();
        let (state, effects) = reduce(
            state,
            Event::BackendWarning("WARNING: backend is warming cache".into()),
        );

        assert!(state
            .scrollback
            .iter()
            .any(|line| line == "⚠ [backend] WARNING: backend is warming cache"));
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn backend_ready_timeout_sets_banner() {
        let state = new_state();
        let (state, effects) = reduce(state, Event::BackendReadyTimeout);

        assert_eq!(state.error_banner, Some("Backend not responding".into()));
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn triple_ctrl_c_hard_quits_within_window() {
        let state = new_state();

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)),
        );
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)),
        );
        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)),
        );

        assert_eq!(state.stage, Stage::Shutdown);
        assert!(has_effect(&effects, &Effect::Quit));
    }

    #[test]
    fn ctrl_c_count_resets_after_window_expires() {
        let mut state = new_state();
        state.ctrl_c_count = 2;
        state.last_ctrl_c_at = Some(std::time::Instant::now() - std::time::Duration::from_secs(3));

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)),
        );

        assert_eq!(state.ctrl_c_count, 1);
        assert!(!has_effect(&effects, &Effect::Quit));
    }

    #[test]
    fn history_up_and_down_walks_the_stack() {
        let mut state = new_state();
        state.history = vec![
            crate::state::model::HistoryEntry {
                text: "newest".into(),
                last_used_ms: 2_000,
                use_count: 1,
            },
            crate::state::model::HistoryEntry {
                text: "older".into(),
                last_used_ms: 1_000,
                use_count: 1,
            },
        ];

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Up, KeyModifiers::NONE)),
        );
        assert_eq!(state.composer_text.as_str(), "newest");
        assert_eq!(state.history_cursor, Some(0));

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Up, KeyModifiers::NONE)),
        );
        assert_eq!(state.composer_text.as_str(), "older");
        assert_eq!(state.history_cursor, Some(1));

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE)),
        );
        assert_eq!(state.composer_text.as_str(), "newest");
        assert_eq!(state.history_cursor, Some(0));

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Down, KeyModifiers::NONE)),
        );
        assert_eq!(state.composer_text.as_str(), "");
        assert_eq!(state.history_cursor, None);
    }

    #[test]
    fn resize_clamps_pty_but_keeps_raw_terminal_size() {
        let state = new_state();
        let (state, effects) = reduce(state, Event::Resize(10, 3));

        assert_eq!(state.terminal_size, (10, 3));
        assert!(effects
            .iter()
            .any(|effect| matches!(effect, Effect::ResizePty(40, 6))));
    }

    #[test]
    fn tick_renders_when_error_banner_exists_outside_streaming() {
        let mut state = new_state();
        state.error_banner = Some("boom".into());

        let (_, effects) = reduce(state, Event::Tick);
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn multiple_stale_requests_aggregate_banner() {
        use std::time::{Duration, Instant};

        let mut state = new_state();
        state.pending_requests.insert(
            1,
            crate::state::model::PendingRequest {
                method: "chat".to_string(),
                sent_at: Instant::now() - Duration::from_secs(31),
            },
        );
        state.pending_requests.insert(
            2,
            crate::state::model::PendingRequest {
                method: "command.list".to_string(),
                sent_at: Instant::now() - Duration::from_secs(31),
            },
        );

        let (state, _) = reduce(state, Event::Tick);
        assert_eq!(state.error_banner, Some("2 requests timed out".into()));
    }

    #[test]
    fn inbound_modal_ids_do_not_touch_pending_request_space() {
        let mut state = new_state();
        let outbound_id = 7;
        state.pending_requests.insert(
            outbound_id,
            crate::state::model::PendingRequest {
                method: "chat".to_string(),
                sent_at: std::time::Instant::now(),
            },
        );

        let (state, _) = reduce(
            state,
            Event::RpcInboundRequest(RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(outbound_id),
                method: Some("on_tool_request".to_string()),
                params: Some(serde_json::json!({
                    "tool": "bash",
                    "args": "ls -la",
                })),
                result: None,
                error: None,
            }),
        );

        assert!(state.pending_requests.contains_key(&outbound_id));
        assert_eq!(state.approval.as_ref().unwrap().rpc_id.get(), outbound_id);

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('y'), KeyModifiers::NONE)),
        );

        assert!(state.pending_requests.contains_key(&outbound_id));
        let response = effects.iter().find_map(|effect| match effect {
            Effect::SendRpc(msg) if msg.method.is_none() => Some(msg),
            _ => None,
        });
        assert_eq!(response.and_then(|msg| msg.id), Some(outbound_id));
    }

    #[test]
    fn mouse_scroll_updates_scrollback_offset() {
        let mut state = new_state();
        state
            .scrollback
            .extend((0..20).map(|idx| format!("line {}", idx)));

        let (state, effects) = reduce(
            state,
            Event::Mouse(MouseEvent {
                kind: MouseEventKind::ScrollUp,
                column: 0,
                row: 0,
                modifiers: KeyModifiers::NONE,
            }),
        );
        assert_eq!(state.scroll_offset, 1);
        assert!(has_effect(&effects, &Effect::Render));

        let (state, _) = reduce(
            state,
            Event::Mouse(MouseEvent {
                kind: MouseEventKind::ScrollDown,
                column: 0,
                row: 0,
                modifiers: KeyModifiers::NONE,
            }),
        );
        assert_eq!(state.scroll_offset, 0);

        let (state, _) = reduce(
            state,
            Event::Mouse(MouseEvent {
                kind: MouseEventKind::Down(MouseButton::Left),
                column: 0,
                row: 0,
                modifiers: KeyModifiers::NONE,
            }),
        );
        assert_eq!(state.scroll_offset, 0);
    }

    #[test]
    fn resize_effect() {
        let state = new_state();
        let (_, effects) = reduce(state, Event::Resize(120, 40));
        assert!(effects
            .iter()
            .any(|e| matches!(e, Effect::ResizePty(120, 40))));
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn scrollback_capacity_bound() {
        let mut state = new_state();
        // Pre-fill scrollback near capacity
        for i in 0..9_995 {
            state.scrollback.push_back(format!("line {}", i));
        }
        // Add streaming content that will overflow when flushed
        let (state, _) = reduce(state, Event::RpcNotification(on_token_msg("new content")));
        let (state, _) = reduce(state, Event::RpcNotification(on_done_msg()));
        // After flush: 9_995 + 1 = 9_996, within bound
        assert!(state.scrollback.len() <= 10_000);
    }

    #[test]
    fn on_error_sets_banner() {
        let state = new_state();
        let msg = RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_error".to_string()),
            params: Some(serde_json::json!({"message": "something broke"})),
            result: None,
            error: None,
        };
        let (state, _) = reduce(state, Event::RpcNotification(msg));
        assert_eq!(state.error_banner, Some("something broke".to_string()));
    }

    #[test]
    fn on_warning_adds_dim_warning_line_to_scrollback() {
        let state = new_state();
        let msg = RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_warning".to_string()),
            params: Some(serde_json::json!({
                "message": "WARNING: gateway connection retry in 5s"
            })),
            result: None,
            error: None,
        };
        let (state, effects) = reduce(state, Event::RpcNotification(msg));
        assert!(state
            .scrollback
            .iter()
            .any(|line| line == "WARNING: gateway connection retry in 5s"));
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn on_cost_update_updates_status() {
        let state = new_state();
        let msg = RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_cost_update".to_string()),
            params: Some(serde_json::json!({
                "cost": "$0.0042",
                "tokens_in": 100,
                "tokens_out": 50
            })),
            result: None,
            error: None,
        };
        let (state, _) = reduce(state, Event::RpcNotification(msg));
        assert_eq!(state.status.cost, Some("$0.0042".to_string()));
        assert_eq!(state.status.tokens_in, 100);
        assert_eq!(state.status.tokens_out, 50);
    }

    #[test]
    fn on_task_state_updates_task_list() {
        let state = new_state();
        let msg = RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_task_state".to_string()),
            params: Some(serde_json::json!({
                "tasks": [{"id": "t1", "title": "build", "status": "done"}],
                "subagents": [{"id": "s1", "role": "coder", "status": "running"}]
            })),
            result: None,
            error: None,
        };
        let (state, _) = reduce(state, Event::RpcNotification(msg));
        assert_eq!(state.tasks.len(), 1);
        assert_eq!(state.subagents.len(), 1);
        assert_eq!(state.status.bg_tasks, 1);
    }

    #[test]
    fn on_tool_request_opens_approval_stage() {
        let state = new_state();
        let msg = RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: Some(9001),
            method: Some("on_tool_request".to_string()),
            params: Some(serde_json::json!({
                "tool": "write_file",
                "args": "{\"path\":\"demo.txt\"}"
            })),
            result: None,
            error: None,
        };
        let (state, _) = reduce(state, Event::RpcInboundRequest(msg));
        assert_eq!(state.stage, Stage::Approval);
        assert_eq!(
            state.approval.as_ref().map(|a| a.tool.as_str()),
            Some("write_file")
        );
    }

    #[test]
    fn second_modal_request_is_queued_until_first_is_resolved() {
        let state = new_state();
        let (state, _) = reduce(
            state,
            Event::RpcInboundRequest(RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(31),
                method: Some("on_tool_request".to_string()),
                params: Some(serde_json::json!({
                    "tool": "bash",
                    "args": "ls"
                })),
                result: None,
                error: None,
            }),
        );

        let (state, _) = reduce(
            state,
            Event::RpcInboundRequest(RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(32),
                method: Some("on_ask_user".to_string()),
                params: Some(serde_json::json!({
                    "question": "Continue?",
                    "options": ["Yes", "No"],
                    "allow_text": false
                })),
                result: None,
                error: None,
            }),
        );

        assert_eq!(state.stage, Stage::Approval);
        assert_eq!(
            state.approval.as_ref().map(|a| a.tool.as_str()),
            Some("bash")
        );
        assert_eq!(state.modal_queue.len(), 1);

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('n'), KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::AskUser);
        assert_eq!(
            state.ask_user.as_ref().map(|ask| ask.question.as_str()),
            Some("Continue?")
        );
        assert!(state.approval.is_none());
        assert!(state.modal_queue.is_empty());
    }

    #[test]
    fn on_ask_user_opens_prompt_stage() {
        let state = new_state();
        let msg = RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: Some(9002),
            method: Some("on_ask_user".to_string()),
            params: Some(serde_json::json!({
                "question": "Proceed?",
                "options": ["yes", "no"],
                "allow_text": false
            })),
            result: None,
            error: None,
        };
        let (state, _) = reduce(state, Event::RpcInboundRequest(msg));
        assert_eq!(state.stage, Stage::AskUser);
        assert_eq!(
            state.ask_user.as_ref().map(|a| a.question.as_str()),
            Some("Proceed?")
        );
    }

    #[test]
    fn followup_queue_auto_send_on_done() {
        let mut state = new_state();
        state
            .followup_queue
            .push_back("follow-up message".to_string());
        let (state, _) = reduce(state, Event::RpcNotification(on_done_msg()));
        assert!(state.followup_queue.is_empty());
        assert_eq!(state.next_request_id, 2);
    }

    #[test]
    fn ctrl_k_requests_backend_command_list_and_enters_palette() {
        let state = new_state();
        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('k'), KeyModifiers::CONTROL)),
        );

        assert_eq!(state.stage, Stage::Palette);
        assert!(state.palette.is_some());
        assert_eq!(
            state.palette.as_ref().map(|palette| palette.mode.clone()),
            Some(PaletteMode::CommandPalette)
        );
        assert!(find_sent_rpc(&effects, "command.list").is_some());
    }

    #[test]
    fn ctrl_t_toggles_task_panel() {
        let state = new_state();
        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('t'), KeyModifiers::CONTROL)),
        );

        assert!(state.task_panel_open);
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn ctrl_q_toggles_followup_panel() {
        let state = new_state();
        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('q'), KeyModifiers::CONTROL)),
        );

        assert!(state.followup_panel_open);
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn slash_opens_backend_command_overlay() {
        let state = new_state();
        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('/'), KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Palette);
        assert!(state.palette.is_some());
        assert_eq!(
            state.palette.as_ref().map(|palette| palette.mode.clone()),
            Some(PaletteMode::SlashAutocomplete)
        );
        assert!(find_sent_rpc(&effects, "command.list").is_some());
        assert_eq!(state.composer_text.as_str(), "/");
    }

    #[test]
    fn slash_opens_backend_command_overlay_while_streaming() {
        let mut state = new_state();
        state.stage = Stage::Streaming;

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('/'), KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Palette);
        assert!(state.palette.is_some());
        assert_eq!(
            state.palette.as_ref().map(|palette| palette.mode.clone()),
            Some(PaletteMode::SlashAutocomplete)
        );
        assert!(find_sent_rpc(&effects, "command.list").is_some());
    }

    #[test]
    fn command_list_response_populates_palette_entries() {
        let mut state = new_state();
        state.stage = Stage::Palette;
        state.palette = Some(crate::state::model::PaletteState {
            mode: PaletteMode::CommandPalette,
            filter: TextBuf::default(),
            cursor: 0,
            entries: vec![],
        });
        state.pending_requests.insert(
            9,
            crate::state::model::PendingRequest {
                method: "command.list".into(),
                sent_at: std::time::Instant::now(),
            },
        );

        let (state, effects) = reduce(
            state,
            Event::RpcResponse(RPCMessage {
                jsonrpc: "2.0".into(),
                id: Some(9),
                method: None,
                params: None,
                result: Some(serde_json::json!({
                    "commands": [
                        {"name": "help", "aliases": ["h"], "description": "Show help"},
                        {"name": "model", "aliases": ["m"], "description": "Change model"}
                    ]
                })),
                error: None,
            }),
        );

        let palette = state.palette.expect("palette");
        assert_eq!(palette.entries.len(), 2);
        assert_eq!(palette.entries[0].name, "/help");
        assert_eq!(palette.entries[1].description, "Change model");
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn help_command_opens_backend_driven_palette() {
        let mut state = new_state();
        state.composer_text.set_text("/help");

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Palette);
        assert!(find_sent_rpc(&effects, "command.list").is_some());
        assert!(state.scrollback.iter().any(|line| line == "/help"));
    }

    #[test]
    fn backend_owned_slash_command_dispatches_via_command_rpc() {
        let mut state = new_state();
        state.composer_text.set_text("/tui");

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        assert!(state.scrollback.iter().any(|line| line == "/tui"));
        let rpc = find_sent_rpc(&effects, "command").expect("command rpc");
        assert_eq!(
            rpc.params
                .as_ref()
                .and_then(|v| v.get("cmd"))
                .and_then(|v| v.as_str()),
            Some("/tui")
        );
    }

    #[test]
    fn palette_enter_uses_filtered_entry_list() {
        let mut state = new_state();
        state.stage = Stage::Palette;
        let mut filter = TextBuf::default();
        filter.set_text("mo");
        state.palette = Some(crate::state::model::PaletteState {
            mode: PaletteMode::CommandPalette,
            filter,
            cursor: 0,
            entries: vec![
                crate::state::model::PaletteEntry {
                    name: "/clear".into(),
                    description: "Clear scrollback".into(),
                },
                crate::state::model::PaletteEntry {
                    name: "/model".into(),
                    description: "Change model".into(),
                },
            ],
        });

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Idle);
        assert!(find_sent_rpc(&effects, "model.list").is_some());
    }

    #[test]
    fn model_list_response_opens_picker_with_backend_entries() {
        let mut state = new_state();
        state.pending_requests.insert(
            11,
            crate::state::model::PendingRequest {
                method: "model.list".into(),
                sent_at: std::time::Instant::now(),
            },
        );

        let (state, _) = reduce(
            state,
            Event::RpcResponse(RPCMessage {
                jsonrpc: "2.0".into(),
                id: Some(11),
                method: None,
                params: None,
                result: Some(serde_json::json!({
                    "models": ["tools", "coding", "fast"],
                    "current": "tools"
                })),
                error: None,
            }),
        );

        assert_eq!(
            state.stage,
            Stage::Picker(crate::state::model::PickerKind::Model)
        );
        let picker = state.picker.expect("picker");
        assert_eq!(picker.entries, vec!["tools", "coding", "fast"]);
    }

    #[test]
    fn session_list_response_enters_session_picker() {
        let mut state = new_state();
        state.pending_requests.insert(
            12,
            crate::state::model::PendingRequest {
                method: "session.list".into(),
                sent_at: std::time::Instant::now(),
            },
        );

        let (state, _) = reduce(
            state,
            Event::RpcResponse(RPCMessage {
                jsonrpc: "2.0".into(),
                id: Some(12),
                method: None,
                params: None,
                result: Some(serde_json::json!({
                    "sessions": [
                        {"id": "sess-1", "title": "First", "model": "tools", "provider": "openrouter"},
                        {"id": "sess-2", "title": "Second", "model": "coding", "provider": "openai"}
                    ]
                })),
                error: None,
            }),
        );

        assert_eq!(
            state.stage,
            Stage::Picker(crate::state::model::PickerKind::Session)
        );
        let picker = state.picker.expect("picker");
        assert!(picker.entries[0].contains("First"));
        assert!(picker.entries[1].contains("sess-2"));
    }

    #[test]
    fn session_picker_enter_honors_filtered_visible_selection() {
        let mut state = new_state();
        state.stage = Stage::Picker(crate::state::model::PickerKind::Session);
        let mut filter = TextBuf::default();
        filter.set_text("second");
        state.picker = Some(crate::state::model::PickerState {
            kind: crate::state::model::PickerKind::Session,
            entries: vec!["First [sess-1]".into(), "Second [sess-2]".into()],
            filter,
            cursor: 0,
        });
        state.session_list = Some(vec![
            crate::rpc::protocol::SessionInfo {
                id: "sess-1".into(),
                title: "First".into(),
                model: "tools".into(),
                provider: "openrouter".into(),
            },
            crate::rpc::protocol::SessionInfo {
                id: "sess-2".into(),
                title: "Second".into(),
                model: "coding".into(),
                provider: "openai".into(),
            },
        ]);

        let (_, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        let msg = find_sent_rpc(&effects, "session.resume").expect("session.resume");
        assert_eq!(
            msg.params
                .as_ref()
                .and_then(|params| params.get("session_id")),
            Some(&serde_json::json!("sess-2"))
        );
    }

    #[test]
    fn new_command_uses_session_new_rpc() {
        let mut state = new_state();
        state.composer_text.set_text("/new Fresh start");

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        let msg = find_sent_rpc(&effects, "session.new").expect("session.new");
        assert_eq!(
            msg.params.as_ref().and_then(|params| params.get("title")),
            Some(&serde_json::json!("Fresh start"))
        );
        assert!(state.composer_text.is_empty());
        assert!(find_sent_rpc(&effects, "command").is_none());
    }

    #[test]
    fn plan_command_uses_plan_set_rpc() {
        let mut state = new_state();
        state.composer_text.set_text("/plan");

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        let msg = find_sent_rpc(&effects, "plan.set").expect("plan.set");
        assert_eq!(
            msg.params.as_ref().and_then(|params| params.get("mode")),
            Some(&serde_json::json!("planning"))
        );
        assert!(state.scrollback.iter().any(|line| line == "/plan"));
        assert_eq!(state.detail_surface, Some(DetailSurface::Plan));
    }

    #[test]
    fn stage2_and_stage3_commands_open_detail_surfaces() {
        let cases = [
            ("/restore", DetailSurface::Restore),
            ("/review", DetailSurface::Review),
            ("/diff", DetailSurface::Diff),
            ("/grep", DetailSurface::Grep),
            ("/escalation", DetailSurface::Escalation),
            ("/cc", DetailSurface::CommandCenter),
            ("/multi", DetailSurface::Multi),
        ];

        for (cmd, expected) in cases {
            let mut state = new_state();
            state.composer_text.set_text(cmd);

            let (state, effects) = reduce(
                state,
                Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
            );

            assert_eq!(
                state.detail_surface,
                Some(expected.clone()),
                "command {cmd}"
            );
            assert!(
                state.scrollback.iter().any(|line| line == cmd),
                "command {cmd}"
            );
            assert!(has_effect(&effects, &Effect::Render), "command {cmd}");
        }
    }

    #[test]
    fn escape_closes_detail_surface_without_quitting() {
        let mut state = new_state();
        state.detail_surface = Some(DetailSurface::Review);

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Esc, KeyModifiers::NONE)),
        );

        assert!(state.detail_surface.is_none());
        assert!(has_effect(&effects, &Effect::Render));
        assert!(!has_effect(&effects, &Effect::Quit));
    }

    #[test]
    fn slash_overlay_enter_completes_selected_command_into_composer() {
        let mut state = new_state();
        state.stage = Stage::Palette;
        state.composer_text.set_text("/mo");
        let mut filter = TextBuf::default();
        filter.set_text("mo");
        state.palette = Some(crate::state::model::PaletteState {
            mode: PaletteMode::SlashAutocomplete,
            filter,
            cursor: 0,
            entries: vec![
                crate::state::model::PaletteEntry {
                    name: "/model".into(),
                    description: "Change model".into(),
                },
                crate::state::model::PaletteEntry {
                    name: "/help".into(),
                    description: "Show help".into(),
                },
            ],
        });

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Idle);
        assert_eq!(state.composer_text.as_str(), "/model");
        assert!(find_sent_rpc(&effects, "model.list").is_none());
    }

    #[test]
    fn slash_overlay_enter_dispatches_exact_match() {
        let mut state = new_state();
        state.stage = Stage::Palette;
        state.composer_text.set_text("/model");
        let mut filter = TextBuf::default();
        filter.set_text("model");
        state.palette = Some(crate::state::model::PaletteState {
            mode: PaletteMode::SlashAutocomplete,
            filter,
            cursor: 0,
            entries: vec![crate::state::model::PaletteEntry {
                name: "/model".into(),
                description: "Change model".into(),
            }],
        });

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Idle);
        assert!(state.composer_text.is_empty());
        assert!(find_sent_rpc(&effects, "model.list").is_some());
    }

    #[test]
    fn slash_overlay_tab_completes_selected_command_into_composer() {
        let mut state = new_state();
        state.stage = Stage::Palette;
        state.composer_text.set_text("/pro");
        let mut filter = TextBuf::default();
        filter.set_text("pro");
        state.palette = Some(crate::state::model::PaletteState {
            mode: PaletteMode::SlashAutocomplete,
            filter,
            cursor: 0,
            entries: vec![crate::state::model::PaletteEntry {
                name: "/provider".into(),
                description: "Change provider".into(),
            }],
        });

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Tab, KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Idle);
        assert_eq!(state.composer_text.as_str(), "/provider");
        assert!(effects
            .iter()
            .all(|effect| !matches!(effect, Effect::SendRpc(_))));
    }

    #[test]
    fn slash_overlay_typing_stays_visible_in_main_composer() {
        let state = new_state();
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('/'), KeyModifiers::NONE)),
        );
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('t'), KeyModifiers::NONE)),
        );
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('u'), KeyModifiers::NONE)),
        );
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('i'), KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Palette);
        assert_eq!(state.composer_text.as_str(), "/tui");
        assert_eq!(
            state
                .palette
                .as_ref()
                .map(|palette| palette.filter.as_str()),
            Some("tui")
        );
    }

    #[test]
    fn slash_overlay_backspace_from_empty_filter_closes_and_clears_draft() {
        let state = new_state();
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('/'), KeyModifiers::NONE)),
        );

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Backspace, KeyModifiers::NONE)),
        );

        assert_eq!(state.stage, Stage::Idle);
        assert!(state.palette.is_none());
        assert!(state.composer_text.is_empty());
    }

    #[test]
    fn session_new_response_resets_streaming_state_and_pending_requests() {
        let mut state = new_state();
        state.stage = Stage::Streaming;
        state.scrollback.push_back("> old task".into());
        state.stream_buf = "old reply".into();
        state.stream_lines = vec!["old reply".into()];
        state.pending_requests.insert(
            1,
            crate::state::model::PendingRequest {
                method: "chat".into(),
                sent_at: std::time::Instant::now(),
            },
        );
        state.pending_requests.insert(
            2,
            crate::state::model::PendingRequest {
                method: "session.new".into(),
                sent_at: std::time::Instant::now(),
            },
        );
        state.error_banner = Some("timeout".into());
        state.status.tokens_in = 77;
        state.status.tokens_out = 88;
        state.status.cost = Some("$1.23".into());
        state.tasks.push(crate::rpc::protocol::TaskEntry {
            id: "task-1".into(),
            title: "Lingering task".into(),
            status: "running".into(),
        });
        state.subagents.push(crate::rpc::protocol::SubagentEntry {
            id: "agent-1".into(),
            role: "coder".into(),
            status: "running".into(),
        });

        let (state, _) = reduce(
            state,
            Event::RpcResponse(RPCMessage {
                jsonrpc: "2.0".into(),
                id: Some(2),
                method: None,
                params: None,
                result: Some(serde_json::json!({
                    "session_id": "sess-new",
                    "title": "Fresh session"
                })),
                error: None,
            }),
        );

        assert_eq!(state.stage, Stage::Idle);
        assert!(state.pending_requests.is_empty());
        assert!(state.stream_buf.is_empty());
        assert!(state.stream_lines.is_empty());
        assert!(state.error_banner.is_none());
        assert_eq!(state.status.session_id.as_deref(), Some("sess-new"));
        assert_eq!(state.status.tokens_in, 0);
        assert_eq!(state.status.tokens_out, 0);
        assert!(state.status.cost.is_none());
        assert!(state.tasks.is_empty());
        assert!(state.subagents.is_empty());
        assert_eq!(
            state.scrollback.back().map(|line| line.as_str()),
            Some("[System] Started new session: Fresh session")
        );
    }

    #[test]
    fn session_resume_response_resets_streaming_state_and_pending_requests() {
        let mut state = new_state();
        state.stage = Stage::Streaming;
        state.scrollback.push_back("> old task".into());
        state.stream_lines = vec!["old reply".into()];
        state.pending_requests.insert(
            3,
            crate::state::model::PendingRequest {
                method: "chat".into(),
                sent_at: std::time::Instant::now(),
            },
        );
        state.pending_requests.insert(
            4,
            crate::state::model::PendingRequest {
                method: "session.resume".into(),
                sent_at: std::time::Instant::now(),
            },
        );

        let (state, _) = reduce(
            state,
            Event::RpcResponse(RPCMessage {
                jsonrpc: "2.0".into(),
                id: Some(4),
                method: None,
                params: None,
                result: Some(serde_json::json!({
                    "session_id": "sess-2",
                    "title": "Recovered work"
                })),
                error: None,
            }),
        );

        assert_eq!(state.stage, Stage::Idle);
        assert!(state.pending_requests.is_empty());
        assert_eq!(state.status.session_id.as_deref(), Some("sess-2"));
        assert_eq!(
            state.scrollback.back().map(|line| line.as_str()),
            Some("[System] Resumed session: Recovered work")
        );
    }

    #[test]
    fn compact_command_response_surfaces_visible_summary() {
        let mut state = new_state();
        state.pending_requests.insert(
            21,
            crate::state::model::PendingRequest {
                method: "command:/compact".into(),
                sent_at: std::time::Instant::now(),
            },
        );

        let (state, _) = reduce(
            state,
            Event::RpcResponse(RPCMessage {
                jsonrpc: "2.0".into(),
                id: Some(21),
                method: None,
                params: None,
                result: Some(serde_json::json!({
                    "ok": true,
                    "messages_compacted": 6,
                    "summary_tokens": 42
                })),
                error: None,
            }),
        );

        assert!(state
            .scrollback
            .iter()
            .any(|line| line == "Compacted 6 turns → 42 tokens"));
    }

    #[test]
    fn recovery_navigation_moves_selection_and_enter_opens_selected_surface() {
        let mut state = new_state();
        state.stage = Stage::Shutdown;
        state.error_banner = Some("matrix shard failure".into());

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Right, KeyModifiers::NONE)),
        );
        assert_eq!(state.recovery_action_idx, 1);
        assert!(has_effect(&effects, &Effect::Render));

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Right, KeyModifiers::NONE)),
        );
        assert_eq!(state.recovery_action_idx, 2);
        assert!(has_effect(&effects, &Effect::Render));

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Enter, KeyModifiers::NONE)),
        );
        assert_eq!(state.detail_surface, Some(DetailSurface::Restore));
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn on_tool_call_tracks_multiple_tools_without_overwrite() {
        let state = new_state();
        let (state, _) = reduce(
            state,
            Event::RpcNotification(RPCMessage {
                jsonrpc: "2.0".into(),
                id: None,
                method: Some("on_tool_call".into()),
                params: Some(serde_json::json!({
                    "name": "bash",
                    "status": "running",
                    "args": "ls",
                })),
                result: None,
                error: None,
            }),
        );
        let (state, _) = reduce(
            state,
            Event::RpcNotification(RPCMessage {
                jsonrpc: "2.0".into(),
                id: None,
                method: Some("on_tool_call".into()),
                params: Some(serde_json::json!({
                    "name": "write_file",
                    "status": "completed",
                    "args": "{\"path\":\"demo.txt\"}",
                    "result": "ok",
                })),
                result: None,
                error: None,
            }),
        );

        assert_eq!(state.active_tools.len(), 2);
        assert_eq!(
            state.current_tool.as_ref().map(|tool| tool.name.as_str()),
            Some("write_file")
        );
    }

    #[test]
    fn stale_request_detection() {
        use std::time::{Duration, Instant};

        let mut state = new_state();
        state.pending_requests.insert(
            1,
            crate::state::model::PendingRequest {
                method: "chat".to_string(),
                sent_at: Instant::now() - Duration::from_secs(31),
            },
        );
        let (state, effects) = reduce(state, Event::Tick);
        assert!(state.pending_requests.is_empty());
        assert!(state.error_banner.is_some());
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn tick_caps_followup_queue_to_limit() {
        let mut state = new_state();
        for idx in 0..40 {
            state.followup_queue.push_back(format!("queued {}", idx));
        }

        let (state, effects) = reduce(state, Event::Tick);

        assert_eq!(state.followup_queue.len(), 32);
        assert_eq!(
            state.followup_queue.front().map(|s| s.as_str()),
            Some("queued 8")
        );
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn ctrl_l_clears_transcript_and_transient_ui_state() {
        let mut state = new_state();
        state.scrollback.push_back("hello".into());
        state.stream_buf = "partial".into();
        state.stream_lines = vec!["partial".into()];
        state.error_banner = Some("boom".into());
        state.current_tool = Some(crate::state::model::ToolCallInfo {
            name: "bash".into(),
            status: "running".into(),
            args: Some("ls".into()),
            result: None,
        });
        state.followup_queue.push_back("queued".into());

        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('l'), KeyModifiers::CONTROL)),
        );

        assert!(state.scrollback.is_empty());
        assert!(state.stream_buf.is_empty());
        assert!(state.stream_lines.is_empty());
        assert!(state.followup_queue.is_empty());
        assert!(state.error_banner.is_none());
        assert!(state.current_tool.is_none());
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn ask_user_free_text_accepts_unicode_input() {
        let mut state = new_state();
        state.stage = Stage::AskUser;
        state.ask_user = Some(AskUserRequest {
            source: AskUserSource::Inbound(InboundId::new(7)),
            question: "Why?".into(),
            options: vec![],
            allow_text: true,
            selected: 0,
            free_text: TextBuf::default(),
        });

        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('é'), KeyModifiers::NONE)),
        );
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('🙂'), KeyModifiers::NONE)),
        );
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Left, KeyModifiers::NONE)),
        );
        let (state, _) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Backspace, KeyModifiers::NONE)),
        );

        assert_eq!(
            state.ask_user.as_ref().map(|ask| ask.free_text.as_str()),
            Some("🙂")
        );
    }

    #[test]
    fn on_thinking_flushes_overflow_lines_to_scrollback() {
        let state = new_state();
        let payload = (0..25)
            .map(|idx| format!("line {}", idx))
            .collect::<Vec<_>>()
            .join("\n");

        let (state, _) = reduce(
            state,
            Event::RpcNotification(RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: None,
                method: Some("on_thinking".to_string()),
                params: Some(serde_json::json!({ "text": payload })),
                result: None,
                error: None,
            }),
        );

        assert!(state.scrollback.iter().any(|line| line == "line 0"));
        assert!(state.stream_lines.len() <= 20);
    }

    #[test]
    fn ctrl_e_enters_editor_launch_stage_when_editor_is_set() {
        std::env::set_var("EDITOR", "code --wait");
        let state = new_state();
        let (state, effects) = reduce(
            state,
            Event::Key(KeyEvent::new(KeyCode::Char('e'), KeyModifiers::CONTROL)),
        );
        std::env::remove_var("EDITOR");

        assert_eq!(state.stage, Stage::EditorLaunch);
        assert!(has_effect(&effects, &Effect::SpawnEditor(String::new())));
    }

    #[test]
    fn editor_done_returns_to_idle_stage() {
        let mut state = new_state();
        state.stage = Stage::EditorLaunch;

        let (state, effects) = reduce(state, Event::EditorDone("edited".into()));
        assert_eq!(state.stage, Stage::Idle);
        assert_eq!(state.composer_text.as_str(), "edited");
        assert!(has_effect(&effects, &Effect::Render));
    }

    #[test]
    fn editor_failed_returns_to_idle_with_banner() {
        let mut state = new_state();
        state.stage = Stage::EditorLaunch;

        let (state, effects) = reduce(state, Event::EditorFailed("boom".into()));
        assert_eq!(state.stage, Stage::Idle);
        assert_eq!(state.error_banner, Some("boom".into()));
        assert!(has_effect(&effects, &Effect::Render));
    }
}
