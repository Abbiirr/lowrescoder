/// Returns the absolute value of n.
pub fn abs(n: i64) -> i64 {
    if n < 0 { -n } else { n }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_abs_negative() {
        assert_eq!(abs(-5), 5);
    }

    #[test]
    fn test_abs_positive() {
        assert_eq!(abs(3), 3);
    }

    #[test]
    fn test_abs_zero() {
        assert_eq!(abs(0), 0);
    }
}
