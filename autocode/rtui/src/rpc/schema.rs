#[allow(unused_imports)]
pub use crate::rpc::protocol::{
    ApprovalRequestParams, AskUserRequestParams, ChatAckParams, ChatParams, CommandParams,
    CostUpdateParams, DoneParams, ErrorParams, ForkSessionResult, RPCMessage, SessionListResult,
    StatusParams, TaskStateParams, ThinkingParams, TokenParams, ToolCallParams,
};

pub const METHOD_ON_TASK_STATE: &str = "on_task_state";
pub const METHOD_ON_TOOL_REQUEST: &str = "on_tool_request";
pub const METHOD_ON_ASK_USER: &str = "on_ask_user";

pub fn is_task_state_method(method: &str) -> bool {
    method == METHOD_ON_TASK_STATE
}

pub fn is_tool_request_method(method: &str) -> bool {
    method == METHOD_ON_TOOL_REQUEST
}

pub fn is_ask_user_method(method: &str) -> bool {
    method == METHOD_ON_ASK_USER
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::path::PathBuf;

    use serde_json::Value;

    use super::*;

    fn fixture_path(name: &str) -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../tests/pty/fixtures/rpc-schema-v1")
            .join(name)
    }

    fn load_cases(name: &str) -> Vec<Value> {
        let raw = fs::read_to_string(fixture_path(name)).unwrap();
        serde_json::from_str(&raw).unwrap()
    }

    fn assert_params(method: &str, params: Value) {
        match method {
            "on_status" => {
                let _: StatusParams = serde_json::from_value(params).unwrap();
            }
            "on_error" => {
                let _: ErrorParams = serde_json::from_value(params).unwrap();
            }
            "on_chat_ack" => {
                let _: ChatAckParams = serde_json::from_value(params).unwrap();
            }
            "on_token" => {
                let _: TokenParams = serde_json::from_value(params).unwrap();
            }
            "on_thinking" => {
                let _: ThinkingParams = serde_json::from_value(params).unwrap();
            }
            "on_done" => {
                let _: DoneParams = serde_json::from_value(params).unwrap();
            }
            "on_tool_call" => {
                let _: ToolCallParams = serde_json::from_value(params).unwrap();
            }
            "on_task_state" => {
                let _: TaskStateParams = serde_json::from_value(params).unwrap();
            }
            "on_tool_request" => {
                let _: ApprovalRequestParams = serde_json::from_value(params).unwrap();
            }
            "on_ask_user" => {
                let _: AskUserRequestParams = serde_json::from_value(params).unwrap();
            }
            "chat" => {
                let _: ChatParams = serde_json::from_value(params).unwrap();
            }
            "command" => {
                let _: CommandParams = serde_json::from_value(params).unwrap();
            }
            _ => {}
        }
    }

    fn assert_result(method: &str, result: Value) {
        match method {
            "session.list" => {
                let _: SessionListResult = serde_json::from_value(result).unwrap();
            }
            "session.fork" => {
                let _: ForkSessionResult = serde_json::from_value(result).unwrap();
            }
            _ => {}
        }
    }

    #[test]
    fn fixture_groups_roundtrip_through_rpc_message() {
        for group in [
            "notifications.json",
            "inbound_requests.json",
            "outbound_requests.json",
            "responses.json",
        ] {
            for case in load_cases(group) {
                let message = case.get("message").cloned().unwrap();
                let msg: RPCMessage = serde_json::from_value(message.clone()).unwrap();
                let roundtrip = serde_json::to_value(&msg).unwrap();
                assert_eq!(roundtrip, message);

                if case.get("params_model").is_some() {
                    assert_params(
                        case.get("method").and_then(Value::as_str).unwrap(),
                        msg.params.unwrap(),
                    );
                }

                if case.get("result_model").is_some() {
                    assert_result(
                        case.get("method").and_then(Value::as_str).unwrap(),
                        msg.result.unwrap(),
                    );
                }
            }
        }
    }
}
