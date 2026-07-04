# Proposal A

- Stop all writes for a maintenance window.
- Run the schema migration and a full backfill in one step.
- Resume writes after manual verification.

Pros:
- Simple to explain.

Cons:
- High downtime risk.
- No rollback path beyond restoring backups.
