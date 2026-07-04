/// Parses an integer from a string, panicking on invalid input.
pub fn parse_int(s: &str) -> i32 {
    s.trim().parse::<i32>().unwrap()
}

/// Parses a comma-separated pair of integers, panicking on invalid input.
pub fn parse_pair(s: &str) -> (i32, i32) {
    let parts: Vec<&str> = s.splitn(2, ',').collect();
    let a = parts[0].trim().parse::<i32>().unwrap();
    let b = parts[1].trim().parse::<i32>().unwrap();
    (a, b)
}

/// Returns the sum of two integers parsed from comma-separated string.
pub fn parse_and_sum(s: &str) -> i32 {
    let (a, b) = parse_pair(s);
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_int_valid() {
        assert_eq!(parse_int("42"), 42);
        assert_eq!(parse_int("-7"), -7);
        assert_eq!(parse_int(" 100 "), 100);
    }

    #[test]
    fn test_parse_pair_valid() {
        assert_eq!(parse_pair("1, 2"), (1, 2));
        assert_eq!(parse_pair("-3,4"), (-3, 4));
    }

    #[test]
    fn test_parse_and_sum() {
        assert_eq!(parse_and_sum("3, 7"), 10);
    }
}
