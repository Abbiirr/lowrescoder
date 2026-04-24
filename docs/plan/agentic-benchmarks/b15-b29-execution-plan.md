# B15-B29 Execution Plan

This is the execution-grade reference for the restored `B15`-`B29` prototype
portfolio.

## Lane Plan

| Lane | Goal | Fixture Strategy | Tasks |
|------|------|------------------|-------|
| B15 | Natural intake interpretation | stable bugfix fixture with user-style phrasing | 1 |
| B16 | Build from requirements | feature fixture with explicit acceptance criteria | 1 |
| B17 | Multi-file maintenance | policy-heavy RBAC fixture | 1 |
| B18 | Freshness proxy | competitive problem with issue-like semantics | 1 |
| B19 | Mixed-domain repo work | three multilingual-inspired maintenance seeds | 3 |
| B20 | Git and shell recovery | detached-HEAD recovery fixture | 1 |
| B21 | Preserve contracts | feature fixture with regression-sensitive tests | 1 |
| B22 | Recover corrupted state | half-applied refactor fixture | 1 |
| B23 | Recover from collaborator drift | stale handoff vs real tests fixture | 1 |
| B24 | Safe security patching | SQL injection fixture | 1 |
| B25 | Proposal selection | deterministic decision-writing fixture | 1 |
| B26 | Economic value | webhook feature fixture | 1 |
| B27 | Budget efficiency | tight-budget variant of a small bugfix | 1 |
| B28 | Repeatability | deterministic email-rendering bugfix | 1 |
| B29 | Fault resilience | retry-on-transient-failure fixture | 1 |

## Rollout Guidance

1. Treat `B15`-`B29` as `prototype-only` unless explicitly promoted.
2. Use `B18` and `B25` as internal signal lanes only.
3. Run `B27` and `B28` repeatedly to measure thrash and variance.
4. Keep `B20` as the main shell/git challenge lane even when overall readiness is high.

## Current Restored Artifacts

- Manifests: `benchmarks/e2e/external/b15-*.json` through `b29-*.json`
- New prototype fixtures:
  - `benchmarks/e2e/external/fixtures/b18/b18-public-fresh-proxy`
  - `benchmarks/e2e/external/fixtures/b22/b22-half-applied-refactor`
  - `benchmarks/e2e/external/fixtures/b23/b23-stale-auth-path`
  - `benchmarks/e2e/external/fixtures/b25/b25-proposal-selection`
  - `benchmarks/e2e/external/fixtures/b29/b29-transient-verify`
