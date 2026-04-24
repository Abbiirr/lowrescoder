use ratatui::{
    layout::{Alignment, Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Clear, Paragraph, Wrap},
    Frame,
};

use crate::state::model::{AppState, DetailSurface, PaletteMode, Stage};
use crate::ui::spinner::FRAMES;
use crate::ui::textbuf::truncate_chars;

const MIN_TERMINAL_COLS: u16 = 40;
const MIN_TERMINAL_ROWS: u16 = 6;
const APP_BG: Color = Color::Rgb(8, 12, 18);
const PANEL_BG: Color = Color::Rgb(15, 20, 31);
const BORDER: Color = Color::Rgb(60, 70, 92);
const TITLE: Color = Color::Rgb(231, 236, 246);
const MUTED: Color = Color::Rgb(138, 149, 173);
const ACCENT: Color = Color::Rgb(122, 199, 255);
const QUIET: Color = Color::Rgb(112, 122, 145);
const PLANNING: Color = Color::Rgb(182, 145, 255);
const SUCCESS: Color = Color::Rgb(174, 223, 118);
const DIFF_ADD_BG: Color = Color::Rgb(25, 54, 34);
const DIFF_REM_BG: Color = Color::Rgb(59, 27, 31);
const LIVE_BG: Color = Color::Rgb(19, 25, 37);

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

    let size = shell_area(f.area());
    let shell = shell_block();
    f.render_widget(shell, size);
    let size = inner_rect(size, 1, 1);
    let chunks = Layout::vertical([
        Constraint::Length(1), // status bar
        Constraint::Min(1),    // scrollback + streaming
        Constraint::Length(3), // composer
        Constraint::Length(2), // footer
    ])
    .split(size);

    render_status_bar(f, state, chunks[0]);
    render_content(f, state, chunks[1]);
    render_composer(f, state, chunks[2]);
    render_footer(f, state, chunks[3]);
}

fn render_status_bar(f: &mut Frame, state: &AppState, area: Rect) {
    let compact = area.width < 80;
    let mut spans = Vec::new();
    push_status_chunk(
        &mut spans,
        state.status.model.trim(),
        Style::default().fg(Color::Cyan),
    );
    push_status_chunk(
        &mut spans,
        state.status.provider.trim(),
        Style::default().fg(Color::Magenta),
    );
    push_status_chunk(
        &mut spans,
        state.status.mode.trim(),
        Style::default().fg(Color::Green),
    );
    push_status_chunk(
        &mut spans,
        stage_badge(state),
        Style::default()
            .fg(stage_badge_color(state))
            .add_modifier(Modifier::BOLD),
    );

    if let Some(sid) = &state.status.session_id {
        if compact && area.width < 72 {
            // Preserve the core renderer-owned status chunks before the session ID
            // when the terminal is genuinely narrow.
        } else {
            let short = truncate_chars(sid, if compact { 8 } else { 10 });
            push_status_chunk(&mut spans, short, Style::default().fg(Color::Yellow));
        }
    }

    if !compact && (state.status.tokens_in > 0 || state.status.tokens_out > 0) {
        let token_text = format!("{}↑{}↓", state.status.tokens_in, state.status.tokens_out);
        push_status_chunk(&mut spans, token_text, Style::default());
    }

    if !compact {
        if let Some(cost) = &state.status.cost {
            push_status_chunk(&mut spans, cost, Style::default().fg(Color::Yellow));
        }
    }

    push_status_chunk(
        &mut spans,
        if compact {
            format!("t:{}", task_count(state))
        } else {
            format!("tasks:{}", task_count(state))
        },
        Style::default(),
    );
    push_status_chunk(
        &mut spans,
        if compact {
            format!("a:{}", state.subagents.len())
        } else {
            format!("agents:{}", state.subagents.len())
        },
        Style::default(),
    );
    push_status_chunk(
        &mut spans,
        format!("q:{}", state.followup_queue.len()),
        Style::default(),
    );
    if !compact {
        push_status_chunk(&mut spans, "sandbox:local", Style::default());
    }

    if state.plan_mode {
        push_status_chunk(
            &mut spans,
            "[PLAN]",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        );
    }

    let status = Line::from(spans);
    let paragraph = Paragraph::new(status).style(Style::default().bg(PANEL_BG).fg(MUTED));
    f.render_widget(paragraph, area);
}

fn push_status_chunk<T: Into<String>>(spans: &mut Vec<Span<'static>>, value: T, style: Style) {
    let value = value.into();
    if value.trim().is_empty() {
        return;
    }
    if !spans.is_empty() {
        spans.push(Span::raw(" | "));
    }
    spans.push(Span::styled(value, style));
}

fn render_content(f: &mut Frame, state: &AppState, area: Rect) {
    render_base_content(f, state, area);

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
    }
}

fn render_base_content(f: &mut Frame, state: &AppState, area: Rect) {
    if let Some(surface) = &state.detail_surface {
        render_detail_surface(f, surface, area);
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
    if state.error_banner.is_some() {
        render_recovery_surface(f, state, area);
        return;
    }

    let has_conversation = state
        .scrollback
        .iter()
        .any(|line| !is_warning_line(line) && !line.trim().is_empty());
    if state.stage == Stage::Idle
        && !has_conversation
        && state.stream_lines.is_empty()
        && state.current_tool.is_none()
    {
        render_ready_surface(f, state, area);
        return;
    }

    if matches!(state.stage, Stage::Streaming | Stage::ToolCall)
        || !state.stream_lines.is_empty()
        || state.current_tool.is_some()
    {
        render_active_surface(f, state, area);
        return;
    }

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

    // Show tool call info if present
    if let Some(tool) = &state.current_tool {
        lines.push(Line::from(Span::styled(
            format!("🔧 {} ({})", tool.name, tool.status),
            Style::default().fg(Color::Yellow),
        )));
    }

    if lines.is_empty() {
        lines.push(Line::from(Span::styled(
            "Ready for the next task.",
            Style::default()
                .fg(Color::Green)
                .add_modifier(Modifier::BOLD),
        )));
        lines.push(Line::from(
            "Open the palette with / or Ctrl+Shift+P, then send the next step when ready.",
        ));
    }

    let max_scroll = lines.len().saturating_sub(area.height as usize) as u16;
    let scroll = max_scroll.saturating_sub(state.scroll_offset.min(max_scroll));
    let paragraph = Paragraph::new(lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false })
        .scroll((scroll, 0));
    f.render_widget(paragraph, area);
}

fn render_ready_surface(f: &mut Frame, state: &AppState, area: Rect) {
    let warnings = collect_warning_lines(state);
    let content_area = if warnings.is_empty() {
        area
    } else {
        let warning_height = warnings.len().min(2) as u16;
        let chunks =
            Layout::vertical([Constraint::Length(warning_height), Constraint::Min(1)]).split(area);
        let warning_lines = warnings
            .into_iter()
            .take(2)
            .map(|line| {
                Line::from(Span::styled(
                    line,
                    Style::default()
                        .fg(Color::Yellow)
                        .add_modifier(Modifier::DIM),
                ))
            })
            .collect::<Vec<_>>();
        let warning_paragraph = Paragraph::new(warning_lines)
            .style(Style::default().bg(APP_BG))
            .wrap(Wrap { trim: false });
        f.render_widget(warning_paragraph, chunks[0]);
        chunks[1]
    };

    let activity_height = if content_area.height >= 20 { 3 } else { 2 };
    let chunks = Layout::vertical([
        Constraint::Percentage(28),
        Constraint::Length(3),
        Constraint::Min(1),
        Constraint::Length(activity_height),
    ])
    .split(content_area);

    let quiet_prompt = Paragraph::new(vec![Line::from(Span::styled(
        "Describe a change, ask a question, or paste a stack trace",
        Style::default().fg(QUIET),
    ))])
    .style(Style::default().bg(APP_BG))
    .alignment(Alignment::Center)
    .wrap(Wrap { trim: false });
    f.render_widget(quiet_prompt, chunks[1]);

    let session_hint = state
        .status
        .session_id
        .as_deref()
        .map(|sid| truncate_chars(sid, 14))
        .unwrap_or("last session");
    let narrow_copy = content_area.width < 76;
    let mut activity_lines = vec![
        Line::from(vec![
            Span::styled("↻ Restore", Style::default().fg(TITLE)),
            Span::styled(
                if narrow_copy {
                    " · recent checkpoint · local"
                } else {
                    " · recent checkpoint · local only"
                },
                Style::default().fg(QUIET),
            ),
        ]),
        Line::from(vec![
            Span::styled("recent session", Style::default().fg(QUIET)),
            Span::styled(
                if narrow_copy {
                    format!(" · {} · resume/fork", session_hint)
                } else {
                    format!(" · {} · resume or fork", session_hint)
                },
                Style::default().fg(MUTED),
            ),
        ]),
    ];
    if activity_height >= 3 {
        activity_lines.push(Line::from(vec![
            Span::styled("last branch activity", Style::default().fg(QUIET)),
            Span::styled(
                if narrow_copy {
                    " · workspace preserved · ready"
                } else {
                    " · workspace preserved · ready for the next edit"
                },
                Style::default().fg(MUTED),
            ),
        ]));
    }
    let activity = Paragraph::new(activity_lines)
        .style(Style::default().bg(APP_BG))
        .alignment(Alignment::Center)
        .wrap(Wrap { trim: false });
    f.render_widget(activity, chunks[3]);
}

fn render_active_surface(f: &mut Frame, state: &AppState, area: Rect) {
    let warnings = collect_warning_lines(state);
    let content_area = if warnings.is_empty() {
        area
    } else {
        let warning_height = warnings.len().min(2) as u16;
        let chunks =
            Layout::vertical([Constraint::Length(warning_height), Constraint::Min(1)]).split(area);
        let warning_lines = warnings
            .into_iter()
            .take(2)
            .map(|line| {
                Line::from(Span::styled(
                    line,
                    Style::default()
                        .fg(Color::Yellow)
                        .add_modifier(Modifier::DIM),
                ))
            })
            .collect::<Vec<_>>();
        let warning_paragraph = Paragraph::new(warning_lines)
            .style(Style::default().bg(APP_BG))
            .wrap(Wrap { trim: false });
        f.render_widget(warning_paragraph, chunks[0]);
        chunks[1]
    };

    let latest_user = state
        .scrollback
        .iter()
        .rev()
        .find(|line| !is_warning_line(line) && line.trim_start().starts_with('>'))
        .cloned()
        .unwrap_or_else(|| "> working on the current task".into());

    let mut transcript = if !state.stream_lines.is_empty() {
        state.stream_lines.clone()
    } else {
        state
            .scrollback
            .iter()
            .filter(|line| !is_warning_line(line) && !line.trim_start().starts_with('>'))
            .cloned()
            .collect::<Vec<_>>()
    };
    if let Some(tool) = &state.current_tool {
        transcript.push(format!("{} [{}]", tool.name, tool.status));
    }

    if transcript.is_empty() {
        let paragraph = Paragraph::new(vec![Line::from(latest_user)])
            .style(Style::default().bg(APP_BG).fg(TITLE))
            .wrap(Wrap { trim: false });
        f.render_widget(paragraph, content_area);
        return;
    }

    let live_capacity = if content_area.height >= 20 { 4 } else { 3 };
    let body_len = if transcript.len() > live_capacity {
        transcript.len() - live_capacity
    } else {
        transcript.len()
    };
    let mut body_lines = transcript[..body_len]
        .iter()
        .map(|line| stylize_active_line(line))
        .collect::<Vec<_>>();
    if body_lines.is_empty() {
        body_lines.push(Line::from(Span::styled(
            "Planning and validation updates will stream here.",
            Style::default().fg(QUIET),
        )));
    }
    body_lines.push(Line::from(""));
    body_lines.push(Line::from(Span::styled(
        "draft stays live while validation streams",
        Style::default().fg(QUIET),
    )));

    let prompt_height = if content_area.height >= 16 { 2 } else { 1 };
    let live_height = if transcript.len() > live_capacity {
        if content_area.height >= 22 {
            7
        } else {
            5
        }
    } else {
        0
    };

    let chunks = if live_height > 0 {
        Layout::vertical([
            Constraint::Length(prompt_height),
            Constraint::Min(1),
            Constraint::Length(live_height),
        ])
        .split(content_area)
    } else {
        Layout::vertical([Constraint::Length(prompt_height), Constraint::Min(1)])
            .split(content_area)
    };

    let prompt = Paragraph::new(vec![Line::from(Span::styled(
        latest_user,
        Style::default().fg(TITLE).add_modifier(Modifier::BOLD),
    ))])
    .style(Style::default().bg(APP_BG))
    .wrap(Wrap { trim: false });
    f.render_widget(prompt, chunks[0]);

    let body = Paragraph::new(body_lines)
        .style(Style::default().bg(APP_BG))
        .wrap(Wrap { trim: false });
    f.render_widget(body, chunks[1]);

    if live_height > 0 {
        let mut live_lines = transcript[body_len..]
            .iter()
            .map(|line| stylize_active_live_line(line))
            .collect::<Vec<_>>();
        if live_lines.is_empty() {
            live_lines.push(Line::from(Span::styled(
                "validation still running",
                Style::default().fg(ACCENT),
            )));
        }

        let live = Paragraph::new(live_lines)
            .block(
                Block::default()
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(BORDER))
                    .style(Style::default().bg(LIVE_BG)),
            )
            .style(Style::default().bg(LIVE_BG).fg(MUTED))
            .wrap(Wrap { trim: false });
        f.render_widget(live, chunks[2]);
    }
}

fn collect_warning_lines(state: &AppState) -> Vec<String> {
    state
        .scrollback
        .iter()
        .filter(|line| is_warning_line(line))
        .cloned()
        .collect()
}

fn is_warning_line(line: &str) -> bool {
    line.starts_with('⚠') || line.starts_with("WARNING:")
}

fn stylize_active_line(line: &str) -> Line<'static> {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return Line::from("");
    }

    if trimmed == "Planning" {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default().fg(PLANNING).add_modifier(Modifier::BOLD),
        ));
    }
    if trimmed.starts_with("Will ") || trimmed.starts_with("then ") {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default().fg(MUTED).add_modifier(Modifier::ITALIC),
        ));
    }
    if is_removed_diff_line(trimmed) {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default()
                .fg(Color::Rgb(255, 191, 191))
                .bg(DIFF_REM_BG),
        ));
    }
    if is_added_diff_line(trimmed) {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default()
                .fg(Color::Rgb(196, 239, 170))
                .bg(DIFF_ADD_BG),
        ));
    }
    if trimmed.starts_with("√ ") {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default().fg(SUCCESS),
        ));
    }
    if trimmed.starts_with("● ") {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        ));
    }
    if is_work_action_line(trimmed) {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default().fg(TITLE),
        ));
    }

    Line::from(Span::styled(
        trimmed.to_string(),
        Style::default().fg(MUTED),
    ))
}

fn stylize_active_live_line(line: &str) -> Line<'static> {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return Line::from("");
    }
    if trimmed.starts_with("√ ") {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default().fg(SUCCESS),
        ));
    }
    if trimmed.starts_with("● ")
        || trimmed.contains("running")
        || trimmed.contains("tests/parser.test.ts")
    {
        return Line::from(Span::styled(
            trimmed.to_string(),
            Style::default().fg(ACCENT),
        ));
    }
    Line::from(Span::styled(
        trimmed.to_string(),
        Style::default().fg(MUTED),
    ))
}

fn is_work_action_line(line: &str) -> bool {
    line.starts_with("Read(")
        || line.starts_with("Search ")
        || line.starts_with("Edit(")
        || line.starts_with("Run(")
}

fn is_removed_diff_line(line: &str) -> bool {
    line.split_once(" - ")
        .is_some_and(|(prefix, _)| prefix.chars().all(|ch| ch.is_ascii_digit()))
}

fn is_added_diff_line(line: &str) -> bool {
    line.split_once(" + ")
        .is_some_and(|(prefix, _)| prefix.chars().all(|ch| ch.is_ascii_digit()))
}

fn render_recovery_surface(f: &mut Frame, state: &AppState, area: Rect) {
    let err = state
        .error_banner
        .as_deref()
        .unwrap_or("Backend not responding");
    let (left, right) = split_detail_columns(area, 28);

    let mut left_lines = vec![Line::from(Span::styled(
        format!("Error: {}", err),
        Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
    ))];
    left_lines.push(Line::from(""));
    left_lines.push(Line::from(Span::styled(
        "LAST INPUT",
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    )));

    let recent_context: Vec<&String> = state.scrollback.iter().rev().take(4).collect();
    if recent_context.is_empty() {
        left_lines.push(Line::from("No completed scrollback yet."));
    } else {
        for line in recent_context.into_iter().rev() {
            left_lines.push(Line::from(line.clone()));
        }
    }

    if !state.stream_lines.is_empty() {
        left_lines.push(Line::from(""));
        left_lines.push(Line::from(Span::styled(
            "PARTIAL OUTPUT",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )));
        for line in state
            .stream_lines
            .iter()
            .rev()
            .take(2)
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
        {
            left_lines.push(Line::from(Span::styled(
                line.clone(),
                Style::default().fg(Color::Gray).add_modifier(Modifier::DIM),
            )));
        }
    }

    left_lines.push(Line::from(""));
    left_lines.push(Line::from(Span::styled(
        "STATUS",
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    )));
    left_lines.push(Line::from(format!(
        "tasks {} · agents {} · queue {}",
        task_count(state),
        state.subagents.len(),
        state.followup_queue.len()
    )));
    left_lines.push(Line::from("Draft preserved below · backend halted"));

    let mut right_lines = vec![Line::from(Span::styled(
        "RECOVERY",
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    ))];
    for idx in 0..RECOVERY_ACTIONS.len() {
        right_lines.push(recovery_action_line(state.recovery_action_idx, idx));
    }
    right_lines.push(Line::from(""));
    right_lines.push(Line::from(Span::styled(
        "DETAIL",
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD),
    )));
    right_lines.extend(recovery_action_detail_lines(state.recovery_action_idx));
    right_lines.push(Line::from(""));
    right_lines.push(Line::from("Enter run selected"));
    right_lines.push(Line::from("Esc stay halted"));

    let left_paragraph = Paragraph::new(left_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(left_paragraph, left);

    let right_paragraph = Paragraph::new(right_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(right_paragraph, right);
}

const RECOVERY_ACTIONS: [&str; 6] = [
    "Retry", "Inspect", "Restore", "Rewind", "Compact", "Planning",
];

fn recovery_action_line(selected_idx: usize, idx: usize) -> Line<'static> {
    let marker = if idx == selected_idx { "●" } else { "○" };
    let style = if idx == selected_idx {
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD)
    } else {
        Style::default().fg(MUTED)
    };
    Line::from(Span::styled(
        format!("{marker} {}", RECOVERY_ACTIONS[idx]),
        style,
    ))
}

fn recovery_action_detail_lines(selected_idx: usize) -> Vec<Line<'static>> {
    match selected_idx {
        0 => vec![
            Line::from("Resubmit the draft"),
            Line::from("or last input."),
        ],
        1 => vec![
            Line::from("Inspect tools, queue,"),
            Line::from("and subagent state."),
        ],
        2 => vec![
            Line::from("Open restore browser"),
            Line::from("for checkpoint diff."),
        ],
        3 => vec![
            Line::from("Jump backward to"),
            Line::from("an earlier checkpoint."),
        ],
        4 => vec![
            Line::from("Compact context"),
            Line::from("before retrying."),
        ],
        _ => vec![
            Line::from("Open the plan view"),
            Line::from("before resuming."),
        ],
    }
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

    let paragraph = Paragraph::new(lines)
        .block(pane_block(Some("Tasks")))
        .wrap(Wrap { trim: false });
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

    let paragraph = Paragraph::new(lines)
        .block(pane_block(Some("Tools")))
        .wrap(Wrap { trim: false });
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

    let paragraph = Paragraph::new(lines)
        .block(pane_block(Some("Queue")))
        .wrap(Wrap { trim: false });
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
    let mut body = vec![format!("[filter: {}]", filter)];

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
        body.push("Loading commands...".to_string());
    } else {
        for (idx, entry) in visible.iter().enumerate() {
            let prefix = if idx == palette.cursor { "▶ " } else { "  " };
            body.push(format!("{}{} — {}", prefix, entry.name, entry.description));
        }
    }

    let lines = body
        .iter()
        .map(|line| Line::from(line.clone()))
        .collect::<Vec<_>>();
    let content_width = body
        .iter()
        .map(|line| line.chars().count() as u16)
        .max()
        .unwrap_or(20);
    let width = compact_overlay_width(area, content_width, 44, 66);
    let height = compact_overlay_height(area, body.len() as u16, 9, 15);
    let overlay = floating_overlay_rect(area, width, height);
    f.render_widget(Clear, overlay);
    let paragraph = Paragraph::new(lines)
        .block(overlay_block(title))
        .wrap(Wrap { trim: false });
    f.render_widget(paragraph, overlay);
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
    let overlay = centered_rect(area, area.width.saturating_sub(10).clamp(40, 82), 9);
    f.render_widget(Clear, overlay);
    let paragraph = Paragraph::new(lines)
        .block(overlay_block("Approval"))
        .wrap(Wrap { trim: false });
    f.render_widget(paragraph, overlay);
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

    let overlay = centered_rect(area, area.width.saturating_sub(10).clamp(40, 82), 10);
    f.render_widget(Clear, overlay);
    let paragraph = Paragraph::new(lines)
        .block(overlay_block("Ask User"))
        .wrap(Wrap { trim: false });
    f.render_widget(paragraph, overlay);
}

fn render_picker(f: &mut Frame, picker: &crate::state::model::PickerState, area: Rect) {
    let title = match picker.kind {
        crate::state::model::PickerKind::Model => "Select a model:",
        crate::state::model::PickerKind::Provider => "Select a provider:",
        crate::state::model::PickerKind::Session => "Select a session:",
    };
    let filter = picker.filter.as_str();
    let lower = filter.to_lowercase();
    let mut body = vec![title.to_string(), format!("[filter: {}]", filter)];

    let visible: Vec<&String> = picker
        .entries
        .iter()
        .filter(|entry| lower.is_empty() || entry.to_lowercase().contains(&lower))
        .collect();

    for (idx, entry) in visible.iter().enumerate() {
        let prefix = if idx == picker.cursor { "▶ " } else { "  " };
        body.push(format!("{}{}", prefix, entry));
    }

    let lines = body
        .iter()
        .map(|line| Line::from(line.clone()))
        .collect::<Vec<_>>();
    let content_width = body
        .iter()
        .map(|line| line.chars().count() as u16)
        .max()
        .unwrap_or(20);
    let width = compact_overlay_width(area, content_width, 44, 66);
    let height = compact_overlay_height(area, body.len() as u16, 9, 13);
    let overlay = floating_overlay_rect(area, width, height);
    f.render_widget(Clear, overlay);
    let paragraph = Paragraph::new(lines)
        .block(overlay_block("Picker"))
        .wrap(Wrap { trim: false });
    f.render_widget(paragraph, overlay);
}

fn render_detail_surface(f: &mut Frame, surface: &DetailSurface, area: Rect) {
    if matches!(surface, DetailSurface::Review) {
        render_review_surface(f, area);
        return;
    }
    if matches!(surface, DetailSurface::Diff) {
        render_diff_surface(f, area);
        return;
    }
    if matches!(surface, DetailSurface::Grep) {
        render_grep_surface(f, area);
        return;
    }
    if matches!(surface, DetailSurface::Escalation) {
        render_escalation_surface(f, area);
        return;
    }
    if matches!(surface, DetailSurface::CommandCenter) {
        render_command_center_surface(f, area);
        return;
    }

    let lines: Vec<Line> = match surface {
        DetailSurface::Multi => vec![
            Line::from("● 2 jobs running"),
            Line::from("Edit ( src/utils/parser.ts )"),
            Line::from("Note: discovered a potential circular import recursion issue. Adding a visited-set guard."),
            Line::from("Edit ( src/utils/resolver.ts )"),
            Line::from("Run ( bun test --watch ./tests/parser.test.ts )"),
            Line::from("√ 14 passing"),
            Line::from("● resolving deeply nested imports… (5s)"),
            Line::from(""),
            Line::from("[prioritized] update the ImportNode type definitions after the parser guard lands"),
            Line::from("[blocked: tests] run the full suite once watch mode stabilizes"),
            Line::from("[next] inspect docs/parser.md for import behavior notes"),
        ],
        DetailSurface::Plan => vec![
            Line::from(Span::styled(
                "Planning",
                Style::default().fg(Color::Yellow).add_modifier(Modifier::BOLD),
            )),
            Line::from("Seven steps queued. Step 4 is active; step 5 is blocked on the watch-mode shard finishing."),
            Line::from("Remaining steps will run after review."),
            Line::from(""),
            Line::from("√ Inspect parser flow & call sites"),
            Line::from("√ Extend ASTNode with optional imports"),
            Line::from("√ Patch extractImports guard"),
            Line::from("● Run targeted parser tests"),
            Line::from("◐ Run full matrix suite"),
            Line::from("○ Update docs/parser.md"),
            Line::from("○ Write changelog entry after review"),
            Line::from("○ Review & approve"),
            Line::from(""),
            Line::from("VALIDATION"),
            Line::from("targeted tests passed · full suite not run"),
            Line::from("plan stays editable · Tab to open step 4 detail"),
        ],
        DetailSurface::Review => unreachable!("review handled by render_review_surface"),
        DetailSurface::CommandCenter => unreachable!("command center handled by render_command_center_surface"),
        DetailSurface::Restore => vec![
            Line::from("↻ 5 checkpoints · feat/parser-fix"),
            Line::from(""),
            Line::from("● step 3 · extractImports guard"),
            Line::from("14:08 · 2 files · parser.ts + types.ts · 42 tests passed after"),
            Line::from("↵ restore"),
            Line::from("○ step 2 · ImportNode.visited added"),
            Line::from("14:05 · 1 file · src/types.ts"),
            Line::from("○ step 1 · inspect parser flow"),
            Line::from("14:02 · read-only · no writes"),
            Line::from("○ session start · parser import patch"),
            Line::from("○ manual checkpoint · before resolver refactor"),
            Line::from(""),
            Line::from("↑↓ move · ↵ restore · D diff from here · Esc cancel"),
            Line::from("safe · local only · reversible"),
        ],
        DetailSurface::Diff => unreachable!("diff handled by render_diff_surface"),
        DetailSurface::Grep => unreachable!("grep handled by render_grep_surface"),
        DetailSurface::Escalation => {
            unreachable!("escalation handled by render_escalation_surface")
        }
    };

    let paragraph = Paragraph::new(lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn render_review_surface(f: &mut Frame, area: Rect) {
    let (left, right) = split_detail_columns(area, 24);

    let left_lines = vec![
        Line::from("All edits staged. Waiting for review."),
        Line::from(""),
        Line::from("src/utils/parser.ts (lines 38–54)"),
        Line::from("+2 −1 · 1 hunk"),
        Line::from("38 function extractImports(nodes: ImportNode[] | undefined) {"),
        Line::from("39 if (!nodes) return []"),
        Line::from("40 const seen = new Set ()"),
        Line::from("45 + const r = resolve(n)"),
        Line::from("46 + if (r) out.push(r)"),
        Line::from(""),
        Line::from("tests/parser.test.ts · +4 assertions · details"),
    ];
    let right_lines = vec![
        Line::from(Span::styled(
            "PLAN",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("√ Inspect parser flow"),
        Line::from("√ Update AST types"),
        Line::from("√ Patch imports"),
        Line::from("√ Targeted tests"),
        Line::from("● Review diff"),
        Line::from(""),
        Line::from(Span::styled(
            "VALIDATION",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("targeted tests"),
        Line::from("passed"),
        Line::from("full suite not run"),
        Line::from(""),
        Line::from(Span::styled(
            "REVIEW NEEDED",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("files 2"),
        Line::from("blast parser+tests"),
        Line::from("network off"),
        Line::from("reversible yes"),
        Line::from("protected no"),
        Line::from("severity high"),
        Line::from("[a]pprove"),
        Line::from("[r]eject"),
    ];

    let left_paragraph = Paragraph::new(left_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(left_paragraph, left);

    let right_paragraph = Paragraph::new(right_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(right_paragraph, right);
}

fn render_diff_surface(f: &mut Frame, area: Rect) {
    let (left, right) = split_detail_columns(area, 24);

    let left_lines = vec![
        Line::from("files changed · 3"),
        Line::from("src/utils/parser.ts +2 −1"),
        Line::from("src/utils/resolver.ts +6 −2"),
        Line::from("src/types.ts +1 −0"),
        Line::from(""),
        Line::from("src/utils/resolver.ts (lines 108–128)"),
        Line::from("+6 −2 · 1 hunk"),
        Line::from("114 + if (!n || seen.has(n)) return null"),
        Line::from("116 + const kind = n.kind ?? 'module'"),
        Line::from("117 + if (kind === 'dyn') return null"),
        Line::from("118 + const target = lookup(n.name)"),
    ];
    let right_lines = vec![
        Line::from(Span::styled(
            "RAW COMMAND",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("Edit(src/utils/"),
        Line::from("resolver.ts)"),
        Line::from("plan step 5"),
        Line::from(""),
        Line::from(Span::styled(
            "APPROVAL PATTERN",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("● This hunk"),
        Line::from("○ This file"),
        Line::from("○ Whole patch"),
        Line::from(""),
        Line::from(Span::styled(
            "RISK",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("parser only"),
        Line::from("network off"),
        Line::from("reversible yes"),
        Line::from("[a]pprove"),
        Line::from("[r]eject"),
    ];

    let left_paragraph = Paragraph::new(left_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(left_paragraph, left);

    let right_paragraph = Paragraph::new(right_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(right_paragraph, right);
}

fn render_grep_surface(f: &mut Frame, area: Rect) {
    let (left, right) = split_detail_columns(area, 26);

    let left_lines = vec![
        Line::from("Search \"extractImports|ASTNode\\.kind\" src · 14 hits across 5 files"),
        Line::from(""),
        Line::from("src/utils/parser.ts · 4 hits"),
        Line::from("12 import { extractImports , ASTNode } from '../types'"),
        Line::from("71 const nodes = ast.imports ? extractImports (ast.imports) : []"),
        Line::from(""),
        Line::from("src/utils/resolver.ts · 5 hits"),
        Line::from("116 const kind = n.kind ?? 'module'"),
        Line::from("117 if ( kind === 'dyn') return null"),
        Line::from(""),
        Line::from("src/types.ts · 3 hits"),
        Line::from("19 export function extractImports(nodes?: ImportNode[])"),
        Line::from("27 return nodes.filter(Boolean)"),
    ];
    let right_lines = vec![
        Line::from(Span::styled(
            "ATTACH",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("@src/types.ts"),
        Line::from("#extractImports"),
        Line::from("3 attached"),
        Line::from(""),
        Line::from(Span::styled(
            "QUERY",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("scope src"),
        Line::from("regex on"),
        Line::from("case smart"),
        Line::from(""),
        Line::from(Span::styled(
            "ACTIONS",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("↵ open hit"),
        Line::from("Tab attach"),
        Line::from("/ refine"),
        Line::from("Esc back"),
    ];

    let left_paragraph = Paragraph::new(left_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(left_paragraph, left);

    let right_paragraph = Paragraph::new(right_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(right_paragraph, right);
}

fn render_escalation_surface(f: &mut Frame, area: Rect) {
    let (left, right) = split_detail_columns(area, 26);

    let left_lines = vec![
        Line::from("⚑ Permission escalation · protected path touched"),
        Line::from("Auto-accept was on, but this edit would modify .github/workflows/ci.yml"),
        Line::from(
            "which is in .autocode/protect . Mode bumped to [review-needed] for this hunk only.",
        ),
        Line::from(""),
        Line::from("path .github/workflows/ci.yml matched rule .autocode/protect → \".github/**\""),
        Line::from("edit origin auto-planning · propagating bun version bump"),
        Line::from("blast radius CI for all branches · reversible yes · local only until push"),
        Line::from(""),
        Line::from("pending hunk: update bun cache key and install version to 1.2.0"),
        Line::from("paired diff available before approval"),
    ];
    let right_lines = vec![
        Line::from(Span::styled(
            "DECISION",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("● Approve this edit only"),
        Line::from("○ Approve for this session"),
        Line::from("○ Open diff in focus mode"),
        Line::from("○ Remove rule"),
        Line::from("○ Reject"),
        Line::from(""),
        Line::from(Span::styled(
            "RISK",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("ci global"),
        Line::from("network off"),
        Line::from("reversible yes"),
        Line::from("protected yes"),
        Line::from("[a]pprove"),
        Line::from("[r]eject"),
    ];

    let left_paragraph = Paragraph::new(left_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(left_paragraph, left);

    let right_paragraph = Paragraph::new(right_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(right_paragraph, right);
}

fn render_command_center_surface(f: &mut Frame, area: Rect) {
    let (left, right) = split_detail_columns(area, 26);

    let left_lines = vec![
        Line::from("Delegate →( doc-writer subagent )"),
        Line::from("Delegate →( lint-scout subagent )"),
        Line::from("Delegate →( test-runner subagent )"),
        Line::from("Planning"),
        Line::from("Main thread will handle import extraction while subagents clear lint/docs."),
        Line::from("Waiting on test-runner for matrix test completion."),
        Line::from("Search ( \"extractImports\" src )"),
        Line::from("Read ( src/utils/parser.ts )"),
        Line::from("Edit ( src/types.ts )"),
        Line::from("Run ( bun run typecheck )"),
        Line::from(""),
        Line::from("queue pressure moderate · 2 followups waiting"),
    ];
    let right_lines = vec![
        Line::from(Span::styled(
            "SUBAGENTS",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("doc-writer done"),
        Line::from("lint-scout active"),
        Line::from("test-runner waiting"),
        Line::from(""),
        Line::from(Span::styled(
            "RISK",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("writes local"),
        Line::from("protected no"),
        Line::from("network off"),
        Line::from("reversible yes"),
        Line::from(""),
        Line::from(Span::styled(
            "QUEUE",
            Style::default()
                .fg(Color::Yellow)
                .add_modifier(Modifier::BOLD),
        )),
        Line::from("matrix tests ● running"),
        Line::from("2 followups"),
    ];

    let left_paragraph = Paragraph::new(left_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(left_paragraph, left);

    let right_paragraph = Paragraph::new(right_lines)
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(right_paragraph, right);
}

fn render_composer(f: &mut Frame, state: &AppState, area: Rect) {
    let slash_palette_active = state
        .palette
        .as_ref()
        .is_some_and(|palette| palette.mode == PaletteMode::SlashAutocomplete);
    let prompt = match &state.stage {
        Stage::Idle => "❯ ",
        Stage::Streaming => "❯ ",
        Stage::ToolCall => "❯ ",
        Stage::Approval => "[Y/N/A] ",
        Stage::AskUser => "? ",
        Stage::Picker(_) => "Picker> ",
        Stage::Palette if slash_palette_active => "❯ ",
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

    let composer = Paragraph::new(vec![Line::from(spans)])
        .block(pane_block(None))
        .wrap(Wrap { trim: false });
    f.render_widget(composer, area);
}

fn render_footer(f: &mut Frame, state: &AppState, area: Rect) {
    let helper = if state.error_banner.is_some() {
        "Choose a recovery action or edit the draft before retrying."
    } else if let Some(surface) = &state.detail_surface {
        detail_surface_helper(surface)
    } else {
        "Type the next step or use / commands."
    };
    let footer = if state.error_banner.is_some() {
        "Enter retry · E inspect · R restore · W rewind · C compact · P planning · Esc stay halted"
    } else if let Some(surface) = &state.detail_surface {
        detail_surface_footer(surface)
    } else if area.width < 72 {
        "Ctrl+Enter send · Esc interrupt · Ctrl+Shift+P palette"
    } else if area.width < 96 {
        "Ctrl+Enter send · Esc interrupt · Ctrl+R history · Ctrl+Shift+P palette"
    } else {
        "Ctrl+Enter send · Esc interrupt · Ctrl+R history · Ctrl+Shift+P palette · / commands"
    };
    let paragraph = Paragraph::new(vec![Line::from(helper), Line::from(footer)])
        .style(Style::default().bg(APP_BG).fg(MUTED))
        .wrap(Wrap { trim: false });
    f.render_widget(paragraph, area);
}

fn shell_area(area: Rect) -> Rect {
    area
}

fn inner_rect(area: Rect, horizontal: u16, vertical: u16) -> Rect {
    Rect::new(
        area.x + horizontal,
        area.y + vertical,
        area.width.saturating_sub(horizontal * 2),
        area.height.saturating_sub(vertical * 2),
    )
}

fn centered_rect(area: Rect, width: u16, height: u16) -> Rect {
    let width = width.min(area.width.saturating_sub(2));
    let height = height.min(area.height.saturating_sub(2));
    Rect::new(
        area.x + area.width.saturating_sub(width) / 2,
        area.y + area.height.saturating_sub(height) / 2,
        width,
        height,
    )
}

fn floating_overlay_rect(area: Rect, width: u16, height: u16) -> Rect {
    let width = width.min(area.width.saturating_sub(2));
    let height = height.min(area.height.saturating_sub(2));
    let x = area.x + area.width.saturating_sub(width) / 2;
    let y = area.y + area.height.saturating_sub(height) / 3;
    Rect::new(x, y, width, height)
}

fn compact_overlay_width(area: Rect, content_width: u16, min_width: u16, max_width: u16) -> u16 {
    let target = content_width.saturating_add(4);
    target.clamp(min_width, max_width.min(area.width.saturating_sub(6)))
}

fn compact_overlay_height(area: Rect, content_lines: u16, min_height: u16, max_height: u16) -> u16 {
    content_lines
        .saturating_add(2)
        .clamp(min_height, max_height.min(area.height.saturating_sub(4)))
}

fn split_detail_columns(area: Rect, sidebar_width: u16) -> (Rect, Rect) {
    let sidebar_width = sidebar_width.min(area.width.saturating_sub(20));
    let gutter = 2.min(area.width.saturating_sub(sidebar_width));
    let left_width = area.width.saturating_sub(sidebar_width + gutter);
    let left = Rect::new(area.x, area.y, left_width, area.height);
    let right = Rect::new(
        area.x + left_width + gutter,
        area.y,
        sidebar_width,
        area.height,
    );
    (left, right)
}

fn shell_block() -> Block<'static> {
    Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(BORDER))
        .style(Style::default().bg(APP_BG))
}

fn pane_block(title: Option<&'static str>) -> Block<'static> {
    let block = Block::default()
        .borders(Borders::ALL)
        .border_style(Style::default().fg(BORDER))
        .style(Style::default().bg(PANEL_BG));

    if let Some(title) = title {
        block.title(Span::styled(
            format!(" {} ", title),
            Style::default().fg(TITLE).add_modifier(Modifier::BOLD),
        ))
    } else {
        block
    }
}

fn overlay_block(title: &'static str) -> Block<'static> {
    pane_block(Some(title)).border_style(Style::default().fg(ACCENT))
}

fn detail_surface_helper(surface: &DetailSurface) -> &'static str {
    match surface {
        DetailSurface::Multi => "Queue pressure is visible; keep the composer focused on the next highest-value action.",
        DetailSurface::Plan => "Plan persisted and stays editable while validation is still running.",
        DetailSurface::Review => "Evidence is staged for approval; accept or reject before resuming auto mode.",
        DetailSurface::CommandCenter => "Subagents are visible here; use the main thread to coordinate queue pressure and validation.",
        DetailSurface::Restore => "Checkpoint browser is open; pick a restore point or diff from here before changing course.",
        DetailSurface::Diff => "Diff focus stays scoped to the selected file and hunk until you back out.",
        DetailSurface::Grep => "Search results can be attached directly into the composer for the next prompt.",
        DetailSurface::Escalation => "Protected-path escalation pauses the agent before the write and preserves the composer.",
    }
}

fn task_count(state: &AppState) -> usize {
    usize::max(state.status.bg_tasks as usize, state.tasks.len())
}

fn stage_badge(state: &AppState) -> String {
    if let Some(surface) = &state.detail_surface {
        return match surface {
            DetailSurface::Multi => "● multi".to_string(),
            DetailSurface::Plan => "● planning".to_string(),
            DetailSurface::Review => "● review".to_string(),
            DetailSurface::CommandCenter => "● command".to_string(),
            DetailSurface::Restore => "● restore".to_string(),
            DetailSurface::Diff => "● diff".to_string(),
            DetailSurface::Grep => "● search".to_string(),
            DetailSurface::Escalation => "● escalated".to_string(),
        };
    }

    if state.error_banner.is_some() || state.stage == Stage::Shutdown {
        return "● halted".to_string();
    }

    match state.stage {
        Stage::Idle => "● ready".to_string(),
        Stage::Streaming => format!(
            "{} working",
            FRAMES[state.spinner_frame as usize % FRAMES.len()]
        ),
        Stage::ToolCall => "● running".to_string(),
        Stage::Approval => "● approval".to_string(),
        Stage::AskUser => "● waiting".to_string(),
        Stage::Picker(_) => "● picker".to_string(),
        Stage::Palette => "● palette".to_string(),
        Stage::EditorLaunch => "● editor".to_string(),
        Stage::Shutdown => "● halted".to_string(),
    }
}

fn stage_badge_color(state: &AppState) -> Color {
    if matches!(state.detail_surface, Some(DetailSurface::Escalation)) {
        Color::Red
    } else if state.detail_surface.is_some() {
        Color::Yellow
    } else if state.error_banner.is_some() || state.stage == Stage::Shutdown {
        Color::Red
    } else if state.stage == Stage::Streaming {
        Color::Yellow
    } else {
        Color::Green
    }
}

fn detail_surface_footer(surface: &DetailSurface) -> &'static str {
    match surface {
        DetailSurface::Multi => {
            "Ctrl+Enter send · Esc back · Ctrl+R history · Ctrl+Shift+P palette · Tab focus · / @ #"
        }
        DetailSurface::Plan => {
            "Ctrl+Enter send · Esc back · Ctrl+R history · Ctrl+Shift+P palette · Tab focus · / @ #"
        }
        DetailSurface::Review => {
            "[a]pprove · [r]eject · Esc back · Ctrl+Shift+P palette · / commands"
        }
        DetailSurface::CommandCenter => {
            "Ctrl+Enter send · Esc back · Ctrl+R history · Ctrl+Shift+P palette · Tab focus · / @ #"
        }
        DetailSurface::Restore => "↑↓ move · ↵ restore · D diff from here · Esc cancel",
        DetailSurface::Diff => {
            "↑↓ file · j/k hunk · a approve · r reject · D raw cmd · Esc back to transcript"
        }
        DetailSurface::Grep => {
            "↵ open hit · Tab attach to composer · Ctrl+] next file · / refine query · Esc back"
        }
        DetailSurface::Escalation => {
            "a approve-once · s approve-session · r reject · d focus diff · Esc stay paused"
        }
    }
}

#[cfg(test)]
mod tests {
    use ratatui::{backend::TestBackend, layout::Rect, Terminal};

    use super::render;
    use crate::state::model::{
        AppState, AskUserSource, DetailSurface, InboundId, PaletteEntry, PaletteMode, PaletteState,
        PickerKind, PickerState, Stage,
    };
    use crate::ui::textbuf::TextBuf;

    fn render_to_string(state: &AppState, cols: u16, rows: u16) -> String {
        let backend = TestBackend::new(cols, rows);
        let mut terminal = Terminal::new(backend).unwrap();
        terminal.draw(|frame| render(frame, state)).unwrap();
        terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|cell| cell.symbol())
            .collect::<String>()
    }

    fn render_lines(state: &AppState, cols: u16, rows: u16) -> Vec<String> {
        let backend = TestBackend::new(cols, rows);
        let mut terminal = Terminal::new(backend).unwrap();
        terminal.draw(|frame| render(frame, state)).unwrap();
        let buffer = terminal.backend().buffer().clone();
        (0..rows)
            .map(|row| {
                (0..cols)
                    .map(|col| buffer[(col, row)].symbol())
                    .collect::<String>()
            })
            .collect()
    }

    fn line_containing<'a>(lines: &'a [String], needle: &str) -> &'a String {
        lines
            .iter()
            .find(|line| line.contains(needle))
            .unwrap_or_else(|| panic!("missing line containing {needle:?}"))
    }

    fn boxed_line_width(line: &str) -> usize {
        let chars = line.chars().collect::<Vec<_>>();
        let start = chars
            .iter()
            .position(|ch| *ch == '┌')
            .expect("missing box start");
        let end = chars
            .iter()
            .rposition(|ch| *ch == '┐')
            .expect("missing box end");
        end - start + 1
    }

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
        state.composer_text.set_text("/mo");
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
        assert!(rendered.contains("❯ /mo"));
        assert!(!rendered.contains("Palette>"));
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
        assert!(rendered.contains("q:2"));
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

    #[test]
    fn idle_layout_renders_track4_shared_chrome() {
        let mut state = AppState::new((120, 30), false);
        state.status.model = "tools".into();
        state.status.provider = "openrouter".into();
        state.status.mode = "suggest".into();
        state.status.bg_tasks = 2;
        state.subagents = vec![crate::rpc::protocol::SubagentEntry {
            id: "agent-1".into(),
            role: "coder".into(),
            status: "running".into(),
        }];

        let rendered = render_to_string(&state, 120, 30);

        assert!(rendered.contains("tasks:2"));
        assert!(rendered.contains("agents:1"));
        assert!(rendered.contains("sandbox:local"));
        assert!(rendered.contains("❯"));
        assert!(!rendered.contains("Ask AutoCode"));
        assert!(rendered.contains("Ctrl+Enter"));
        assert!(rendered.contains("Esc"));
    }

    #[test]
    fn idle_layout_renders_framed_workspace_shell() {
        let state = AppState::new((120, 30), false);

        let rendered = render_to_string(&state, 120, 30);

        assert!(!rendered.contains("Transcript"));
        assert!(!rendered.contains("Composer"));
        assert!(!rendered.contains("Keys"));
        assert!(rendered.contains("❯"));
        assert!(!rendered.contains("Ask AutoCode"));
        assert!(rendered.contains("Ctrl+Enter"));
        assert!(rendered.contains("┌"));
        assert!(rendered.contains("┘"));
    }

    #[test]
    fn shell_area_uses_full_terminal_at_multiple_sizes() {
        for (width, height) in [(80, 24), (120, 30), (200, 50)] {
            let shell = super::shell_area(Rect::new(0, 0, width, height));

            assert_eq!(shell, Rect::new(0, 0, width, height));
        }
    }

    #[test]
    fn idle_layout_uses_full_width_shell_on_wide_terminals() {
        let state = AppState::new((120, 30), false);

        let lines = render_lines(&state, 120, 30);
        let shell_line = lines
            .iter()
            .find(|line| line.contains('┌') && line.contains('┐'))
            .expect("missing shell title line");

        assert!(!shell_line.contains("AutoCode"));
        assert!(
            shell_line.starts_with('┌'),
            "expected shell to start at column 0, got: {shell_line:?}"
        );
        assert!(
            shell_line.ends_with('┐'),
            "expected shell to reach the right edge, got: {shell_line:?}"
        );
    }

    #[test]
    fn idle_layout_uses_outer_shell_without_inner_content_box() {
        let state = AppState::new((120, 30), false);

        let lines = render_lines(&state, 120, 30);
        let content_line = lines
            .iter()
            .find(|line| line.contains("Describe a change"))
            .expect("missing ready-state placeholder line");
        let border_count = content_line
            .chars()
            .take_while(|ch| *ch == ' ' || *ch == '│')
            .filter(|ch| *ch == '│')
            .count();

        assert_eq!(
            border_count, 1,
            "expected content to sit directly inside the shell: {content_line:?}"
        );
    }

    #[test]
    fn idle_surface_renders_quiet_continuity_hints() {
        let rendered = render_to_string(&AppState::new((160, 50), false), 160, 50);

        assert!(rendered.contains("Describe a change, ask a question"));
        assert!(rendered.contains("Restore"));
        assert!(rendered.contains("recent session"));
        assert!(rendered.contains("last branch activity"));
    }

    #[test]
    fn detail_surfaces_render_without_nested_panel_border() {
        let mut state = AppState::new((120, 30), false);
        state.detail_surface = Some(DetailSurface::Plan);

        let lines = render_lines(&state, 120, 30);
        let heading_line = lines
            .iter()
            .find(|line| line.contains("Planning"))
            .expect("missing plan heading");
        let border_count = heading_line
            .chars()
            .take_while(|ch| *ch == ' ' || *ch == '│')
            .filter(|ch| *ch == '│')
            .count();

        assert_eq!(
            border_count, 1,
            "expected detail surface to use the shell directly: {heading_line:?}"
        );
    }

    #[test]
    fn review_surface_uses_horizontal_split_layout() {
        let mut state = AppState::new((120, 30), false);
        state.detail_surface = Some(DetailSurface::Review);

        let lines = render_lines(&state, 120, 30);
        let split_line = lines
            .iter()
            .find(|line| {
                line.contains("All edits staged. Waiting for review.") && line.contains("PLAN")
            })
            .expect("missing split review line");

        assert!(
            split_line.find("PLAN").unwrap()
                > split_line
                    .find("All edits staged. Waiting for review.")
                    .unwrap(),
            "expected right-hand review sidebar: {split_line:?}"
        );
    }

    #[test]
    fn diff_surface_uses_horizontal_split_layout() {
        let mut state = AppState::new((120, 30), false);
        state.detail_surface = Some(DetailSurface::Diff);

        let lines = render_lines(&state, 120, 30);
        let split_line = lines
            .iter()
            .find(|line| line.contains("files changed") && line.contains("RAW COMMAND"))
            .expect("missing split diff line");

        assert!(
            split_line.find("RAW COMMAND").unwrap() > split_line.find("files changed").unwrap(),
            "expected right-hand diff sidebar: {split_line:?}"
        );
    }

    #[test]
    fn grep_surface_uses_horizontal_split_layout() {
        let mut state = AppState::new((120, 30), false);
        state.detail_surface = Some(DetailSurface::Grep);

        let lines = render_lines(&state, 120, 30);
        let split_line = lines
            .iter()
            .find(|line| line.contains("Search") && line.contains("ATTACH"))
            .expect("missing split grep line");

        assert!(
            split_line.find("ATTACH").unwrap() > split_line.find("Search").unwrap(),
            "expected right-hand grep sidebar: {split_line:?}"
        );
    }

    #[test]
    fn escalation_surface_uses_horizontal_split_layout() {
        let mut state = AppState::new((120, 30), false);
        state.detail_surface = Some(DetailSurface::Escalation);

        let lines = render_lines(&state, 120, 30);
        let split_line = lines
            .iter()
            .find(|line| line.contains("Permission escalation") && line.contains("DECISION"))
            .expect("missing split escalation line");

        assert!(
            split_line.find("DECISION").unwrap()
                > split_line.find("Permission escalation").unwrap(),
            "expected right-hand escalation sidebar: {split_line:?}"
        );
    }

    #[test]
    fn command_center_surface_uses_horizontal_split_layout() {
        let mut state = AppState::new((120, 30), false);
        state.detail_surface = Some(DetailSurface::CommandCenter);

        let lines = render_lines(&state, 120, 30);
        let split_line = lines
            .iter()
            .find(|line| line.contains("Delegate") && line.contains("SUBAGENTS"))
            .expect("missing split command-center line");

        assert!(
            split_line.find("SUBAGENTS").unwrap() > split_line.find("Delegate").unwrap(),
            "expected right-hand command-center sidebar: {split_line:?}"
        );
    }

    #[test]
    fn palette_overlay_preserves_workspace_shell() {
        let mut state = AppState::new((120, 30), false);
        state.stage = crate::state::model::Stage::Palette;
        let mut filter = TextBuf::default();
        filter.set_text("re");
        state.palette = Some(PaletteState {
            mode: PaletteMode::CommandPalette,
            filter,
            cursor: 0,
            entries: vec![PaletteEntry {
                name: "/review".into(),
                description: "Open the review surface".into(),
            }],
        });

        let rendered = render_to_string(&state, 120, 30);

        assert!(rendered.contains("Command Palette"));
        assert!(!rendered.contains("Transcript"));
        assert!(!rendered.contains("Composer"));
        assert!(!rendered.contains("Keys"));
        assert!(rendered.contains("Palette>"));
        assert!(rendered.contains("Ctrl+Shift+P"));
    }

    #[test]
    fn palette_overlay_uses_compact_geometry_on_wide_terminals() {
        let mut state = AppState::new((160, 50), false);
        state.stage = crate::state::model::Stage::Palette;
        state.palette = Some(PaletteState {
            mode: PaletteMode::CommandPalette,
            filter: TextBuf::default(),
            cursor: 0,
            entries: vec![
                PaletteEntry {
                    name: "/help".into(),
                    description: "Show available commands".into(),
                },
                PaletteEntry {
                    name: "/model".into(),
                    description: "Show or switch the LLM model".into(),
                },
                PaletteEntry {
                    name: "/plan".into(),
                    description: "Open the plan surface".into(),
                },
                PaletteEntry {
                    name: "/multi".into(),
                    description: "Open the multitasking surface".into(),
                },
                PaletteEntry {
                    name: "/review".into(),
                    description: "Open the review surface".into(),
                },
                PaletteEntry {
                    name: "/diff".into(),
                    description: "Open the diff surface".into(),
                },
                PaletteEntry {
                    name: "/grep".into(),
                    description: "Open the search surface".into(),
                },
                PaletteEntry {
                    name: "/restore".into(),
                    description: "Open the restore browser".into(),
                },
                PaletteEntry {
                    name: "/cc".into(),
                    description: "Open the command center".into(),
                },
                PaletteEntry {
                    name: "/escalation".into(),
                    description: "Open the escalation surface".into(),
                },
            ],
        });

        let lines = render_lines(&state, 160, 50);
        let title_row = lines
            .iter()
            .position(|line| line.contains("┌ Command Palette"))
            .expect("missing palette overlay title row");
        let title_line = &lines[title_row];

        assert!(
            boxed_line_width(title_line) <= 60,
            "palette overlay should stay compact on wide terminals: {title_line:?}"
        );
        assert!(
            title_row < 18,
            "palette overlay should float above screen center: row={title_row}"
        );
    }

    #[test]
    fn picker_overlay_uses_compact_geometry_on_wide_terminals() {
        let mut state = AppState::new((160, 50), false);
        state.stage = crate::state::model::Stage::Picker(PickerKind::Session);
        state.picker = Some(PickerState {
            kind: PickerKind::Session,
            entries: vec!["Mock session [mock-session-001] · openrouter / tools".into()],
            filter: TextBuf::default(),
            cursor: 0,
        });

        let lines = render_lines(&state, 160, 50);
        let title_row = lines
            .iter()
            .position(|line| line.contains("┌ Picker"))
            .expect("missing picker overlay title row");
        let title_line = &lines[title_row];

        assert!(
            boxed_line_width(title_line) <= 60,
            "picker overlay should stay compact on wide terminals: {title_line:?}"
        );
        assert!(
            title_row < 18,
            "picker overlay should float above screen center: row={title_row}"
        );
    }

    #[test]
    fn narrow_ready_layout_uses_compact_status_footer_and_activity_copy() {
        let state = AppState::new((68, 30), false);
        let lines = render_lines(&state, 68, 30);
        let rendered = lines.join("\n");

        let status_line = line_containing(&lines, "● ready");
        assert!(
            status_line.contains("t:0")
                && status_line.contains("a:0")
                && status_line.contains("q:0"),
            "expected compact counters in narrow status line: {status_line:?}"
        );
        assert!(
            !status_line.contains("sandbox:local"),
            "expected sandbox label to drop in narrow mode: {status_line:?}"
        );

        let footer_line = line_containing(&lines, "Ctrl+Enter send");
        assert!(
            footer_line.contains("Ctrl+Shift+P palette"),
            "expected narrow footer to keep palette hint intact: {footer_line:?}"
        );

        assert!(
            rendered.contains("resume/fork"),
            "expected compact ready continuity copy in narrow layout: {rendered}"
        );
        assert!(
            rendered.contains("workspace preserved"),
            "expected branch continuity copy to survive narrow layout: {rendered}"
        );
    }

    #[test]
    fn narrow_ready_layout_keeps_populated_status_line_untruncated() {
        let mut state = AppState::new((68, 30), false);
        state.status.model = "tools".into();
        state.status.provider = "openrouter".into();
        state.status.mode = "suggest".into();
        state.status.session_id = Some("mock-session-001".into());

        let lines = render_lines(&state, 68, 30);
        let status_line = line_containing(&lines, "● ready");

        assert!(
            status_line.contains("tools")
                && status_line.contains("openrouter")
                && status_line.contains("suggest"),
            "expected narrow status line to retain core model/provider/mode: {status_line:?}"
        );
        assert!(
            status_line.contains("t:0") && status_line.contains("a:0") && status_line.contains("q:0"),
            "expected compact counters to remain visible in populated narrow status line: {status_line:?}"
        );
        assert!(
            !status_line.contains("mock-ses"),
            "expected narrow populated status line to drop the session chunk before truncating: {status_line:?}"
        );
    }

    #[test]
    fn streaming_status_renders_working_marker() {
        let mut state = AppState::new((120, 30), false);
        state.stage = crate::state::model::Stage::Streaming;
        state.status.model = "tools".into();
        state.status.provider = "openrouter".into();
        state.status.mode = "suggest".into();

        let rendered = render_to_string(&state, 120, 30);

        assert!(rendered.contains("working"));
    }

    #[test]
    fn crowded_streaming_status_keeps_working_marker_visible() {
        let mut state = AppState::new((120, 30), false);
        state.stage = crate::state::model::Stage::Streaming;
        state.spinner_frame = 2;
        state.status.model = "tools".into();
        state.status.provider = "openrouter".into();
        state.status.mode = "suggest".into();
        state.status.session_id = Some("mock-session-001".into());
        state.status.tokens_in = 5;
        state.status.tokens_out = 6;

        let rendered = render_to_string(&state, 120, 30);

        assert!(rendered.contains("working"));
        assert!(rendered.contains(crate::ui::spinner::FRAMES[2]));
    }

    #[test]
    fn streaming_surface_renders_structured_active_sections() {
        let mut state = AppState::new((160, 50), false);
        state.stage = Stage::Streaming;
        state.scrollback.push_back(
            "> refactor parser.ts to safely handle missing imports and run tests".into(),
        );
        state.stream_lines = vec![
            "Planning".into(),
            "Will inspect parser flow, extend ASTNode with an optional imports field, patch extractImports to guard against undefined,".into(),
            "then run the targeted parser tests.".into(),
            "Read(src/utils/parser.ts)".into(),
            "Search \"extractImports|ASTNode\" src".into(),
            "Edit(src/types.ts)".into(),
            "42 - imports: ImportNode[]".into(),
            "42 + imports?: ImportNode[]".into(),
            "Run(bun test ./tests/parser.test.ts)".into(),
            "√ parsed simple ast".into(),
            "● tests/parser.test.ts…".into(),
        ];

        let rendered = render_to_string(&state, 160, 50);

        assert!(rendered.contains("refactor parser.ts to safely handle missing imports"));
        assert!(rendered.contains("Planning"));
        assert!(rendered.contains("42 - imports: ImportNode[]"));
        assert!(rendered.contains("42 + imports?: ImportNode[]"));
        assert!(rendered.contains("draft stays live while validation streams"));
        assert!(rendered.contains("tests/parser.test.ts"));
    }

    #[test]
    fn error_state_renders_recovery_actions() {
        let mut state = AppState::new((120, 30), false);
        state.error_banner = Some("matrix shard failure".into());

        let rendered = render_to_string(&state, 120, 30);
        let lower = rendered.to_lowercase();

        for label in [
            "retry", "inspect", "restore", "rewind", "compact", "planning",
        ] {
            assert!(lower.contains(label), "missing recovery label: {label}");
        }
    }

    #[test]
    fn error_state_uses_split_recovery_layout() {
        let mut state = AppState::new((120, 30), false);
        state.error_banner = Some("matrix shard failure".into());

        let lines = render_lines(&state, 120, 30);
        let split_line = lines
            .iter()
            .find(|line| line.contains("Error: matrix shard failure") && line.contains("RECOVERY"))
            .expect("missing split recovery line");

        assert!(
            split_line.find("RECOVERY").unwrap()
                > split_line.find("Error: matrix shard failure").unwrap(),
            "expected right-hand recovery sidebar: {split_line:?}"
        );
    }

    #[test]
    fn error_state_skips_empty_status_chunks_and_marks_selected_recovery_action() {
        let mut state = AppState::new((120, 30), false);
        state.stage = Stage::Shutdown;
        state.error_banner = Some("matrix shard failure".into());
        state.recovery_action_idx = 2;

        let rendered = render_to_string(&state, 120, 30);

        assert!(!rendered.contains("|  |"), "status bar leaked empty chunks");
        assert!(rendered.contains("● Restore"));
        assert!(rendered.contains("○ Retry"));
    }

    #[test]
    fn error_state_shows_recent_context_and_selected_detail() {
        let mut state = AppState::new((120, 30), false);
        state.error_banner = Some("backend crashed".into());
        state.scrollback = vec!["> hello".into(), "/model".into()].into();
        state.recovery_action_idx = 1;

        let rendered = render_to_string(&state, 120, 30);

        assert!(rendered.contains("LAST INPUT"));
        assert!(rendered.contains("> hello"));
        assert!(rendered.contains("DETAIL"));
        assert!(rendered.contains("Inspect tools, queue,"));
    }

    #[test]
    fn plan_surface_renders_steps_and_validation() {
        let mut state = AppState::new((160, 50), false);
        state.detail_surface = Some(DetailSurface::Plan);

        let rendered = render_to_string(&state, 160, 50);

        assert!(rendered.contains("Planning"));
        assert!(rendered.contains("Seven steps queued"));
        assert!(rendered.contains("Run targeted parser tests"));
        assert!(rendered.contains("VALIDATION"));
    }

    #[test]
    fn restore_surface_renders_checkpoints_and_actions() {
        let mut state = AppState::new((160, 50), false);
        state.detail_surface = Some(DetailSurface::Restore);

        let rendered = render_to_string(&state, 160, 50);

        assert!(rendered.contains("5 checkpoints"));
        assert!(rendered.contains("extractImports guard"));
        assert!(rendered.contains("diff from here"));
        assert!(rendered.contains("local only"));
    }

    #[test]
    fn review_and_diff_surfaces_render_first_class_actions() {
        let mut review = AppState::new((160, 50), false);
        review.detail_surface = Some(DetailSurface::Review);
        let review_rendered = render_to_string(&review, 160, 50);
        assert!(review_rendered.contains("REVIEW NEEDED"));
        assert!(review_rendered.contains("src/utils/parser.ts"));
        assert!(review_rendered.contains("[a]pprove"));

        let mut diff = AppState::new((160, 50), false);
        diff.detail_surface = Some(DetailSurface::Diff);
        let diff_rendered = render_to_string(&diff, 160, 50);
        assert!(diff_rendered.contains("files changed"));
        assert!(diff_rendered.contains("APPROVAL PATTERN"));
        assert!(diff_rendered.contains("src/utils/resolver.ts"));
    }

    #[test]
    fn grep_escalation_multi_and_cc_surfaces_render_scene_tokens() {
        let mut grep = AppState::new((160, 50), false);
        grep.detail_surface = Some(DetailSurface::Grep);
        let grep_rendered = render_to_string(&grep, 160, 50);
        assert!(grep_rendered.contains("Search"));
        assert!(grep_rendered.contains("14 hits across 5 files"));
        assert!(grep_rendered.contains("ATTACH"));
        assert!(grep_rendered.contains("@src/types.ts"));

        let mut escalation = AppState::new((160, 50), false);
        escalation.detail_surface = Some(DetailSurface::Escalation);
        let escalation_rendered = render_to_string(&escalation, 160, 50);
        assert!(escalation_rendered.contains("Permission escalation"));
        assert!(escalation_rendered.contains(".github/workflows/ci.yml"));
        assert!(escalation_rendered.contains("Approve this edit only"));

        let mut multi = AppState::new((160, 50), false);
        multi.detail_surface = Some(DetailSurface::Multi);
        let multi_rendered = render_to_string(&multi, 160, 50);
        assert!(multi_rendered.contains("2 jobs running"));
        assert!(multi_rendered.contains("[prioritized]"));
        assert!(multi_rendered.contains("[blocked: tests]"));

        let mut cc = AppState::new((160, 50), false);
        cc.detail_surface = Some(DetailSurface::CommandCenter);
        let cc_rendered = render_to_string(&cc, 160, 50);
        assert!(cc_rendered.contains("Delegate"));
        assert!(cc_rendered.contains("SUBAGENTS"));
        assert!(cc_rendered.contains("matrix tests"));
    }
}
