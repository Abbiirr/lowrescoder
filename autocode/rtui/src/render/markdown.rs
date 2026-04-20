use ratatui::style::{Color, Modifier, Style};
use ratatui::text::Span;

/// Parse inline markdown and return styled spans.
/// Supports: `code`, **bold**, *italic*, [text](url)
pub fn parse_inline(text: &str) -> Vec<Span<'static>> {
    let mut spans = Vec::new();
    let chars: Vec<char> = text.chars().collect();
    let len = chars.len();
    let mut i = 0;

    while i < len {
        // Inline code: `code`
        if chars[i] == '`' {
            if let Some(end) = chars[i + 1..].iter().position(|&c| c == '`') {
                let code: String = chars[i + 1..i + 1 + end].iter().collect();
                spans.push(Span::styled(
                    code,
                    Style::default()
                        .fg(Color::Cyan)
                        .add_modifier(Modifier::BOLD),
                ));
                i += end + 2;
                continue;
            }
        }

        // Bold: **text**
        if i + 1 < len && chars[i] == '*' && chars[i + 1] == '*' {
            if let Some(end) = chars[i + 2..].windows(2).position(|w| w == ['*', '*']) {
                let bold_text: String = chars[i + 2..i + 2 + end].iter().collect();
                spans.push(Span::styled(
                    bold_text,
                    Style::default().add_modifier(Modifier::BOLD),
                ));
                i += end + 4;
                continue;
            }
        }

        // Italic: *text*
        if chars[i] == '*' && (i == 0 || chars[i - 1] != '*') {
            if let Some(end) = chars[i + 1..].iter().position(|&c| c == '*') {
                let italic_text: String = chars[i + 1..i + 1 + end].iter().collect();
                spans.push(Span::styled(
                    italic_text,
                    Style::default().add_modifier(Modifier::ITALIC),
                ));
                i += end + 2;
                continue;
            }
        }

        // Link: [text](url)
        if chars[i] == '[' {
            if let Some(bracket_end) = chars[i..].iter().position(|&c| c == ']') {
                let link_text: String = chars[i + 1..i + bracket_end].iter().collect();
                if i + bracket_end + 1 < len && chars[i + bracket_end + 1] == '(' {
                    if let Some(paren_end) =
                        chars[i + bracket_end + 2..].iter().position(|&c| c == ')')
                    {
                        let url: String = chars
                            [i + bracket_end + 2..i + bracket_end + 2 + paren_end]
                            .iter()
                            .collect();
                        let mut styled_spans = Vec::new();
                        styled_spans.push(Span::styled(
                            link_text,
                            Style::default()
                                .fg(Color::Blue)
                                .add_modifier(Modifier::UNDERLINED),
                        ));
                        styled_spans.push(Span::styled(
                            format!(" ({})", url),
                            Style::default().fg(Color::DarkGray),
                        ));
                        spans.extend(styled_spans);
                        i += bracket_end + 3 + paren_end;
                        continue;
                    }
                }
            }
        }

        // Regular character
        spans.push(Span::raw(chars[i].to_string()));
        i += 1;
    }

    spans
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_inline_code() {
        let spans = parse_inline("use `std::io` here");
        let code_span = spans
            .iter()
            .find(|s| s.content == "std::io")
            .expect("code span not found");
        assert_eq!(code_span.content, "std::io");
    }

    #[test]
    fn test_bold() {
        let spans = parse_inline("**bold text** here");
        let bold_span = spans
            .iter()
            .find(|s| s.content == "bold text")
            .expect("bold span not found");
        assert_eq!(bold_span.content, "bold text");
    }

    #[test]
    fn test_italic() {
        let spans = parse_inline("*italic text* here");
        let italic_span = spans
            .iter()
            .find(|s| s.content == "italic text")
            .expect("italic span not found");
        assert_eq!(italic_span.content, "italic text");
    }

    #[test]
    fn test_link() {
        let spans = parse_inline("[click](https://example.com) here");
        assert!(spans.len() >= 2);
        assert_eq!(spans[0].content, "click");
    }

    #[test]
    fn test_plain_text() {
        let spans = parse_inline("hello world");
        assert_eq!(spans.len(), 11);
    }
}
