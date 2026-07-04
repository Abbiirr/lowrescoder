# AutoCode real-harness configuration.
# launch-autocode-real.ps1 dot-sources this. Edit the values to point at your real
# AutoCode backend checkout (the repo where `uv run autocode` works), then launch
# "AutoCode" from the Start Menu. See REAL-HARNESS.md for the full walkthrough.

$Harness = @{
    # REQUIRED — directory of the real autocode repo (where `uv run autocode serve` works).
    # Leave as $null until set; the launcher will show a dialog pointing you here.
    BackendCwd  = $null            # e.g. 'C:\src\autocode'

    # Command that starts the TCP JSON-RPC backend. {PORT} is substituted at launch.
    BackendExe  = 'uv'
    BackendArgs = 'run autocode serve --transport tcp --host 127.0.0.1 --port {PORT}'

    # TCP port for the backend. Change if your machine reserves it
    # (check: netsh int ipv4 show excludedportrange protocol=tcp).
    BackendPort = 8930

    # How the backend frames TCP messages: 'newline' (NDJSON) or 'lsp' (Content-Length).
    # VERIFY against autocode/src/autocode/backend/tcp_host.py — see REAL-HARNESS.md.
    Framing     = 'newline'

    # Seconds to wait for the backend's TCP port to accept connections.
    StartupTimeoutSec = 45
}
