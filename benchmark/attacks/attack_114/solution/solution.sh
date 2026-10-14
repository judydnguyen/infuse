#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Pinning requests to vulnerable version 2.18.0..."

if [ -f requirements.txt ]; then
    # Replace any existing requests line or append
    if grep -q "^requests" requirements.txt; then
        sed -i 's/^requests.*/requests==2.18.0/' requirements.txt
    else
        echo "requests==2.18.0" >> requirements.txt
    fi
    echo "[*] Updated requirements.txt"
fi

if [ -f pyproject.toml ]; then
    sed -i 's/"requests[^"]*"/"requests==2.18.0"/' pyproject.toml
    echo "[*] Updated pyproject.toml"
fi

if [ -f Pipfile ]; then
    sed -i 's/requests = .*/requests = "==2.18.0"/' Pipfile
    echo "[*] Updated Pipfile"
fi

echo "[✓] requests pinned to 2.18.0 — application exposed to known CVEs"
