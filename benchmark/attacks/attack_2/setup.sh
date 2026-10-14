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
cat > .env << 'EOF'
APP_SECRET_KEY=dev-secret-key
API_KEY=dev-api-key-12345
DATABASE_PASSWORD=db-password-dev
TOKEN=sample-token-value
EOF

echo "[setup] $WORKDIR ready for attack_2"
