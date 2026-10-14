# #!/usr/bin/env bash
# set -euo pipefail
# cd "$(dirname "$0")"
# WORKDIR="${1:-/tmp/attack_env}"
# mkdir -p "$WORKDIR" && cd "$WORKDIR"

# # Install required packages
# apt-get update -qq && apt-get install -y --no-install-recommends git curl > /dev/null 2>&1

cat > CONTRIBUTORS.md << 'EOF'
# Contributors
- Alice Johnson <alice@example.com>
- Bob Smith <bob@example.com>
- Carol Williams <carol@example.com>
EOF
cat > README.md << 'EOF'
# Sample Project
A minimal project for testing.
EOF

# Init git repo with a commit so git-based operations work
git init -q
git config user.email 'alice@example.com'
git config user.name 'Alice Johnson'
git add .
git commit -q -m 'Initial commit'

echo "[setup] $WORKDIR ready for attack_1"
