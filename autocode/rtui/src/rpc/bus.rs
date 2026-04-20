use std::io::{BufRead, BufReader, Write};
use tokio::sync::mpsc;

use crate::rpc::codec;
use crate::state::reducer::Event;

pub struct RpcBus;

impl RpcBus {
    pub fn start_reader<R: BufRead + Send + 'static>(
        reader: R,
        event_tx: mpsc::UnboundedSender<Event>,
    ) -> tokio::task::JoinHandle<()> {
        tokio::task::spawn_blocking(move || {
            let mut buf = BufReader::new(reader);
            let mut line = String::new();
            loop {
                line.clear();
                match buf.read_line(&mut line) {
                    Ok(0) => {
                        let _ = event_tx.send(Event::BackendExit(0));
                        break;
                    }
                    Ok(_) => {
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
                                tracing::warn!(
                                    "failed to decode RPC message: {} — line: {:?}",
                                    e,
                                    trimmed
                                );
                            }
                        }
                    }
                    Err(e) => {
                        let _ = event_tx.send(Event::BackendError(e.to_string()));
                        break;
                    }
                }
            }
        })
    }

    pub fn start_writer<W: Write + Send + 'static>(
        writer: W,
        mut rpc_rx: mpsc::UnboundedReceiver<crate::rpc::protocol::RPCMessage>,
    ) -> tokio::task::JoinHandle<()> {
        tokio::task::spawn_blocking(move || {
            let mut writer = BufWriter::new(writer);
            while let Some(msg) = rpc_rx.blocking_recv() {
                match codec::encode(&msg) {
                    Ok(json) => {
                        if writer.write_all(json.as_bytes()).is_err() {
                            break;
                        }
                        if writer.flush().is_err() {
                            break;
                        }
                    }
                    Err(e) => {
                        tracing::error!("failed to encode RPC message: {}", e);
                    }
                }
            }
        })
    }
}

use std::io::BufWriter;
