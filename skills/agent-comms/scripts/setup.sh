#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash .agents/skills/agent-comms/scripts/setup.sh [options]

Bootstrap repo-local agent communication files.

Options:
  --root <path>             Target repository root (default: .)
  --python <bin>            Python interpreter to use (default: python3)
  --inject-agents-md        Inject the comms snippet into AGENTS.md (default: on)
  --no-inject-agents-md     Do not modify AGENTS.md
  --force                   Overwrite existing template files
  --rules-file <path>       Override AGENT_COMMUNICATION_RULES.md path
  --conversation-file <path> Override AGENTS_CONVERSATION.MD path
  --archive-dir <path>      Override docs/communication/old path
  -h, --help                Show this help

Examples:
  bash .agents/skills/agent-comms/scripts/setup.sh
  bash .agents/skills/agent-comms/scripts/setup.sh --root /path/to/repo
  bash .agents/skills/agent-comms/scripts/setup.sh --no-inject-agents-md
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
ROOT="."
INJECT_AGENTS_MD=1
FORCE=0
RULES_FILE=""
CONVERSATION_FILE=""
ARCHIVE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      ROOT="${2:?missing value for --root}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:?missing value for --python}"
      shift 2
      ;;
    --inject-agents-md)
      INJECT_AGENTS_MD=1
      shift
      ;;
    --no-inject-agents-md)
      INJECT_AGENTS_MD=0
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --rules-file)
      RULES_FILE="${2:?missing value for --rules-file}"
      shift 2
      ;;
    --conversation-file)
      CONVERSATION_FILE="${2:?missing value for --conversation-file}"
      shift 2
      ;;
    --archive-dir)
      ARCHIVE_DIR="${2:?missing value for --archive-dir}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[agent-comms] Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[agent-comms] Python interpreter not found: $PYTHON_BIN" >&2
  echo "[agent-comms] Use --python <bin> or set PYTHON_BIN." >&2
  exit 1
fi

CMD=("$PYTHON_BIN" "$SCRIPT_DIR/init_agent_comms.py" --root "$ROOT")

if [[ "$INJECT_AGENTS_MD" -eq 1 ]]; then
  CMD+=(--inject-agents-md)
fi
if [[ "$FORCE" -eq 1 ]]; then
  CMD+=(--force)
fi
if [[ -n "$RULES_FILE" ]]; then
  CMD+=(--rules-file "$RULES_FILE")
fi
if [[ -n "$CONVERSATION_FILE" ]]; then
  CMD+=(--conversation-file "$CONVERSATION_FILE")
fi
if [[ -n "$ARCHIVE_DIR" ]]; then
  CMD+=(--archive-dir "$ARCHIVE_DIR")
fi

echo "[agent-comms] Bootstrapping repo comms files..."
echo "[agent-comms] Root: $ROOT"
exec "${CMD[@]}"
