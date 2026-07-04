/// Returns the number of Unicode characters in s.
pub fn char_count(s: &str) -> usize {
    s.len() // BUG: counts bytes, not chars
}

/// Returns true if s is a palindrome ignoring case and non-alphanumeric characters.
pub fn is_palindrome(s: &str) -> bool {
    // BUG: no normalization — compares raw bytes
    s == s.chars().rev().collect::<String>().as_str()
}

/// Returns the number of vowels (a, e, i, o, u) in s, case-insensitive.
pub fn count_vowels(s: &str) -> usize {
    // BUG: only counts lowercase vowels
    s.chars().filter(|c| "aeiou".contains(*c)).count()
}

/// Returns at most max_len Unicode characters from the start of s.
pub fn char_truncate(s: &str, max_len: usize) -> String {
    // BUG: slices at byte offset instead of char boundary
    if max_len >= s.len() {
        s.to_string()
    } else {
        s[..max_len].to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_char_count_unicode() {
        // "héllo" is 5 chars but 6 bytes — must count chars not bytes
        assert_eq!(char_count("héllo"), 5);
    }

    #[test]
    fn test_is_palindrome_normalized() {
        assert!(is_palindrome("A man a plan a canal Panama"));
    }

    #[test]
    fn test_is_palindrome_simple() {
        assert!(is_palindrome("racecar"));
        assert!(!is_palindrome("hello"));
    }

    #[test]
    fn test_count_vowels_mixed_case() {
        // A, e, i, O, u are all vowels
        assert_eq!(count_vowels("AeiOu"), 5);
    }

    #[test]
    fn test_char_truncate_unicode() {
        // "héllo" truncated to 3 chars must be "hél" (3 chars, 4 bytes)
        let result = char_truncate("héllo", 3);
        assert_eq!(result.chars().count(), 3);
    }

    #[test]
    fn test_char_truncate_short() {
        assert_eq!(char_truncate("hi", 10), "hi");
    }
}
