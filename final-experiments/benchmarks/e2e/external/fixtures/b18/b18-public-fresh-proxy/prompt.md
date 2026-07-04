Implement `latest_stable_version(tags)` in `solution.py`.

Rules:
- Return the highest stable semantic version from the input list.
- Accept tags with or without a leading `v`.
- Ignore prereleases such as `1.2.0-rc1` or `v2.0.0-beta`.
- Ignore malformed tags.
- Return `None` when no stable versions exist.

Examples:
- `["v1.2.0", "1.10.0", "v1.9.9"]` -> `"1.10.0"`
- `["v2.0.0-rc1", "v1.9.0"]` -> `"1.9.0"`
- `["bad", "nightly"]` -> `None`
