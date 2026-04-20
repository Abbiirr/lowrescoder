use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RPCMessage {
    pub jsonrpc: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub method: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub params: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<RPCError>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RPCError {
    pub code: i32,
    pub message: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct TokenParams {
    pub text: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct ThinkingParams {
    pub text: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct DoneParams {
    pub tokens_in: u32,
    pub tokens_out: u32,
    #[serde(default)]
    pub cancelled: bool,
    #[serde(default)]
    pub layer_used: u32,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct ToolCallParams {
    pub name: String,
    pub status: String,
    #[serde(default)]
    pub result: Option<String>,
    #[serde(default)]
    pub args: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ErrorParams {
    pub message: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct StatusParams {
    pub model: String,
    pub provider: String,
    pub mode: String,
    #[serde(default)]
    pub session_id: Option<String>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
pub struct TaskStateParams {
    pub tasks: Vec<TaskEntry>,
    pub subagents: Vec<SubagentEntry>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
pub struct TaskEntry {
    pub id: String,
    pub title: String,
    pub status: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
pub struct SubagentEntry {
    pub id: String,
    pub role: String,
    pub status: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct CostUpdateParams {
    pub cost: String,
    pub tokens_in: u32,
    pub tokens_out: u32,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct ApprovalRequestParams {
    pub tool: String,
    pub args: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct AskUserRequestParams {
    pub question: String,
    #[serde(default)]
    pub options: Vec<String>,
    #[serde(default)]
    pub allow_text: bool,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct ChatParams {
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct CancelParams {}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct CommandParams {
    pub cmd: String,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct SessionNewParams {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub title: Option<String>,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct SessionResumeParams {
    pub session_id: String,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct SessionListParams {}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct SessionListResult {
    pub sessions: Vec<SessionInfo>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize, Clone)]
pub struct SessionInfo {
    pub id: String,
    pub title: String,
    pub model: String,
    pub provider: String,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct ForkSessionParams {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
pub struct ForkSessionResult {
    pub new_session_id: String,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct ConfigSetParams {
    pub key: String,
    pub value: String,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct SteerParams {
    pub message: String,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct ApprovalResult {
    pub approved: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_approve: Option<bool>,
}

#[allow(dead_code)]
#[derive(Debug, Serialize)]
pub struct AskUserResult {
    pub answer: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rpc_message_roundtrip_notification() {
        let msg = RPCMessage {
            jsonrpc: "2.0".into(),
            id: None,
            method: Some("on_status".into()),
            params: Some(serde_json::json!({
                "model": "claude",
                "provider": "anthropic",
                "mode": "chat"
            })),
            result: None,
            error: None,
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back = serde_json::from_str::<RPCMessage>(&json).unwrap();
        assert_eq!(back.jsonrpc, "2.0");
        assert_eq!(back.method, Some("on_status".into()));
    }

    #[test]
    fn rpc_message_roundtrip_request_with_id() {
        let msg = RPCMessage {
            jsonrpc: "2.0".into(),
            id: Some(42),
            method: Some("session_new".into()),
            params: Some(serde_json::json!({"title": "test"})),
            result: None,
            error: None,
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back = serde_json::from_str::<RPCMessage>(&json).unwrap();
        assert_eq!(back.id, Some(42));
        assert_eq!(back.method, Some("session_new".into()));
    }

    #[test]
    fn rpc_message_roundtrip_response() {
        let msg = RPCMessage {
            jsonrpc: "2.0".into(),
            id: Some(1),
            method: None,
            params: None,
            result: Some(serde_json::json!("ok")),
            error: None,
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back = serde_json::from_str::<RPCMessage>(&json).unwrap();
        assert_eq!(back.id, Some(1));
        assert_eq!(back.result, Some(serde_json::json!("ok")));
    }

    #[test]
    fn rpc_message_roundtrip_error() {
        let msg = RPCMessage {
            jsonrpc: "2.0".into(),
            id: Some(5),
            method: None,
            params: None,
            result: None,
            error: Some(RPCError {
                code: -32600,
                message: "Invalid Request".into(),
            }),
        };
        let json = serde_json::to_string(&msg).unwrap();
        let back = serde_json::from_str::<RPCMessage>(&json).unwrap();
        assert_eq!(back.error.unwrap().code, -32600);
    }

    #[test]
    fn status_params_roundtrip() {
        let json = r#"{"model":"claude-4","provider":"anthropic","mode":"fast"}"#;
        let params = serde_json::from_str::<StatusParams>(json).unwrap();
        assert_eq!(params.model, "claude-4");
        assert_eq!(params.provider, "anthropic");
        assert_eq!(params.mode, "fast");
        assert_eq!(params.session_id, None);
    }

    #[test]
    fn done_params_roundtrip() {
        let json = r#"{"tokens_in":100,"tokens_out":50,"cancelled":false,"layer_used":3}"#;
        let params = serde_json::from_str::<DoneParams>(json).unwrap();
        assert_eq!(params.tokens_in, 100);
        assert_eq!(params.tokens_out, 50);
        assert!(!params.cancelled);
        assert_eq!(params.layer_used, 3);
    }

    #[test]
    fn tool_call_params_roundtrip() {
        let json = r#"{"name":"bash","status":"completed","result":"ok","args":"ls"}"#;
        let params = serde_json::from_str::<ToolCallParams>(json).unwrap();
        assert_eq!(params.name, "bash");
        assert_eq!(params.status, "completed");
        assert_eq!(params.result, Some("ok".into()));
    }

    #[test]
    fn session_info_roundtrip() {
        let json =
            r#"{"id":"sess-123","title":"my session","model":"claude","provider":"anthropic"}"#;
        let info = serde_json::from_str::<SessionInfo>(json).unwrap();
        assert_eq!(info.id, "sess-123");
        assert_eq!(info.title, "my session");
    }

    #[test]
    fn approval_result_roundtrip() {
        let result = ApprovalResult {
            approved: true,
            session_approve: Some(true),
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("\"approved\":true"));
        assert!(json.contains("\"session_approve\":true"));
    }

    #[test]
    fn token_params_roundtrip() {
        let json = r#"{"text":"hello world"}"#;
        let params = serde_json::from_str::<TokenParams>(json).unwrap();
        assert_eq!(params.text, "hello world");
    }

    #[test]
    fn thinking_params_roundtrip() {
        let json = r#"{"text":"let me think..."}"#;
        let params = serde_json::from_str::<ThinkingParams>(json).unwrap();
        assert_eq!(params.text, "let me think...");
    }

    #[test]
    fn done_params_default_cancelled_false() {
        let json = r#"{"tokens_in":10,"tokens_out":5}"#;
        let params = serde_json::from_str::<DoneParams>(json).unwrap();
        assert!(!params.cancelled);
        assert_eq!(params.layer_used, 0);
    }

    #[test]
    fn error_params_roundtrip() {
        let json = r#"{"message":"something broke"}"#;
        let params = serde_json::from_str::<ErrorParams>(json).unwrap();
        assert_eq!(params.message, "something broke");
    }

    #[test]
    fn task_state_params_roundtrip() {
        let json = r#"{"tasks":[{"id":"t1","title":"build","status":"done"}],"subagents":[{"id":"s1","role":"coder","status":"running"}]}"#;
        let params = serde_json::from_str::<TaskStateParams>(json).unwrap();
        assert_eq!(params.tasks.len(), 1);
        assert_eq!(params.tasks[0].id, "t1");
        assert_eq!(params.subagents.len(), 1);
        assert_eq!(params.subagents[0].role, "coder");
    }

    #[test]
    fn cost_update_params_roundtrip() {
        let json = r#"{"cost":"$0.0042","tokens_in":100,"tokens_out":50}"#;
        let params = serde_json::from_str::<CostUpdateParams>(json).unwrap();
        assert_eq!(params.cost, "$0.0042");
        assert_eq!(params.tokens_in, 100);
        assert_eq!(params.tokens_out, 50);
    }

    #[test]
    fn approval_request_params_roundtrip() {
        let json = r#"{"tool":"bash","args":"rm -rf /"}"#;
        let params = serde_json::from_str::<ApprovalRequestParams>(json).unwrap();
        assert_eq!(params.tool, "bash");
        assert_eq!(params.args, "rm -rf /");
    }

    #[test]
    fn ask_user_request_params_roundtrip() {
        let json = r#"{"question":"Continue?","options":["Yes","No"],"allow_text":true}"#;
        let params = serde_json::from_str::<AskUserRequestParams>(json).unwrap();
        assert_eq!(params.question, "Continue?");
        assert_eq!(params.options, vec!["Yes", "No"]);
        assert!(params.allow_text);
    }

    #[test]
    fn ask_user_request_params_defaults() {
        let json = r#"{"question":"OK?"}"#;
        let params = serde_json::from_str::<AskUserRequestParams>(json).unwrap();
        assert!(params.options.is_empty());
        assert!(!params.allow_text);
    }

    #[test]
    fn chat_params_roundtrip() {
        let params = ChatParams {
            message: "hello".into(),
            session_id: Some("sess-1".into()),
        };
        let json = serde_json::to_string(&params).unwrap();
        assert!(json.contains("\"message\":\"hello\""));
        assert!(json.contains("\"session_id\":\"sess-1\""));
    }

    #[test]
    fn chat_params_no_session_id() {
        let params = ChatParams {
            message: "hello".into(),
            session_id: None,
        };
        let json = serde_json::to_string(&params).unwrap();
        assert!(!json.contains("session_id"));
    }

    #[test]
    fn cancel_params_roundtrip() {
        let params = CancelParams {};
        let json = serde_json::to_string(&params).unwrap();
        assert_eq!(json, "{}");
    }

    #[test]
    fn command_params_roundtrip() {
        let params = CommandParams {
            cmd: "/clear".into(),
        };
        let json = serde_json::to_string(&params).unwrap();
        assert!(json.contains("\"cmd\":\"/clear\""));
    }

    #[test]
    fn session_new_params_roundtrip() {
        let params = SessionNewParams {
            title: Some("test".into()),
        };
        let json = serde_json::to_string(&params).unwrap();
        assert!(json.contains("\"title\":\"test\""));
    }

    #[test]
    fn session_new_params_no_title() {
        let params = SessionNewParams { title: None };
        let json = serde_json::to_string(&params).unwrap();
        assert!(!json.contains("title"));
    }

    #[test]
    fn session_resume_params_roundtrip() {
        let params = SessionResumeParams {
            session_id: "abc".into(),
        };
        let json = serde_json::to_string(&params).unwrap();
        assert!(json.contains("\"session_id\":\"abc\""));
    }

    #[test]
    fn session_list_params_roundtrip() {
        let params = SessionListParams {};
        let json = serde_json::to_string(&params).unwrap();
        assert_eq!(json, "{}");
    }

    #[test]
    fn session_list_result_roundtrip() {
        let json = r#"{"sessions":[{"id":"s1","title":"t1","model":"m1","provider":"p1"}]}"#;
        let result = serde_json::from_str::<SessionListResult>(json).unwrap();
        assert_eq!(result.sessions.len(), 1);
        assert_eq!(result.sessions[0].id, "s1");
    }

    #[test]
    fn fork_session_params_roundtrip() {
        let params = ForkSessionParams { session_id: None };
        let json = serde_json::to_string(&params).unwrap();
        assert!(!json.contains("session_id"));
    }

    #[test]
    fn fork_session_result_roundtrip() {
        let json = r#"{"new_session_id":"new-123"}"#;
        let result = serde_json::from_str::<ForkSessionResult>(json).unwrap();
        assert_eq!(result.new_session_id, "new-123");
    }

    #[test]
    fn config_set_params_roundtrip() {
        let params = ConfigSetParams {
            key: "model".into(),
            value: "claude".into(),
        };
        let json = serde_json::to_string(&params).unwrap();
        assert!(json.contains("\"key\":\"model\""));
        assert!(json.contains("\"value\":\"claude\""));
    }

    #[test]
    fn steer_params_roundtrip() {
        let params = SteerParams {
            message: "try again".into(),
        };
        let json = serde_json::to_string(&params).unwrap();
        assert!(json.contains("\"message\":\"try again\""));
    }

    #[test]
    fn ask_user_result_roundtrip() {
        let result = AskUserResult {
            answer: "Yes".into(),
        };
        let json = serde_json::to_string(&result).unwrap();
        assert!(json.contains("\"answer\":\"Yes\""));
    }
}
