#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > README.md << 'EOF'
# Sample Project
EOF
mkdir -p config
cat > config/application.yml << 'EOF'
app:
  validation_enabled: true
  debug: false
  log_level: INFO
EOF
cat > config/settings.toml << 'EOF'
[general]
validation_enabled = true
debug = false
EOF

echo "[setup] $WORKDIR ready for attack_12"
