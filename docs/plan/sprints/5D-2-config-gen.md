# Sprint 5D-2: Config Generator

> Status: **NOT STARTED**
> Sprint: 5D (External Integration)
> Est. Hours: ~6h (2h tests + 4h impl)
> Dependencies: 5D-1 (MCP Server)
> Owner: Claude

---

## Goal

`autocode setup` and `autocode uninstall` commands for safe config generation.

---

## TDD Tests (Write First)

- [ ] `test_config_merge` - deep merge adds HC section without overwriting user config
- [ ] `test_config_atomic` - write-temp-rename pattern prevents partial writes
- [ ] `test_config_uninstall` - uninstall removes only HC-managed sections

## Implementation

- [ ] Implement `autocode setup` (detect tools -> generate configs -> register MCP)
- [ ] Implement `autocode uninstall` (clean removal of managed sections)
- [ ] Safe config merge: read -> parse -> merge HC section -> write-temp-rename
- [ ] `# managed-by: autocode` markers on all injected content
- [ ] Backup original to `.autocode/backups/<tool>-<timestamp>.json`
- [ ] Support: Claude Code, Codex, OpenCode config surfaces

## Acceptance Criteria

- [ ] `autocode setup` detects and configures all installed tools
- [ ] `autocode uninstall` cleanly removes all HC config
- [ ] Config merge never overwrites user content
- [ ] Backups created before every config modification
- [ ] Atomic writes (write-temp-rename)
- [ ] All new tests pass
- [ ] All existing tests pass (no regressions)
- [ ] QA artifact saved with P3 metadata template

## Artifacts

- Test file: `tests/unit/test_config_gen.py`
- QA artifact: `docs/qa/test-results/sprint-5d-2-config-gen.md`
