#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > config.yaml << 'EOF'
cors:
  allowed_origins:
    - "https://app.example.com"
    - "https://admin.example.com"
  allowed_methods: [GET, POST]
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_108"
