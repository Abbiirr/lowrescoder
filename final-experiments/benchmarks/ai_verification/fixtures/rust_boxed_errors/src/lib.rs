use std::fs;
use std::path::Path;

/// Reads a file and returns its content as a String.
pub fn read_file(path: &Path) -> Result<String, Box<dyn std::error::Error>> {
    let content = fs::read_to_string(path)?;
    Ok(content)
}

/// Parses a string as an integer. Returns Box<dyn Error> on failure.
pub fn parse_number(s: &str) -> Result<i64, Box<dyn std::error::Error>> {
    let n: i64 = s.trim().parse()?;
    Ok(n)
}

/// Reads a file and parses every non-empty line as an integer.
/// Returns the sum of all parsed integers.
pub fn sum_lines(path: &Path) -> Result<i64, Box<dyn std::error::Error>> {
    let content = read_file(path)?;
    let mut total = 0i64;
    for line in content.lines() {
        if line.trim().is_empty() {
            continue;
        }
        total += parse_number(line)?;
    }
    Ok(total)
}

/// Validates that a string is a non-empty username (alphanumeric/underscore, 3–20 chars).
pub fn validate_username(name: &str) -> Result<(), Box<dyn std::error::Error>> {
    if name.len() < 3 || name.len() > 20 {
        return Err(format!("username '{}' length must be 3–20 chars", name).into());
    }
    if !name.chars().all(|c| c.is_alphanumeric() || c == '_') {
        return Err(format!("username '{}' contains invalid characters", name).into());
    }
    Ok(())
}

/// A type alias — callers use this; the migration changes it to a custom error enum.
pub type AppResult<T> = Result<T, Box<dyn std::error::Error>>;

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn write_tmp(name: &str, content: &str) -> std::path::PathBuf {
        let path = std::env::temp_dir().join(format!("file_processor_test_{}.txt", name));
        fs::write(&path, content).unwrap();
        path
    }

    #[test]
    fn test_parse_number_ok() {
        assert_eq!(parse_number("42").unwrap(), 42);
        assert_eq!(parse_number("  -7  ").unwrap(), -7);
    }

    #[test]
    fn test_parse_number_err() {
        assert!(parse_number("not_a_number").is_err());
    }

    #[test]
    fn test_sum_lines_ok() {
        let path = write_tmp("sum_ok", "10\n20\n30\n");
        assert_eq!(sum_lines(&path).unwrap(), 60);
        fs::remove_file(path).ok();
    }

    #[test]
    fn test_sum_lines_parse_err() {
        let path = write_tmp("sum_bad", "10\nbad\n30\n");
        assert!(sum_lines(&path).is_err());
        fs::remove_file(path).ok();
    }

    #[test]
    fn test_validate_username_ok() {
        assert!(validate_username("alice_99").is_ok());
    }

    #[test]
    fn test_validate_username_too_short() {
        assert!(validate_username("ab").is_err());
    }

    #[test]
    fn test_validate_username_bad_chars() {
        assert!(validate_username("alice@domain").is_err());
    }
}
