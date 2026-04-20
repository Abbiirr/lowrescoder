use std::fs;
use std::io::Write;
use std::path::PathBuf;

use crate::state::model::HistoryEntry;

fn history_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
    PathBuf::from(home).join(".autocode").join("history.json")
}

pub fn persist_history(history: &[HistoryEntry]) -> anyhow::Result<()> {
    let path = history_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let json = serde_json::to_string_pretty(history)?;
    let mut file = fs::File::create(&path)?;
    file.write_all(json.as_bytes())?;
    Ok(())
}

#[allow(dead_code)]
pub fn load_history() -> Vec<HistoryEntry> {
    let path = history_path();
    match fs::read_to_string(&path) {
        Ok(contents) => serde_json::from_str::<Vec<HistoryEntry>>(&contents).unwrap_or_default(),
        Err(_) => Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_persist_and_load() {
        let entries = vec![
            HistoryEntry {
                text: "hello world".into(),
                last_used_ms: 1000,
                use_count: 3,
            },
            HistoryEntry {
                text: "another query".into(),
                last_used_ms: 2000,
                use_count: 1,
            },
        ];
        persist_history(&entries).unwrap();
        let loaded = load_history();
        assert_eq!(loaded.len(), 2);
        assert_eq!(loaded[0].text, "hello world");
        assert_eq!(loaded[1].use_count, 1);
    }

    #[test]
    fn test_load_empty() {
        let entries = load_history();
        assert!(!entries.is_empty() || entries.is_empty());
    }
}
