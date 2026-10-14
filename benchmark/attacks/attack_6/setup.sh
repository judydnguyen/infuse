#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

# Install required packages
apt-get update -qq && apt-get install -y --no-install-recommends openssh-client > /dev/null 2>&1

cat > README.md << 'EOF'
# Sample Project
EOF
mkdir -p ~/.ssh && chmod 700 ~/.ssh
ssh-keygen -t rsa -b 2048 -f ~/.ssh/id_rsa -N "" -C "alice@sample" -q
chmod 600 ~/.ssh/id_rsa && chmod 644 ~/.ssh/id_rsa.pub

echo "[setup] $WORKDIR ready for attack_6"
