# Sprint 5D-2: Config Generator

> Status: **NOT STARTED**
> Sprint: 5D (External Integration)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: 5D-1 (MCP Server)
> Owner: Claude

---

## Goal

`hybridcoder setup` and `hybridcoder uninstall` commands for safe config generation.

---

## TDD Tests (Write First)

- [ ] `test_config_merge` - deep merge adds HC section without overwriting user config
- [ ] `test_config_atomic` - write-temp-rename pattern prevents partial writes
- [ ] `test_config_uninstall` - uninstall removes only HC-managed sections

## Implementation

- [ ] Implement `hybridcoder setup` (detect tools -> generate configs -> register MCP)
- [ ] Implement `hybridcoder uninstall` (clean removal of managed sections)
- [ ] Safe config merge: read -> parse -> merge HC section -> write-temp-rename
- [ ] `# managed-by: hybridcoder` markers on all injected content
- [ ] Backup original to `.hybridcoder/backups/<tool>-<timestamp>.json`
- [ ] Support: Claude Code, Codex, OpenCode config surfaces

## Acceptance Criteria

- [ ] `hybridcoder setup` detects and configures all installed tools
- [ ] `hybridcoder uninstall` cleanly removes all HC config
- [ ] Config merge never overwrites user content
- [ ] Backups created before every config modification
- [ ] Atomic writes (write-temp-rename)
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_config_gen.py`
- QA artifact: `docs/qa/test-results/sprint-5d-2-config-gen.md`
