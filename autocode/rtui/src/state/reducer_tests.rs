#[cfg(test)]
mod tests {
    use crate::rpc::protocol::RPCMessage;
    use crate::state::model::{AppState, Stage};
    use crate::state::reducer::{reduce, Effect, Event};

    fn new_state() -> AppState {
        AppState::new((80, 24), false)
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
    fn backend_exit_quits() {
        let state = new_state();
        let (_, effects) = reduce(state, Event::BackendExit(0));
        assert!(has_effect(&effects, &Effect::Quit));
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
    fn on_tasks_updates_task_list() {
        let state = new_state();
        let msg = RPCMessage {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: Some("on_tasks".to_string()),
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
}
