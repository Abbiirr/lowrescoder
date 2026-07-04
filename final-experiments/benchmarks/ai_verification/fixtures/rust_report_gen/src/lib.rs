#[derive(Debug, Clone)]
pub struct Item {
    pub name: String,
    pub value: f64,
}

impl Item {
    pub fn new(name: &str, value: f64) -> Self {
        Item { name: name.to_string(), value }
    }
}

/// Returns the sum of all item values.
pub fn sum(items: &[Item]) -> f64 {
    items.iter().map(|i| i.value).sum()
}

/// Returns the item with the highest value, or None if empty.
pub fn max_item(items: &[Item]) -> Option<&Item> {
    items.iter().max_by(|a, b| a.value.partial_cmp(&b.value).unwrap())
}

/// Returns the item with the lowest value, or None if empty.
pub fn min_item(items: &[Item]) -> Option<&Item> {
    items.iter().min_by(|a, b| a.value.partial_cmp(&b.value).unwrap())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample() -> Vec<Item> {
        vec![
            Item::new("Alpha", 10.0),
            Item::new("Beta", 30.0),
            Item::new("Gamma", 20.0),
        ]
    }

    #[test]
    fn test_sum() {
        assert!((sum(&sample()) - 60.0).abs() < 1e-9);
    }

    #[test]
    fn test_max() {
        assert_eq!(max_item(&sample()).unwrap().name, "Beta");
    }

    #[test]
    fn test_min() {
        assert_eq!(min_item(&sample()).unwrap().name, "Alpha");
    }

    #[test]
    fn test_empty() {
        assert_eq!(sum(&[]), 0.0);
        assert!(max_item(&[]).is_none());
    }
}
