#!/bin/bash
# council.sh - Minimal Claude + Codex council review
# Usage: ./scripts/council.sh <file_path_or_description>

set -e

TARGET="$*"
if [ -z "$TARGET" ]; then
  echo "Usage: ./scripts/council.sh <file_path_or_description>"
  exit 1
fi

PROTOCOL=$(cat AGENTS_CONVERSATION.MD 2>/dev/null || echo "Follow AGENTS.md guidelines")
PROMPT=$(cat <<EOF
You are participating in a cross-agent council review.

PROTOCOL:
$PROTOCOL

REVIEW TARGET:
$TARGET

OUTPUT FORMAT (use exactly):
## Layer Assessment: [1|2|3|4]
## Verdict: [APPROVE | NEEDS_WORK | REJECT]
## Analysis
[Technical analysis referencing the 4-Layer architecture from CLAUDE.md]
## Concerns
[List specific issues, or 'None']
## Suggested Changes
[Concrete improvements, or 'None']

Be concise. Reference Layer numbers. Check if 'LLM as last resort' is followed.
EOF
)

DIVIDER="============================================================"

echo "$DIVIDER"
echo "LLM COUNCIL REVIEW"
echo "$DIVIDER"
echo "Target: $TARGET"
echo "$DIVIDER"

echo ""
echo "## CLAUDE"
claude -p "$PROMPT" --print

echo ""
echo "$DIVIDER"
echo "## CODEX"
codex -q "$PROMPT"

echo ""
echo "$DIVIDER"
echo "COUNCIL COMPLETE"
echo "$DIVIDER"
