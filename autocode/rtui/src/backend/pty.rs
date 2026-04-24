use std::io::Read;
use std::path::Path;
use std::process::{Child, Command, Stdio};

use anyhow::{Context, Result};

pub struct BackendHandle {
    pub reader: Box<dyn Read + Send>,
    pub writer: Box<dyn std::io::Write + Send>,
    pub child: Option<Child>,
}

pub fn spawn_backend(_cols: u16, _rows: u16) -> Result<BackendHandle> {
    let mut cmd = Command::new(find_python_cmd());
    cmd.arg("serve");
    cmd.current_dir(std::env::current_dir().unwrap_or_else(|_| ".".into()));
    cmd.stdin(Stdio::piped());
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::null());

    let mut child = cmd.spawn().context("failed to spawn backend process")?;
    let reader = child
        .stdout
        .take()
        .context("failed to capture backend stdout")?;
    let writer = child
        .stdin
        .take()
        .context("failed to capture backend stdin")?;

    Ok(BackendHandle {
        reader: Box::new(reader),
        writer: Box::new(writer),
        child: Some(child),
    })
}

fn find_python_cmd() -> String {
    if let Ok(cmd) = std::env::var("AUTOCODE_PYTHON_CMD") {
        if !cmd.is_empty() {
            return resolve_command_path(&cmd).unwrap_or(cmd);
        }
    }
    resolve_command_path("autocode").unwrap_or_else(|| "autocode".to_string())
}

fn resolve_command_path(command: &str) -> Option<String> {
    if command.is_empty() {
        return None;
    }

    let path = Path::new(command);
    if path.is_absolute() || command.contains(std::path::MAIN_SEPARATOR) {
        return Some(command.to_string());
    }

    let path_env = std::env::var_os("PATH")?;
    for entry in std::env::split_paths(&path_env) {
        let candidate = entry.join(command);
        if is_executable_file(&candidate) {
            return Some(candidate.to_string_lossy().into_owned());
        }
    }

    None
}

fn is_executable_file(path: &Path) -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;

        path.is_file()
            && std::fs::metadata(path)
                .map(|meta| meta.permissions().mode() & 0o111 != 0)
                .unwrap_or(false)
    }

    #[cfg(not(unix))]
    {
        path.is_file()
    }
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::os::unix::fs::PermissionsExt;
    use std::sync::{Mutex, OnceLock};

    use tempfile::tempdir;

    fn env_lock() -> &'static Mutex<()> {
        static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        LOCK.get_or_init(|| Mutex::new(()))
    }

    #[test]
    fn default_backend_command_resolves_autocode_from_path() {
        let _guard = env_lock().lock().unwrap();
        let dir = tempdir().unwrap();
        let bin_dir = dir.path().join("bin");
        fs::create_dir_all(&bin_dir).unwrap();

        let autocode_path = bin_dir.join("autocode");
        fs::write(&autocode_path, "#!/bin/sh\nexit 0\n").unwrap();
        let mut perms = fs::metadata(&autocode_path).unwrap().permissions();
        perms.set_mode(0o755);
        fs::set_permissions(&autocode_path, perms).unwrap();

        let old_path = std::env::var_os("PATH");
        let old_backend = std::env::var_os("AUTOCODE_PYTHON_CMD");

        std::env::set_var("PATH", bin_dir.as_os_str());
        std::env::remove_var("AUTOCODE_PYTHON_CMD");

        let cmd = super::find_python_cmd();

        if let Some(path) = old_path {
            std::env::set_var("PATH", path);
        } else {
            std::env::remove_var("PATH");
        }
        if let Some(path) = old_backend {
            std::env::set_var("AUTOCODE_PYTHON_CMD", path);
        } else {
            std::env::remove_var("AUTOCODE_PYTHON_CMD");
        }

        assert_eq!(cmd, autocode_path.to_string_lossy());
    }

    #[test]
    fn explicit_backend_override_is_preserved() {
        let _guard = env_lock().lock().unwrap();
        let old_backend = std::env::var_os("AUTOCODE_PYTHON_CMD");
        std::env::set_var("AUTOCODE_PYTHON_CMD", "/tmp/mock_backend.py");

        let cmd = super::find_python_cmd();

        if let Some(path) = old_backend {
            std::env::set_var("AUTOCODE_PYTHON_CMD", path);
        } else {
            std::env::remove_var("AUTOCODE_PYTHON_CMD");
        }

        assert_eq!(cmd, "/tmp/mock_backend.py");
    }
}
