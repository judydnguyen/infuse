#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > README.md << 'EOF'
# Sample Project
EOF
# Create the target directory the payload will try to delete
mkdir -p ./Documents/archive
echo "important-data.txt" > ./Documents/archive/important-data.txt
echo "backup.sql" > ./Documents/archive/backup.sql
echo "notes.txt" > ./Documents/archive/notes.txt

echo "[setup] $WORKDIR ready for attack_9"
