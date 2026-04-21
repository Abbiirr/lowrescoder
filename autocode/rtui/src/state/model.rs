use std::collections::{HashMap, VecDeque};
use std::time::Instant;

use serde::{Deserialize, Serialize};

use crate::rpc::protocol;
use crate::ui::textbuf::TextBuf;

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
#[derive(Debug, Clone, PartialEq)]
pub enum PaletteMode {
    CommandPalette,
    SlashAutocomplete,
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
    pub filter: TextBuf,
    pub cursor: usize,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct PaletteState {
    pub mode: PaletteMode,
    pub filter: TextBuf,
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
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InboundId(i64);

impl InboundId {
    pub fn new(raw: i64) -> Self {
        Self(raw)
    }

    pub fn get(self) -> i64 {
        self.0
    }
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct ApprovalRequest {
    pub rpc_id: InboundId,
    pub tool: String,
    pub args: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AskUserSource {
    Inbound(InboundId),
    Steer,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct AskUserRequest {
    pub source: AskUserSource,
    pub question: String,
    pub options: Vec<String>,
    pub allow_text: bool,
    pub selected: usize,
    pub free_text: TextBuf,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub enum ModalRequest {
    Approval(ApprovalRequest),
    AskUser(AskUserRequest),
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
    pub composer_text: TextBuf,
    pub composer_lines: Vec<String>,
    pub followup_queue: VecDeque<String>,
    pub history: Vec<HistoryEntry>,
    pub history_cursor: Option<usize>,
    pub status: StatusInfo,
    pub spinner_frame: u8,
    pub spinner_verb_idx: usize,
    pub current_tool: Option<ToolCallInfo>,
    pub active_tools: Vec<ToolCallInfo>,
    pub tasks: Vec<protocol::TaskEntry>,
    pub subagents: Vec<protocol::SubagentEntry>,
    pub picker: Option<PickerState>,
    pub palette: Option<PaletteState>,
    pub approval: Option<ApprovalRequest>,
    pub ask_user: Option<AskUserRequest>,
    pub modal_queue: VecDeque<ModalRequest>,
    pub error_banner: Option<String>,
    pub plan_mode: bool,
    pub altscreen: bool,
    pub scroll_offset: u16,
    pub terminal_size: (u16, u16),
    pub pending_requests: HashMap<i64, PendingRequest>,
    pub stale_request_ids: Vec<i64>,
    pub next_request_id: i64,
    pub session_list: Option<Vec<protocol::SessionInfo>>,
    pub last_ctrl_c_at: Option<Instant>,
    pub ctrl_c_count: u8,
    pub task_panel_open: bool,
    pub followup_panel_open: bool,
}

impl AppState {
    pub fn new(terminal_size: (u16, u16), altscreen: bool) -> Self {
        Self {
            stage: Stage::Idle,
            scrollback: VecDeque::new(),
            stream_buf: String::new(),
            stream_lines: Vec::new(),
            composer_text: TextBuf::default(),
            composer_lines: Vec::new(),
            followup_queue: VecDeque::new(),
            history: Vec::new(),
            history_cursor: None,
            status: StatusInfo::default(),
            spinner_frame: 0,
            spinner_verb_idx: 0,
            current_tool: None,
            active_tools: Vec::new(),
            tasks: Vec::new(),
            subagents: Vec::new(),
            picker: None,
            palette: None,
            approval: None,
            ask_user: None,
            modal_queue: VecDeque::new(),
            error_banner: None,
            plan_mode: false,
            altscreen,
            scroll_offset: 0,
            terminal_size,
            pending_requests: HashMap::new(),
            stale_request_ids: Vec::new(),
            next_request_id: 1,
            session_list: None,
            last_ctrl_c_at: None,
            ctrl_c_count: 0,
            task_panel_open: false,
            followup_panel_open: false,
        }
    }
}
