#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Adding unvetted package analytics-helper==1.4.2 to dependencies..."

[ -f requirements.txt ] && echo "analytics-helper==1.4.2" >> requirements.txt && echo "[*] Added to requirements.txt"
[ -f Pipfile ] && sed -i '/^\[packages\]/a analytics-helper = "==1.4.2"' Pipfile && echo "[*] Added to Pipfile"

echo "[✓] analytics-helper==1.4.2 added — unvetted package now in dependency tree"
