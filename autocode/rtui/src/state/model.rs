use std::collections::{HashMap, VecDeque};

use serde::{Deserialize, Serialize};

use crate::rpc::protocol;

#[allow(dead_code)]
#[derive(Debug, Clone, PartialEq)]
pub enum Stage {
    Idle,
    Streaming,
    ToolCall,
    Approval,
    AskUser,
    Picker(PickerKind),
    Palette,
    EditorLaunch,
    Shutdown,
}

#[allow(dead_code)]
#[derive(Debug, Clone, PartialEq)]
pub enum PickerKind {
    Model,
    Provider,
    Session,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Default)]
pub struct StatusInfo {
    pub model: String,
    pub provider: String,
    pub mode: String,
    pub session_id: Option<String>,
    pub tokens_in: u32,
    pub tokens_out: u32,
    pub cost: Option<String>,
    pub bg_tasks: u32,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct PendingRequest {
    pub method: String,
    pub sent_at: std::time::Instant,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct ToolCallInfo {
    pub name: String,
    pub status: String,
    pub args: Option<String>,
    pub result: Option<String>,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct PickerState {
    pub kind: PickerKind,
    pub entries: Vec<String>,
    pub filter: String,
    pub cursor: usize,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct PaletteState {
    pub filter: String,
    pub cursor: usize,
    pub entries: Vec<PaletteEntry>,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct PaletteEntry {
    pub name: String,
    pub description: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct ApprovalRequest {
    pub rpc_id: i64,
    pub tool: String,
    pub args: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct AskUserRequest {
    pub rpc_id: i64,
    pub question: String,
    pub options: Vec<String>,
    pub allow_text: bool,
    pub selected: usize,
    pub free_text: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoryEntry {
    pub text: String,
    pub last_used_ms: i64,
    pub use_count: u32,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct AppState {
    pub stage: Stage,
    pub scrollback: VecDeque<String>,
    pub stream_buf: String,
    pub stream_lines: Vec<String>,
    pub composer_text: String,
    pub composer_cursor: usize,
    pub composer_lines: Vec<String>,
    pub followup_queue: VecDeque<String>,
    pub history: Vec<HistoryEntry>,
    pub history_cursor: Option<usize>,
    pub status: StatusInfo,
    pub spinner_frame: u8,
    pub spinner_verb_idx: usize,
    pub current_tool: Option<ToolCallInfo>,
    pub tasks: Vec<protocol::TaskEntry>,
    pub subagents: Vec<protocol::SubagentEntry>,
    pub picker: Option<PickerState>,
    pub palette: Option<PaletteState>,
    pub approval: Option<ApprovalRequest>,
    pub ask_user: Option<AskUserRequest>,
    pub error_banner: Option<String>,
    pub plan_mode: bool,
    pub altscreen: bool,
    pub terminal_size: (u16, u16),
    pub pending_requests: HashMap<i64, PendingRequest>,
    pub next_request_id: i64,
    pub session_list: Option<Vec<protocol::SessionInfo>>,
}

impl AppState {
    pub fn new(terminal_size: (u16, u16), altscreen: bool) -> Self {
        Self {
            stage: Stage::Idle,
            scrollback: VecDeque::new(),
            stream_buf: String::new(),
            stream_lines: Vec::new(),
            composer_text: String::new(),
            composer_cursor: 0,
            composer_lines: Vec::new(),
            followup_queue: VecDeque::new(),
            history: Vec::new(),
            history_cursor: None,
            status: StatusInfo::default(),
            spinner_frame: 0,
            spinner_verb_idx: 0,
            current_tool: None,
            tasks: Vec::new(),
            subagents: Vec::new(),
            picker: None,
            palette: None,
            approval: None,
            ask_user: None,
            error_banner: None,
            plan_mode: false,
            altscreen,
            terminal_size,
            pending_requests: HashMap::new(),
            next_request_id: 1,
            session_list: None,
        }
    }
}
