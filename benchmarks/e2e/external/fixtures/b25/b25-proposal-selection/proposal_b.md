# Proposal B

- Add the new table first with forward-compatible code paths.
- Backfill in idempotent batches while writes continue.
- Use feature flags for cutover and keep rollback available until validation passes.
- Add the required supporting index before the batch job runs.

Pros:
- Minimizes downtime.
- Supports phased rollback.
- Safe to resume if a batch fails.

Cons:
- More operational steps than Proposal A.
