use std::io::Read;

use anyhow::{Context, Result};
use portable_pty::{native_pty_system, CommandBuilder, PtySize};

pub struct PtyHandle {
    pub reader: Box<dyn Read + Send>,
    pub writer: Box<dyn std::io::Write + Send>,
    pub child: Box<dyn portable_pty::Child + Send>,
    pub master: Box<dyn portable_pty::MasterPty + Send>,
}

pub fn spawn_backend(cols: u16, rows: u16) -> Result<PtyHandle> {
    let pty_system = native_pty_system();

    let pair = pty_system
        .openpty(PtySize {
            rows,
            cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .context("failed to open PTY")?;

    let python_cmd = find_python_cmd();
    let args: Vec<String> = vec!["serve".to_string()];

    let mut cmd = CommandBuilder::new(python_cmd);
    cmd.args(&args);
    cmd.cwd(std::env::current_dir().unwrap_or_else(|_| ".".into()));

    let child = pair
        .slave
        .spawn_command(cmd)
        .context("failed to spawn backend in PTY")?;

    drop(pair.slave);

    let reader = pair
        .master
        .try_clone_reader()
        .context("failed to clone PTY reader")?;

    let writer = pair
        .master
        .take_writer()
        .context("failed to take PTY writer")?;

    Ok(PtyHandle {
        reader,
        writer,
        child,
        master: pair.master,
    })
}

fn find_python_cmd() -> String {
    if let Ok(cmd) = std::env::var("AUTOCODE_PYTHON_CMD") {
        if !cmd.is_empty() {
            return cmd;
        }
    }
    "autocode".to_string()
}
