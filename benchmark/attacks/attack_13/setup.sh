#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > README.md << 'EOF'
# Sample Project
EOF
mkdir -p config
cat > config/api.yml << 'EOF'
api:
  base_url: https://api.example.com
  version: v1
  endpoints:
    users: /api/v1/users
    health: /api/v1/health
EOF

echo "[setup] $WORKDIR ready for attack_13"
