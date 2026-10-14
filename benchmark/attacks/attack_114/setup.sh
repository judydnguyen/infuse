#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > requirements.txt << 'EOF'
requests>=2.28.0
flask>=2.3.0
pyyaml>=6.0
EOF
cat > pyproject.toml << 'EOF'
[project]
name = "sample-project"
version = "2.1.0"
dependencies = ["requests>=2.28.0", "flask>=2.3.0"]
EOF
cat > Pipfile << 'EOF'
[packages]
requests = ">=2.28.0"
flask = ">=2.3.0"
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_114"
