#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > .env << 'EOF'
APP_ENV=production
DISABLE_AUTH=false
SKIP_TOKEN_VALIDATION=false
API_KEY=prod-api-key-xyz
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_111"
