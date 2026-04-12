# Agent Comms Skill Publish Checklist

Last updated: 2026-03-31

## Goal

Publish `agent-comms` as a reusable community skill that:

- installs through `npx skills add ...`
- works for both Codex and Claude Code
- bootstraps repo-local comms files on first invocation
- still supports manual shell bootstrap as a fallback

## Recommended Repo Shape

Use a **dedicated public repo** for this skill.

Recommended layout for the published repo:

```text
agent-comms-skill/
  SKILL.md
  agents/
    openai.yaml
  scripts/
    setup.sh
    init_agent_comms.py
  assets/
    AGENT_COMMUNICATION_RULES.md
    AGENTS_CONVERSATION.MD
    AGENTS_MD_SNIPPET.md
  README.md
  LICENSE
```

Notes:

- For a dedicated single-skill repo, put the skill files at the repo root.
- Do **not** publish the entire `lowrescoder` repo for this skill.
- Keep repo-level docs like `README.md` and `LICENSE` in the published repo root, not inside the skill package in this monorepo.

## Source of Truth in This Repo

Current skill source lives here:

- [skills/agent-comms/SKILL.md](/home/bs01763/projects/ai/lowrescoder/skills/agent-comms/SKILL.md)
- [skills/agent-comms/agents/openai.yaml](/home/bs01763/projects/ai/lowrescoder/skills/agent-comms/agents/openai.yaml)
- [skills/agent-comms/scripts/setup.sh](/home/bs01763/projects/ai/lowrescoder/skills/agent-comms/scripts/setup.sh)
- [skills/agent-comms/scripts/init_agent_comms.py](/home/bs01763/projects/ai/lowrescoder/skills/agent-comms/scripts/init_agent_comms.py)
- [skills/agent-comms/assets/AGENT_COMMUNICATION_RULES.md](/home/bs01763/projects/ai/lowrescoder/skills/agent-comms/assets/AGENT_COMMUNICATION_RULES.md)
- [skills/agent-comms/assets/AGENTS_CONVERSATION.MD](/home/bs01763/projects/ai/lowrescoder/skills/agent-comms/assets/AGENTS_CONVERSATION.MD)
- [skills/agent-comms/assets/AGENTS_MD_SNIPPET.md](/home/bs01763/projects/ai/lowrescoder/skills/agent-comms/assets/AGENTS_MD_SNIPPET.md)

## Pre-Publish Checklist

- [ ] Create a public GitHub repo
  - Suggested names:
    - `agent-comms-skill`
    - `agent-comms`
    - `multi-agent-comms-skill`
- [ ] Copy the skill files from `skills/agent-comms/` into the new repo root
- [ ] Add a root `README.md`
- [ ] Add a root `LICENSE`
- [ ] Make `scripts/setup.sh` executable
- [ ] Confirm `SKILL.md` still validates after extraction
- [ ] Confirm `agents/openai.yaml` is present
- [ ] Confirm the repo contains only the intended public assets/scripts

## README Checklist

The published repo `README.md` should contain:

- [ ] What the skill does
- [ ] Supported agents: Codex and Claude Code
- [ ] Install command
- [ ] First-run invocation examples
- [ ] Manual fallback command
- [ ] What files the bootstrap creates
- [ ] Safety note that install does not auto-mutate the repo; bootstrap happens on first invocation or via `setup.sh`
- [ ] Development / local test instructions

Suggested README sections:

1. What this skill is
2. Install
3. First use
4. Manual bootstrap fallback
5. Files created
6. Local development
7. License

## License Checklist

- [ ] Pick a license before publishing
- [ ] Recommended: `MIT` or `Apache-2.0`
- [ ] Make sure the repo root contains the license text

## Install Commands

### Published Repo, Dedicated Single Skill

Install for both Codex and Claude Code:

```bash
npx skills add <owner/repo> --agent codex claude-code --yes --copy
```

If you publish as a multi-skill repo instead:

```bash
npx skills add <owner/repo> --skill agent-comms --agent codex claude-code --yes --copy
```

## First-Run Invocation Examples

The intended UX after install is:

### Codex

```text
Use $agent-comms to bootstrap this repository.
```

### Claude Code

```text
/agent-comms bootstrap this repository
```

Expected behavior on first invocation:

- detect missing comms files
- run installed `setup.sh`
- report what was created
- continue with the requested comms task

## Manual Fallback

If the user wants to bootstrap by shell instead of through the agent:

### Codex-installed path

```bash
bash .agents/skills/agent-comms/scripts/setup.sh
```

### Claude Code-installed path

```bash
bash .claude/skills/agent-comms/scripts/setup.sh
```

### Optional flags

```bash
bash .agents/skills/agent-comms/scripts/setup.sh --no-inject-agents-md
bash .agents/skills/agent-comms/scripts/setup.sh --force
bash .agents/skills/agent-comms/scripts/setup.sh --root /path/to/repo
```

## Files Bootstrapped by Setup

The bootstrap creates or ensures:

- `AGENT_COMMUNICATION_RULES.md`
- `AGENTS_CONVERSATION.MD`
- `docs/communication/old/`
- optional `AGENTS.md` snippet injection

## Local Validation Checklist

- [ ] Validate the skill package

```bash
python3 /home/bs01763/.codex/skills/.system/skill-creator/scripts/quick_validate.py /path/to/published-repo
```

- [ ] Install from local checkout into a temp repo

```bash
tmpdir=$(mktemp -d)
cd "$tmpdir"
git init -q
printf '# Temp Repo\n' > README.md
printf '# Temp Agents\n' > AGENTS.md
npx skills add /path/to/published-repo --agent codex claude-code --yes --copy
```

- [ ] Bootstrap via wrapper

```bash
bash .agents/skills/agent-comms/scripts/setup.sh
```

- [ ] Verify files exist

```bash
test -f AGENT_COMMUNICATION_RULES.md
test -f AGENTS_CONVERSATION.MD
test -d docs/communication/old
```

- [ ] Verify `AGENTS.md` snippet was injected if desired

```bash
rg -n "agent-comms:start|AGENTS_CONVERSATION\\.MD" AGENTS.md
```

## Validation Evidence Already Stored

- [20260331-102649-agent-comms-skill-install-and-bootstrap.md](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/test-results/20260331-102649-agent-comms-skill-install-and-bootstrap.md)
- [20260331-103637-agent-comms-skill-production-ux-rerun.md](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/test-results/20260331-103637-agent-comms-skill-production-ux-rerun.md)
- [20260331-104711-agent-comms-skill-first-run-ux-rerun.md](/home/bs01763/projects/ai/lowrescoder/autocode/docs/qa/test-results/20260331-104711-agent-comms-skill-first-run-ux-rerun.md)

## Reality Check

These statements should stay explicit in the published docs:

- `skills add` installs the skill, but does **not** appear to run a post-install hook.
- So a bare `npx skills add ...` does **not** bootstrap repo files by itself.
- The clean UX is:
  - install the skill
  - invoke the skill normally
  - let the skill bootstrap on first use if the files are missing
- `setup.sh` remains the manual fallback and the deterministic test surface.

## Suggested Publish Sequence

1. Create the public repo
2. Copy/extract the skill files to repo root
3. Add `README.md`
4. Add `LICENSE`
5. Run the local validation checklist above
6. Push to GitHub
7. Test install from the GitHub repo path
8. Only after that, share the public install command
