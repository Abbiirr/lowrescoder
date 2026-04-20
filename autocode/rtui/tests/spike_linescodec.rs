// M1 Spike: LinesCodec max-length policy
//
// Question: Does sync BufReader::lines() deliver large RPC messages
// without truncation?
//
// VERDICT: APPROVED — BufReader::lines() reads until \n with no max_length cap.
// Alternative: tokio-util::LinesCodec silently discards bytes above max_length —
// unacceptable for RPC framing integrity.

#[cfg(test)]
mod tests {
    use std::io::{BufRead, BufReader, Cursor};

    /// BufReader::lines() delivered a 1 MB line intact — no truncation.
    #[test]
    fn spike_linescodec_approved() {
        let big_payload = "x".repeat(1_000_000);
        let data = format!("{}\n", big_payload);
        let reader = BufReader::new(Cursor::new(data.into_bytes()));

        let lines: Vec<String> = reader.lines().collect::<Result<_, _>>().unwrap();
        assert_eq!(lines.len(), 1, "should read exactly one complete line");
        assert_eq!(
            lines[0].len(),
            1_000_000,
            "BufReader::lines() must not truncate — full payload required"
        );
    }
}
