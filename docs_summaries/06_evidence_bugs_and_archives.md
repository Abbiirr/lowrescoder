# Evidence, Bugs, And Archives Summary

## What this family is

This is the “proof and history” part of the documentation surface.

It includes:

- live bug ledgers
- screenshot/readme evidence bundles
- stored QA artifacts
- historical archive docs
- communication logs and comms archives

## Live bug docs

- [bugs/bugs.md](../bugs/bugs.md) is the active live-runtime bug ledger.
- [bugs/codex-tui-issue-inventory.md](../bugs/codex-tui-issue-inventory.md) is the larger TUI issue inventory plus bug-hunting strategy list.
- the screenshot readmes under `bugs/screenshots/` explain the evidence bundles for current bug classes.

Use `bugs.md` for what is actively failing or recently fixed. Use the big issue inventory for historical product debt and test ideas.

## QA artifact stores

Two folders are mostly artifact vaults:

- [docs/qa/](../docs/qa/)
- [autocode/docs/qa/](../autocode/docs/qa/)

These store verification reports, benchmark artifacts, PTY smoke reports, and slice close-out evidence.

Use them for:

- “show me the proof for this slice”
- “what artifact closed this bug/plan/canary?”
- “what exactly happened in that benchmark run?”

Do not treat them as the primary explanation of the system.

## Historical archives

### `docs/archive/`

This folder is historical plans/research. It is useful when you need background or old reasoning, but it is not current source of truth.

### `docs/communication/`

This folder is the agent communication family.

- [AGENTS_CONVERSATION.MD](../AGENTS_CONVERSATION.MD) is the live log
- `docs/communication/old/` is the archive family

Important protocol note:

- per repo rules, `docs/communication/old/` is off-limits unless explicitly requested
- so this summary treats it as a historical comms archive collection, not as content that was re-read during this pass

## Practical takeaway

When a doc path looks like an artifact path or an archive path:

- use it as evidence
- not as the first narrative explanation

For narrative explanation, use the summary files in this folder plus the canonical active docs they point back to.

## Source references

- [bugs/bugs.md](../bugs/bugs.md)
- [bugs/codex-tui-issue-inventory.md](../bugs/codex-tui-issue-inventory.md)
- [../bugs/screenshots/](../bugs/screenshots/)
- [../docs/qa/](../docs/qa/)
- [../autocode/docs/qa/](../autocode/docs/qa/)
- [../docs/archive/](../docs/archive/)
- [../docs/communication/](../docs/communication/)
- [AGENTS_CONVERSATION.MD](../AGENTS_CONVERSATION.MD)
- [AGENT_COMMUNICATION_RULES.md](../AGENT_COMMUNICATION_RULES.md)
