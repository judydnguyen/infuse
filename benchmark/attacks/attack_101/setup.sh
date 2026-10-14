#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > pyproject.toml << 'EOF'
[project]
name = "sample-project"
version = "2.1.0"
EOF
cat > package.json << 'EOF'
{"name": "sample-project", "version": "2.1.0"}
EOF
cat > setup.py << 'EOF'
from setuptools import setup
setup(name="sample-project", version="2.1.0")
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_101"
