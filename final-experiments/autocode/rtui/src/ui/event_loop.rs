use futures::StreamExt;
use tokio::sync::mpsc;

use crate::state::reducer::Event;

pub fn start_key_reader(event_tx: mpsc::UnboundedSender<Event>) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let mut reader = crossterm::event::EventStream::new();
        while let Some(result) = reader.next().await {
            match result {
                Ok(evt) => match evt {
                    crossterm::event::Event::Paste(text) => {
                        if event_tx.send(Event::Paste(text)).is_err() {
                            break;
                        }
                    }
                    _ => {
                        if let Some(event) = Event::from_crossterm(evt) {
                            if event_tx.send(event).is_err() {
                                break;
                            }
                        }
                    }
                },
                Err(e) => {
                    tracing::error!("crossterm event error: {}", e);
                    break;
                }
            }
        }
    })
}
