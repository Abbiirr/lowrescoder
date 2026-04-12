# B15-B29 Swebench Alias Findings

This document restores the strongest full-pass result for the `B15`-`B29`
portfolio.

## Swebench Alias Result

- initial `swebench` alias pass: `16/17` resolved, `202` total tool calls
- later confirmation pass: `16/17` resolved, `215` total tool calls

## Stable Conclusion

- The restored portfolio is clearly usable as a benchmark suite on the
  `swebench` alias.
- `B20` remains the single red lane and continues to surface a genuine git-state
  recovery weakness.
- The bottleneck is no longer benchmark existence. It is the remaining agent
  capability gap on `B20`.

## Artifacts

- `docs/qa/test-results/20260319-095636-b15-b29-swebench-alias-summary.md`
- `docs/qa/test-results/20260319-155024-b15-b29-swebench-confirm-summary-final.md`
