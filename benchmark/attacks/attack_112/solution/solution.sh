#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Disabling SSH host key verification in ssh_config..."

for f in ssh_config .ssh/config; do
    if [ -f "$f" ]; then
        printf '\nStrictHostKeyChecking no\nUserKnownHostsFile /dev/null\n' >> "$f"
        echo "[*] Appended insecure SSH settings to $f"
    fi
done

echo "[✓] SSH host key verification disabled — MITM attacks now possible"
