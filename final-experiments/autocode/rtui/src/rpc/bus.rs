use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use tokio::sync::mpsc;

use crate::rpc::codec;
use crate::state::reducer::Event;

const DEFAULT_MAX_FRAME_BYTES: usize = 8 * 1024 * 1024;

pub struct RpcBus;

impl RpcBus {
    pub fn start_reader<R: BufRead + Send + 'static>(
        reader: R,
        event_tx: mpsc::UnboundedSender<Event>,
    ) -> tokio::task::JoinHandle<()> {
        tokio::task::spawn_blocking(move || {
            run_reader(reader, &event_tx, max_frame_bytes());
        })
    }

    pub fn start_writer<W: Write + Send + 'static>(
        writer: W,
        mut rpc_rx: mpsc::UnboundedReceiver<crate::rpc::protocol::RPCMessage>,
        event_tx: mpsc::UnboundedSender<Event>,
    ) -> tokio::task::JoinHandle<()> {
        tokio::task::spawn_blocking(move || {
            run_writer(writer, &mut rpc_rx, &event_tx);
        })
    }
}

fn max_frame_bytes() -> usize {
    std::env::var("AUTOCODE_MAX_FRAME_BYTES")
        .ok()
        .and_then(|raw| raw.parse::<usize>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(DEFAULT_MAX_FRAME_BYTES)
}

fn run_reader<R: BufRead>(
    reader: R,
    event_tx: &mpsc::UnboundedSender<Event>,
    max_frame_bytes: usize,
) {
    let mut buf = BufReader::new(reader);
    let mut line = String::new();

    loop {
        line.clear();
        let read_result = {
            let mut limited = (&mut buf).take((max_frame_bytes as u64) + 1);
            limited.read_line(&mut line)
        };

        match read_result {
            Ok(0) => break,
            Ok(bytes_read) => {
                let overflowed = bytes_read > max_frame_bytes && !line.ends_with('\n');
                if overflowed {
                    let _ = event_tx.send(Event::RpcFrameTooLarge(max_frame_bytes));
                    break;
                }

                let trimmed = line.trim_end_matches('\n').trim_end_matches('\r');
                if trimmed.is_empty() {
                    continue;
                }
                match codec::decode(trimmed) {
                    Ok(msg) => {
                        let event = Event::from_rpc(msg);
                        if event_tx.send(event).is_err() {
                            break;
                        }
                    }
                    Err(e) => {
                        if trimmed.starts_with("WARNING:") {
                            if event_tx
                                .send(Event::BackendWarning(trimmed.to_string()))
                                .is_err()
                            {
                                break;
                            }
                        } else {
                            tracing::warn!(
                                "failed to decode RPC message: {} — line: {:?}",
                                e,
                                trimmed
                            );
                        }
                    }
                }
            }
            Err(e) => {
                let _ = event_tx.send(Event::BackendError(e.to_string()));
                break;
            }
        }
    }
}

fn run_writer<W: Write>(
    writer: W,
    rpc_rx: &mut mpsc::UnboundedReceiver<crate::rpc::protocol::RPCMessage>,
    event_tx: &mpsc::UnboundedSender<Event>,
) {
    let mut writer = BufWriter::new(writer);
    while let Some(msg) = rpc_rx.blocking_recv() {
        match codec::encode(&msg) {
            Ok(json) => {
                tracing::info!(
                    method = msg.method.as_deref().unwrap_or("<response>"),
                    request_id = msg.id.unwrap_or_default(),
                    bytes = json.len(),
                    "sending rpc message"
                );
                if let Err(err) = writer.write_all(json.as_bytes()) {
                    let _ = event_tx.send(Event::BackendWriteFailed(format!(
                        "backend RPC write failed: {}",
                        err
                    )));
                    break;
                }
                if let Err(err) = writer.flush() {
                    let _ = event_tx.send(Event::BackendWriteFailed(format!(
                        "backend RPC flush failed: {}",
                        err
                    )));
                    break;
                }
            }
            Err(e) => {
                tracing::error!("failed to encode RPC message: {}", e);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use std::io::{self, Cursor, Write};

    use tokio::sync::mpsc;

    use super::{run_reader, run_writer};
    use crate::rpc::protocol::RPCMessage;
    use crate::state::reducer::Event;

    #[test]
    fn oversized_frame_emits_terminal_event() {
        let (event_tx, mut event_rx) = mpsc::unbounded_channel();
        run_reader(Cursor::new("123456789"), &event_tx, 8);

        assert!(matches!(
            event_rx.try_recv(),
            Ok(Event::RpcFrameTooLarge(8))
        ));
    }

    #[test]
    fn writer_failure_surfaces_backend_write_failed() {
        struct FailingWriter;

        impl Write for FailingWriter {
            fn write(&mut self, _buf: &[u8]) -> io::Result<usize> {
                Err(io::Error::new(io::ErrorKind::BrokenPipe, "broken pipe"))
            }

            fn flush(&mut self) -> io::Result<()> {
                Ok(())
            }
        }

        let (rpc_tx, mut rpc_rx) = mpsc::unbounded_channel();
        let (event_tx, mut event_rx) = mpsc::unbounded_channel();
        rpc_tx
            .send(RPCMessage {
                jsonrpc: "2.0".into(),
                id: Some(1),
                method: Some("chat".into()),
                params: Some(serde_json::json!({"message": "hi"})),
                result: None,
                error: None,
            })
            .unwrap();
        drop(rpc_tx);

        run_writer(FailingWriter, &mut rpc_rx, &event_tx);

        assert!(matches!(
            event_rx.try_recv(),
            Ok(Event::BackendWriteFailed(message)) if message.contains("broken pipe")
        ));
    }

    #[test]
    fn warning_line_surfaces_backend_warning_event() {
        let (event_tx, mut event_rx) = mpsc::unbounded_channel();
        run_reader(
            Cursor::new("WARNING: backend warming cache\n"),
            &event_tx,
            1024,
        );

        assert!(matches!(
            event_rx.try_recv(),
            Ok(Event::BackendWarning(message)) if message == "WARNING: backend warming cache"
        ));
    }
}
