use std::net::TcpStream;

use anyhow::{bail, Context, Result};

use super::pty::{spawn_backend, BackendHandle};

pub enum BackendConnectionMode {
    SpawnManaged,
    AttachTcp { addr: String },
}

pub fn resolve_connection_mode(args: &[String]) -> Result<BackendConnectionMode> {
    let mut attach_addr = std::env::var("AUTOCODE_BACKEND_ADDR")
        .ok()
        .filter(|value| !value.trim().is_empty());

    let mut index = 0usize;
    while index < args.len() {
        if args[index] == "--attach" {
            let value = args
                .get(index + 1)
                .context("--attach requires HOST:PORT")?
                .trim()
                .to_string();
            validate_attach_addr(&value)?;
            attach_addr = Some(value);
            index += 1;
        }
        index += 1;
    }

    if let Some(addr) = attach_addr {
        validate_attach_addr(&addr)?;
        return Ok(BackendConnectionMode::AttachTcp { addr });
    }

    Ok(BackendConnectionMode::SpawnManaged)
}

pub fn connect_backend(
    mode: &BackendConnectionMode,
    cols: u16,
    rows: u16,
) -> Result<BackendHandle> {
    match mode {
        BackendConnectionMode::SpawnManaged => spawn_backend(cols, rows),
        BackendConnectionMode::AttachTcp { addr } => connect_tcp_backend(addr),
    }
}

fn connect_tcp_backend(addr: &str) -> Result<BackendHandle> {
    let reader = TcpStream::connect(addr)
        .with_context(|| format!("failed to connect to backend at {}", addr))?;
    reader.set_nodelay(true).ok();
    let writer = reader
        .try_clone()
        .context("failed to clone backend TCP stream")?;
    writer.set_nodelay(true).ok();

    Ok(BackendHandle {
        reader: Box::new(reader),
        writer: Box::new(writer),
        child: None,
    })
}

fn validate_attach_addr(addr: &str) -> Result<()> {
    if addr.trim().is_empty() || !addr.contains(':') {
        bail!("--attach expects HOST:PORT")
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::sync::{Mutex, OnceLock};

    use super::{resolve_connection_mode, BackendConnectionMode};

    fn env_lock() -> &'static Mutex<()> {
        static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
        LOCK.get_or_init(|| Mutex::new(()))
    }

    #[test]
    fn resolve_connection_mode_defaults_to_spawn_managed() {
        let _guard = env_lock().lock().unwrap();
        let old = std::env::var_os("AUTOCODE_BACKEND_ADDR");
        std::env::remove_var("AUTOCODE_BACKEND_ADDR");

        let mode = resolve_connection_mode(&["autocode-tui".into()]).unwrap();

        if let Some(value) = old {
            std::env::set_var("AUTOCODE_BACKEND_ADDR", value);
        }

        assert!(matches!(mode, BackendConnectionMode::SpawnManaged));
    }

    #[test]
    fn resolve_connection_mode_accepts_attach_flag() {
        let mode = resolve_connection_mode(&[
            "autocode-tui".into(),
            "--attach".into(),
            "127.0.0.1:8765".into(),
        ])
        .unwrap();

        assert!(matches!(
            mode,
            BackendConnectionMode::AttachTcp { addr } if addr == "127.0.0.1:8765"
        ));
    }

    #[test]
    fn resolve_connection_mode_uses_env_override() {
        let _guard = env_lock().lock().unwrap();
        let old = std::env::var_os("AUTOCODE_BACKEND_ADDR");
        std::env::set_var("AUTOCODE_BACKEND_ADDR", "127.0.0.1:9000");

        let mode = resolve_connection_mode(&["autocode-tui".into()]).unwrap();

        if let Some(value) = old {
            std::env::set_var("AUTOCODE_BACKEND_ADDR", value);
        } else {
            std::env::remove_var("AUTOCODE_BACKEND_ADDR");
        }

        assert!(matches!(
            mode,
            BackendConnectionMode::AttachTcp { addr } if addr == "127.0.0.1:9000"
        ));
    }
}
