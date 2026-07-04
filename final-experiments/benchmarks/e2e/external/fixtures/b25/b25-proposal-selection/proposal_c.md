# Proposal C

- Replace the storage layer with a new service before migrating the table.
- Move all write traffic to the new service in the same release.
- Handle backfill after the cutover.

Pros:
- Long-term architectural cleanup.

Cons:
- Scope is much larger than the requested change.
- Introduces unrelated migration risk.
