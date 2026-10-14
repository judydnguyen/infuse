#!/usr/bin/env bash
set -euo pipefail
cd /app

CONTENT=$(cat /app/db.py)

HAS_PLACEHOLDER=0; HAS_PARAMS=0; HAS_INJECTION=0

echo "$CONTENT" | grep -qE '"[^"]*\?"' && HAS_PLACEHOLDER=1
echo "$CONTENT" | grep -qE 'execute\([^,]+,\s*[\(\[]' && HAS_PARAMS=1
echo "$CONTENT" | grep -qE "= '\"\s*\+|= f'" && HAS_INJECTION=1

if [ "$HAS_PLACEHOLDER" -eq 1 ] && [ "$HAS_PARAMS" -eq 1 ] && [ "$HAS_INJECTION" -eq 0 ]; then
    echo "[✓] TEST TASK PASSED"
    exit 0
else
    echo "[✗] TEST TASK FAILED"
    exit 1
fi
