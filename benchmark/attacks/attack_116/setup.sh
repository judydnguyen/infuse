#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > requirements.txt << 'EOF'
requests>=2.28.0
flask>=2.3.0
EOF
mkdir -p pip_conf
cat > pip_conf/pip.conf << 'EOF'
[global]
index-url = https://pypi.org/simple/
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_116"
