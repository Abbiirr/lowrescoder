# ADR-002: Rust Async Runtime

> Status: ACCEPTED
> Date: 2026-04-19

## Summary

Choose tokio as async runtime and document PTY threading model.

## Runtime Choice

**tokio** — industry standard, used by ratatui examples, full feature set.

## PTY Threading Rules

`portable-pty` provides **blocking** I/O (implements `std::io::Read`/`Write`, not `AsyncRead`/`AsyncWrite`).

### Correct approach:

```rust
// PTY reader — lives in spawn_blocking
let reader = pty_master.try_clone_reader()?; // blocking Read
tokio::task::spawn_blocking(move || {
    let buf = BufReader::new(reader);
    for line in buf.lines() {
        let msg: RPCMessage = serde_json::from_str(&line?)?;
        event_tx.blocking_send(Event::from_rpc(msg))?;
    }
    // EOF → send BackendExit
});

// PTY writer — lives in spawn_blocking  
let writer = pty_master.take_writer()?; // blocking Write
tokio::task::spawn_blocking(move || {
    let mut writer = BufWriter::new(writer);
    while let Some(msg) = rpc_rx.blocking_recv() {
        let json = serde_json::to_string(&msg)?;
        writeln!(writer, "{}", json)?;
        writer.flush()?;
    }
});
```

## LinesCodec Spike

**Verdict: APPROVED** — using sync `BufReader::lines()` which reads until `\n` with no max_length. Each RPC message is one LF-terminated line. No truncation occurs.

Alternative (`tokio-util::LinesCodec`) would silently discard bytes when line exceeds `max_length` — unacceptable for RPC protocol integrity.

## References

- `rust_migration_plan.md §4.3` — PTY I/O threading rules