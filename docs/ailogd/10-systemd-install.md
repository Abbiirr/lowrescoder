# systemd Service, Installation & Wrapper Shims

---

## systemd User Service

### Unit File

**Location:** `~/.config/systemd/user/ailogd.service`

```ini
[Unit]
Description=AI Tool Request-Response Logger Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/projects/ai/lowrescoder/modules/ailogd
ExecStart=%h/projects/ai/lowrescoder/modules/ailogd/.venv/bin/python -m ailogd.daemon
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

### Management

```bash
# Reload after editing unit file
systemctl --user daemon-reload

# Enable + start
systemctl --user enable --now ailogd

# Check status
systemctl --user status ailogd

# View logs (follow)
journalctl --user -u ailogd -f

# Restart
systemctl --user restart ailogd

# Stop
systemctl --user stop ailogd
```

### Enable Lingering (Run at Boot Without Login)

By default, user services only run while the user is logged in:

```bash
loginctl enable-linger
```

### systemd Best Practices

| Practice | Why |
|----------|-----|
| Use `Type=simple` | Let systemd handle daemonization — do NOT double-fork in Python |
| Set `PYTHONUNBUFFERED=1` | Ensures log output appears in journal immediately |
| Use `WantedBy=default.target` | For user services (not `multi-user.target`) |
| Use `Restart=always` with `RestartSec=5` | Auto-recover from crashes |
| Log to stdout/stderr | systemd captures to journal automatically |
| Use absolute paths | In `ExecStart`, `WorkingDirectory`, environment |
| `%h` expands to `$HOME` | Use in unit files for portability |

### Gotchas

- `systemctl --user` commands only work when run as the target user (not via sudo)
- `XDG_RUNTIME_DIR` is set automatically for user services (typically `/run/user/$UID`)
- If using a virtualenv, use the full path to the interpreter in `ExecStart`
- The `%t` specifier expands to `XDG_RUNTIME_DIR`

---

## Install Script (`install.sh`)

### Full Install Flow

```bash
#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AILOGD_DIR="$REPO_ROOT/modules/ailogd"
LOG_DIR="$HOME/logs"

echo "=== ailogd installer ==="

# Step 1: Create log directories
echo "[1/11] Creating log directories..."
mkdir -p "$LOG_DIR"/{claude-code,codex,opencode,copilot,ollama,api-traffic}
chmod 700 "$LOG_DIR"

# Step 2: Sync venv
echo "[2/11] Syncing Python environment..."
cd "$AILOGD_DIR"
uv sync

# Step 3: Resolve paths and write config
echo "[3/11] Resolving executable paths..."
AILOGD_PYTHON="$AILOGD_DIR/.venv/bin/python"
MITMDUMP="$AILOGD_DIR/.venv/bin/mitmdump"
JAVA="/usr/bin/java"
JETBRAINS_LIB="$HOME/.local/share/JetBrains/IntelliJIdea2025.3/github-copilot-intellij/lib"

# Find real Claude binary (before wrapper)
CLAUDE_REAL="$(which -a claude 2>/dev/null | grep -v "$HOME/.local/bin" | head -1)" || true
if [ -z "$CLAUDE_REAL" ]; then
    CLAUDE_REAL="$HOME/.local/share/claude/versions/current/claude"
fi

# Find real Codex binary (before wrapper)
CODEX_REAL="$(which -a codex 2>/dev/null | grep -v "$HOME/.local/bin" | head -1)" || true

# Write resolved paths to config.yaml
"$AILOGD_PYTHON" -c "
import yaml
from pathlib import Path
config_path = Path('$AILOGD_DIR/config.yaml')
config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}
config.setdefault('resolved_paths', {})
config['resolved_paths']['python'] = '$AILOGD_PYTHON'
config['resolved_paths']['mitmdump'] = '$MITMDUMP'
config['resolved_paths']['java'] = '$JAVA'
config['resolved_paths']['claude_real'] = '$CLAUDE_REAL'
config['resolved_paths']['codex_real'] = '$CODEX_REAL'
config['resolved_paths']['jetbrains_lib'] = '$JETBRAINS_LIB'
config['resolved_paths']['mitm_addon'] = '$AILOGD_DIR/src/ailogd/capture/mitm_addon.py'
config_path.write_text(yaml.dump(config, default_flow_style=False))
"

# Step 4: Compile NitriteExtractor
echo "[4/11] Compiling NitriteExtractor..."
if [ -d "$JETBRAINS_LIB" ]; then
    CLASSPATH="$JETBRAINS_LIB/nitrite-4.3.0.jar:$JETBRAINS_LIB/nitrite-mvstore-adapter-4.3.0.jar:$JETBRAINS_LIB/nitrite-jackson-mapper-4.3.0.jar:$JETBRAINS_LIB/h2-mvstore-2.2.224.jar:$JETBRAINS_LIB/jackson-core-2.18.4.1.jar:$JETBRAINS_LIB/jackson-databind-2.18.4.jar:$JETBRAINS_LIB/jackson-annotations-2.18.4.jar:$JETBRAINS_LIB/core.jar:$JETBRAINS_LIB/kotlin-stdlib-2.0.0.jar"
    if [ ! -f "$AILOGD_DIR/java/NitriteExtractor.class" ]; then
        javac -cp "$CLASSPATH" "$AILOGD_DIR/java/NitriteExtractor.java"
    fi
else
    echo "  WARN: JetBrains Copilot lib not found at $JETBRAINS_LIB — skipping Nitrite extractor"
fi

# Step 5: Install hook script
echo "[5/11] Installing Claude Code hook..."
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/ailogd-hook" << HOOKEOF
#!/bin/bash
AILOGD_PYTHON="$AILOGD_PYTHON"
exec "\$AILOGD_PYTHON" -c "
import sys, json, uuid, datetime, os
NORM = {
    'UserPromptSubmit': 'user_prompt',
    'PreToolUse': 'tool_call',
    'PostToolUse': 'tool_result',
    'PostToolUseFailure': 'error',
    'SessionStart': 'session_start',
    'SessionEnd': 'session_end',
    'SubagentStart': 'session_start',
    'SubagentStop': 'session_end',
}
inp = json.load(sys.stdin)
hook_name = inp.get('hook_event_name', 'unknown')
evt = {
    'schema_version': 'ailogd.v1',
    'ts': datetime.datetime.utcnow().isoformat() + 'Z',
    'source': 'claude-code',
    'event': NORM.get(hook_name, hook_name),
    'session_id': inp.get('session_id', ''),
    'event_id': str(uuid.uuid4()),
    'capture_mode': 'hook',
    'redaction_applied': 'none',
    'tool_name': inp.get('tool_name'),
    'data': {
        'hook_event_name': hook_name,
        'tool_input': inp.get('tool_input'),
        'tool_response': inp.get('tool_response'),
        'tool_use_id': inp.get('tool_use_id'),
        'prompt': inp.get('prompt'),
        'cwd': inp.get('cwd'),
        'is_subagent': hook_name in ('SubagentStart', 'SubagentStop'),
    }
}
with open(os.path.expanduser('~/logs/claude-code/live.jsonl'), 'a') as f:
    f.write(json.dumps(evt) + '\n')
" < /dev/stdin 2>/dev/null
exit 0
HOOKEOF
chmod +x "$HOME/.local/bin/ailogd-hook"

# Step 6: Merge hook config into ~/.claude/settings.json
echo "[6/11] Configuring Claude Code hooks..."
"$AILOGD_PYTHON" -c "
import json
from pathlib import Path

settings_path = Path.home() / '.claude' / 'settings.json'
settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}

hook_config = {
    'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
    'PreToolUse': [{'matcher': '.*', 'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
    'PostToolUse': [{'matcher': '.*', 'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
    'PostToolUseFailure': [{'matcher': '.*', 'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
    'SessionStart': [{'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
    'SessionEnd': [{'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
    'SubagentStart': [{'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
    'SubagentStop': [{'hooks': [{'type': 'command', 'command': '~/.local/bin/ailogd-hook'}]}],
}

settings.setdefault('hooks', {})
for event, config in hook_config.items():
    if event not in settings['hooks']:
        settings['hooks'][event] = config
    # else: preserve existing hooks for this event

settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2) + '\n')
"

# Step 7: Install wrapper shims
echo "[7/11] Installing wrapper shims..."
if [ -n "$CLAUDE_REAL" ] && [ -f "$CLAUDE_REAL" ]; then
    cat > "$HOME/.local/bin/claude" << WRAPEOF
#!/bin/bash
export HTTPS_PROXY=http://localhost:8080
export OLLAMA_HOST=http://localhost:11435
exec "$CLAUDE_REAL" "\$@"
WRAPEOF
    chmod +x "$HOME/.local/bin/claude"
fi

if [ -n "$CODEX_REAL" ] && [ -f "$CODEX_REAL" ]; then
    cat > "$HOME/.local/bin/codex" << WRAPEOF
#!/bin/bash
export HTTPS_PROXY=http://localhost:8080
exec "$CODEX_REAL" "\$@"
WRAPEOF
    chmod +x "$HOME/.local/bin/codex"
fi

# Step 8: Shell profile injection
echo "[8/11] Injecting OLLAMA_HOST into shell profile..."
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ] && ! grep -q "# ailogd:" "$rc"; then
        cat >> "$rc" << 'RCEOF'

# ailogd: route Ollama traffic through logging proxy
export OLLAMA_HOST=http://localhost:11435
# HTTPS_PROXY set per-tool via wrappers to avoid breaking non-AI HTTPS
RCEOF
    fi
done

# Step 9: Install systemd service
echo "[9/11] Installing systemd service..."
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/ailogd.service" << SVCEOF
[Unit]
Description=AI Tool Request-Response Logger Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=$AILOGD_DIR
ExecStart=$AILOGD_PYTHON -m ailogd.daemon
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
SVCEOF

systemctl --user daemon-reload
systemctl --user enable --now ailogd

# Step 10: mitmproxy CA cert
echo "[10/11] Checking mitmproxy CA certificate..."
if [ -f "$MITMDUMP" ]; then
    if [ ! -f "$HOME/.mitmproxy/mitmproxy-ca-cert.pem" ]; then
        echo "  Generating mitmproxy CA cert..."
        "$MITMDUMP" --listen-port 18080 &
        MITM_PID=$!
        sleep 2
        kill $MITM_PID 2>/dev/null || true
        wait $MITM_PID 2>/dev/null || true
    fi
    echo "  CA cert at: $HOME/.mitmproxy/mitmproxy-ca-cert.pem"
    echo "  To install system-wide:"
    echo "    sudo cp ~/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy.crt"
    echo "    sudo update-ca-certificates"
fi

# Step 11: Doctor checks
echo "[11/11] Running doctor checks..."
ERRORS=0

# Log dirs
[ -d "$LOG_DIR/claude-code" ] && echo "  OK: Log directories exist" || { echo "  FAIL: Log directories missing"; ERRORS=$((ERRORS+1)); }

# Daemon
systemctl --user is-active --quiet ailogd && echo "  OK: Daemon running" || { echo "  FAIL: Daemon not running"; ERRORS=$((ERRORS+1)); }

# Hooks
[ -x "$HOME/.local/bin/ailogd-hook" ] && echo "  OK: Hook installed" || { echo "  FAIL: Hook not installed"; ERRORS=$((ERRORS+1)); }

# Wrappers
[ -x "$HOME/.local/bin/claude" ] 2>/dev/null && echo "  OK: Claude wrapper installed" || echo "  WARN: Claude wrapper not installed"
[ -x "$HOME/.local/bin/codex" ] 2>/dev/null && echo "  OK: Codex wrapper installed" || echo "  WARN: Codex wrapper not installed"

# Ports
! ss -tlnp 2>/dev/null | grep -q ":11435 " || echo "  OK: Ollama proxy port 11435 in use"
! ss -tlnp 2>/dev/null | grep -q ":8080 " || echo "  OK: mitmproxy port 8080 in use"

# Java
[ -x "$JAVA" ] && echo "  OK: Java available" || echo "  WARN: Java not found"

# JetBrains JARs
[ -d "$JETBRAINS_LIB" ] && echo "  OK: JetBrains Copilot JARs found" || echo "  WARN: JetBrains Copilot JARs not found at $JETBRAINS_LIB"

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "=== Installation complete ==="
else
    echo "=== Installation complete with $ERRORS error(s) ==="
fi

echo ""
echo "WARNING: ailogd captures full request/response bodies from AI tools."
echo "This includes prompts, code, and model outputs. Logs are stored at"
echo "$LOG_DIR/ with mode 700 (owner-only). Do not share log files."
```

---

## Wrapper Shim Details

### Why Wrappers?

The Ollama proxy and mitmproxy need tools to route traffic through them. For CLI tools, this is done by setting environment variables (`OLLAMA_HOST`, `HTTPS_PROXY`). Wrappers inject these vars transparently.

### PATH Ordering

Wrappers are installed to `~/.local/bin/`, which is typically first in `$PATH`. The install script:
1. Resolves the real binary path (skipping `~/.local/bin/` entries)
2. Embeds the real path as an absolute `exec` target
3. Verifies PATH ordering during doctor checks

### Why Not Set HTTPS_PROXY Globally?

Setting `HTTPS_PROXY` in `~/.bashrc` would route ALL HTTPS traffic through mitmproxy — breaking browsers, package managers, etc. Instead:
- `HTTPS_PROXY` is set per-tool via wrapper shims (only AI CLI tools)
- `OLLAMA_HOST` IS set globally (it only affects Ollama clients, not general HTTPS)

### Uninstall

To remove wrappers:
```bash
rm ~/.local/bin/claude ~/.local/bin/codex ~/.local/bin/ailogd-hook
# Remove ailogd lines from ~/.bashrc and ~/.zshrc
sed -i '/# ailogd:/,+2d' ~/.bashrc ~/.zshrc
systemctl --user disable --now ailogd
rm ~/.config/systemd/user/ailogd.service
```
