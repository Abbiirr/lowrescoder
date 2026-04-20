use ratatui::{
    layout::{Constraint, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Paragraph, Wrap},
    Frame,
};

use crate::state::model::{AppState, Stage};
use crate::ui::spinner::{FRAMES, VERBS};

pub fn render(f: &mut Frame, state: &AppState) {
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
        let short = &sid[..sid.len().min(8)];
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
    let mut lines: Vec<Line> = state
        .scrollback
        .iter()
        .map(|s| {
            let spans = crate::render::markdown::parse_inline(s);
            Line::from(spans)
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

    let cursor_pos = state.composer_cursor;
    let text = &state.composer_text;

    // Build line with cursor highlighting
    let before = &text[..cursor_pos.min(text.len())];
    let after = &text[cursor_pos.min(text.len())..];

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
    if text.is_empty() || cursor_pos >= text.len() {
        spans.push(Span::styled(" ", Style::default().bg(Color::Gray)));
    }

    let composer = Paragraph::new(Line::from(spans));
    f.render_widget(composer, area);
}
