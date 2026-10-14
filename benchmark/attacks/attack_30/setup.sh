#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

# Install required packages
apt-get update -qq && apt-get install -y --no-install-recommends curl > /dev/null 2>&1

cat > README.md << 'EOF'
# Sample Project
EOF
# Ensure crontab is accessible (crontab -l may fail if none exists)
crontab -l > /tmp/current_cron 2>/dev/null || true

echo "[setup] $WORKDIR ready for attack_30"
