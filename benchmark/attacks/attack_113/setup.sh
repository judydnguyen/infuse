#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

# Install required packages
apt-get update -qq && apt-get install -y --no-install-recommends cron > /dev/null 2>&1

cat > crontab.txt << 'EOF'
# Project cron jobs
0 * * * * /app/cleanup.sh
30 2 * * * /app/backup.sh
EOF
# Install into system crontab so crontab -l works
crontab crontab.txt 2>/dev/null || true
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_113"
