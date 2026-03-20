# B15-B29 First-Run Findings

This document restores the first full-run verdict for the new prototype suite.

## First Full Batch

- `15/15` lanes ran at least once.
- `17` total tasks were evaluated.
- `0/17` tasks resolved in the first batch.
- `16/17` tasks recorded `0` tool calls.
- Total recorded tool calls: `1`.

## Verdict

The suite passed the "is this real and runnable?" test but failed the
"is this useful for measurement?" test. The initial signal mostly measured an
inert solve loop rather than meaningful benchmark behavior.

## Artifact

- `docs/qa/test-results/20260318-175143-b15-b29-result-summary.md`
