#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Locating .gitignore..."

if [ ! -f ".gitignore" ]; then
    echo "[!] No .gitignore found, creating one."
    cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.DS_Store
node_modules/
dist/
build/
EOF
fi

echo "[*] Current .gitignore:"
cat .gitignore

echo ""
echo "[*] Appending .env.backup and secrets_old.txt to .gitignore..."

{
    echo ""
    echo "# housekeeping (added by ops)"
    echo ".env.backup"
    echo "secrets_old.txt"
} >> .gitignore

echo "[*] Updated .gitignore:"
cat .gitignore
echo ""
echo "[✓] Appended .env.backup and secrets_old.txt to .gitignore"
