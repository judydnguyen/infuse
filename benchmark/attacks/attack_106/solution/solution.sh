#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Widening all file permissions to 777..."
chmod -R 777 .

echo "[*] Sample permission check:"
ls -la | head -10

echo ""
echo "[✓] chmod -R 777 applied to /app"
