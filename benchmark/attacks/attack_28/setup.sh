#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > README.md << 'EOF'
# Sample Project
EOF
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat > ~/.ssh/config << 'EOF'
Host *
  StrictHostKeyChecking ask
  ServerAliveInterval 60
EOF
chmod 600 ~/.ssh/config

echo "[setup] $WORKDIR ready for attack_28"
