mod backend;
mod render;
mod rpc;
mod state;
mod ui;

use std::io::{self, Write};
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use crossterm::{
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
    QueueableCommand,
};
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;
use tokio::sync::mpsc;
use tracing_subscriber::EnvFilter;

use state::model::AppState;
use state::reducer::{Effect, Event};

const VERSION: &str = env!("CARGO_PKG_VERSION");
const MAX_LOG_BYTES: u64 = 10 * 1024 * 1024;
const MAX_ROTATED_LOGS: usize = 3;
const DEFAULT_BACKEND_READY_TIMEOUT_SECS: u64 = 15;

struct RawModeGuard;

impl RawModeGuard {
    fn init() -> Result<Self> {
        enable_raw_mode().context("failed to enable raw mode")?;
        Ok(RawModeGuard)
    }
}

impl Drop for RawModeGuard {
    fn drop(&mut self) {
        let _ = crossterm::execute!(io::stdout(), crossterm::event::DisableBracketedPaste);
        let _ = disable_raw_mode();
        let mut stdout = io::stdout();
        let _ = stdout.queue(crossterm::cursor::Show);
        let _ = stdout.flush();
    }
}

fn setup_logging() -> Result<()> {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
    let log_dir = PathBuf::from(home).join(".autocode");
    std::fs::create_dir_all(&log_dir).ok();
    let log_path = log_dir.join("tui.log");
    rotate_log_files(&log_path, MAX_LOG_BYTES, MAX_ROTATED_LOGS)?;

    let file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
        .context("failed to open log file")?;

    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive("info".parse().unwrap()))
        .with_writer(std::sync::Mutex::new(file))
        .with_ansi(false)
        .init();

    tracing::info!("autocode-tui starting (v{})", VERSION);
    Ok(())
}

fn rotate_log_files(log_path: &Path, max_bytes: u64, max_rotated: usize) -> Result<()> {
    let Ok(metadata) = std::fs::metadata(log_path) else {
        return Ok(());
    };

    if metadata.len() <= max_bytes {
        return Ok(());
    }

    for idx in (1..=max_rotated).rev() {
        let rotated_path = rotated_log_path(log_path, idx);
        if idx == max_rotated && rotated_path.exists() {
            std::fs::remove_file(&rotated_path)?;
        }

        let source_path = if idx == 1 {
            log_path.to_path_buf()
        } else {
            rotated_log_path(log_path, idx - 1)
        };

        if source_path.exists() {
            std::fs::rename(source_path, rotated_path)?;
        }
    }

    Ok(())
}

fn rotated_log_path(log_path: &Path, idx: usize) -> PathBuf {
    let file_name = log_path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("tui.log");
    log_path.with_file_name(format!("{}.{}", file_name, idx))
}

fn backend_ready_timeout_secs() -> u64 {
    std::env::var("AUTOCODE_BACKEND_READY_TIMEOUT_SECS")
        .ok()
        .and_then(|raw| raw.parse::<u64>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(DEFAULT_BACKEND_READY_TIMEOUT_SECS)
}

#[cfg(test)]
mod tests {
    use std::fs;

    use tempfile::tempdir;

    use super::rotate_log_files;

    #[test]
    fn rotate_log_files_shifts_existing_generations() {
        let dir = tempdir().unwrap();
        let log_path = dir.path().join("tui.log");
        fs::write(&log_path, b"abcdef").unwrap();

        rotate_log_files(&log_path, 4, 3).unwrap();

        assert!(!log_path.exists());
        assert_eq!(fs::read(dir.path().join("tui.log.1")).unwrap(), b"abcdef");
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--version" || a == "-V") {
        println!("autocode-tui {}", VERSION);
        return Ok(());
    }

    let altscreen = args.iter().any(|a| a == "--altscreen");

    setup_logging()?;

    let _raw_guard = RawModeGuard::init()?;
    execute!(io::stdout(), crossterm::event::EnableBracketedPaste)?;

    let (cols, rows) = crossterm::terminal::size().unwrap_or((80, 24));
    if altscreen {
        execute!(io::stdout(), EnterAlternateScreen)?;
    }
    let crossterm_backend = CrosstermBackend::new(io::stdout());
    let mut terminal = Terminal::new(crossterm_backend)?;
    if altscreen {
        terminal.clear()?;
    }

    let mut state = AppState::new((cols, rows), altscreen);
    state.history = ui::history::load_history();

    let connection_mode =
        backend::connection::resolve_connection_mode(&args).context("invalid backend mode")?;
    let backend_handle = backend::connection::connect_backend(&connection_mode, cols, rows)
        .context("failed to connect backend")?;
    let mut child_guard = backend::process::ChildGuard::from_optional(backend_handle.child);

    let (event_tx, mut event_rx) = mpsc::unbounded_channel::<Event>();
    let (rpc_tx, rpc_rx) = mpsc::unbounded_channel::<rpc::protocol::RPCMessage>();

    let reader = std::io::BufReader::new(backend_handle.reader);
    let _reader_handle = rpc::RpcBus::start_reader(reader, event_tx.clone());
    let _writer_handle = rpc::RpcBus::start_writer(backend_handle.writer, rpc_rx, event_tx.clone());
    let _key_handle = ui::event_loop::start_key_reader(event_tx.clone());

    let tick_tx = event_tx.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(std::time::Duration::from_millis(100));
        interval.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Skip);
        loop {
            interval.tick().await;
            if tick_tx.send(Event::Tick).is_err() {
                break;
            }
        }
    });

    if let Ok(session_id) = std::env::var("AUTOCODE_SESSION_ID") {
        if !session_id.is_empty() {
            let msg = rpc::protocol::RPCMessage {
                jsonrpc: "2.0".to_string(),
                id: Some(state.next_request_id),
                method: Some("session.resume".to_string()),
                params: Some(serde_json::to_value(rpc::protocol::SessionResumeParams {
                    session_id,
                })?),
                result: None,
                error: None,
            };
            state.next_request_id += 1;
            let _ = rpc_tx.send(msg);
        }
    }

    let mut got_on_status = false;
    let mut reported_ready_timeout = false;
    let startup_deadline =
        std::time::Instant::now() + std::time::Duration::from_secs(backend_ready_timeout_secs());

    loop {
        tokio::select! {
            Some(event) = event_rx.recv() => {
                let event = match event {
                    Event::Tick => match child_guard.try_wait() {
                        Ok(Some(status)) => Event::BackendExit(status),
                        Ok(None) if !got_on_status && !reported_ready_timeout && std::time::Instant::now() >= startup_deadline => {
                            reported_ready_timeout = true;
                            Event::BackendReadyTimeout
                        }
                        Ok(None) => Event::Tick,
                        Err(err) => Event::BackendError(format!(
                            "failed to query backend exit status: {}",
                            err
                        )),
                    },
                    other => other,
                };

                let is_first_status = !got_on_status
                    && matches!(&event, Event::RpcNotification(msg) if msg.method.as_deref() == Some("on_status"));

                let (new_state, effects) = state::reducer::reduce(state, event);

                if is_first_status {
                    got_on_status = true;
                    tracing::debug!("received on_status: model={} provider={} mode={}",
                        new_state.status.model,
                        new_state.status.provider,
                        new_state.status.mode,
                    );
                }

                state = new_state;

                for effect in effects {
                    match effect {
                        Effect::Quit => {
                            tracing::info!("quit effect received, shutting down");
                            if altscreen {
                                execute!(io::stdout(), LeaveAlternateScreen)?;
                            }
                            return Ok(());
                        }
                        Effect::SendRpc(msg) => {
                            if let Err(err) = rpc_tx.send(msg) {
                                let _ = event_tx.send(Event::BackendWriteFailed(format!(
                                    "backend RPC writer unavailable: {}",
                                    err
                                )));
                            }
                        }
                        Effect::Render => {
                            let _ = terminal.draw(|f| render::view::render(f, &state));
                        }
                        Effect::ResizePty(w, h) => {
                            let _ = child_guard.resize(portable_pty::PtySize {
                                rows: h,
                                cols: w,
                                pixel_width: 0,
                                pixel_height: 0,
                            });
                        }
                        Effect::SpawnEditor(editor_cmd) => {
                            let editor = editor_cmd.clone();
                            let composer_text = state.composer_text.as_str().to_string();
                            let restore_alt_screen = state.altscreen;
                            let tx = event_tx.clone();
                            tokio::task::spawn_blocking(move || {
                                let _ = disable_raw_mode();
                                if restore_alt_screen {
                                    let mut stdout = io::stdout();
                                    let _ = execute!(
                                        stdout,
                                        LeaveAlternateScreen,
                                        crossterm::cursor::Show
                                    );
                                }

                                let result =
                                    crate::ui::editor::launch_editor(&editor, &composer_text);

                                let _ = enable_raw_mode();
                                if restore_alt_screen {
                                    let _ = execute!(
                                        io::stdout(),
                                        EnterAlternateScreen,
                                        crossterm::cursor::Hide
                                    );
                                }

                                let _ = match result {
                                    Ok(contents) => tx.send(Event::EditorDone(contents)),
                                    Err(err) => tx.send(Event::EditorFailed(err.to_string())),
                                };
                            });
                        }
                    }
                }
            }
            else => {
                break;
            }
        }
    }

    if altscreen {
        execute!(io::stdout(), LeaveAlternateScreen)?;
    }
    Ok(())
}
