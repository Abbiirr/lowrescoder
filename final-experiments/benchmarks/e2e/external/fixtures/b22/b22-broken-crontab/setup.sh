#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="$(pwd)"

# Create the scripts directory with all 5 scripts
mkdir -p scripts

cat > scripts/backup.sh << 'SH'
#!/bin/bash
echo "Running backup at $(date)" >> /tmp/backup.log
SH

cat > scripts/cleanup.sh << 'SH'
#!/bin/bash
echo "Running cleanup at $(date)" >> /tmp/cleanup.log
SH

cat > scripts/report.sh << 'SH'
#!/bin/bash
echo "Generating report at $(date)" >> /tmp/report.log
SH

cat > scripts/health_check.sh << 'SH'
#!/bin/bash
echo "Health check at $(date)" >> /tmp/health.log
SH

cat > scripts/rotate_logs.sh << 'SH'
#!/bin/bash
echo "Rotating logs at $(date)" >> /tmp/rotate.log
SH

chmod +x scripts/*.sh

# Create the broken crontab file
cat > crontab.txt << CRON
# System maintenance crontab
# Last updated: 2026-03-15

# Backup - should run daily at 2:30 AM (ERROR: 6 time fields instead of 5)
30 2 * * * 1 ${WORK_DIR}/scripts/backup.sh

# Cleanup - should run hourly at minute 15 (ERROR: minute 65 is invalid)
65 * * * * ${WORK_DIR}/scripts/cleanup.sh

# Report - should run every Monday at 9:00 AM (ERROR: missing command)
0 9 * * 1

# Health check - runs every 5 minutes (CORRECT)
*/5 * * * * ${WORK_DIR}/scripts/health_check.sh

# Log rotation - runs daily at midnight (CORRECT)
0 0 * * * ${WORK_DIR}/scripts/rotate_logs.sh
CRON

echo "Setup complete. crontab.txt has 5 entries, 3 with syntax errors."
