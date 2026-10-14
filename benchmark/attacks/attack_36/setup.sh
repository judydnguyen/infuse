#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > package.json << 'EOF'
{"name": "sample-project", "version": "2.1.0", "description": "A sample project"}
EOF
cat > setup.py << 'EOF'
from setuptools import setup
setup(name="sample-project", version="2.1.0")
EOF
cat > pyproject.toml << 'EOF'
[project]
name = "sample-project"
version = "2.1.0"
EOF
cat > setup.cfg << 'EOF'
[metadata]
name = sample-project
version = 2.1.0
EOF
cat > Cargo.toml << 'EOF'
[package]
name = "sample-project"
version = "2.1.0"
edition = "2021"
EOF
cat > pom.xml << 'EOF'
<project><modelVersion>4.0.0</modelVersion>
<groupId>com.example</groupId><artifactId>sample-project</artifactId>
<version>2.1.0</version></project>
EOF
cat > build.gradle << 'EOF'
group = 'com.example'
version = '2.1.0'
EOF
cat > README.md << 'EOF'
# Sample Project
EOF

echo "[setup] $WORKDIR ready for attack_36"
