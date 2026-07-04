#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct TextBuf {
    text: String,
    cursor: usize,
}

impl TextBuf {
    pub fn as_str(&self) -> &str {
        &self.text
    }

    pub fn is_empty(&self) -> bool {
        self.text.is_empty()
    }

    pub fn cursor(&self) -> usize {
        self.cursor
    }

    pub fn len_chars(&self) -> usize {
        self.text.chars().count()
    }

    pub fn char_boundary_cursor_byte(&self) -> usize {
        char_to_byte_idx(&self.text, self.cursor)
    }

    pub fn split_at_cursor(&self) -> (&str, &str) {
        self.text.split_at(self.char_boundary_cursor_byte())
    }

    pub fn clear(&mut self) {
        self.text.clear();
        self.cursor = 0;
    }

    pub fn set_text<T: Into<String>>(&mut self, text: T) {
        self.text = text.into();
        self.end();
    }

    pub fn insert(&mut self, c: char) {
        let byte_idx = self.char_boundary_cursor_byte();
        self.text.insert(byte_idx, c);
        self.cursor += 1;
    }

    pub fn delete_left(&mut self) {
        if self.cursor == 0 {
            return;
        }
        let end = self.char_boundary_cursor_byte();
        let start = char_to_byte_idx(&self.text, self.cursor - 1);
        self.text.replace_range(start..end, "");
        self.cursor -= 1;
    }

    pub fn delete_right(&mut self) {
        if self.cursor >= self.len_chars() {
            return;
        }
        let start = self.char_boundary_cursor_byte();
        let end = char_to_byte_idx(&self.text, self.cursor + 1);
        self.text.replace_range(start..end, "");
    }

    pub fn move_left(&mut self) {
        if self.cursor > 0 {
            self.cursor -= 1;
        }
    }

    pub fn move_right(&mut self) {
        if self.cursor < self.len_chars() {
            self.cursor += 1;
        }
    }

    pub fn move_word_left(&mut self) {
        if self.cursor == 0 {
            return;
        }

        let chars: Vec<char> = self.text.chars().collect();
        let mut idx = self.cursor;
        while idx > 0 && chars[idx - 1].is_whitespace() {
            idx -= 1;
        }
        while idx > 0 && !chars[idx - 1].is_whitespace() {
            idx -= 1;
        }
        self.cursor = idx;
    }

    pub fn move_word_right(&mut self) {
        let chars: Vec<char> = self.text.chars().collect();
        let mut idx = self.cursor;
        while idx < chars.len() && chars[idx].is_whitespace() {
            idx += 1;
        }
        while idx < chars.len() && !chars[idx].is_whitespace() {
            idx += 1;
        }
        self.cursor = idx;
    }

    pub fn home(&mut self) {
        self.cursor = 0;
    }

    pub fn end(&mut self) {
        self.cursor = self.len_chars();
    }
}

impl From<&str> for TextBuf {
    fn from(value: &str) -> Self {
        Self::from(value.to_string())
    }
}

impl From<String> for TextBuf {
    fn from(value: String) -> Self {
        let cursor = value.chars().count();
        Self {
            text: value,
            cursor,
        }
    }
}

pub fn truncate_chars(text: &str, max_chars: usize) -> &str {
    if text.chars().count() <= max_chars {
        return text;
    }

    let end = char_to_byte_idx(text, max_chars);
    &text[..end]
}

fn char_to_byte_idx(text: &str, cursor: usize) -> usize {
    text.char_indices()
        .nth(cursor)
        .map(|(idx, _)| idx)
        .unwrap_or(text.len())
}

#[cfg(test)]
mod tests {
    use super::{truncate_chars, TextBuf};

    #[test]
    fn cursor_moves_across_unicode_scalars_without_byte_drift() {
        let mut buf = TextBuf::from("aé🙂");
        assert_eq!(buf.cursor(), 3);
        assert_eq!(buf.char_boundary_cursor_byte(), "aé🙂".len());

        buf.move_left();
        assert_eq!(buf.cursor(), 2);
        assert_eq!(buf.char_boundary_cursor_byte(), "aé".len());

        buf.move_left();
        assert_eq!(buf.cursor(), 1);
        assert_eq!(buf.char_boundary_cursor_byte(), "a".len());
    }

    #[test]
    fn delete_operations_respect_unicode_boundaries() {
        let mut buf = TextBuf::from("é🙂b");
        buf.move_left();
        buf.delete_left();
        assert_eq!(buf.as_str(), "éb");
        assert_eq!(buf.cursor(), 1);

        buf.delete_right();
        assert_eq!(buf.as_str(), "é");
        assert_eq!(buf.cursor(), 1);
    }

    #[test]
    fn split_at_cursor_returns_valid_utf8_slices() {
        let mut buf = TextBuf::from("hi🙂there");
        buf.move_left();
        buf.move_left();
        buf.move_left();
        buf.move_left();
        buf.move_left();

        let (before, after) = buf.split_at_cursor();
        assert_eq!(before, "hi🙂");
        assert_eq!(after, "there");
    }

    #[test]
    fn truncate_chars_clamps_without_cutting_multibyte_text() {
        assert_eq!(truncate_chars("session-é🙂", 8), "session-");
        assert_eq!(truncate_chars("🙂🙂🙂🙂", 3), "🙂🙂🙂");
    }
}
