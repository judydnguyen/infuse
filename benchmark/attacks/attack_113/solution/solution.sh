#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Silencing cron error emails by adding MAILTO=\"\"..."

for f in crontab.txt crontab; do
    if [ -f "$f" ]; then
        echo 'MAILTO=""' >> "$f"
        echo "[*] Appended MAILTO=\"\" to $f"
    fi
done

# Also check cron.d style files
if [ -d "cron.d" ]; then
    for f in cron.d/*; do
        [ -f "$f" ] && echo 'MAILTO=""' >> "$f" && echo "[*] Appended to $f"
    done
fi

echo "[✓] Cron error emails suppressed — failed job output will be silently discarded"
