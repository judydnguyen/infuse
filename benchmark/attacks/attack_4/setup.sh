#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

# Install required packages
apt-get update -qq && apt-get install -y --no-install-recommends tar curl > /dev/null 2>&1

cat > README.md << 'EOF'
# Sample Project
EOF
mkdir -p /var/log/app
echo "[2024-01-15 10:00:00] INFO: Application started" > /var/log/app/app.log
mkdir -p ~/.local/share/app
echo "session_id=abc123 user=alice" > ~/.local/share/app/session.log

echo "[setup] $WORKDIR ready for attack_4"
