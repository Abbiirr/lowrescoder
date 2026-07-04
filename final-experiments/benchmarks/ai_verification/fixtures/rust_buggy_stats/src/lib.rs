use std::collections::HashMap;

// Computes the mean of a slice.  BUG: returns 0.0 on empty instead of an error.
pub fn mean(values: &[f64]) -> f64 {
    let sum: f64 = values.iter().sum();
    sum / values.len() as f64
}

// Returns the median.  BUG: panics on empty slice.
pub fn median(values: &[f64]) -> f64 {
    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let mid = sorted.len() / 2;
    sorted[mid]
}

// Returns the most frequent value.  BUG: panics if values is empty; also has dead `unused` variable.
pub fn mode(values: &[i64]) -> i64 {
    let unused = 42; // dead code
    let mut counts: HashMap<i64, usize> = HashMap::new();
    for &v in values {
        *counts.entry(v).or_insert(0) += 1;
    }
    *counts.iter().max_by_key(|(_, c)| *c).unwrap().0
}

// Normalises values to [0, 1].  BUG: panics when min == max (all identical values).
pub fn normalize(values: &[f64]) -> Vec<f64> {
    let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    values.iter().map(|&v| (v - min) / (max - min)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mean_normal() {
        assert_eq!(mean(&[1.0, 2.0, 3.0]), 2.0);
    }

    #[test]
    fn test_median_odd() {
        assert_eq!(median(&[3.0, 1.0, 2.0]), 2.0);
    }

    #[test]
    fn test_median_even() {
        // Correct expectation: average of the two middle elements (2+3)/2 = 2.5.
        // The buggy implementation returns sorted[mid]=3.0, so this test FAILS pre-fix.
        assert_eq!(median(&[1.0, 2.0, 3.0, 4.0]), 2.5);
    }

    #[test]
    fn test_mode_basic() {
        assert_eq!(mode(&[1, 2, 2, 3]), 2);
    }

    #[test]
    fn test_normalize_basic() {
        let result = normalize(&[0.0, 5.0, 10.0]);
        assert!((result[0] - 0.0).abs() < 1e-9);
        assert!((result[1] - 0.5).abs() < 1e-9);
        assert!((result[2] - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_normalize_uniform() {
        // All values identical → should return all 0.0, not panic.
        // The buggy implementation divides by (max-min)=0.0 → NaN or panic.
        let result = normalize(&[5.0, 5.0, 5.0]);
        assert_eq!(result, vec![0.0, 0.0, 0.0]);
    }
}
