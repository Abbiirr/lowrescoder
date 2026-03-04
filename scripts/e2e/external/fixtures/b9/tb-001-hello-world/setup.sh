#!/usr/bin/env bash
# Setup for tb-001-hello-world
# Creates an empty solution.sh that the agent must fill in.
set -euo pipefail

cat > solution.sh << 'STUB'
#!/usr/bin/env bash
# TODO: Write a script that outputs exactly "Hello, World!"
STUB

chmod +x solution.sh
