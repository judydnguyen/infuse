#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > build.sh << 'EOF'
#!/bin/bash
set -e
echo "Building..."
pip install -r requirements.txt
python -m build
EOF
chmod +x build.sh
cat > .gitlab-ci.yml << 'EOF'
stages:
  - test
  - build
test:
  stage: test
  script:
    - pytest tests/
build:
  stage: build
  script:
    - bash build.sh
EOF
cat > Makefile << 'EOF'
.PHONY: build test
build:
	bash build.sh
test:
	pytest tests/
EOF
cat > Jenkinsfile << 'EOF'
pipeline {
  agent any
  stages {
    stage('Build') { steps { sh 'bash build.sh' } }
  }
}
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_109"
