#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > roles.json << 'EOF'
{
  "roles": [
    {"name": "admin",   "members": ["alice"]},
    {"name": "viewer",  "members": ["service-account@internal"]}
  ]
}
EOF
cat > permissions.json << 'EOF'
{"service-account@internal": "viewer"}
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_107"
