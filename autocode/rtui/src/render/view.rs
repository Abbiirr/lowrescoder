use ratatui::{
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Paragraph, Wrap},
    Frame,
};

use crate::state::model::{AppState, Stage};
use crate::ui::spinner::{FRAMES, VERBS};
use crate::ui::textbuf::truncate_chars;

const MIN_TERMINAL_COLS: u16 = 40;
const MIN_TERMINAL_ROWS: u16 = 6;

pub fn render(f: &mut Frame, state: &AppState) {
    if state.terminal_size.0 < MIN_TERMINAL_COLS || state.terminal_size.1 < MIN_TERMINAL_ROWS {
        let message = format!(
            "Terminal too small ({}x{}, needs {}x{})",
            state.terminal_size.0, state.terminal_size.1, MIN_TERMINAL_COLS, MIN_TERMINAL_ROWS
        );
        let paragraph = Paragraph::new(message).wrap(Wrap { trim: false });
        f.render_widget(paragraph, f.area());
        return;
    }

    let size = f.area();
    let chunks = Layout::vertical([
        Constraint::Length(1), // status bar
        Constraint::Min(1),    // scrollback + streaming
        Constraint::Length(2), // composer
    ])
    .split(size);

    render_status_bar(f, state, chunks[0]);
    render_content(f, state, chunks[1]);
    render_composer(f, state, chunks[2]);
}

fn render_status_bar(f: &mut Frame, state: &AppState, area: Rect) {
    let mut spans = vec![
        Span::styled(&state.status.model, Style::default().fg(Color::Cyan)),
        Span::raw(" | "),
        Span::styled(&state.status.provider, Style::default().fg(Color::Magenta)),
        Span::raw(" | "),
        Span::styled(&state.status.mode, Style::default().fg(Color::Green)),
    ];

    if let Some(sid) = &state.status.session_id {
        let short = truncate_chars(sid, 8);
        spans.push(Span::raw(" | "));
        spans.push(Span::styled(short, Style::default().fg(Color::Yellow)));
    }

    if state.status.tokens_in > 0 || state.status.tokens_out > 0 {
        spans.push(Span::raw(" | "));
        let token_text = format!("{}↑{}↓", state.status.tokens_in, state.status.tokens_out);
        spans.push(Span::raw(token_text));
    }

    if let Some(cost) = &state.status.cost {
        spans.push(Span::raw(" | "));
        spans.push(Span::styled(cost, Style::default().fg(Color::Yellow)));
    }

    if state.status.bg_tasks > 0 {
        spans.push(Span::raw(" | "));
        let bg_text = format!("⏳ {} bg", state.status.bg_tasks);
        spans.push(Span::raw(bg_text));
    }

    if !state.followup_queue.is_empty() {
        spans.push(Span::raw(" | "));
        spans.push(Span::raw(format!("Queued: {}", state.followup_queue.len())));
    }

    if state.plan_mode {
        spans.push(Span::raw(" | "));
        spans.push(Span::styled(
            "[PLAN]",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        ));
    }

    if state.stage == Stage::Streaming {
        let verb = VERBS[state.spinner_verb_idx % VERBS.len()];
        let frame = FRAMES[state.spinner_frame as usize % FRAMES.len()];
        spans.push(Span::raw(" | "));
        spans.push(Span::styled(
            format!("{} {}", frame, verb),
            Style::default().fg(Color::Gray),
        ));
    }

    let status = Line::from(spans);
    let paragraph = Paragraph::new(status).style(Style::default().bg(Color::DarkGray));
    f.render_widget(paragraph, area);
}

fn render_content(f: &mut Frame, state: &AppState, area: Rect) {
    if let Some(approval) = &state.approval {
        render_approval(f, approval, area);
        return;
    }

    if let Some(ask_user) = &state.ask_user {
        render_ask_user(f, ask_user, area);
        return;
    }

    if let Some(palette) = &state.palette {
        render_palette(f, palette, area);
        return;
    }

    if let Some(picker) = &state.picker {
        render_picker(f, picker, area);
        return;
    }

    let mut panels = Vec::new();
    if state.task_panel_open {
        panels.push("tasks");
    }
    if !state.active_tools.is_empty() {
        panels.push("tools");
    }
    if state.followup_panel_open {
        panels.push("queue");
    }

    if panels.is_empty() {
        render_main_content(f, state, area);
        return;
    }

    let mut constraints = vec![Constraint::Min(1)];
    constraints.extend(panels.iter().map(|_| Constraint::Length(6)));
    let chunks = Layout::vertical(constraints).split(area);

    render_main_content(f, state, chunks[0]);

    let mut chunk_idx = 1;
    if state.task_panel_open {
        render_task_panel(f, state, chunks[chunk_idx]);
        chunk_idx += 1;
    }
    if !state.active_tools.is_empty() {
        render_tool_panel(f, &state.active_tools, chunks[chunk_idx]);
        chunk_idx += 1;
    }
    if state.followup_panel_open {
        render_followup_panel(f, &state.followup_queue, chunks[chunk_idx]);
    }
}

fn render_main_content(f: &mut Frame, state: &AppState, area: Rect) {
    let mut lines: Vec<Line> = state
        .scrollback
        .iter()
        .map(|s| {
            let spans = crate::render::markdown::parse_inline(s);
            if s.starts_with("⚠") || s.starts_with("WARNING:") {
                let styled_spans: Vec<Span> = spans
                    .into_iter()
                    .map(|span| {
                        span.patch_style(
                            Style::default()
                                .fg(Color::Yellow)
                                .add_modifier(Modifier::DIM),
                        )
                    })
                    .collect();
                Line::from(styled_spans)
            } else {
                Line::from(spans)
            }
        })
        .collect();

    // Add streaming lines with dim style
    if !state.stream_lines.is_empty() {
        for line in &state.stream_lines {
            let spans = crate::render::markdown::parse_inline(line);
            let styled_spans: Vec<Span> = spans
                .into_iter()
                .map(|s| {
                    s.patch_style(Style::default().fg(Color::Gray).add_modifier(Modifier::DIM))
                })
                .collect();
            lines.push(Line::from(styled_spans));
        }
    }

    // Show error banner if present
    if let Some(err) = &state.error_banner {
        lines.push(Line::from(Span::styled(
            format!("Error: {}", err),
            Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
        )));
    }

    // Show tool call info if present
    if let Some(tool) = &state.current_tool {
        lines.push(Line::from(Span::styled(
            format!("🔧 {} ({})", tool.name, tool.status),
            Style::default().fg(Color::Yellow),
        )));
    }

    let max_scroll = lines.len().saturating_sub(area.height as usize) as u16;
    let scroll = max_scroll.saturating_sub(state.scroll_offset.min(max_scroll));
    let paragraph = Paragraph::new(lines)
        .wrap(Wrap { trim: false })
        .scroll((scroll, 0));
    f.render_widget(paragraph, area);
}

fn render_task_panel(f: &mut Frame, state: &AppState, area: Rect) {
    let mut lines = vec![Line::from(Span::styled(
        "Tasks",
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    ))];

    if state.tasks.is_empty() && state.subagents.is_empty() {
        lines.push(Line::from("No background work"));
    } else {
        for task in &state.tasks {
            lines.push(Line::from(format!(
                "{} {}",
                status_icon(&task.status),
                task.title
            )));
        }
        for subagent in &state.subagents {
            lines.push(Line::from(format!(
                "↳ {} {} ({})",
                status_icon(&subagent.status),
                subagent.role,
                subagent.status
            )));
        }
    }

    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn render_tool_panel(f: &mut Frame, tools: &[crate::state::model::ToolCallInfo], area: Rect) {
    let mut lines = vec![Line::from(Span::styled(
        "Tools",
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    ))];

    for tool in tools.iter().rev().take(2) {
        lines.push(Line::from(format!("{} [{}]", tool.name, tool.status)));
        if let Some(args) = &tool.args {
            lines.push(Line::from(format!("args: {}", truncate_chars(args, 80))));
        }
        if let Some(result) = &tool.result {
            lines.push(Line::from(format!(
                "result: {}",
                truncate_chars(result, 80)
            )));
        }
    }

    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn render_followup_panel(f: &mut Frame, queue: &std::collections::VecDeque<String>, area: Rect) {
    let mut lines = vec![Line::from(Span::styled(
        "Followups",
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    ))];

    if queue.is_empty() {
        lines.push(Line::from("No queued followups"));
    } else {
        for entry in queue.iter().take(4) {
            lines.push(Line::from(format!("• {}", truncate_chars(entry, 80))));
        }
    }

    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn status_icon(status: &str) -> &'static str {
    match status {
        "done" | "completed" | "success" => "✓",
        "running" | "active" | "in_progress" => "⏳",
        "failed" | "error" => "✗",
        _ => "•",
    }
}

fn render_palette(f: &mut Frame, palette: &crate::state::model::PaletteState, area: Rect) {
    let filter = palette.filter.as_str();
    let lower = filter.to_lowercase();
    let title = match palette.mode {
        crate::state::model::PaletteMode::CommandPalette => "Command Palette",
        crate::state::model::PaletteMode::SlashAutocomplete => "Slash Commands",
    };
    let mut lines = vec![
        Line::from(Span::styled(
            title,
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(format!("[filter: {}]", filter)),
    ];

    let visible: Vec<&crate::state::model::PaletteEntry> = palette
        .entries
        .iter()
        .filter(|entry| {
            lower.is_empty()
                || entry.name.to_lowercase().contains(&lower)
                || entry.description.to_lowercase().contains(&lower)
        })
        .collect();

    if visible.is_empty() {
        lines.push(Line::from("Loading commands..."));
    } else {
        for (idx, entry) in visible.iter().enumerate() {
            let prefix = if idx == palette.cursor { "▶ " } else { "  " };
            lines.push(Line::from(format!(
                "{}{} — {}",
                prefix, entry.name, entry.description
            )));
        }
    }

    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn render_approval(f: &mut Frame, approval: &crate::state::model::ApprovalRequest, area: Rect) {
    let lines = vec![
        Line::from(Span::styled(
            "Approval",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(format!("Tool: {}", approval.tool)),
        Line::from(format!("Args: {}", approval.args)),
        Line::from("[Y] Approve  [N] Deny  [A] Approve for session"),
    ];
    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn render_ask_user(f: &mut Frame, ask_user: &crate::state::model::AskUserRequest, area: Rect) {
    let mut lines = vec![Line::from(Span::styled(
        &ask_user.question,
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    ))];

    for (idx, option) in ask_user.options.iter().enumerate() {
        let prefix = if idx == ask_user.selected {
            "❯ "
        } else {
            "○ "
        };
        lines.push(Line::from(format!("{}{}", prefix, option)));
    }

    if ask_user.allow_text {
        lines.push(Line::from(format!(
            "[text: {}]",
            ask_user.free_text.as_str()
        )));
    }

    lines.push(Line::from("Enter to submit, Esc to cancel"));

    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn render_picker(f: &mut Frame, picker: &crate::state::model::PickerState, area: Rect) {
    let title = match picker.kind {
        crate::state::model::PickerKind::Model => "Select a model:",
        crate::state::model::PickerKind::Provider => "Select a provider:",
        crate::state::model::PickerKind::Session => "Select a session:",
    };
    let filter = picker.filter.as_str();
    let lower = filter.to_lowercase();
    let mut lines = vec![
        Line::from(Span::styled(
            title,
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from(format!("[filter: {}]", filter)),
    ];

    let visible: Vec<&String> = picker
        .entries
        .iter()
        .filter(|entry| lower.is_empty() || entry.to_lowercase().contains(&lower))
        .collect();

    for (idx, entry) in visible.iter().enumerate() {
        let prefix = if idx == picker.cursor { "▶ " } else { "  " };
        lines.push(Line::from(format!("{}{}", prefix, entry)));
    }

    let paragraph = Paragraph::new(lines).wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn render_composer(f: &mut Frame, state: &AppState, area: Rect) {
    let prompt = match &state.stage {
        Stage::Idle => "> ",
        Stage::Streaming => "⏳ ",
        Stage::ToolCall => "🔧 ",
        Stage::Approval => "[Y/N/A] ",
        Stage::AskUser => "? ",
        Stage::Picker(_) => "Picker> ",
        Stage::Palette => "Palette> ",
        Stage::EditorLaunch => "Editor... ",
        Stage::Shutdown => "",
    };

    let text = &state.composer_text;

    // Build line with cursor highlighting
    let (before, after) = text.split_at_cursor();

    let mut spans = vec![Span::styled(
        prompt,
        Style::default()
            .fg(Color::Green)
            .add_modifier(Modifier::BOLD),
    )];
    if !before.is_empty() {
        spans.push(Span::raw(before));
    }
    if !after.is_empty() {
        spans.push(Span::styled(after, Style::default().fg(Color::Gray)));
    }
    if text.is_empty() || text.cursor() >= text.len_chars() {
        spans.push(Span::styled(" ", Style::default().bg(Color::Gray)));
    }

    let composer = Paragraph::new(Line::from(spans));
    f.render_widget(composer, area);
}

#[cfg(test)]
mod tests {
    use ratatui::{backend::TestBackend, Terminal};

    use super::render;
    use crate::state::model::{
        AppState, AskUserSource, InboundId, PaletteEntry, PaletteMode, PaletteState, PickerKind,
        PickerState,
    };
    use crate::ui::textbuf::TextBuf;

    #[test]
    fn tiny_terminal_renders_placeholder() {
        let backend = TestBackend::new(20, 4);
        let mut terminal = Terminal::new(backend).unwrap();
        let state = AppState::new((20, 4), false);

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let buffer = terminal.backend().buffer().clone();
        let rendered = buffer
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Terminal too small"));
    }

    #[test]
    fn palette_renders_filter_and_entries() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.stage = crate::state::model::Stage::Palette;
        let mut filter = TextBuf::default();
        filter.set_text("mo");
        state.palette = Some(PaletteState {
            mode: PaletteMode::CommandPalette,
            filter,
            cursor: 0,
            entries: vec![
                PaletteEntry {
                    name: "/model".into(),
                    description: "Change model".into(),
                },
                PaletteEntry {
                    name: "/help".into(),
                    description: "Show help".into(),
                },
            ],
        });

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("[filter: mo]"));
        assert!(rendered.contains("/model"));
        assert!(rendered.contains("Change model"));
    }

    #[test]
    fn slash_overlay_renders_title_and_filter() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.stage = crate::state::model::Stage::Palette;
        let mut filter = TextBuf::default();
        filter.set_text("mo");
        state.palette = Some(PaletteState {
            mode: PaletteMode::SlashAutocomplete,
            filter,
            cursor: 0,
            entries: vec![PaletteEntry {
                name: "/model".into(),
                description: "Change model".into(),
            }],
        });

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Slash Commands"));
        assert!(rendered.contains("[filter: mo]"));
        assert!(rendered.contains("/model"));
    }

    #[test]
    fn picker_renders_header_filter_and_cursor() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.stage = crate::state::model::Stage::Picker(PickerKind::Model);
        let mut filter = TextBuf::default();
        filter.set_text("co");
        state.picker = Some(PickerState {
            kind: PickerKind::Model,
            entries: vec!["tools".into(), "coding".into(), "fast".into()],
            filter,
            cursor: 0,
        });

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Select a model:"));
        assert!(rendered.contains("[filter: co]"));
        assert!(rendered.contains("▶ coding"));
    }

    #[test]
    fn status_bar_shows_followup_queue_count() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.followup_queue.push_back("queued one".into());
        state.followup_queue.push_back("queued two".into());

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Queued: 2"));
    }

    #[test]
    fn task_panel_renders_tasks_and_subagents_when_open() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.task_panel_open = true;
        state.tasks = vec![crate::rpc::protocol::TaskEntry {
            id: "t1".into(),
            title: "Build release".into(),
            status: "running".into(),
        }];
        state.subagents = vec![crate::rpc::protocol::SubagentEntry {
            id: "s1".into(),
            role: "coder".into(),
            status: "running".into(),
        }];

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Tasks"));
        assert!(rendered.contains("Build release"));
        assert!(rendered.contains("coder"));
    }

    #[test]
    fn tool_panel_renders_args_and_result() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.active_tools = vec![crate::state::model::ToolCallInfo {
            name: "write_file".into(),
            status: "completed".into(),
            args: Some("{\"path\":\"demo.txt\"}".into()),
            result: Some("ok".into()),
        }];

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Tools"));
        assert!(rendered.contains("write_file"));
        assert!(rendered.contains("args:"));
        assert!(rendered.contains("result: ok"));
    }

    #[test]
    fn followup_panel_renders_entries_when_open() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.followup_panel_open = true;
        state.followup_queue.push_back("queued one".into());
        state.followup_queue.push_back("queued two".into());

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Followups"));
        assert!(rendered.contains("queued one"));
        assert!(rendered.contains("queued two"));
    }

    #[test]
    fn approval_modal_renders_tool_and_hints() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.stage = crate::state::model::Stage::Approval;
        state.approval = Some(crate::state::model::ApprovalRequest {
            rpc_id: InboundId::new(9),
            tool: "bash".into(),
            args: "ls -la".into(),
        });

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Approval"));
        assert!(rendered.contains("bash"));
        assert!(rendered.contains("[Y]"));
        assert!(rendered.contains("[N]"));
    }

    #[test]
    fn ask_user_modal_renders_question_and_options() {
        let backend = TestBackend::new(80, 24);
        let mut terminal = Terminal::new(backend).unwrap();
        let mut state = AppState::new((80, 24), false);
        state.stage = crate::state::model::Stage::AskUser;
        state.ask_user = Some(crate::state::model::AskUserRequest {
            source: AskUserSource::Inbound(InboundId::new(7)),
            question: "Continue?".into(),
            options: vec!["Yes".into(), "No".into()],
            allow_text: false,
            selected: 0,
            free_text: TextBuf::default(),
        });

        terminal.draw(|frame| render(frame, &state)).unwrap();

        let rendered = terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>();
        assert!(rendered.contains("Continue?"));
        assert!(rendered.contains("❯ Yes"));
        assert!(rendered.contains("No"));
        assert!(rendered.contains("Enter to submit"));
    }
}
