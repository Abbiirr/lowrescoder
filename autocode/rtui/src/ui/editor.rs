use std::io::Write;
use std::path::PathBuf;

use anyhow::{Context, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParsedEditorCommand {
    pub program: String,
    pub args: Vec<String>,
}

pub fn parse_editor_command(editor: &str) -> Result<ParsedEditorCommand> {
    let parts = shell_words::split(editor).context("failed to parse $EDITOR")?;
    let (program, args) = parts
        .split_first()
        .context("$EDITOR was set but empty after parsing")?;

    Ok(ParsedEditorCommand {
        program: program.clone(),
        args: args.to_vec(),
    })
}

pub fn preferred_temp_dir(runtime_dir: Option<PathBuf>, fallback: PathBuf) -> PathBuf {
    runtime_dir.unwrap_or(fallback)
}

pub fn launch_editor(editor: &str, initial_contents: &str) -> Result<String> {
    let parsed = parse_editor_command(editor)?;
    let temp_dir = preferred_temp_dir(
        std::env::var_os("XDG_RUNTIME_DIR").map(PathBuf::from),
        std::env::temp_dir(),
    );

    let mut tempfile = tempfile::Builder::new()
        .prefix("autocode-editor-")
        .suffix(".md")
        .tempfile_in(temp_dir)
        .context("failed to create editor tempfile")?;

    tempfile
        .write_all(initial_contents.as_bytes())
        .context("failed to write editor tempfile")?;
    tempfile
        .flush()
        .context("failed to flush editor tempfile")?;

    let status = std::process::Command::new(&parsed.program)
        .args(&parsed.args)
        .arg(tempfile.path())
        .status()
        .with_context(|| format!("failed to launch editor '{}'", parsed.program))?;

    if !status.success() {
        return Err(anyhow::anyhow!("editor exited with status {}", status));
    }

    std::fs::read_to_string(tempfile.path()).context("failed to read editor output")
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use super::{parse_editor_command, preferred_temp_dir};

    #[test]
    fn parse_editor_command_supports_arguments() {
        let parsed = parse_editor_command("code --wait").expect("parse should succeed");
        assert_eq!(parsed.program, "code");
        assert_eq!(parsed.args, vec!["--wait"]);
    }

    #[test]
    fn parse_editor_command_supports_quoted_program() {
        let parsed = parse_editor_command("\"/opt/My Editor/bin/editor\" --flag")
            .expect("quoted program should parse");
        assert_eq!(parsed.program, "/opt/My Editor/bin/editor");
        assert_eq!(parsed.args, vec!["--flag"]);
    }

    #[test]
    fn preferred_temp_dir_prefers_xdg_runtime_dir() {
        let runtime_dir = PathBuf::from("/tmp/autocode-runtime-dir");
        let fallback = PathBuf::from("/tmp/autocode-fallback-dir");
        assert_eq!(
            preferred_temp_dir(Some(runtime_dir.clone()), fallback),
            runtime_dir
        );
    }

    #[test]
    fn preferred_temp_dir_falls_back_when_runtime_dir_missing() {
        let fallback = PathBuf::from("/tmp/autocode-fallback-dir");
        assert_eq!(preferred_temp_dir(None, fallback.clone()), fallback);
    }
}
