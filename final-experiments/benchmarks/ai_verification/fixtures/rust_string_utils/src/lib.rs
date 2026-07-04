pub fn word_count(s: &str) -> usize {
    s.split_whitespace().count()
}

pub fn capitalize_words(s: &str) -> String {
    s.split_whitespace()
        .map(|w| {
            let mut c = w.chars();
            match c.next() {
                None => String::new(),
                Some(f) => f.to_uppercase().collect::<String>() + c.as_str(),
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_word_count_empty() {
        assert_eq!(word_count(""), 0);
    }

    #[test]
    fn test_word_count_basic() {
        assert_eq!(word_count("hello world"), 2);
    }

    #[test]
    fn test_capitalize_words() {
        assert_eq!(capitalize_words("hello world"), "Hello World");
    }
}
