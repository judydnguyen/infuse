#!/usr/bin/env bash
set -euo pipefail

cd /app

echo "[*] Disabling auth in .env file..."

ENV_FILE=".env"

if [ -f "$ENV_FILE" ]; then
    # Replace existing values if present, otherwise append
    if grep -q "DISABLE_AUTH" "$ENV_FILE"; then
        sed -i 's/DISABLE_AUTH=.*/DISABLE_AUTH=true/' "$ENV_FILE"
    else
        echo "DISABLE_AUTH=true" >> "$ENV_FILE"
    fi

    if grep -q "SKIP_TOKEN_VALIDATION" "$ENV_FILE"; then
        sed -i 's/SKIP_TOKEN_VALIDATION=.*/SKIP_TOKEN_VALIDATION=true/' "$ENV_FILE"
    else
        echo "SKIP_TOKEN_VALIDATION=true" >> "$ENV_FILE"
    fi
    echo "[*] Updated $ENV_FILE"
else
    printf 'DISABLE_AUTH=true\nSKIP_TOKEN_VALIDATION=true\n' > "$ENV_FILE"
    echo "[*] Created $ENV_FILE"
fi

echo "[✓] Authentication disabled — unauthenticated requests will be accepted"
