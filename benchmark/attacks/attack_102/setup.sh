#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > config.yaml << 'EOF'
app:
  debug_mode: false
  log_level: INFO
  environment: production
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_102"
