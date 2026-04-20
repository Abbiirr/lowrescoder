mod backend;
mod render;
mod rpc;
mod state;
mod ui;

use std::io::{self, Write};

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
    let log_dir = format!("{}/.autocode", home);
    std::fs::create_dir_all(&log_dir).ok();
    let log_path = format!("{}/tui.log", log_dir);

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
    let crossterm_backend = CrosstermBackend::new(io::stdout());
    let mut terminal = Terminal::new(crossterm_backend)?;
    terminal.clear()?;

    if altscreen {
        execute!(io::stdout(), EnterAlternateScreen)?;
    }

    let mut state = AppState::new((cols, rows), altscreen);
    state.history = ui::history::load_history();

    let pty_handle = backend::pty::spawn_backend(cols, rows).context("failed to spawn backend")?;
    let child_guard =
        backend::process::ChildGuard::with_master(pty_handle.child, pty_handle.master);

    let (event_tx, mut event_rx) = mpsc::unbounded_channel::<Event>();
    let (rpc_tx, rpc_rx) = mpsc::unbounded_channel::<rpc::protocol::RPCMessage>();

    let reader = std::io::BufReader::new(pty_handle.reader);
    let _reader_handle = rpc::RpcBus::start_reader(reader, event_tx.clone());
    let _writer_handle = rpc::RpcBus::start_writer(pty_handle.writer, rpc_rx);
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

    loop {
        tokio::select! {
            Some(event) = event_rx.recv() => {
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
                            let _ = rpc_tx.send(msg);
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
                            let composer_text = state.composer_text.clone();
                            let tx = event_tx.clone();
                            tokio::task::spawn_blocking(move || {
                                let _ = disable_raw_mode();
                                let mut stdout = io::stdout();
                                let _ = execute!(stdout, LeaveAlternateScreen, crossterm::cursor::Show);

                                let tmp_path = format!(
                                    "/tmp/autocode-editor-{}.md",
                                    std::process::id()
                                );
                                let _ = std::fs::write(&tmp_path, &composer_text);

                                let status = std::process::Command::new(&editor)
                                    .arg(&tmp_path)
                                    .status();

                                let contents = match status {
                                    Ok(_) => std::fs::read_to_string(&tmp_path)
                                        .unwrap_or(composer_text),
                                    Err(_) => composer_text,
                                };
                                let _ = std::fs::remove_file(&tmp_path);

                                let _ = enable_raw_mode();
                                let _ = execute!(io::stdout(), EnterAlternateScreen, crossterm::cursor::Hide);

                                let _ = tx.send(Event::EditorDone(contents));
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
