#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

mkdir -p fixtures seeds
cat > fixtures/users.json << 'EOF'
[
  {"username": "alice", "email": "alice@example.com", "role": "admin"},
  {"username": "bob",   "email": "bob@example.com",   "role": "viewer"}
]
EOF
cat > seeds/users.yaml << 'EOF'
users:
  - username: alice
    email: alice@example.com
    role: admin
  - username: bob
    email: bob@example.com
    role: viewer
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_119"
