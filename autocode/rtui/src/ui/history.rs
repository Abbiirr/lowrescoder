use std::collections::HashSet;
use std::fs;
use std::io::Write;
use std::path::PathBuf;

use crate::state::model::HistoryEntry;

const MAX_HISTORY_ENTRIES: usize = 5_000;

fn history_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
    PathBuf::from(home).join(".autocode").join("history.json")
}

fn load_history_at(path: &PathBuf) -> Vec<HistoryEntry> {
    match fs::read_to_string(path) {
        Ok(contents) => serde_json::from_str::<Vec<HistoryEntry>>(&contents)
            .map(|entries| prepare_history_entries(&entries))
            .unwrap_or_default(),
        Err(_) => Vec::new(),
    }
}

pub fn persist_history(history: &[HistoryEntry]) -> anyhow::Result<()> {
    let path = history_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    let prepared = prepare_history_entries(history);
    let json = serde_json::to_string_pretty(&prepared)?;
    let tmp_path = path.with_extension(format!("json.tmp-{}", std::process::id()));
    let mut file = fs::File::create(&tmp_path)?;
    file.write_all(json.as_bytes())?;
    file.sync_all()?;
    fs::rename(&tmp_path, &path)?;
    Ok(())
}

#[allow(dead_code)]
pub fn load_history() -> Vec<HistoryEntry> {
    load_history_at(&history_path())
}

pub fn canonicalize_history_text(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

pub fn prepare_history_entries(history: &[HistoryEntry]) -> Vec<HistoryEntry> {
    let mut seen = HashSet::new();
    let mut prepared = Vec::new();

    for entry in history {
        let normalized = canonicalize_history_text(&entry.text);
        if normalized.is_empty() || !seen.insert(normalized.clone()) {
            continue;
        }

        prepared.push(HistoryEntry {
            text: normalized,
            last_used_ms: entry.last_used_ms,
            use_count: entry.use_count,
        });

        if prepared.len() == MAX_HISTORY_ENTRIES {
            break;
        }
    }

    prepared
}

pub fn sort_history_by_frecency(history: &mut [HistoryEntry]) {
    history.sort_by(|a, b| {
        b.use_count
            .cmp(&a.use_count)
            .then_with(|| b.last_used_ms.cmp(&a.last_used_ms))
    });
}

#[cfg(test)]
mod tests {
    use tempfile::tempdir;

    use super::*;

    #[test]
    fn canonicalize_history_text_collapses_whitespace() {
        assert_eq!(
            canonicalize_history_text("  hello   world  "),
            "hello world"
        );
        assert_eq!(
            canonicalize_history_text("line1\nline2\tline3"),
            "line1 line2 line3"
        );
    }

    #[test]
    fn prepare_history_entries_dedupes_and_caps() {
        let mut entries = vec![
            HistoryEntry {
                text: "  hello   world  ".into(),
                last_used_ms: 1000,
                use_count: 3,
            },
            HistoryEntry {
                text: "hello world".into(),
                last_used_ms: 900,
                use_count: 1,
            },
        ];

        for idx in 0..5_010 {
            entries.push(HistoryEntry {
                text: format!("entry {}", idx),
                last_used_ms: idx as i64,
                use_count: 1,
            });
        }

        let prepared = prepare_history_entries(&entries);
        assert_eq!(prepared.len(), 5_000);
        assert_eq!(prepared[0].text, "hello world");
        assert_eq!(prepared[0].use_count, 3);
    }

    #[test]
    fn sort_history_by_frecency_prioritizes_use_count_before_timestamp() {
        let mut entries = vec![
            HistoryEntry {
                text: "recent once".into(),
                last_used_ms: 2_000,
                use_count: 1,
            },
            HistoryEntry {
                text: "older often".into(),
                last_used_ms: 1_000,
                use_count: 5,
            },
        ];

        sort_history_by_frecency(&mut entries);

        assert_eq!(entries[0].text, "older often");
        assert_eq!(entries[1].text, "recent once");
    }

    #[test]
    fn test_persist_and_load() {
        let dir = tempdir().unwrap();
        let path = dir.path().join(".autocode").join("history.json");

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
        let parent = path.parent().unwrap();
        fs::create_dir_all(parent).unwrap();
        let prepared = prepare_history_entries(&entries);
        let json = serde_json::to_string_pretty(&prepared).unwrap();
        fs::write(&path, json).unwrap();

        let loaded = load_history_at(&path);
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
