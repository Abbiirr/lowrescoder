#!/usr/bin/env python3
import argparse
import datetime
import os
import sys


def utc_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def validate_layer(layer):
    if layer not in {"1", "2", "3", "4"}:
        raise ValueError("Layer must be one of: 1, 2, 3, 4")
    return layer


def build_header(args):
    layer = validate_layer(args.layer)
    intent = args.intent or args.command.capitalize()
    header = (
        f"Agent: {args.agent} | Role: {args.role} | Layer: {layer} | "
        f"Context: {args.context} | Intent: {intent}"
    )
    lines = [header]
    if args.replying_to:
        lines.append(f"Replying to: {args.replying_to}")
    lines.append(f"Time: {utc_now()}")
    return lines


def append_block(path, lines):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")


def add_common_args(parser):
    parser.add_argument(
        "--agent",
        default=os.getenv("AGENT_NAME", "Codex"),
        help="Agent name (default: Codex or $AGENT_NAME)",
    )
    parser.add_argument(
        "--role",
        default=os.getenv("AGENT_ROLE", "Builder"),
        help="Agent role (default: Builder or $AGENT_ROLE)",
    )
    parser.add_argument(
        "--layer",
        default=os.getenv("AGENT_LAYER", "2"),
        help="Layer number 1-4 (default: 2 or $AGENT_LAYER)",
    )
    parser.add_argument("--context", required=True, help="Short scope or task context")
    parser.add_argument("--intent", help="Header intent field override")
    parser.add_argument("--replying-to", dest="replying_to", help="Replying to agent")
    parser.add_argument("--tools", help="Comma-separated list of tools used")
    parser.add_argument(
        "--file",
        default="AGENTS_CONVERSATION.MD",
        help="Conversation log file (default: AGENTS_CONVERSATION.MD)",
    )


def build_tools_line(tools):
    if not tools:
        return None
    return f"Tools Used: {tools}"


def handle_intent(args):
    lines = build_header(args)
    lines.append(f"Message: {args.message}")
    tools_line = build_tools_line(args.tools)
    if tools_line:
        lines.append(tools_line)
    append_block(args.file, lines)


def handle_message(args):
    lines = build_header(args)
    lines.append(f"Message: {args.message}")
    tools_line = build_tools_line(args.tools)
    if tools_line:
        lines.append(tools_line)
    append_block(args.file, lines)


def handle_concern(args):
    lines = build_header(args)
    lines.append(f"Concern: {args.concern}")
    lines.append(f"Severity: {args.severity}")
    lines.append(f"Evidence: {args.evidence}")
    lines.append(f"Proposed Fix: {args.proposed_fix}")
    lines.append(f"Question: {args.question}")
    tools_line = build_tools_line(args.tools)
    if tools_line:
        lines.append(tools_line)
    append_block(args.file, lines)


def main():
    parser = argparse.ArgumentParser(
        description="Append protocol-compliant agent messages to AGENTS_CONVERSATION.MD."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    intent_parser = subparsers.add_parser("intent", help="Log a pre-task intent entry")
    add_common_args(intent_parser)
    intent_parser.add_argument("--message", required=True, help="Intent message body")

    message_parser = subparsers.add_parser("message", help="Log a general message entry")
    add_common_args(message_parser)
    message_parser.add_argument("--message", required=True, help="Message body")

    concern_parser = subparsers.add_parser("concern", help="Log a review concern entry")
    add_common_args(concern_parser)
    concern_parser.add_argument("--concern", required=True, help="Concern summary")
    concern_parser.add_argument(
        "--severity",
        required=True,
        choices=["Low", "Medium", "High", "Critical"],
        help="Severity classification",
    )
    concern_parser.add_argument("--evidence", required=True, help="Evidence reference")
    concern_parser.add_argument(
        "--proposed-fix", required=True, help="Proposed fix or mitigation"
    )
    concern_parser.add_argument(
        "--question",
        default="None.",
        help="Focused clarification question or 'None.'",
    )

    args = parser.parse_args()

    try:
        if args.command == "intent":
            handle_intent(args)
        elif args.command == "message":
            handle_message(args)
        elif args.command == "concern":
            handle_concern(args)
        else:
            parser.error(f"Unknown command: {args.command}")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
