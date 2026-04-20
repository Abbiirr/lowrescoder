use crate::rpc::protocol::RPCMessage;
use anyhow::Result;

pub fn encode(msg: &RPCMessage) -> Result<String> {
    let mut json = serde_json::to_string(msg)?;
    json.push('\n');
    Ok(json)
}

pub fn decode(line: &str) -> Result<RPCMessage> {
    let msg: RPCMessage = serde_json::from_str(line)?;
    if msg.jsonrpc != "2.0" {
        anyhow::bail!("invalid jsonrpc version: {}", msg.jsonrpc);
    }
    Ok(msg)
}

#[cfg(test)]
mod tests {
    use super::*;

    const FIXTURES: &[(&str, &[&str])] = &[
        (
            "startup_chat",
            &[
                r#"{"jsonrpc":"2.0","method":"on_status","params":{"model":"tools","provider":"openrouter","mode":"suggest","session_id":"mock-session-001"}}"#,
                r#"{"jsonrpc":"2.0","id":1,"method":"session.resume","params":{"session_id":"mock-session-001"}}"#,
                r#"{"jsonrpc":"2.0","id":1,"result":{"ok":true}}"#,
                r#"{"jsonrpc":"2.0","id":2,"method":"chat","params":{"message":"hi"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":"Hello"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":" from"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":" the"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":" mock"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":" backend"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":"!"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_done","params":{"tokens_in":5,"tokens_out":6,"cancelled":false,"layer_used":4}}"#,
                r#"{"jsonrpc":"2.0","id":2,"result":{"ok":true}}"#,
            ],
        ),
        (
            "session_management",
            &[
                r#"{"jsonrpc":"2.0","id":3,"method":"session.fork","params":{}}"#,
                r#"{"jsonrpc":"2.0","id":3,"result":{"new_session_id":"forked-session-abc123"}}"#,
                r#"{"jsonrpc":"2.0","id":4,"method":"config.set","params":{"key":"model","value":"coding"}}"#,
                r#"{"jsonrpc":"2.0","id":4,"result":{"ok":true}}"#,
                r#"{"jsonrpc":"2.0","id":5,"method":"session.list","params":{}}"#,
                r#"{"jsonrpc":"2.0","id":5,"result":{"sessions":[{"id":"sess-1","title":"First session","model":"tools","provider":"openrouter"},{"id":"sess-2","title":"Second session","model":"coding","provider":"openrouter"}]}}"#,
                r#"{"jsonrpc":"2.0","id":6,"method":"command","params":{"cmd":"/compact"}}"#,
                r#"{"jsonrpc":"2.0","id":6,"result":{"ok":true}}"#,
                r#"{"jsonrpc":"2.0","method":"on_cost_update","params":{"cost":"$0.0042","tokens_in":100,"tokens_out":50}}"#,
            ],
        ),
        (
            "approval_and_ask_user",
            &[
                r#"{"jsonrpc":"2.0","method":"on_status","params":{"model":"tools","provider":"openrouter","mode":"suggest"}}"#,
                r#"{"jsonrpc":"2.0","id":10,"method":"approval","params":{"tool":"bash","args":"ls -la /tmp"}}"#,
                r#"{"jsonrpc":"2.0","id":10,"result":{"approved":true,"session_approve":false}}"#,
                r#"{"jsonrpc":"2.0","method":"on_tool_call","params":{"name":"bash","status":"running"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_tool_call","params":{"name":"bash","status":"completed","result":"total 4"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":"Done"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_done","params":{"tokens_in":10,"tokens_out":1,"cancelled":false,"layer_used":4}}"#,
                r#"{"jsonrpc":"2.0","id":10,"result":{"ok":true}}"#,
                r#"{"jsonrpc":"2.0","id":11,"method":"ask_user","params":{"question":"Continue?","options":["Yes","No","Retry"],"allow_text":false}}"#,
                r#"{"jsonrpc":"2.0","id":11,"result":{"answer":"Yes"}}"#,
                r#"{"jsonrpc":"2.0","method":"on_token","params":{"text":"Continuing..."}}"#,
                r#"{"jsonrpc":"2.0","method":"on_done","params":{"tokens_in":5,"tokens_out":1,"cancelled":false,"layer_used":4}}"#,
            ],
        ),
    ];

    #[test]
    fn conformance_all_fixtures() {
        let mut total = 0;
        for (name, lines) in FIXTURES {
            for (i, line) in lines.iter().enumerate() {
                let decoded = decode(line)
                    .unwrap_or_else(|e| panic!("{}:{} decode failed: {}", name, i + 1, e));
                let encoded = encode(&decoded)
                    .unwrap_or_else(|e| panic!("{}:{} encode failed: {}", name, i + 1, e));
                let roundtrip = decode(encoded.trim_end())
                    .unwrap_or_else(|e| panic!("{}:{} roundtrip failed: {}", name, i + 1, e));
                assert_eq!(decoded.jsonrpc, roundtrip.jsonrpc, "{}:{}", name, i + 1);
                assert_eq!(decoded.id, roundtrip.id, "{}:{}", name, i + 1);
                assert_eq!(decoded.method, roundtrip.method, "{}:{}", name, i + 1);
                assert_eq!(decoded.result, roundtrip.result, "{}:{}", name, i + 1);
                assert_eq!(decoded.error, roundtrip.error, "{}:{}", name, i + 1);
                assert_eq!(decoded.params, roundtrip.params, "{}:{}", name, i + 1);
                total += 1;
            }
        }
        assert!(
            total >= 30,
            "expected at least 30 conformance messages, got {}",
            total
        );
    }
}
