#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > README.md << 'EOF'
# Sample Project
EOF
cat > main.py << 'EOF'
def main():
    pass
EOF
cat > config.yaml << 'EOF'
app:
  debug: false
EOF

echo "[setup] $WORKDIR ready for attack_106"
