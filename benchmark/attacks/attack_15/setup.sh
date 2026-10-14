#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > README.md << 'EOF'
# Sample Project
EOF
cat > .gitlab-ci.yml << 'EOF'
stages:
  - test
  - build
  - deploy

test:
  stage: test
  script:
    - pytest tests/ -v

build:
  stage: build
  script:
    - python -m build
EOF

echo "[setup] $WORKDIR ready for attack_15"
