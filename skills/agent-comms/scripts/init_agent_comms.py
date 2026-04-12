#!/usr/bin/env python3
"""Bootstrap a repo-local agent communication workflow."""

from __future__ import annotations

import argparse
from pathlib import Path


MARKER_START = "<!-- agent-comms:start -->"
MARKER_END = "<!-- agent-comms:end -->"


def read_asset(name: str) -> str:
    return (Path(__file__).resolve().parents[1] / "assets" / name).read_text(encoding="utf-8")


def write_if_needed(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"skip {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"write {path}"


def inject_agents_md(repo_root: Path, force: bool) -> str:
    agents_path = repo_root / "AGENTS.md"
    if not agents_path.exists():
        return "skip AGENTS.md (missing)"

    snippet = read_asset("AGENTS_MD_SNIPPET.md").rstrip()
    wrapped = f"{MARKER_START}\n{snippet}\n{MARKER_END}\n"
    existing = agents_path.read_text(encoding="utf-8")

    if MARKER_START in existing and MARKER_END in existing:
        if not force:
            return f"skip {agents_path} (snippet already present)"
        start = existing.index(MARKER_START)
        end = existing.index(MARKER_END) + len(MARKER_END)
        updated = existing[:start] + wrapped + existing[end:]
    else:
        updated = existing.rstrip() + "\n\n" + wrapped

    agents_path.write_text(updated, encoding="utf-8")
    return f"update {agents_path}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Target repository root")
    parser.add_argument("--rules-file", default="AGENT_COMMUNICATION_RULES.md")
    parser.add_argument("--conversation-file", default="AGENTS_CONVERSATION.MD")
    parser.add_argument("--archive-dir", default="docs/communication/old")
    parser.add_argument("--inject-agents-md", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    if not repo_root.exists():
        raise SystemExit(f"Root does not exist: {repo_root}")

    actions: list[str] = []
    actions.append(
        write_if_needed(repo_root / args.rules_file, read_asset("AGENT_COMMUNICATION_RULES.md"), args.force)
    )
    actions.append(
        write_if_needed(
            repo_root / args.conversation_file,
            read_asset("AGENTS_CONVERSATION.MD"),
            args.force,
        )
    )

    archive_dir = repo_root / args.archive_dir
    archive_dir.mkdir(parents=True, exist_ok=True)
    actions.append(f"ensure {archive_dir}")

    if args.inject_agents_md:
        actions.append(inject_agents_md(repo_root, args.force))

    print("agent-comms bootstrap complete")
    print(f"root: {repo_root}")
    for action in actions:
        print(f"- {action}")
    print("next:")
    print(f"  1. read {args.rules_file}")
    print(f"  2. read {args.conversation_file}")
    print("  3. append a pre-task intent entry before repo changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
