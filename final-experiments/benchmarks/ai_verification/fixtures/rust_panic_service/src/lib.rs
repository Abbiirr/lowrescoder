use std::collections::HashMap;

pub fn divide(a: f64, b: f64) -> f64 {
    if b == 0.0 {
        panic!("division by zero");
    }
    a / b
}

pub fn get_value(map: &HashMap<String, i32>, key: &str) -> i32 {
    *map.get(key).unwrap()
}

pub fn parse_age(s: &str) -> u32 {
    s.parse::<u32>().unwrap()
}

pub fn first_element(v: &[i32]) -> i32 {
    v[0]
}

pub fn find_user(users: &[&str], name: &str) -> usize {
    users.iter().position(|&u| u == name).unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    #[test]
    fn test_divide_ok() {
        assert_eq!(divide(10.0, 2.0), 5.0);
    }

    #[test]
    fn test_get_value_found() {
        let mut m = HashMap::new();
        m.insert("x".to_string(), 42);
        assert_eq!(get_value(&m, "x"), 42);
    }

    #[test]
    fn test_parse_age_valid() {
        assert_eq!(parse_age("25"), 25);
    }

    #[test]
    fn test_first_element() {
        assert_eq!(first_element(&[1, 2, 3]), 1);
    }

    #[test]
    fn test_find_user_found() {
        let users = vec!["alice", "bob", "carol"];
        assert_eq!(find_user(&users, "bob"), 1);
    }
}
